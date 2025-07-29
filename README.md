# SewPatGen

A Python library for automatically creating sewing patterns based on 2D CAD primitives.
Sewing patterns are exported to vector graphics for customization in editors like Inkscape.

## Features

- Generate patterns for female clothes: Blouse

## Installation

### Requirements

- Python 3.8 or higher
- NumPy 1.24.0 or higher
- uv package manager (recommended)

### Setting Up with UV

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone the repository
git clone https://github.com/yourusername/sewpat.git
cd sewpat

# Install the package in development mode
uv sync --extra dev
```

## Usage Examples

### Basic Geometric Operations

```python
from sewpat.src.geometry import Point, Line, Circle
import numpy as np

# Create a line between two points
p1 = Point(0, 0)
p2 = Point(10, 10)
line = Line(p1, p2)

# Calculate the length and midpoint of the line
print(f"Line length: {line.length}")  # 14.142135623730951
print(f"Line midpoint: {line.midpoint}")  # Point(5.0, 5.0)

# Access the underlying NumPy array
print(f"Point coordinates as NumPy array: {p1.coords}")  # [0. 0.]

# Create a ray with a NumPy direction vector
from sewpat.src.geometry import Ray
ray = Ray(Point(0, 0), np.array([1, 1]))

# Create a circle and find intersections with the line
circle = Circle(Point(5, 5), 3)
intersections = circle.intersect_with(line)
print(f"Number of intersections: {len(intersections)}")
for i, point in enumerate(intersections):
    print(f"Intersection {i+1}: {point}")
```

### Check out the Examples

For more detailed examples, see the `examples/geometry_example.py` file. Run it directly:

```bash
python examples/geometry_example.py
```

## Development

### Running Tests

```bash
uv run pytest
```

### Code Formatting

```bash
# Format code with black
black src tests

# Sort imports with isort
isort src tests
```

### Linting

```bash
flake8 src tests
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the project
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request
