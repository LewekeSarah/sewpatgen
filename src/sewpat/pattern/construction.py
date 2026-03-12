"""Construction-grid classes — orthogonal drafting-aid helpers.

These classes are pure grid/geometry objects; they do not belong in the
general ``part`` module.  Keeping them here makes the dependency arrow
directional: ``grids.py → construction.py → geometry.py``.

This module owns:

* :class:`ConstructionGridPart` — a :class:`~sewpat.pattern.PatternPart`
  whose elements are all stamped ``is_construction=True``.
* :class:`ConstructionGrid` — builder that produces a
  :class:`ConstructionGridPart` from lists of named vertical / horizontal
  guide lines.
"""

from typing import TYPE_CHECKING

from ..geometry import Point, Segment
from ..style import STYLE_CONSTRUCTION_GRID, StyleOptions
from .part import PatternPart

if TYPE_CHECKING:
    from ..element import PatternElement


class ConstructionGridPart(PatternPart):
    """A :class:`PatternPart` that represents a construction grid.

    Grid elements are kept separate from the main pattern pieces when rendering
    by default — they are only included when requested explicitly by name via
    the ``parts=`` argument of the export functions.

    All elements appended to this part automatically receive
    ``is_construction=True``, so they are hidden when ``show_construction=False``
    is passed to the export functions.

    Prefer building instances via :class:`ConstructionGrid` rather than
    creating them directly.
    """

    def __init__(
        self,
        name: str = "Grid",
        elements: list[PatternElement] | None = None,
    ) -> None:
        """Initialise a construction-grid part; all elements stamped ``is_construction=True``."""
        super().__init__(name=name, elements=elements, is_construction=True)


class ConstructionGrid:
    """Builds an orthogonal construction grid as a :class:`ConstructionGridPart`.

    Each horizontal/vertical line is labelled with its measurement name so it
    can be retrieved later via :meth:`~sewpat.pattern.PatternPart.get_element`.

    Args:
        anchor: Top-left origin of the grid.
        verticals: ``(name, x_offset_mm)`` pairs — guide lines parallel to
            the y-axis.
        horizontals: ``(name, y_offset_mm)`` pairs — guide lines parallel to
            the x-axis.
        extent: Half-length of each guide line in mm.  Defaults to ``1500``.
        part_name: Name of the produced :class:`ConstructionGridPart`.
            Defaults to ``"Grid"``.
        style: Visual style for all guide lines.  Defaults to
            :data:`~sewpat.style.STYLE_CONSTRUCTION_GRID`.

    Example::

        from sewpat.units import CM

        grid = ConstructionGrid(
            anchor=Point(10 * CM, 10 * CM),
            verticals=[("Center Back", 0), ("Side Back", 20 * CM)],
            horizontals=[("Chest", 0), ("Waist", 20 * CM), ("Hip", 36 * CM)],
        )
        pattern.add_part(grid.build())
    """

    def __init__(
        self,
        anchor: Point,
        verticals: list[tuple[str, float]] | None = None,
        horizontals: list[tuple[str, float]] | None = None,
        extent: float = 1500.0,
        part_name: str = "Grid",
        style: StyleOptions | None = None,
    ) -> None:
        """Store grid parameters; pass ``None`` for verticals/horizontals to get an empty axis."""
        self.anchor = anchor
        self.verticals: list[tuple[str, float]] = verticals or []
        self.horizontals: list[tuple[str, float]] = horizontals or []
        self.extent = extent
        self.part_name = part_name
        self.style = style if style is not None else STYLE_CONSTRUCTION_GRID

    def build(self) -> ConstructionGridPart:
        """Build and return the grid as a :class:`ConstructionGridPart`."""
        part = ConstructionGridPart(name=self.part_name)
        ax, ay = self.anchor.x, self.anchor.y
        for name, x_off in self.verticals:
            x = ax + x_off
            part.add_construction_line(
                Segment(Point(x, ay - self.extent), Point(x, ay + self.extent), name=name),
                style=self.style,
            )
        for name, y_off in self.horizontals:
            y = ay + y_off
            part.add_construction_line(
                Segment(Point(ax - self.extent, y), Point(ax + self.extent, y), name=name),
                style=self.style,
            )
        return part
