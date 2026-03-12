"""DIN paper-size constants for sewing pattern export.

All dimensions are in mm (the project's internal unit).
Import the namespace constant that matches the target paper size and pass it to
:func:`~sewpat.render.export_pattern_svg_mm`.

Example:
    >>> from sewpat.pages import DinA4
    >>> print(DinA4.width, DinA4.height)
    210.0 297.0
"""

from types import SimpleNamespace

from sewpat.units import MM

#: DIN A4 paper size: 210 × 297 mm.
DinA4 = SimpleNamespace(width=210 * MM, height=297 * MM)

#: DIN A3 paper size: 297 × 420 mm.
DinA3 = SimpleNamespace(width=297 * MM, height=420 * MM)

#: DIN A2 paper size: 420 × 594 mm.
DinA2 = SimpleNamespace(width=420 * MM, height=594 * MM)

#: DIN A1 paper size: 594 × 841 mm.
DinA1 = SimpleNamespace(width=594 * MM, height=841 * MM)

#: DIN A0 paper size: 841 × 1189 mm.
DinA0 = SimpleNamespace(width=841 * MM, height=1189 * MM)
