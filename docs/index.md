# sewpat

**sewpat** is a Python library for generating sewing patterns as SVG and PDF vector files.

## Overview

sewpat provides:

- Geometry primitives (point, segment, curve, circle, Bézier curve …)
- Dart construction and transfer
- Pattern part management with seam allowance
- Construction grids for basic blocks
- SVG/PDF rendering with scale and page format

## Quick Start

```python
import sewpat as sp

# Create a person
person = sp.Person(
    name="Example",
    gender=sp.Gender.FEMALE,
    bust=88.0,
    waist=70.0,
    hip=96.0,
)

# Determine fit class
fit = sp.FitClass.from_person(person)
```

## Installation

```bash
pip install sewpat
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv add sewpat
```

## API Reference

- [Geometry](api/geometry.md)
- [Patterns & Pattern Parts](api/pattern.md)
- [Measurements & Fit Classes](api/measurements.md)
- [Person](api/person.md)
- [Style & Rendering](api/style.md)
- [Pages](api/pages.md)

## License

MIT — see [LICENSE](https://github.com/sleweke/sewpatgen/blob/main/LICENSE).
