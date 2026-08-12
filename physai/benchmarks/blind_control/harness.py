"""Runner for the blind-data control.

A 2x2 factorial over {variable names} x {data}:

    A  real names  + data      the system's normal operating condition
    B  real names  + NO data   if the target still appears, the data, the
                               fitter and the CAS are inert
    C  obfuscated  + data      semantics stripped; can it fit at all?
    D  obfuscated  + NO data   floor; anything here is guessing

Obfuscation strips the physics word and keeps the declared unit, because units
are prior information the system is designed to use (ADR 0001). `length_m
[Length]` becomes `var_a [Length]`: the hint that this is a pendulum is
removed, the dimensional constraint is not.

Every run's full output is written to JSONL so results can be re-scored without
spending inference again. That mattered: the first detector both under-counted
and produced false positives, and the traces made re-scoring free.
"""

from __future__ import annotations

import csv
import json
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Tuple

from physai.benchmarks.blind_control.detectors import PROBLEMS, Problem

PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "system_prompt.txt"
BENCHMARK_DIR = Path(__file__).resolve().parents[2] / "data" / "benchmarks"
DEFAULT_ENDPOINT = "http://localhost:11434/api/chat"

CONDITIONS: Tuple[Tuple[str, bool, bool], ...] = (
    ("A_real_data", False, True),
    ("B_real_blind", False, False),
    ("C_obf_data", True, True),
    ("D_obf_blind", True, False),
)


@dataclass(frozen=True)
class RunConfig:
    """Everything that must be recorded for a run to be reproducible."""

    model: str
    samples: int
    temperature: float = 0.3
    max_tokens: int = 128
    endpoint: str = DEFAULT_ENDPOINT
    timeout: int = 120
    data_rows: int = 12
    think: bool = False


def render_data(problem: Problem, mapping: Optional[Dict[str, str]], rows: int) -> str:
    """Render an evenly-spaced sample of the dataset as the prompt shows it."""
    with open(BENCHMARK_DIR / problem.dataset, encoding="utf-8") as handle:
        table = list(csv.reader(handle))
    header, body = table[0], table[1:]
    if mapping:
        header = [mapping.get(column, column) for column in header]
    step = max(1, len(body) // rows)
    sample = body[::step][:rows]
    return "\n".join([", ".join(header)] + [", ".join(row) for row in sample])


def build_user_prompt(
    problem: Problem, obfuscated: bool, with_data: bool, data_rows: int
) -> str:
    """Compose the user turn for one condition."""
    roles = problem.variable_map(obfuscated)
    column_map = None
    if obfuscated:
        column_map = {problem.target[0]: roles["target"]}
        for index, (name, _) in enumerate(problem.inputs):
            column_map[name] = roles[f"in{index}"]

    inputs = ", ".join(
        f"{roles[f'in{i}']} [{unit}]" for i, (_, unit) in enumerate(problem.inputs)
    )
    parts = [f"Target: {roles['target']} [{problem.target[1]}]", f"Inputs: {inputs}"]
    if with_data:
        parts += ["", "Data:", render_data(problem, column_map, data_rows)]
    parts += ["", "Output:"]
    return "\n".join(parts)


def query(config: RunConfig, system: str, user: str) -> str:
    """One chat completion. Raises on transport failure; the caller records it."""
    payload = json.dumps(
        {
            "model": config.model,
            "stream": False,
            "options": {
                "temperature": config.temperature,
                "num_predict": config.max_tokens,
            },
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
    ).encode()
    request = urllib.request.Request(
        config.endpoint, payload, {"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(request, timeout=config.timeout) as response:
        body = json.loads(response.read())
    return body.get("message", {}).get("content", "")


def run(config: RunConfig, sink: Path) -> Iterator[Tuple[str, str, int, int]]:
    """Execute the full matrix, appending one JSON record per run.

    Yields (problem_id, condition, hits, samples) as each cell completes.
    """
    system = PROMPT_PATH.read_text(encoding="utf-8")
    with open(sink, "a", encoding="utf-8") as handle:
        for problem in PROBLEMS:
            for label, obfuscated, with_data in CONDITIONS:
                user = build_user_prompt(
                    problem, obfuscated, with_data, config.data_rows
                )
                hits = 0
                for index in range(config.samples):
                    record = _one_run(
                        config,
                        problem,
                        obfuscated=obfuscated,
                        system=system,
                        user=user,
                        index=index,
                    )
                    record["condition"] = label
                    hits += record["emitted_target_form"]
                    handle.write(json.dumps(record) + "\n")
                    handle.flush()
                yield (problem.problem_id, label, hits, config.samples)


def _one_run(
    config: RunConfig,
    problem: Problem,
    *,
    obfuscated: bool,
    system: str,
    user: str,
    index: int,
) -> Dict[str, object]:
    """Execute and score a single sample, recording the failure if there is one."""
    started = time.perf_counter()
    try:
        output, error = query(config, system, user), None
    except (OSError, TimeoutError, ValueError) as exc:
        output, error = "", f"{type(exc).__name__}: {exc}"
    return {
        "model": config.model,
        "problem": problem.problem_id,
        "run": index,
        "temperature": config.temperature,
        "obfuscated": obfuscated,
        "elapsed_s": round(time.perf_counter() - started, 3),
        "emitted_target_form": (
            bool(problem.matches(output, obfuscated=obfuscated)) if not error else False
        ),
        "recited_target_law": (
            bool(problem.recites(output, obfuscated=obfuscated)) if not error else False
        ),
        "error": error,
        "output": output.strip()[:400],
    }


def main(argv: List[str]) -> int:
    """CLI: harness.py MODEL SAMPLES [TEMPERATURE] [OUTPUT.jsonl]"""
    if len(argv) < 3:
        print("usage: harness.py MODEL SAMPLES [TEMPERATURE] [OUTPUT.jsonl]")
        return 2
    config = RunConfig(
        model=argv[1],
        samples=int(argv[2]),
        temperature=float(argv[3]) if len(argv) > 3 else 0.3,
    )
    sink = Path(argv[4]) if len(argv) > 4 else Path(f"blind_{config.model}.jsonl")
    started = time.perf_counter()
    for problem_id, condition, hits, total in run(config, sink):
        print(f"  {problem_id:14s} {condition:13s} {hits:3d}/{total}", flush=True)
    print(f"\n{config.model}: {time.perf_counter() - started:.0f}s -> {sink}")
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv))
