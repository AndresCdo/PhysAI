# PhysAI

**Neuro-Symbolic Framework for Physics Equation Discovery via LLM-Guided Program Synthesis**

PhysAI is an open-source research project investigating whether a **small,
locally-hosted** language model can contribute usable physical priors to
equation discovery when paired with a symbolic validator. The LLM acts as a
hypothesis generator and a computer algebra system fits and scores each
candidate.

> **Status: research proposal in development. No discovery result is claimed.**
> The architecture is not novel — it is the one introduced by
> [LLM-SR](https://arxiv.org/abs/2404.18400) (Shojaee et al., ICLR 2025) and
> [In-Context Symbolic Regression](https://arxiv.org/abs/2404.19094)
> (Merler et al., ACL SRW 2024). Dimensional analysis as a pruning step dates
> to [AI Feynman](https://arxiv.org/abs/1905.11481) (Udrescu & Tegmark, 2019).
> The open question this project pursues is narrower and is stated under
> [Research agenda](#research-agenda).

## Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                  PhysAI Neuro-Symbolic Engine                  │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌──────────────┐      ┌──────────────┐      ┌─────────────┐  │
│   │   Dataset    │      │    Ollama    │      │  Wolfram    │  │
│   │  (CSV/JSON)  │─────▶│   Granite    │─────▶│  Kernel     │  │
│   │              │      │ (Code Gen)   │      │ (Execution) │  │
│   └──────────────┘      └──────────────┘      └─────────────┘  │
│          │                     │                    │          │
│          │                     │                    │          │
│          ▼                     ▼                    ▼          │
│   ┌──────────────┐      ┌──────────────┐      ┌─────────────┐  │
│   │   Metadata   │      │   Feedback   │◀─────│   Error /   │  │
│   │   Extractor  │      │    Loop      │      │   Result    │  │
│   └──────────────┘      └──────────────┘      └─────────────┘  │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

## Features

- **Neuro-Symbolic AI**: LLM generates hypotheses, symbolic engine validates them
- **Dimensional Analysis**: Automatic unit consistency checking before expensive fitting
- **Guardrails**: Syntax validation, dimensional filtering, and complexity scoring
- **Qualitative Feedback**: LLM receives actionable hints instead of raw residuals
- **Local Inference**: Uses Ollama for privacy and low latency

## Requirements

- Python 3.9+
- [Ollama](https://ollama.ai/) with a code-optimized model (e.g., `granite4:1b`)
- [Wolfram Engine](https://www.wolfram.com/engine/) or Mathematica (requires license)

## Installation

```bash
# Clone the repository
git clone https://github.com/AndresCdo/PhysAI.git
cd PhysAI

# Create virtual environment with uv
uv venv

# Activate virtual environment
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate     # Windows

# Install dependencies
uv pip install -e ".[dev,wolfram]"

# Pull the LLM model
ollama pull granite4:1b

# Start Ollama server (if not running)
ollama serve
```

## Quick Start

```bash
# Activate the virtual environment first
source .venv/bin/activate

# Run the pendulum discovery
.venv/bin/python -c "
from physai import SymbolicResearcher, ResearcherConfig

config = ResearcherConfig(max_iterations=10, r2_threshold=0.95)
with SymbolicResearcher(model='granite4:1b', config=config) as r:
    result = r.discover(
        'physai/data/benchmarks/pendulum_simple.csv',
        target='period_s',
        inputs=['length_m']
    )
    print(result.summary())
"
```

**Output from a previous run, retained only as a format illustration:**
```
Discovery successful!
  Expression: a * Sqrt[length_m]
  R² = 1.0000
  Iterations: 1
```

That run used a prompt containing `a * Sqrt[length_m]` as a worked example, so
it shows the output format and nothing about capability. Do not treat it as an
expected result — see [Milestone 0](#milestone-0-pipeline-integration-check).

## Milestone 0: pipeline integration check

The first benchmark checks that the pipeline runs end to end on the simple
pendulum period law:

**T = 2π√(L/g)**

### This is not a discovery result

Earlier runs reported `a * Sqrt[length_m]` at R² = 1.0000 in a single
iteration. Those numbers are not evidence of discovery, because **the answer
was in the prompt**: seven of the eight few-shot examples in
`physai/prompts/system_prompt.txt` used benchmark column names, and five
reproduced a target expression verbatim, including
`Output: a * Sqrt[length_m]` against the exact columns of
`pendulum_simple.csv`. The prose also stated "Use Sqrt to convert Length to
Time when needed (e.g. T ∝ √L)".

The prompt has been rebuilt from problems in no evaluation set, and
`physai/tests/test_prompt_contamination.py` fails the build if an example
ever reuses a benchmark column or reproduces a target form again.

The task itself is a warm-up, not a benchmark. With `g` fitted, T = 2π√(L/g)
collapses to `T = c · L^0.5`, which is linear in log-log space and recoverable
by ordinary least squares on two columns. It was rediscovered with a global
optimality guarantee by
[Austel et al. (2017)](https://arxiv.org/abs/1710.10720), and
[Schmidt & Lipson (2009)](https://doi.org/10.1126/science.1165893) recovered
full Lagrangians of a chaotic double pendulum from raw motion data — a
strictly harder problem.

**No re-run has been performed against the decontaminated prompt.** Until one
is, this repository reports no discovery numbers at all.

### Run the Test

```bash
source .venv/bin/activate
.venv/bin/python -m pytest physai/tests/test_milestone_0.py -v -k "not Integration"
```

## Project Structure

```
physai/
├── core/                      # Core Neuro-Symbolic engine
│   ├── researcher.py          # SymbolicResearcher (orchestrator)
│   ├── llm_interface.py       # OllamaInterface (hypothesis generation)
│   ├── wolfram_evaluator.py   # WolframEvaluator (validation & fitting)
│   ├── types.py               # Data types (Variable, FitResult, etc.)
│   └── constants.py           # Physical constants and unit definitions
├── utils/                     # Utilities
│   ├── serialization.py       # Data serialization for Wolfram
│   ├── feedback.py            # LLM feedback generation
│   └── parsing.py             # Expression parsing and validation
├── prompts/                   # LLM prompt templates
│   └── system_prompt.txt      # Few-shot prompt for equation generation
├── data/                      # Datasets
│   └── benchmarks/            # Benchmark datasets for testing
├── tests/                     # Test suite
│   └── test_milestone_0.py    # Integration tests
└── algorithms/                # Legacy components (deprecated)
```

## Research Objective

**"Can a small, local Large Language Model effectively guide a symbolic computation engine to discover physical laws from noisy experimental data?"**

This project explores the hypothesis that neuro-symbolic AI can automate symbolic regression for physics discovery, with potential applications in:

- Automated analysis of experimental data
- Discovery of empirical relationships in complex systems
- Educational tools for physics students

## Troubleshooting

### Ollama Connection Failed

```bash
# Ensure Ollama server is running
ollama serve

# Check if model is installed
ollama list
ollama pull granite4:1b
```

### Wolfram Connection Failed

```bash
# Install wolframclient
uv pip install wolframclient

# Verify Wolfram Engine is installed
which wolframscript
```

### Fitting Failed to Converge

This is often caused by variable names containing underscores (e.g., `length_m`). The `WolframEvaluator` automatically handles this by converting `length_m` → `lengthM` before evaluation.

For more details, see [AGENTS.md](AGENTS.md) - Technical Notes section.

## Milestones

Every milestone below was previously marked complete on the strength of runs
whose prompt contained the answer. They are integration checks — evidence that
the pipeline is wired correctly — and all of them need re-running against the
decontaminated prompt before any number is reported.

| Milestone | Description | Status |
|-----------|-------------|--------|
| 0 | T = 2π√(L/g) from pendulum data | ⚠️ Needs re-run (prompt was contaminated) |
| 1 | Damped pendulum: A = a × √L × e^(-bt) | ⚠️ Needs re-run (prompt was contaminated) |
| 2a | Horizontal drag: x = a × v₀ × (1 - e^(-bt)) | ⚠️ Needs re-run; dataset defect ([#10](https://github.com/AndresCdo/PhysAI/issues/10)) |
| 2b | 2D projectile: R = a × v₀² × sin(2θ) | ⚠️ Needs re-run (prompt was contaminated) |
| 3 | 1D quantum well: E = a × n² / L² | ⚠️ Needs re-run (prompt was contaminated) |

### Known defects in the validation path

Three components that should have constrained the search do not, so none of
them could have influenced the results above:

| Issue | Defect |
|---|---|
| [#12](https://github.com/AndresCdo/PhysAI/issues/12) | The dimensional guardrail never compares against `target_unit`, and returns "sound" on any kernel exception |
| [#13](https://github.com/AndresCdo/PhysAI/issues/13) | The refinement loop computes feedback and never passes it to the generator |
| [#15](https://github.com/AndresCdo/PhysAI/issues/15) | The pre-flight validity gate computes unrecognised Wolfram heads and discards the result |
| [#10](https://github.com/AndresCdo/PhysAI/issues/10) | `projectile_horizontal_drag.csv` deviates up to 33.8% from its own documented model |

## Research agenda

The question worth asking is not whether this pipeline recovers textbook
equations — a two-column least-squares fit does that. It is:

**Does a small locally-hosted model contribute any usable physical prior, or
does the symbolic validator do all the work?**

Answering it requires controls this repository does not yet have:

1. **Decontaminated prompt** — done; enforced by a test.
2. **Blind-data control** — run the system with the problem description and
   variable names but no data rows. If it still emits the target, the data,
   the fitter and the CAS contributed nothing.
3. **Component ablation** — disable the dimensional check, the syntax gate and
   the feedback loop independently and measure the difference. Given #12, #13
   and #15, the current expectation is no difference at all.
4. **Published benchmark** — the five hand-made CSVs here hold 17 to 49 rows
   and are not reproducible from the repository's own generator. Evaluation
   belongs on an established set with an established protocol.
5. **Seeded, repeated runs** — a single run is not a measurement. Model tag and
   digest, quantisation, decoding parameters and seed must be recorded.

A negative answer is a publishable result and the most likely one.

## Contributing

PhysAI is a research project in active development. Contributions are welcome:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Citation

If you use PhysAI in your research, please cite:

```bibtex
@software{physai2026,
  title = {PhysAI: Neuro-Symbolic Framework for Physics Equation Discovery},
  author = {Andres Caicedo},
  year = {2026},
  url = {https://github.com/AndresCdo/PhysAI}
}
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.