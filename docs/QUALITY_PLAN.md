# Quality Plan — sewpat

> **Status as of 2026-03-07 (v0.4.0):** All debt items resolved. Codebase is fully clean.

---

## Gates (must pass before every merge to `main`)

| Gate | Tool | Command | Threshold |
|------|------|---------|-----------|
| Formatting | ruff-format | `uv run ruff format --check src tests` | zero diffs |
| Lint | ruff | `uv run ruff check src tests` | zero errors |
| Type-check | mypy | `uv run mypy src/sewpat/ --ignore-missing-imports` | **0 errors** ✅ |
| Tests | pytest | `uv run pytest` | 627 passed |
| Coverage | pytest-cov | (bundled with pytest) | ≥ 80 % (currently 91 %) |
| Pre-commit | pre-commit | `uv run pre-commit run --all-files` | all 9 hooks pass |

All gates run automatically in the **GitHub Actions CI pipeline** (`.github/workflows/ci.yml`)
and locally via **pre-commit hooks** (`.pre-commit-config.yaml`).

---

## Pre-commit hooks (9 hooks, all passing)

| Hook | Purpose |
|------|---------|
| `trailing-whitespace` | Strip trailing spaces |
| `end-of-file-fixer` | Ensure every file ends with a newline |
| `check-yaml` | Validate YAML syntax |
| `check-toml` | Validate TOML syntax |
| `check-merge-conflict` | Reject unresolved merge markers |
| `debug-statements` | Reject `pdb` / `breakpoint()` leftovers |
| `ruff` (lint) | Lint + auto-fix on commit |
| `ruff-format` | Format on commit |
| `mypy` *(new in v0.4.0)* | Type-check `src/sewpat/` — **blocks regressions** |

Install once per clone: `uv run pre-commit install`

---

## Ruff rule-set

```toml
select = ["E", "F", "I", "UP", "B", "D", "ANN"]
```

| Code | Ruleset | Covers |
|------|---------|--------|
| `E` | pycodestyle errors | Style errors |
| `F` | pyflakes | Unused imports, undefined names |
| `I` | isort | Import ordering |
| `UP` | pyupgrade | Modernise syntax automatically |
| `B` | flake8-bugbear | Common bugs and design issues |
| `D` | pydocstyle (Google) | Docstring completeness & convention |
| `ANN` | flake8-annotations | Type annotation completeness |

Per-file ignores: `tests/**` and `examples/**` are exempt from `ANN` and `D`.

---

## mypy configuration

```toml
[tool.mypy]
python_version        = "3.14"
strict                = false
ignore_missing_imports = true
warn_return_any       = true
warn_unused_ignores   = true
disallow_untyped_defs = true
check_untyped_defs    = true
no_implicit_optional  = true
```

`tests.*` and `examples.*` are excluded via `[[tool.mypy.overrides]]`.

---

## Tech-debt history — resolved

The following 166 mypy errors were systematically resolved between v0.3.0 and v0.4.0:

| # | Error code | Count | Files | Fix applied |
|---|-----------|-------|-------|-------------|
| 1 | `[union-attr]` | 118 | `pattern.py` | Extracted `outline_geoms: list[Segment\|CubicBezier]` narrowing list; added `assert isinstance` in `_project_dart_notches_to_sa`; fixed Rect fast-path variable collision (`g` → `rect_geom`) |
| 2 | `[operator]` | 30 | `person.py`, `measurements.py` | Extracted `float\|None` fields into local variables with `if x is None: raise` guards before arithmetic |
| 3 | `[no-any-return]` | 13 | `geometry.py`, `fitclass.py` | Wrapped numpy/shapely/svgpathtools returns: `float(...)`, `bool(...)`, `np.array(..., dtype=float)`, `np.asarray(...)` |
| 4 | `[assignment]`/`[arg-type]` | 11 | `blocks.py` | Fixed `_SideSeams.waist_offset: Segment`, `_build_darts → tuple[_Darts, Dart]`, `armscye_back_elem: PatternElement`, `Point(x, y, name=...)` instead of `Point(*coords, name=...)`, `fit_class` None-guard |
| 5 | `[attr-defined]` | 3 | `element.py` | Declared `_dart_ref: Dart\|None` and `_leg_pt: Point\|None` as typed attributes in `PatternElement.__init__` |
| 6 | `[misc]` | 1 | `pattern.py` | Converted `elem_sa`/`elem_center` dict comprehensions to explicit loops with narrowed geometry variable |
| **Total** | | **166 → 0** | 6 files | |

---

## Coverage report (v0.4.0)

```
Name                       Stmts   Miss  Cover
----------------------------------------------
src/sewpat/__init__.py        11      0   100%
src/sewpat/blocks.py         187      5    97%
src/sewpat/element.py         45      1    98%
src/sewpat/fitclass.py        93      0   100%
src/sewpat/geometry.py       963    105    89%
src/sewpat/grids.py           25      0   100%
src/sewpat/markers.py         12      0   100%
src/sewpat/measurements.py   106      3    97%
src/sewpat/pages.py           19      0   100%
src/sewpat/pattern.py        628     43    93%
src/sewpat/person.py         122     17    86%
src/sewpat/render.py         233     49    79%
src/sewpat/style.py           59      7    88%
src/sewpat/units.py            3      0   100%
----------------------------------------------
TOTAL                       2527    236    91%
```

**627 tests · 90.66 % total coverage** (threshold: 80 %)

### Known coverage gaps (backlog)

| File | Miss | Notes |
|------|------|-------|
| `geometry.py` | 105 | Several advanced Bézier offset / intersection paths; rare error branches |
| `render.py` | 49 | PDF export path, multi-page layout, grid rendering |
| `person.py` | 17 | `__repr__` / `__str__` and unused `Person` factory variants |
| `pattern.py` | 43 | `OverlayPart.explode`, `add_grid_notches` edge cases |

---

## What to do when a mypy error appears

1. **`[union-attr]`** — Extract the element into a narrowed local: `local: Segment | CubicBezier = elem.geometry` after an `isinstance` guard.
2. **`[no-any-return]`** — Wrap numpy returns with `np.array(..., dtype=float)` / `np.asarray(...)`, shapely comparisons with `bool(...)`, external library calls with `float(...)`.
3. **`[operator]`** — Extract `float | None` fields into locals and add an explicit `if x is None: raise ValueError(...)` guard.
4. **`[arg-type]`** / **`[assignment]`** — Fix the annotation to match the actual type (check what the constructor / function truly returns).
5. **`[attr-defined]`** — Declare the attribute explicitly in `__init__` with its type.
