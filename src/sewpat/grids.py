"""Pre-built construction grids for common garment blocks.

Each grid is a class whose attributes are the named construction lines, so
callers never have to use fragile ``get_element("…")`` string lookups.
The corresponding :class:`~sewpat.pattern.ConstructionGridPart` is available
as ``.part`` for adding to a :class:`~sewpat.pattern.Pattern`.
"""

from dataclasses import dataclass

from .fitclass import FitClass
from .geometry import Segment
from .measurements import BlouseMeasurements, GarmentConfig
from .pattern import ConstructionGrid, ConstructionGridPart, PatternConfig


@dataclass(frozen=True)
class TopGrid:
    """Orthogonal construction grid for a sleeveless top / blouse block.

    Build via :meth:`TopGrid.from_measurements`; then add ``.part`` to your
    pattern and use the typed segment attributes directly — no string lookups.

    Example::

        grid = TopGrid.from_measurements(meas, model, config)
        pattern.add_part(grid.part)

        pt_bust = intersect(grid.chest, grid.side_back)[0]

    Attributes:
        part: The :class:`~sewpat.pattern.ConstructionGridPart` ready to add
            to a :class:`~sewpat.pattern.Pattern`.
        shoulder_front: Horizontal guide at the shoulder_front level.
        shoulder_back: Horizontal guide at the shoulder_back level.
        chest: Horizontal guide at the bust / chest level.
        waist: Horizontal guide at the waist level.
        hip: Horizontal guide at the hip level.
        hem: Horizontal guide at the garment hem.
        center_back: Vertical guide along the back centre.
        hip_adj: Vertical guide for the hip adjustment (BeckenAdjustment).
        neck: Vertical guide at the neck position
        dart_back: Vertical guide at the back dart position.
        armscye_back: Vertical guide at the back armscye position.
        side_back: Vertical guide at the back side-seam position.
        side_front: Vertical guide at the front side-seam position.
        armscye_front: Vertical guide at the front armscye position.
        bust_point: Vertical guide through the bust point.
        center_front: Vertical guide along the front centre.
    """

    part: ConstructionGridPart

    # horizontals
    shoulder_front: Segment
    shoulder_back: Segment
    chest: Segment
    waist: Segment
    hip: Segment
    hem: Segment

    # verticals
    center_back: Segment
    hip_adj: Segment
    neck: Segment
    dart_back: Segment
    armscye_back: Segment
    side_back: Segment
    side_front: Segment
    armscye_front: Segment
    bust_point: Segment
    center_front: Segment

    @classmethod
    def from_measurements(
        cls,
        meas: BlouseMeasurements,
        fit_class: FitClass,
        config: GarmentConfig,
        hip_offset: float = 0.0,
        layout: PatternConfig | None = None,
    ) -> TopGrid:
        """Build and return a :class:`TopGrid` from the given measurements.

        Args:
            meas:       Blouse measurements (ease already included).
            fit_class:  :class:`~sewpat.fitclass.FitClass` for construction offsets.
            hip_offset: Hip adjustment offset (BeckenAdjustment) in mm.
            config:     Garment-design choices (length, seam allowance).
            layout:     Pattern layout configuration.
        """
        bust_point_ease = fit_class.bust_point_ease
        length = config.length

        layout = layout or PatternConfig()

        hip_adj = hip_offset * meas.armscye_depth / meas.back_length
        bust_pos = meas.bust / 10 + bust_point_ease

        cg = ConstructionGrid(
            anchor=layout.anchor,
            horizontals=[
                (
                    "Shoulder Front",
                    meas.back_length - meas.front_length,
                ),  # TODO check front_length vs VL2
                ("Shoulder Back", 0),
                ("Chest", meas.armscye_depth),
                ("Waist", meas.back_length),
                ("Hip", meas.back_length + meas.hip_depth),
                ("Hem", length),
            ],
            verticals=[
                ("Center Back", 0),
                ("Hip Adjustment", hip_adj),
                ("Neck", 0 + meas.neck_size),
                ("Dart Back", hip_adj + meas.back_width / 2),
                ("Armscye Back", hip_adj + meas.back_width),
                ("Side Back", hip_adj + meas.back_width + meas.armscye_width * 2 / 3),
                (
                    "Side Front",
                    hip_adj + meas.back_width + meas.armscye_width * 2 / 3 + layout.margin,
                ),
                (
                    "Armscye Front",
                    hip_adj + meas.back_width + meas.armscye_width + layout.margin,
                ),
                (
                    "Bustpoint",
                    hip_adj
                    + meas.back_width
                    + meas.armscye_width
                    + meas.chest_width
                    - bust_pos
                    + layout.margin,
                ),
                (
                    "Center Front",
                    hip_adj
                    + meas.back_width
                    + meas.armscye_width
                    + meas.chest_width
                    + layout.margin,
                ),
            ],
            part_name="Grid",
        )
        built = cg.build()

        def seg(name: str) -> Segment:
            return built.get_element(name).geometry  # type: ignore[return-value]

        grid = cls(
            part=built,
            shoulder_front=seg("Shoulder Front"),
            shoulder_back=seg("Shoulder Back"),
            chest=seg("Chest"),
            waist=seg("Waist"),
            hip=seg("Hip"),
            hem=seg("Hem"),
            center_back=seg("Center Back"),
            hip_adj=seg("Hip Adjustment"),
            neck=seg("Neck"),
            dart_back=seg("Dart Back"),
            armscye_back=seg("Armscye Back"),
            side_back=seg("Side Back"),
            side_front=seg("Side Front"),
            armscye_front=seg("Armscye Front"),
            bust_point=seg("Bustpoint"),
            center_front=seg("Center Front"),
        )

        _check_chest_width(grid, meas.bust_width / 2)
        return grid


def _check_chest_width(grid: TopGrid, expected_half_width: float) -> None:
    """Validate that the built grid positions satisfy the chest-width constraint.

    The distance from ``hip_adj`` to ``side_back`` (back half-width) plus the
    distance from ``side_front`` to ``center_front`` (front half-width) must
    equal *expected_half_width* (typically ``BrW / 2``).

    This is checked against the actual segment positions rather than the source
    measurements, so any mistake in the grid formulas is caught here regardless
    of how the grid was constructed (from measurements, a file, a database, …).

    Raises:
        ValueError: if the constraint is violated beyond floating-point tolerance.
    """
    actual = (grid.side_back.p1.x - grid.hip_adj.p1.x) + (
        grid.center_front.p1.x - grid.side_front.p1.x
    )
    if abs(actual - expected_half_width) > 1e-6:
        raise ValueError(
            f"Chest-width control failed: hip_adj→side_back + side_front→center_front "
            f"= {actual:.4f} but expected {expected_half_width:.4f}."
        )
