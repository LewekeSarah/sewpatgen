# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

---

## [0.6.0] — 2026-04-07

### Added

- **`WideSleeveBlock`** — complete wide sleeve pattern block assembled from armhole geometry.
  Exposes key points (`cap_crown`, `cap_left`, `cap_right`, `hem_left`, `hem_right`),
  construction geometry (`cap_left_slope`, `cap_right_slope`, `cap_left_curve`,
  `cap_right_curve`, `left_side`, `right_side`, `hem`, `hem_left_curve`,
  `hem_right_curve`), and optional features (`slit`, `pleats`, `cuff`).
  Built via `WideSleeveBlock.from_armhole(armhole, config, seam_allowance=…)`.

- **`CuffBlock`** — rectangular cuff pattern piece with fold line, optional underlap /
  overlap extensions, and button / buttonhole marks.
  Built via `CuffBlock.from_sleeve_config(config, seam_allowance=…)`;
  returns `None` when no `CuffConfig` is present.

- **`WideSleeveGrid`** — construction grid for the wide sleeve (cap line, hem line,
  sleeve-length line, left / right / centre verticals).
  Built via `WideSleeveGrid.from_armhole(armhole, config)`.

- **`SleeveArmhole`** — derives back / front armscye heights and total circumference
  from a finished `TopBlock`.
  Built via `SleeveArmhole.from_block(block)`.

- **`SleeveConfig`** — garment-design choices independent of body measurements:
  `sleeve_length`, `ease`, `cap_offset`, `slit_height`, `pleat_config`,
  `cuff_config`.  Validates `slit_height ≥ 0`.

- **`SleeveConstructionMeasures`** — complete set of derived construction measures
  (`cap_height`, `sleeve_width`, `sleeve_hem_width`, …).
  `from_armhole()` supports WIDE and NARROW types;
  raises `ValueError` when geometry is infeasible or required measurements are absent.

- **`SleeveBlockConfig`** — construction constants for cap and width formulas,
  with four named presets: `WIDE`, `NARROW_BLOUSE`, `NARROW_JACKET`, `STRETCH`.

- **`SleeveType`** / **`SleeveMode`** — enums that classify the sleeve construction
  variant (wide vs. narrow) and the precise construction mode.

- **`ButtonConfig`** — button and buttonhole placement: `num_buttons` (0–2),
  `button_diameter`, `margin`, `buttonhole_ease`.  Full validation with
  descriptive error messages.

- **`CuffConfig`** — cuff dimensions: `length`, `width`, `underlap`, `overlap`,
  optional `button_config`.  Validates all fields ≥ 0 and `length` / `width` > 0.

- **`SleeveMeasurements`** — body measurements required for narrow sleeve
  construction (`upper_arm_circumference`, …).

- **`CuffBlockConfig`** / **`WideSleeveBlockConfig`** — construction constants
  for the cuff and wide sleeve blocks respectively; each ships a `STANDARD` /
  `WIDE` named preset.

- **`PleatConfig`** — configuration for hem pleats: `depth`, `num_pleats`, `spacing`.

- **`Pleat`** — geometry of a single rendered pleat on the hem line,
  including fold lines, roof markers, and arrow marks.  Applied to a `PatternPart`
  via `Pleat.apply_to(part)`.

- **New `CubicBezier` helpers** — `arc_length_from_end(point)` computes the arc
  length from an arbitrary point to the end of the curve.

- **New geometry functions** — `fit_cubic_bezier(…)` and `fit_cubic_bezier_free(…)`
  fit cubic Bézier curves to a set of sample points; `split_bezier_seam_fn(…)`
  splits a curve at a given seam length.

- **New style constants** — `STYLE_SLIT`, `STYLE_PLEAT_FOLD`, `STYLE_PLEAT_ARROW`,
  `STYLE_BUTTON`, `STYLE_BUTTONHOLE` added to `sewpat.style` and exported from
  the top-level `sewpat` namespace (`STYLE_BUTTON`, `STYLE_BUTTONHOLE`).

- **Updated example** — `examples/women/top_casual.py` extended with a full
  wide sleeve and cuff construction demonstrating the new API.

---

## [0.5.0] — 2026-03-21

### Added

- **`Pattern.validate_seam_pairs()`** — cross-part seam length validation.
  Measures the total arc length of all `is_outline` elements carrying a given
  `role` tag on each of two parts and reports whether the difference is within
  tolerance.

  ```python
  result = pattern.validate_seam_pairs([
      (Part.BLOCK_BACK, "side",     Part.BLOCK_FRONT, "side"),              # ±2 mm (default)
      (Part.BLOCK_BACK, "shoulder", Part.BLOCK_FRONT, "shoulder", 13.0, 10.0),  # 10–13 mm
  ])
  assert result.all_ok
  ```

  An optional 5th tuple element sets a per-pair upper tolerance, overriding the
  global `tolerance_mm` keyword argument for that pair only.  An optional 6th
  element adds a **signed lower bound** on `length_a − length_b`, enabling
  range checks (e.g. shoulder ease must be between 10 mm and 13 mm).

- **`SeamPairResult`** dataclass — result for one seam pair: `part_a`, `role_a`,
  `length_a`, `part_b`, `role_b`, `length_b`, `delta_mm`, `tolerance_mm`, `ok`,
  **`min_delta_mm`** (optional signed lower bound, `None` when not set).

- **`SeamValidationResult`** dataclass — aggregated result with `pairs`,
  `all_ok`, `tolerance_mm`, and a human-readable `__str__` showing ✓/✗ per pair.

- **`SeamPairSpec`** type alias — documents the `(part, role, part, role[, tol[, min_delta]])`
  tuple shape accepted by `validate_seam_pairs`; exported from `sewpat` and
  `sewpat.pattern` for use in caller type annotations.  The optional 6th element
  `min_delta` is a **signed lower bound** on `length_a − length_b`, enabling
  range checks such as *shoulder ease must be 10–13 mm*:
  ```python
  (Part.BACK, "shoulder", Part.FRONT, "shoulder", 13.0, 10.0)
  ```

- **`tests/pattern/conftest.py`** — added `_make_side_part()` and
  `_simple_pattern()` shared helpers for seam-validation unit tests.

- **`BlockConfig`** and **`GridConfig`** added to the public `sewpat` namespace
  (`__all__`) and `from .grids import GridConfig` added to `__init__.py`.

### Changed — Casual top block hem & side seam (`BlockConfig.CASUAL`)

- **Back hem** — replaced the horizontal `Segment` with a straight `Segment`
  orthogonal to the center-back edge.  Start and end are found by intersecting
  a ray along the CB right-hand normal from `hem_center_back_outline` with a ray
  along the CB direction from `hip_side_back`.  Guarantees hem ⊥ CB and side ‖ CB.

- **Back side-hem (`side_hip_hem_back`)** — now runs along the CB direction from
  `hip_side_back` to the hem endpoint, arriving exactly orthogonal to the hem.

- **Back hip curve (`side_waist_hip_back`)** — rebuilt inside the casual branch
  with `p2` pulled back along the reversed CB direction (`p2 ≠ p3`) so the Bézier
  end-tangent is non-zero and aligned with `side_hip_hem_back`.  Eliminates the
  degenerate SA miter gap that appeared when seam allowance was added.

- **Front side-hem** — cropped to match the total back side length
  (`side_waist_hip_back.length + side_hip_hem_back.length`) using `seam_length()`
  and `Segment.point_at_length()`.

- **Front hem** — replaced the straight `Segment` with a near-straight
  `CubicBezier` departing horizontally from the CF hem point and arriving at the
  cropped side end via a control point at `intersect(grid.hem, grid.bust_point)`.

- **`_SideSeams.hem_side_to_center_back` / `hem_side_to_center_front`** — field
  types widened from `Segment` to `Segment | CubicBezier`.

### Changed — `blocks.py` refactored into three modules

The monolithic 1 300-line `blocks.py` has been split into three focused files:

| File | Lines | Responsibility |
|---|---|---|
| `blocks.py` | ~330 | Public API only: `BlockConfig`, `TopBlockBack`, `TopBlockFront`, `TopBlock` |
| `_blocks_geometry.py` | ~800 | Internal dataclasses and all `_build_*` geometry builders |
| `_blocks_assembly.py` | ~150 | `_assemble_back_part`, `_assemble_front_part`, role maps |

`_build_side_seams` was further decomposed into:

- **`_build_hip_curves()`** — hip outset points and waist-to-hip Béziers (shared).
- **`_build_casual_back_hem()`** — casual back hem, side-hem, and hip curve end-tangent fix.
- **`_build_casual_front_hem()`** — casual front side crop and hem Bézier.

### Fixed

- **`tests/test_render.py`** — corrected `part.add(bez)` to `part.append(bez)`;
  `PatternPart` has no `add` method (`AttributeError`).

- **SA gap at back hip-to-hem join** — `side_waist_hip_back` previously ended with
  `p2 == p3` (zero end-tangent), causing `edge_tangent()` to fall back to a zero
  vector and `miter_corner()` to produce a degenerate jump in the SA polygon.
  Fixed by giving the Bézier a non-degenerate `p2` aligned to the CB direction.


- **`__init__.py` ruff `F401`** — `BlockConfig` was imported but absent from
  `__all__`; added `BlockConfig` and `GridConfig` to `__all__` and imports.

---

## [0.4.0] — 2026-03-07

### Added

- **`GeometryType`** union alias in `sewpat.element` (and re-exported from `sewpat`)
  — the canonical type for all geometry objects accepted by `PatternElement` and
  `PatternPart.append()`.  Replaces the ad-hoc inline union in `PatternElement.__init__`.
- **`STYLE_STITCH_BEVEL`** added to the public `sewpat` namespace (`__all__`).
- **`TopBlock`** — `fit_class=None` now falls back to `FitClass(pk=4)` instead of
  raising a `TypeError` at runtime.
- **`docs/QUALITY_PLAN.md`** — living document describing all quality gates,
  pre-commit hooks, mypy configuration, tech-debt history, and coverage report.

### Changed

- **`pyproject.toml`** — version bump to `0.4.0`; added `keywords`, `[project.urls]`,
  expanded `classifiers` (including `"Typing :: Typed"`); updated runtime dependency
  lower-bounds to match locked versions (`numpy>=2.2.0`, `pandas>=2.2.0`,
  `shapely>=2.1.2`); added `[tool.uv] package = true`.
- **`PatternPart.append()`** — parameter `geometry` is now typed as `GeometryType`
  instead of `object`, eliminating the `# type: ignore[arg-type]` suppression.
- **`_build_darts()`** in `blocks.py` — return type corrected to
  `tuple[_Darts, Dart]`.
- **`_SideSeams.waist_offset`** — field type corrected from `Line` to `Segment`.
- **`TopGrid.from_measurements()`** — replaced `# type: ignore[return-value]` in
  the inner `seg()` helper with `assert isinstance(geom, Segment)`.

### Fixed — mypy (166 → 0 errors)

All pre-existing type errors resolved across 6 files.  See `docs/QUALITY_PLAN.md`
for the full breakdown by error code.

### Infrastructure

- **pre-commit hook for mypy** added to `.pre-commit-config.yaml` — every local
  commit now runs `mypy src/sewpat/` and blocks on regressions.
- **CI pipeline** (`.github/workflows/ci.yml`) — added `pre-commit run --all-files`
  step between ruff and mypy.
- **`grids.py`** — resolved outstanding `TODO` comment (`front_length vs VL2`)
  with an explanatory inline comment.

---

## [0.3.0] — 2026-03-03

### Added — Dart (Abnäher) support

#### Geometry (`sewpat.Dart`, `sewpat.DartType`)

- New `Dart` class representing dart geometry (mouth endpoints `leg_a`/`leg_b`,
  mouth centre `center`, tip) with both **triangle** (seam-edge) and **rhombus**
  (inner-panel) types via `DartType`.
- Five factory class methods:
  - `Dart.from_edge_at_t(edge, t, width, depth)` — place orthogonally on an edge at parameter *t*
  - `Dart.from_edge_at_point(edge, point, width, depth)` — anchor to a named landmark
  - `Dart.from_edge_free_tip(edge, t, width, reference_point, tip_shortfall)` — tip aimed at bust point
  - `Dart.from_tip_center_width(tip, center, width)` — explicit tip + mouth construction
  - `Dart.from_tip_and_legs(tip, leg_a, leg_b)` — all four points known
- Derived properties: `width`, `depth`, `intake_angle`, **`intake_angle_deg`**,
  `fold_line`, `stitch_line_a/b`, `roof`, `mirror_tip`, `effective_second_tip`.
- Optional curved stitch legs via `stitch_curve_a` / `stitch_curve_b`
  (`Segment` or `CubicBezier`); both run **tip → leg** for consistent orientation.
- Transformations: `translate(dx, dy)`, `rotate(pivot, angle_rad)` — both now
  correctly **preserve** `stitch_curve_a/b`.
- `split(ratio)` — divide one dart into two sub-darts sharing the same tip;
  preserves `dart_type` and appends `" A"` / `" B"` name suffixes.
- `__eq__` / `__hash__` based on defining geometry fields (tip, legs, type, name).

#### Pattern integration (`sewpat.PatternPart.add_dart`)

- `PatternPart.add_dart(dart, …)` returns a `DartResult` with all created elements.
- Elements carry `role` tags: `dart_stitch`, `dart_fold`, `dart_roof`, `dart_tip`,
  `dart_notch`.
- Triangle darts: two stitch legs, fold line, corrected roof segments (replace the
  mouth edge with the *Abnäherdach* geometry), optional notches and precision-tip
  circles with info box.
- Rhombus darts: four stitch segments forming a closed diamond; no fold line or roof.
- Roof segments inherit the style of the source edge element (via `_edge_element`).

#### Style presets (`sewpat.style`)

- `STYLE_DART_STITCH` — dashed dart stitching lines (`seam_allowance=0.0`).
- `STYLE_DART_FOLD` — long-dash/dot dart crease line.
- `STYLE_PRECISION_POINT` — small grey circle for precision tip markers.
- `STYLE_CUT` — now exported from the public `sewpat` namespace.

#### DartResult

- `DartResult.__iter__` — supports ergonomic unpacking:
  `dart, *elems = part.add_dart(my_dart)`.

#### Examples

- Five SVG examples in `examples/darts/`:
  1. Outer seam dart, explicit depth
  2. Outer dart aimed at bust point (reference-point method)
  3. Inner dart rendered as rhombus
  4. Dart split into two equal sub-darts
  5. **Dart transfer via the pivot method** (Schwenkverfahren) — new in this release

#### Public API additions (`sewpat.__init__`)

- `InfoBox`, `STYLE_CUT` added to `__all__`.

### Changed

- `README.md` updated: Python ≥ 3.14, `uv`-only tooling, `ruff` formatter/linter,
  Darts section with factory-method reference table.

---

## [0.2.0] — (prior release)

- Blouse bodice pattern generation.
- Boy's shorts pattern generation.
- Drawstring pouch pattern generation.
- `ConstructionGrid`, `PatternPart`, `Pattern`, `PatternElement`.
- `CubicBezier`, `Segment`, `Ray`, `Line`, `Circle`, `Rect`, `Triangle` geometry.
- SVG export via `export_pattern_svg_mm()`.
