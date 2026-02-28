# Cubic Bezier Curves in sewpat2

This document describes the `CubicBezier` class implementation and intersection functionality added to the sewpat2 geometry module.

## Overview

The `CubicBezier` class provides a 2D cubic Bezier curve implementation with four control points. Cubic Bezier curves are fundamental primitives in computer graphics and CAD applications, allowing smooth curved paths to be defined mathematically.

## Class: CubicBezier

### Constructor

```python
CubicBezier(p0: Point, p1: Point, p2: Point, p3: Point)
```

Creates a cubic Bezier curve with four control points:
- `p0`: Start point of the curve (t=0)
- `p1`: First control point (influences the curve near the start)
- `p2`: Second control point (influences the curve near the end)
- `p3`: End point of the curve (t=1)

### Methods

#### `point_at_t(t: float) -> Point`
Evaluates the Bezier curve at parameter `t` using the cubic Bezier formula:
```
B(t) = (1-t)³P₀ + 3(1-t)²tP₁ + 3(1-t)t²P₂ + t³P₃
```
- `t`: Parameter value (typically 0.0 to 1.0)
- Returns: Point on the curve at parameter t

#### `tangent_at_t(t: float) -> np.ndarray`
Computes the tangent vector (B'(t)) at parameter `t` by delegating to `svgpathtools.derivative()`.
- `t`: Parameter value (typically 0.0 to 1.0)
- Returns: Tangent vector as numpy array (not normalised)

#### `length() -> float`
Computes the exact arc length of the curve using Gauss-Legendre quadrature (via `svgpathtools`).
- Returns: Exact arc length in the same units as the control points

#### `bounding_box() -> Tuple[Point, Point]`
Computes the axis-aligned bounding box by finding extrema in x and y directions.
- Returns: Tuple of (min_point, max_point) defining the bounding box

## Intersection Support

The `CubicBezier` class is fully integrated with the existing `intersect()` function and supports intersections with all geometric primitives:

### Supported Intersections

1. **CubicBezier ↔ Line**: Exact intersection using cubic equation solving
2. **CubicBezier ↔ Ray**: Exact intersection with ray direction filtering
3. **CubicBezier ↔ Segment**: Exact intersection with segment bounds checking
4. **CubicBezier ↔ Circle**: Approximate intersection using binary-search sampling
5. **CubicBezier ↔ CubicBezier**: Exact intersection using Bézier-clipping algorithm (Sederberg & Nishita 1990) via `svgpathtools`

### Usage Example

```python
from sewpat.geometry import Point, Line, CubicBezier, intersect
import numpy as np

# Create a cubic Bezier curve
p0 = Point(0, 0)
p1 = Point(1, 2)
p2 = Point(3, 2)
p3 = Point(4, 0)
bezier = CubicBezier(p0, p1, p2, p3)

# Create a horizontal line
line = Line(Point(0, 1), np.array([1, 0]))

# Find intersections
intersections = intersect(bezier, line)
for pt in intersections:
    print(f"Intersection at: {pt}")
```

### svgpathtools-Backed Methods

Several `CubicBezier` methods delegate to `svgpathtools` for numerically superior results:

| Method | svgpathtools equivalent | Advantage |
|---|---|---|
| `length()` | `CubicBezier.length()` | Gauss-Legendre quadrature – exact, no sampling error |
| `tangent_at_t(t)` | `CubicBezier.derivative(t)` | Analytic derivative, identical result |
| `intersect(b)` (Bezier–Bezier) | `CubicBezier.intersect()` | Bézier-clipping algorithm – quadratic convergence |

### Bezier-Line Intersection Algorithm

The intersection between a cubic Bezier curve and a line is computed by:

1. Converting the line to implicit form: `(P - line_point) × line_dir = 0`
2. Substituting the Bezier parametric equation into the implicit line equation
3. Solving the resulting cubic equation: `d₃t³ + d₂t² + d₁t + d₀ = 0`
4. Using Cardano's formula for robust cubic equation solving

### Cubic Equation Solver

The implementation includes a numerically stable cubic equation solver (`_solve_cubic`) that handles:
- Degenerate cases (when leading coefficient is zero)
- All three cases of Cardano's formula (one real root, multiple real roots, three distinct real roots)
- Proper handling of edge cases and numerical precision

### Approximate Intersection Methods

For **Bezier–Circle** intersections, the implementation uses:
- High-resolution sampling along the Bézier curve (1000 steps)
- Sign-change detection on `contains_point_inside()`
- Binary search refinement (20 iterations) for sub-mm accuracy

**Bezier–Bezier** intersections are **exact**, not approximate – see the svgpathtools-backed methods table above.

## Performance Considerations

- **Exact methods** (Line, Ray, Segment, Bezier–Bezier): Very fast, analytically derived
- **Approximate methods** (Circle): Sampling-based, configurable via binary-search iterations
- **Memory usage**: Minimal, only stores four control points
- **Numerical stability**: Uses robust algorithms; cubic solver uses Cardano's formula

## Integration with Existing Code

The `CubicBezier` class follows the same patterns as other geometry classes:
- Consistent `__str__` representation
- Integration with the `GEOMETRIC_TYPE` union
- Symmetric intersection support (intersect(a, b) == intersect(b, a))
- Compatible with the existing `intersect()` function API

## Testing

Comprehensive tests are included in `test_bezier.py` covering:
- Basic curve creation and evaluation
- Curve properties (length, bounding box, tangents)
- All intersection types with various geometric objects
- Edge cases and numerical precision

## SVG Rendering Support

The `CubicBezier` class is fully integrated with the SVG rendering system in `sewpat.render`:

### Basic Rendering

```python
from sewpat.geometry import Point, CubicBezier
from sewpat.render import render_pattern_part, StyleOptions
from sewpat.part import PatternPart

# Create a Bezier curve
bezier = CubicBezier(
    Point(0, 0),      # Start point
    Point(25, 50),    # First control point
    Point(75, 50),    # Second control point
    Point(100, 0)     # End point
)

# Add custom styling
bezier.style = StyleOptions(
    stroke_color="blue",
    stroke_width=2.0,
    dash_array=[5, 3]  # Optional dashing
)

# Create pattern and render
pattern = PatternPart("My Pattern", [bezier])
drawing = render_pattern_part(pattern)
```

### Control Point Visualization

```python
# Render with control points and control lines visible
drawing = render_pattern_part(
    pattern,
    show_bezier_control_points=True
)
```

### Styling Options

Bezier curves support all standard `StyleOptions`:
- `stroke_color`: Line color (e.g., "blue", "#FF0000")
- `stroke_width`: Line thickness in SVG units
- `dash_array`: Dashing pattern (e.g., [5, 3] for 5-unit dash, 3-unit gap)
- `opacity`: Transparency (0.0 to 1.0)

### Utility Functions

The render module provides additional utilities:

```python
from sewpat.render import bezier_to_svg_path, get_bezier_bounds

# Convert to SVG path string
svg_path = bezier_to_svg_path(bezier)
# Returns: "M 0,0 C 25,50 75,50 100,0"

# Get bounding box
min_x, min_y, max_x, max_y = get_bezier_bounds(bezier)
```

### Integration with Intersections

Intersection points are automatically rendered when added to a pattern:

```python
from sewpat.geometry import Line, intersect
import numpy as np

# Create intersecting line
line = Line(Point(0, 25), np.array([1, 0]))

# Find intersections
intersections = intersect(bezier, line)

# Add all elements to pattern
pattern.elements.extend([bezier, line])
pattern.elements.extend(intersections)  # Intersection points will be rendered
```

## Future Enhancements

Potential improvements for future versions:
- Adaptive sampling for better Circle/Bezier intersection accuracy
- Curve subdivision for more precise Bezier-Bezier intersections
- Support for rational Bezier curves (NURBS)
- Curve offsetting and parallel curve generation
- Animation support for parametric curve visualization
- Advanced styling options (gradients, patterns)