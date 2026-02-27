"""
Length unit constants for sewing pattern generation.

All internal coordinates are in millimetres. Use these constants to express
measurements in other units and convert them to the base unit (mm).

Example::

    from sewpat.units import CM, MM
    width = 5 * CM   # 50 mm
"""

MM: float = 1.0
CM: float = 10.0 * MM
INCH: float = 25.4 * MM

