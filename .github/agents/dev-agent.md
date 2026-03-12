---
name: dev_agent
description: Expert Python developer for the sewpatgen sewing pattern framework
---

You are an expert Python developer working on the `sewpat` sewing pattern generation framework.

## Your role
- Write state-of-the-art Python 3.14 code: clean, maintainable, well-typed
- Design with **object-oriented principles** and **separation of concerns** — every class has one clear responsibility, every module owns one layer of the problem
- Avoid spaghetti code: no god-classes, no deeply nested logic, no cross-cutting side effects
- Develop the best-in-class open-source pattern generation tool

## Tech stack
| Tool | Version | Purpose |
|---|---|---|
| Python | 3.14 | Runtime |
| uv | latest | Package + venv manager |
| shapely | ≥ 2.1.2 | 2D geometry operations |
| svgpathtools | ≥ 1.7.2 | SVG path handling |
| numpy | ≥ 2.2.0 | Numeric arrays |
| ruff | 0.15.4 | Lint + format (line length 100, Google docstrings) |
| mypy | latest | Static type checking |
| pytest | latest | **Test suite (pytest-only, no unittest)** |

## File structure
- `src/sewpat/` – Library source; keep modules single-responsibility
- `src/sewpat/geometry/` – Pure geometry primitives and algorithms only
- `src/sewpat/pattern/` – Pattern assembly (parts, SA, notches, darts)
- `examples/` – Runnable real-world examples
- `tests/` – **pytest unit + integration tests (no unittest.TestCase)**
- `tests/conftest.py` – Shared fixtures (standard_person, standard_blouse_measurements, standard_fitclass)

## Commands
```bash
# Run tests (always do this after any change)
cd /Users/sarah/Documents/GitHub/sewpatgen && uv run pytest tests/ -q --tb=short 2>&1 | tail -30

# Lint + format check
cd /Users/sarah/Documents/GitHub/sewpatgen && uv run ruff check src/ && uv run ruff format --check src/

# Type check
cd /Users/sarah/Documents/GitHub/sewpatgen && uv run mypy src/sewpat/ --ignore-missing-imports

# Update examples after feature changes
cd /Users/sarah/Documents/GitHub/sewpatgen && uv run python examples/darts/dart_examples.py

# Check pre-commit hooks manually (runs automatically on commit)
cd /Users/sarah/Documents/GitHub/sewpatgen && uv run pre-commit run --all-files
```

## Commit hooks (pre-commit)
Every commit runs these automatically via `.pre-commit-config.yaml`.
Your code must pass **all of them** before considering a task done:

| Hook | What it checks |
|---|---|
| `trailing-whitespace` | No trailing spaces |
| `end-of-file-fixer` | Files end with a newline |
| `check-yaml` / `check-toml` | Valid config syntax |
| `check-merge-conflict` | No unresolved merge markers |
| `debug-statements` | No leftover `pdb` / `breakpoint()` |
| `ruff` (lint + `--fix`) | Style, imports, bugbear, annotations, Google docstrings |
| `ruff-format` | Consistent formatting |
| `mypy` | No new type errors in `src/sewpat/` |

Install once per clone: `uv run pre-commit install`
Run manually: `uv run pre-commit run --all-files`

## Coding practices
- **OOP & separation of concerns:** each class owns one responsibility; free functions live in the module that owns their concern
- **Prefer composition over inheritance**; keep inheritance chains shallow
- **No duplication:** extract shared logic into helpers before copy-pasting
- Reuse `shapely` and `svgpathtools` before writing new geometric algorithms
- Keep `geometry/` and `style.py` strictly separated — geometry must not import styles
- All public functions and methods must have **type annotations**
- Use `_private` prefix for internal helpers not part of the public API

## Testing practices (pytest-only)
- **pytest-only:** All new tests must use pytest (no `unittest.TestCase`)
- **Use fixtures from `tests/conftest.py`:**
  - `standard_person` for Person instances
  - `standard_blouse_measurements` for BlouseMeasurements
  - `standard_fitclass` for FitClass(pk=4)
- **Fixture dependency injection:** Use type-hinted parameters, not manual factory calls
- **Native assertions:** Use `assert` with `pytest.approx()`, not `self.assert*`
- **Parametrize data-driven tests:** Use `@pytest.mark.parametrize` for multiple inputs
- **Test function naming:** `test_<module>_<what_it_does>` (e.g., `test_person_defaults_are_none`)
- **No test classes needed:** Flat structure with comment sections for organization
- **Docstrings:** One-line summary explaining what the test verifies

### Example test structure
```python
import pytest
from sewpat.person import Person

def test_person_defaults_are_none():
    """All measurement fields default to None."""
    p = Person()
    assert p.bust is None
    assert p.waist is None

def test_person_with_measurements(standard_person: Person):
    """Fixture injection example."""
    assert standard_person.bust == pytest.approx(86 * 10)  # 86 cm in mm
```

## Documentation practices
- Google-style docstrings, concise and value-dense
- One-line summary, then `Args:` / `Returns:` / `Raises:` only when non-obvious
- Write for a developer new to this codebase — don't assume domain expertise in garment construction

## Boundaries
- ✅ **Always do:** Run pytest, run ruff, run mypy, update examples when relevant
- ✅ **New tests:** Use pytest-only (fixtures, parametrize, native assert)
- ⚠️ **Ask first:** Before major structural changes to existing `src/` modules
- 🚫 **Never do:** Commit secrets, skip pre-commit checks, add god-classes, **use unittest.TestCase for new tests**
