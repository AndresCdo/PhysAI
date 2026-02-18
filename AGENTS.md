# AGENTS.md - Development Guide for PhysAI

This document provides comprehensive guidance for AI agents and developers working on the PhysAI codebase.

## Project Overview

PhysAI is a **Neuro-Symbolic Framework for Physics Equation Discovery** that combines:

- **LLM (Ollama)**: Generates hypotheses as Wolfram Language expressions
- **Symbolic Engine (Wolfram)**: Validates, fits, and scores hypotheses against data
- **Feedback Loop**: Qualitative feedback guides the LLM toward better hypotheses

The goal is to discover physical equations from experimental data through an iterative refinement process.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    PhysAI Neuro-Symbolic Engine                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Dataset ──▶ SymbolicResearcher ──▶ OllamaInterface ──▶ LLM     │
│                    │                                              │
│                    ▼                                              │
│             WolframEvaluator                                      │
│                    │                                              │
│                    ▼                                              │
│              FitResult ──▶ Feedback ──▶ (loop)                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Core Components

| Component | File | Responsibility |
|-----------|------|----------------|
| `SymbolicResearcher` | `physai/core/researcher.py` | Orchestrates discovery loop, manages history |
| `OllamaInterface` | `physai/core/llm_interface.py` | Generates Wolfram expressions via Ollama API |
| `WolframEvaluator` | `physai/core/wolfram_evaluator.py` | Validates syntax, dimensions, fits expressions |
| `Variable`, `FitResult`, `DiscoveryResult` | `physai/core/types.py` | Data structures for the pipeline |
| `extract_parameters()` | `physai/utils/parsing.py` | Extracts free parameters from expressions |
| `extract_wolfram_expression()` | `physai/utils/feedback.py` | Cleans LLM output to extract code |

## Development Setup

### Prerequisites

- Python 3.9+
- [Ollama](https://ollama.ai/) installed and running
- [Wolfram Engine](https://www.wolfram.com/engine/) or Mathematica (requires license)

### Installation

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

### Verify Installation

```bash
# Check Ollama connection
.venv/bin/python -c "
from physai.core.llm_interface import OllamaInterface
interface = OllamaInterface(model='granite4:1b')
print('Ollama connected:', interface.check_connection())
"

# Check Wolfram connection
.venv/bin/python -c "
from physai.core.wolfram_evaluator import WolframEvaluator
with WolframEvaluator() as ev:
    print('Wolfram connected:', ev._session is not None)
"
```

## Code Conventions

### Python Style

- **Type hints**: Required for all function signatures
- **Docstrings**: Google-style format for all public functions and classes
- **Imports**: Standard library first, then third-party, then local
- **Line length**: 100 characters maximum
- **No comments in code** unless explicitly requested

### Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Classes | PascalCase | `SymbolicResearcher` |
| Functions | snake_case | `generate_hypothesis()` |
| Variables | snake_case | `adjusted_r2` |
| Constants | UPPER_SNAKE | `RESERVED_CONSTANTS` |
| Private methods | _leading_underscore | `_validate_syntax()` |

### File Structure

```
physai/
├── core/                      # Core engine (no external dependencies in __init__)
│   ├── __init__.py
│   ├── researcher.py          # Main orchestrator
│   ├── llm_interface.py       # Ollama wrapper
│   ├── wolfram_evaluator.py   # Wolfram wrapper
│   ├── types.py               # Dataclasses
│   └── constants.py           # Physical constants
├── utils/                     # Pure utilities
│   ├── serialization.py       # Data formatting
│   ├── feedback.py            # LLM feedback generation
│   └── parsing.py             # Expression parsing
├── prompts/                   # LLM prompt templates
│   └── system_prompt.txt      # Few-shot prompt
├── data/benchmarks/           # Test datasets
└── tests/                     # Test suite
```

## Testing

### Running Tests

```bash
# Run all unit tests (doesn't require Ollama/Wolfram)
.venv/bin/python -c "
from physai.tests.test_milestone_0 import *
# Tests run automatically
"

# Run full integration test (requires Ollama + Wolfram)
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

### Test Categories

| Category | Marker | Description |
|----------|--------|-------------|
| Unit tests | None | No external dependencies |
| Integration | `@pytest.mark.skip` | Requires Ollama/Wolfram |
| Benchmark | `test_milestone_*` | End-to-end discovery tests |

## Technical Notes

### CRITICAL: Wolfram Underscore Bug

**Problem**: Variable names containing underscores (e.g., `length_m`, `period_s`) are interpreted by Wolfram Language as pattern objects (`Pattern[name, Blank[type]]`), causing `NonlinearModelFit` to fail silently or produce incorrect results.

**Example**:
```wolfram
(* This FAILS - _ is interpreted as Blank *)
NonlinearModelFit[data, a * Sqrt[length_m], {{a, 1}}, {length_m}]
(* Error: length_m becomes Pattern[length, Blank[m]] *)
```

**Solution**: `WolframEvaluator.fit_and_score()` automatically sanitizes variable names:

```python
# In wolfram_evaluator.py
def sanitize_name(name: str) -> str:
    parts = name.split('_')
    if len(parts) == 1:
        return name
    return parts[0] + ''.join(p.capitalize() for p in parts[1:])

# Examples:
# length_m -> lengthM
# period_s -> periodS
# accel_m_s2 -> accelMS2
```

**Important**: Never bypass this sanitization. Variable names with underscores will break Wolfram evaluation.

### Variable Name Validation

The system validates that LLM-generated expressions use exact variable names:

```python
# In researcher.py
def _validate_variable_names(self, expression: str, input_variables: List[str]) -> tuple:
    for var in input_variables:
        pattern = r'\b' + re.escape(var) + r'\b'
        if not re.search(pattern, expression):
            return False, f"Variable '{var}' not found in expression"
    return True, ""
```

This prevents the LLM from abbreviating variable names (e.g., using `length` instead of `length_m`).

### Data Format for NonlinearModelFit

Wolfram's `NonlinearModelFit` expects data in the format `{x1, x2, ..., y}` where:
- `x1, x2, ...` are input variables (in order)
- `y` is the target variable

```python
# CORRECT: inputs first, target last
wolfram_data = data_to_wolfram_string(df[input_vars + [target]])

# WRONG: target first
wolfram_data = data_to_wolfram_string(df[[target] + input_vars])
```

### Reserved Constants

The following identifiers are excluded from parameter fitting:

| Constant | Value | Description |
|----------|-------|-------------|
| `g` | 9.81 m/s² | Gravitational acceleration |
| `c` | 299792458 m/s | Speed of light |
| `pi` | π | Pi constant |
| `e` | e | Euler's number |
| `h` | 6.626e-34 J·s | Planck constant |
| `k` | 1.381e-23 J/K | Boltzmann constant |

See `physai/core/constants.py` for the complete list.

## Troubleshooting

### Ollama Connection Failed

**Error**: `Ollama: NOT CONNECTED`

**Solutions**:
1. Ensure Ollama server is running: `ollama serve`
2. Check if the model is pulled: `ollama list`
3. Pull the model if missing: `ollama pull granite4:1b`
4. Verify the API endpoint: `curl http://localhost:11434/api/tags`

### Wolfram Connection Failed

**Error**: `Failed to connect to Wolfram: wolframclient is required`

**Solutions**:
1. Install wolframclient: `uv pip install wolframclient`
2. Verify Wolfram Engine is installed: `which wolframscript` or `WolframKernel`
3. Check license validity
4. On Linux, ensure `WolframKernel` is in PATH or set `kernel_path` in `WolframEvaluator`

### Fitting Failed to Converge

**Error**: `Fitting failed: Fitting failed to converge`

**Possible causes**:
1. **Underscore bug**: Variable names contain `_` (see Technical Notes above)
2. **Wrong data order**: Target column not last in data array
3. **Missing parameters**: Expression has no free parameters to fit
4. **Bad initial guess**: Try different initial parameter values

### Expression Not Found in LLM Output

**Error**: `Could not extract expression from output`

**Solutions**:
1. Check `extract_wolfram_expression()` in `utils/feedback.py`
2. LLM may be outputting markdown or conversational text
3. Add more examples to the few-shot prompt in `prompts/system_prompt.txt`

### Dimensional Mismatch

**Error**: `Dimension error: [Length] != [Time]`

**Solutions**:
1. The expression doesn't produce the correct units
2. Use `Sqrt` to convert Length → Time (T ∝ √L)
3. Use multiplication/division to adjust units
4. Check `PHYSICAL_UNITS` in `constants.py` for unit definitions

## Commands Reference

### Environment Setup

```bash
uv venv                           # Create virtual environment
source .venv/bin/activate         # Activate (Linux/macOS)
uv pip install -e ".[dev,wolfram]" # Install with all extras
```

### Running Discovery

```bash
# Basic discovery
.venv/bin/python -c "
from physai import SymbolicResearcher
with SymbolicResearcher(model='granite4:1b') as r:
    result = r.discover('data.csv', target='y', inputs=['x'])
    print(result.summary())
"

# With custom config
.venv/bin/python -c "
from physai import SymbolicResearcher, ResearcherConfig
config = ResearcherConfig(max_iterations=20, r2_threshold=0.99)
with SymbolicResearcher(model='granite4:1b', config=config) as r:
    result = r.discover('data.csv', target='y', inputs=['x'])
    print(result.summary())
"
```

### Generating Benchmark Data

```bash
.venv/bin/python -m physai.data.benchmarks.generate_benchmarks
```

### Ollama Commands

```bash
ollama serve                      # Start Ollama server
ollama pull granite4:1b           # Download model
ollama list                       # List installed models
ollama run granite4:1b            # Interactive chat with model
```

## Milestones

| Milestone | Description | Status |
|-----------|-------------|--------|
| 0 | Rediscover T = 2π√(L/g) from pendulum data | ✅ Complete |
| 1 | Damped pendulum: A = a × √L × e^(-bt) | ✅ Complete |
| 2a | Horizontal drag: x = a × v₀ × (1 - e^(-bt)) | ✅ Complete |
| 2b | 2D projectile: R = a × v₀² × sin(2θ) | ✅ Complete |
| 3 | Basic quantum mechanics (Schrödinger 1D) | 🔲 Pending |

## File Modification Checklist

When modifying the codebase, ensure:

- [ ] Type hints are added to all new functions
- [ ] Docstrings follow Google-style format
- [ ] No code comments unless explicitly required
- [ ] Variable names with underscores are handled correctly for Wolfram
- [ ] Tests are updated for new functionality
- [ ] `requirements.txt` is updated if new dependencies are added
- [ ] This AGENTS.md is updated for significant architectural changes
