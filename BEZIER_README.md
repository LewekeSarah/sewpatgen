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
Computes the tangent vector at parameter `t` using the derivative of the Bezier curve.
- `t`: Parameter value (typically 0.0 to 1.0)
- Returns: Tangent vector as numpy array

#### `length_approx(num_segments: int = 100) -> float`
Approximates the arc length of the curve by subdividing it into line segments.
- `num_segments`: Number of segments for approximation (default: 100)
- Returns: Approximate length of the curve

#### `bounding_box() -> Tuple[Point, Point]`
Computes the axis-aligned bounding box by finding extrema in x and y directions.
- Returns: Tuple of (min_point, max_point) defining the bounding box

## Intersection Support

The `CubicBezier` class is fully integrated with the existing `intersect()` function and supports intersections with all geometric primitives:

### Supported Intersections

1. **CubicBezier ↔ Line**: Exact intersection using cubic equation solving
2. **CubicBezier ↔ Ray**: Exact intersection with ray direction filtering
3. **CubicBezier ↔ Segment**: Exact intersection with segment bounds checking
4. **CubicBezier ↔ Circle**: Approximate intersection using sampling method
5. **CubicBezier ↔ CubicBezier**: Approximate intersection using sampling method

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

## Implementation Details

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

For complex intersections (Bezier-Circle, Bezier-Bezier), the implementation uses:
- High-resolution sampling along the curves
- Distance-based intersection detection
- Binary search refinement for improved accuracy
- Duplicate detection to avoid reporting the same intersection multiple times

## Performance Considerations

- **Exact methods** (Line, Ray, Segment): Very fast, O(1) complexity
- **Approximate methods** (Circle, Bezier): Slower due to sampling, but configurable precision
- **Memory usage**: Minimal, only stores four control points
- **Numerical stability**: Uses robust algorithms for cubic equation solving

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

## Future Enhancements

Potential improvements for future versions:
- Adaptive sampling for better Circle/Bezier intersection accuracy
- Curve subdivision for more precise Bezier-Bezier intersections
- Support for rational Bezier curves (NURBS)
- Curve offsetting and parallel curve generation
- Integration with rendering pipeline for visualization