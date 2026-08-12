# ADR 0001 — Replace the Wolfram validation path with SymPy, and give free constants declared units

- **Status:** Accepted
- **Date:** 2026-08-12
- **Supersedes:** nothing
- **Related:** [#12](https://github.com/AndresCdo/PhysAI/issues/12), [#13](https://github.com/AndresCdo/PhysAI/issues/13), [#15](https://github.com/AndresCdo/PhysAI/issues/15)

## Context

`WolframEvaluator` uses a Wolfram kernel for exactly three things:

| Method | Wolfram call | What it produces |
|---|---|---|
| `syntax_check` | `SyntaxQ`, `SyntaxLength` | valid / invalid, plus an error position |
| `is_dimensionally_sound` | one `UnitDimensions` | a result the method discards |
| `fit_and_score` | `NonlinearModelFit` | R², adjusted R², AIC, BIC, RMSE |

Nothing else in the project touches Wolfram.

**No kernel exists in this environment or in CI.** `wolframclient` 1.4.0 is
installed and fails:

```
Failed to communicate with kernel: /usr/local/Wolfram/Mathematica/13.3/Executables/WolframKernel
```

`/opt/Wolfram` contains only WolframScript — no kernel binary. The consequence
is that all seven integration tests are skipped, the validation path has never
executed under CI, and reproducing any result requires a paid licence.

Two design questions had to be settled before writing the replacement, because
getting either wrong produces a check that looks like it works.

## Decision 1 — the candidate expression language becomes SymPy syntax

Candidates are currently emitted in Wolfram Language (`a * Sqrt[length_m]`).

**Decision: the prompt asks for SymPy/Python syntax (`a * sqrt(length_m)`).**

Keeping Wolfram syntax after removing the Wolfram engine means writing and
maintaining a parser for a language nothing in the stack speaks. Wolfram's
`f[x]` call syntax also collides with Python subscripting, so the translation
is not a token substitution. SymPy parses its own dialect natively.

### Consequence that must not be missed

The contamination guard added in `test_prompt_contamination.py` matched
Wolfram spellings only. Measured before changing anything — all five
evaluation answers, rewritten in SymPy syntax, passed every forbidden-form
pattern undetected:

```
PASA INADVERTIDA  a * sqrt(length_m)
PASA INADVERTIDA  a * sqrt(length_m) * exp(-b * time_s)
PASA INADVERTIDA  a * velocity_m_s * (1 - exp(-b * time_s))
PASA INADVERTIDA  a * velocity_m_s**2 * sin(2 * angle_deg * pi / 180)
PASA INADVERTIDA  a * quantum_number_n**2 / well_width_nm**2
```

A dialect switch would therefore have silently retired the guard. The guard now
normalises `[`→`(`, `**`→`^` and case before matching, and
`test_guard_catches_known_answers_in_any_dialect` asserts all five answers are
caught in both dialects. That test is a prerequisite of the migration, not a
follow-up.

## Decision 2 — free constants carry declared units

This is the subtle one. A fitted parameter written as a bare `a` has no
declared dimension, and the choice of what that means decides whether the
dimensional check has any power at all.

Three policies were implemented and measured. STRICT and JOKER were run on the
same 12 cases: the five evaluation targets *as the contaminated prompt wrote
them*, two dimensionally-correct rewrites using `g`, and five expressions that
are physically nonsense. DECLARED needs its own case set, because the whole
point is that each constant arrives with a declared dimension — so it was run
on the five targets with units declared, plus the same five nonsense cases.

| Policy | Free constants are… | Nonsense rejected | Can express M1 / M2a / M3 | Judges a leading-constant candidate |
|---|---|---|---|---|
| STRICT | dimensionless | 5 / 5 | **no** | yes |
| JOKER | an unknown unit, propagated | 5 / 5 | yes | **no** |
| **DECLARED** | **declared per problem** | **5 / 5** | **yes** | **yes** |

All three reject every nonsense case, so that column does not discriminate. The
last two columns do, and no policy but DECLARED scores on both. On its own case
set DECLARED made 0 misjudgments in 10 cases.

**Decision: DECLARED.** Each problem specification declares the dimension of
each free constant, as PhySO does via `free_consts_units`.

### Why not the other two

**STRICT** judges soundly but cannot express the physics. It made no
misjudgment on its case set — it correctly rejected all five targets *as the
prompt wrote them*, because `a * Sqrt[length_m]` really is dimensionally
inconsistent with a period, and it accepted both `g`-bearing rewrites. The
problem is what it forbids: `exp(-b * time_s)` forces `b` to be dimensionless,
yet a damping rate has units of T⁻¹. Milestones 1, 2a and 3 become
inexpressible — not because the gate is wrong, but because a
dimensionless-constant policy cannot represent a decay rate, a drag time
constant, or ħ²/8mₑ.

That STRICT rejects the old milestone answers is itself worth recording: those
expressions were never dimensionally valid, which is independent evidence that
they were pattern-matched from the prompt rather than reasoned about.

**JOKER** — the `[♢,♢,♢]` scheme of
[Unit-Aware Genetic Programming](https://arxiv.org/html/2405.18896) — keeps
real structural power: it still rejected `exp(L)`, `sin(t)`, `L + t`, and
expressions whose result dimension is fully known and wrong. But a joker
multiplied into an expression makes the result a joker, so the final
dimension match is unavailable for any candidate with a leading free constant,
which is nearly all of them. It accepted five targets by declining to judge
them.

DECLARED keeps both properties: the transcendental-argument rule and the
addition-compatibility rule still fire, and the final dimension is fully
determined, so a wrong overall dimension is caught. Verified: `a * v0` with
`a:[T⁻¹]` declared is rejected against a length target, and `exp(b * t)` with
`b:[L⁻¹]` is rejected for a dimensioned argument.

### The disclosure this creates

Declaring `a:[T·L^-1/2]` for milestone 0 is prior information. It does not give
away the functional form — many expressions satisfy that signature — but it is
a constraint supplied by the experimenter, and it is the same class of leak as
the prompt contamination this project already had. **Declared constant units
must be recorded in the problem specification and reported as prior
information**, not treated as part of the harness.

## Decision 3 — SymPy over pint and astropy for the dimensional algebra

`sympy.physics.units`, wrapped in a project-owned checker.

- pint and astropy operate on numeric quantities. A candidate expression is all
  free symbols and no numbers, so neither can represent it.
- pint stores dimensional exponents as floats. Rational exponents are a hard
  requirement here — `sqrt(length)` is L^½, and the project's own
  `UnitDimension.power()` raises `ValueError` on exactly this case
  (`physai/core/types.py`, non-integer power).
- astropy requires *angle* units for trigonometric arguments, which would
  reject a legitimate dimensionless argument such as `sin(g*t²/L)`.
- SymPy is needed anyway to replace `syntax_check` and `extract_parameters`, so
  its units module costs no extra dependency.

**Known SymPy gap:** `SI._collect_factor_and_dimension(exp(meter))` returns
`Dimension(length)` rather than raising — it propagates the argument's
dimension into the result instead of rejecting it. The project-owned checker
must walk the tree and enforce dimensionless arguments to transcendental
functions itself. This is the single behaviour SymPy does not provide.

**Security:** SymPy's own documentation states that `sympify()` "uses `eval`,
and thus shouldn't be used on unsanitized input". Candidates come from an LLM,
so parsing must go through `parse_expr` with a restricted `local_dict`
containing only the declared variables, declared constants and an allowlist of
functions, with every free symbol validated against that allowlist before
evaluation.

## Consequences

**Enables:**

- The seven skipped integration tests can run in CI.
- The dimensional guardrail becomes testable, which is a precondition for
  fixing #12.
- Anyone can reproduce the work without a Wolfram licence.

**Costs:**

- `sympy` and `scipy` become runtime dependencies; `wolframclient` is dropped.
- The prompt changes dialect, so every recorded transcript predates it.
- Each benchmark needs its free-constant units declared, which is new metadata
  and a new disclosure obligation.
- `physai/core/types.py::UnitDimension` is superseded. It is exported and
  unit-tested but called from no production path, so removing it costs nothing
  — and leaving it invites a future reader to mistake it for the live
  implementation.

**Not addressed here:** #12, #13 and #15 remain open. This ADR makes them
fixable; it does not fix them.

## References

- Tenachi, Ibata & Diakogiannis, *Deep symbolic regression for physics guided
  by units constraints*, [arXiv:2303.03192](https://arxiv.org/abs/2303.03192),
  ApJ 959:99 — units consistent by construction; free constants declare units
  ([PhySO docs](https://physo.readthedocs.io/en/latest/r_sr.html)).
- *Unit-Aware Genetic Programming for the Development of Empirical Equations*,
  [arXiv:2405.18896](https://arxiv.org/html/2405.18896) — the joker unit and
  its propagation table.
- Udrescu & Tegmark, *AI Feynman*,
  [arXiv:1905.11481](https://arxiv.org/abs/1905.11481) — dimensional analysis
  as the first pipeline stage.
- [SymPy `sympify` documentation](https://docs.sympy.org/latest/modules/core.html)
  — the `eval` warning.
