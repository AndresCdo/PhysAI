"""Summarise blind-control runs with interval estimates and the key contrasts.

Wilson intervals rather than the normal approximation, because several cells are
expected to sit at exactly 0 or 1 where the normal approximation degenerates to
zero width. Re-scoring reads the recorded output rather than the recorded
verdict, so a corrected detector can be applied to old runs without re-running
inference.
"""

from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

from physai.benchmarks.blind_control.detectors import BY_ID

CONDITION_ORDER = ("A_real_data", "B_real_blind", "C_obf_data", "D_obf_blind")
CONDITION_LABEL = {
    "A_real_data": "A  real names + data",
    "B_real_blind": "B  real names, NO data",
    "C_obf_data": "C  obfuscated + data",
    "D_obf_blind": "D  obfuscated, NO data",
}
CONTRASTS = (
    ("B_real_blind", "D_obf_blind", "strip the semantics (no data)"),
    ("A_real_data", "B_real_blind", "strip the data (real names)"),
    ("C_obf_data", "D_obf_blind", "strip the data (obfuscated)"),
)


def wilson(hits: int, total: int, z: float = 1.96) -> Tuple[float, float]:
    """Wilson score interval, which stays sensible at 0 and at n."""
    if total == 0:
        return (0.0, 0.0)
    proportion = hits / total
    denominator = 1 + z * z / total
    centre = (proportion + z * z / (2 * total)) / denominator
    spread = (
        z
        * math.sqrt(proportion * (1 - proportion) / total + z * z / (4 * total * total))
        / denominator
    )
    return (max(0.0, centre - spread), min(1.0, centre + spread))


def two_proportion_z(
    hits_a: int, total_a: int, hits_b: int, total_b: int
) -> Tuple[float, float]:
    """Pooled two-proportion z test, returning (z, two-sided p)."""
    if total_a == 0 or total_b == 0:
        return (0.0, 1.0)
    pooled = (hits_a + hits_b) / (total_a + total_b)
    error = math.sqrt(pooled * (1 - pooled) * (1 / total_a + 1 / total_b))
    if error == 0:
        return (0.0, 1.0)
    z = (hits_a / total_a - hits_b / total_b) / error
    return (z, 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2)))))


def load(paths: Iterable[Path], rescore: bool = True) -> List[Dict[str, object]]:
    """Read JSONL runs, re-scoring recorded outputs with the current detector."""
    records: List[Dict[str, object]] = []
    for path in paths:
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            if rescore and not record.get("error"):
                obfuscated = record.get(
                    "obfuscated", str(record["condition"]).startswith(("C_", "D_"))
                )
                record["emitted_target_form"] = BY_ID[record["problem"]].matches(
                    record["output"], obfuscated=bool(obfuscated)
                )
            records.append(record)
    return records


def tally(records: Sequence[Dict[str, object]], *keys: str):
    """Count (hits, total) grouped by the given record keys."""
    counts: Dict[Tuple, List[int]] = defaultdict(lambda: [0, 0])
    for record in records:
        bucket = counts[tuple(record[k] for k in keys)]
        bucket[0] += bool(record["emitted_target_form"])
        bucket[1] += 1
    return counts


def _print_condition_table(by_condition, model: str) -> None:
    """One row per condition, with its Wilson interval."""
    print(f"  {'condition':26s} {'hits':>10s} {'rate':>7s}   95% Wilson")
    for condition in CONDITION_ORDER:
        hits, total = by_condition.get((model, condition), [0, 0])
        if not total:
            continue
        low, high = wilson(hits, total)
        print(
            f"  {CONDITION_LABEL[condition]:26s} {hits:4d}/{total:<5d}"
            f" {hits / total:6.1%}   [{low:5.1%}, {high:5.1%}]"
        )


def _print_contrasts(by_condition, model: str) -> None:
    """The three comparisons the factorial design exists to make."""
    print("\n  contrasts:")
    for first, second, question in CONTRASTS:
        hits_a, total_a = by_condition.get((model, first), [0, 0])
        hits_b, total_b = by_condition.get((model, second), [0, 0])
        if not (total_a and total_b):
            continue
        z, p = two_proportion_z(hits_a, total_a, hits_b, total_b)
        verdict = "significant" if p < 0.05 else "not significant"
        print(
            f"    {question:32s} {hits_a / total_a:6.1%} -> "
            f"{hits_b / total_b:6.1%}   z={z:6.2f} p={p:.2e} {verdict}"
        )


def _print_problem_breakdown(by_problem, model: str, problems: Sequence[str]) -> None:
    """Per-problem cells, which is where an aggregate can hide its driver."""
    print("\n  by problem:")
    header = " ".join(f"{c.split('_', 1)[0]:>8s}" for c in CONDITION_ORDER)
    print(f"    {'problem':16s} {header}")
    for problem in problems:
        cells = []
        for condition in CONDITION_ORDER:
            hits, total = by_problem.get((model, problem, condition), [0, 0])
            cells.append(f"{hits}/{total}".rjust(8) if total else "-".rjust(8))
        print(f"    {problem:16s} " + " ".join(cells))
    print()


def report(records: Sequence[Dict[str, object]]) -> None:
    """Print the per-model table, the contrasts, and the per-problem breakdown."""
    errors = sum(1 for r in records if r.get("error"))
    print(f"runs: {len(records)}   errors: {errors}\n")

    by_condition = tally(records, "model", "condition")
    by_problem = tally(records, "model", "problem", "condition")
    problems = sorted({str(r["problem"]) for r in records})

    for model in sorted({str(r["model"]) for r in records}):
        print("=" * 72)
        print(f"MODEL: {model}")
        print("=" * 72)
        _print_condition_table(by_condition, model)
        _print_contrasts(by_condition, model)
        _print_problem_breakdown(by_problem, model, problems)


def main(argv: Sequence[str]) -> int:
    """CLI: analyse.py RESULTS.jsonl [MORE.jsonl ...]"""
    if len(argv) < 2:
        print("usage: analyse.py RESULTS.jsonl [MORE.jsonl ...]")
        return 2
    report(load([Path(p) for p in argv[1:]]))
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv))
