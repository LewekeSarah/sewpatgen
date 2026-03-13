# sewpat

**sewpat** is a Python library for generating sewing patterns as SVG and PDF vector files.

## Overview

sewpat provides:

- Geometry primitives (point, segment, curve, circle, Bézier curve …)
- Dart construction and transfer
- Pattern part management with seam allowance
- Construction grids for basic blocks
- Cross-part seam length validation (`Pattern.validate_seam_pairs`)
- SVG/PDF rendering with scale and page format

## Quick Start

```python
import sewpat as sp

# Create a person
person = sp.Person(
    gender=sp.Gender.FEMALE,
    bust=88.0 * sp.measurements.CM,
    waist=70.0 * sp.measurements.CM,
    hip=96.0 * sp.measurements.CM,
    hip_depth=20.0 * sp.measurements.CM,
    armscye_depth=(88.0 / 10 + 11)  * sp.measurements.CM,
    back_length=27.0 * sp.measurements.CM,
)
# Determine standart fit class
fit_class = sp.FitClass(pk=4)

# Start the pattern with an orthogonal construction grid
layout = sp.pattern.part.PatternConfig()
pattern = sp.pattern.Pattern(name="Simple Shape", anchor=layout.anchor)

grid = sp.pattern.ConstructionGrid(
        anchor=layout.anchor,
        verticals=[
            ("center", 0),
            ("side", person.bust / 4),
        ],
        horizontals=[
            ("shoulder", 0),
            ("bust", person.armscye_depth),
            ("waist", person.back_length),
            ("hip", person.back_length + person.hip_depth),
        ],
    ).build()

pattern.add_part(grid)

# Design the pattern
front = sp.pattern.PatternPart(name="Front Design")
pattern.add_part(front)

front.append(
    sp.geometry.Segment(
        sp.geometry.intersect(grid.get_element("shoulder").geometry, grid.get_element("side").geometry)[0],
        sp.geometry.intersect(grid.get_element("shoulder").geometry, grid.get_element("center").geometry)[0],
    )
)


# Export the pattern as SVG
sp.render.export_pattern_svg_mm(
    pattern,
    width_mm=sp.pages.DinA0.width,
    height_mm=sp.pages.DinA0.height,
    filename="test_grod.svg",
    parts=["Grid", "Front Design"],
    show_bezier_control_points=False,
    show_construction=True,
    show_seam_allowance=False,
)
```

## Installation

There is no PyPI release yet. Install directly from GitHub:

```bash
git clone https://github.com/LewekeSarah/sewpatgen.git
cd sewpatgen
```

Then install the dependencies with [uv](https://docs.astral.sh/uv/):

```bash
uv sync
```


## API Reference

- [Geometry](api/geometry.md)
- [Patterns & Pattern Parts](api/pattern.md)
- [Measurements & Fit Classes](api/measurements.md)
- [Person](api/person.md)
- [Style & Rendering](api/style.md)
- [Pages](api/pages.md)

## License

MIT — see [LICENSE](https://github.com/LewekeSarah/sewpatgen/blob/main/LICENSE).
