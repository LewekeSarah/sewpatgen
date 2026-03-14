# SewPatGen

[![CI & Docs](https://github.com/LewekeSarah/sewpatgen/actions/workflows/ci.yml/badge.svg)](https://github.com/LewekeSarah/sewpatgen/actions/workflows/ci.yml)
[![Docs](https://img.shields.io/badge/docs-GitHub%20Pages-blue)](https://lewekesarah.github.io/sewpatgen/)

A Python library for automatically generating sewing patterns based on 2D CAD primitives.
Patterns are exported as SVG vector files, ready for customisation in Inkscape or any
vector editor.

## Features

- **2D geometry engine** — `Point`, `Segment`, `Ray`, `Line`, `CubicBezier`, `Circle`, `Rect`
- **Dart support** — `Dart` geometry with triangle and rhombus types, factory methods,
  split, rotate (pivot method) and full `PatternPart.add_dart()` integration
- **Pattern structure** — `PatternPart`, `Pattern`, `ConstructionGrid`, seam allowance
- **SVG export** — clean, print-ready vector output via `export_pattern_svg_mm()`
- **Garment examples** — blouse bodice, boy's shorts, drawstring pouch, dart showcases

## Requirements

- Python ≥ 3.14
- [uv](https://docs.astral.sh/uv/) package manager

## Installation

```bash
# Clone the repository
git clone https://github.com/sarahleweke/sewpatgen.git
cd sewpatgen

# Install all dependencies (including dev extras)
uv sync --extra dev
```

## Quick Start

```python
from sewpat import (
    CM, MM, Dart, DartType, Pattern, PatternPart,
    Point, Segment, STYLE_DART_STITCH, STYLE_DART_FOLD,
)
from sewpat.render import export_pattern_svg_mm

# Build a simple bodice-front piece
part = PatternPart("Bodice Front")
o  = Point(0,   0)
tl = Point(0,   200)
tr = Point(120, 200)
br = Point(120, 0)
side = part.append(Segment(tr, br), is_outline=True)
part.append(Segment(o, tl),  is_outline=True)
part.append(Segment(tl, tr), is_outline=True)
part.append(Segment(br, o),  is_outline=True)

# Place a waist dart on the side seam
dart = Dart.from_edge_at_t(
    side, t=0.3, width=22 * MM, depth=80 * MM,
    dart_type=DartType.TRIANGLE, name="Side Seam Dart",
)
part.add_dart(dart, stitch_style=STYLE_DART_STITCH,
              fold_style=STYLE_DART_FOLD, notches=True, precision_tip=True)

pattern = Pattern("Bodice")
pattern.add_part(part)
export_pattern_svg_mm(pattern, filename="bodice.svg", width_mm=210, height_mm=297)
```

## Darts

The dart API supports the full professional workflow:

| Factory method | Use case |
|---|---|
| `Dart.from_edge_at_t(edge, t, width, depth)` | Depth given in mm |
| `Dart.from_edge_at_point(edge, point, width, depth)` | Anchor to a named landmark |
| `Dart.from_edge_free_tip(edge, t, width, reference_point)` | Tip aimed at bust point |
| `Dart.from_tip_center_width(tip, center, width)` | Explicit tip + mouth construction |
| `Dart.from_tip_and_legs(tip, leg_a, leg_b)` | All four points known |

Key properties: `width`, `depth`, `intake_angle`, `intake_angle_deg`, `fold_line`,
`stitch_line_a/b`, `roof`, `mirror_tip`.

Operations: `dart.split(ratio)`, `dart.rotate(pivot, angle_rad)`, `dart.translate(dx, dy)`.

See the [Darts guide](https://lewekesarah.github.io/sewpatgen/guides/darts/) for all factory methods, annotated SVG examples, dart splitting and the pivot-method dart transfer.

## Examples

```bash
# Dart showcase (generates 5 SVGs)
python examples/darts/dart_examples.py

# Blouse bodice
python examples/women/blouse.py

# Drawstring pouch
python examples/items/drawstring_pouch.py
```

## Development

### Running Tests

```bash
uv run pytest
```

### Formatting & Linting

```bash
# Format with ruff
uv run ruff format src tests

# Lint
uv run ruff check src tests
```

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

1. Fork the project
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request
