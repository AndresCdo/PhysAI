# PhysAI

**Neuro-Symbolic Framework for Physics Equation Discovery via LLM-Guided Program Synthesis**

PhysAI is an open-source research tool that combines Large Language Models (LLMs) with symbolic computation engines to discover physical equations from experimental data. Unlike traditional "generative AI" approaches, PhysAI uses the LLM as a **hypothesis generator** and Wolfram Mathematica as a **symbolic validator**, creating a rigorous feedback loop for scientific discovery.

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

**Expected output:**
```
Discovery successful!
  Expression: a * Sqrt[length_m]
  R² = 1.0000
  Iterations: 1
```

## Milestone 0: Rediscovering the Pendulum ✅

The first benchmark demonstrates that PhysAI can rediscover the simple pendulum period formula:

**T = 2π√(L/g)**

From a dataset of length vs. period measurements, the system converges to an expression proportional to `√L`.

### Results

| Metric | Value |
|--------|-------|
| Expression | `a * Sqrt[length_m]` |
| R² | 1.0000 |
| Iterations | 1 |
| Fitted `a` | 2.0077 |
| Expected `a` = 2π/√g | 2.0061 |

The system correctly identifies the square root relationship and fits the parameter to within 0.08% of the theoretical value.

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

| Milestone | Description | Status |
|-----------|-------------|--------|
| 0 | Rediscover T = 2π√(L/g) from pendulum data | ✅ Complete |
| 1 | Damped pendulum: A = a × √L × e^(-bt) | ✅ Complete |
| 2 | Projectile motion with drag | 🔲 Pending |
| 3 | Basic quantum mechanics (Schrödinger 1D) | 🔲 Pending |

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