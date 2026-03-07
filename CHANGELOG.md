# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
