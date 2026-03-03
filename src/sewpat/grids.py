"""Pre-built construction grids for common garment blocks.

Each grid is a class whose attributes are the named construction lines, so
callers never have to use fragile ``get_element("…")`` string lookups.
The corresponding :class:`~sewpat.pattern.ConstructionGridPart` is available
as ``.part`` for adding to a :class:`~sewpat.pattern.Pattern`.
"""

from dataclasses import dataclass

from .geometry import Segment
from .measurements import BlouseMeasurements, ModelConfig
from .pattern import ConstructionGrid, PatternConfig, ConstructionGridPart


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
        sleeve_back: Vertical guide at the back sleeve position.
        side_back: Vertical guide at the back side-seam position.
        side_front: Vertical guide at the front side-seam position.
        sleeve_front: Vertical guide at the front sleeve position.
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
    sleeve_back: Segment
    side_back: Segment
    side_front: Segment
    sleeve_front: Segment
    bust_point: Segment
    center_front: Segment

    @classmethod
    def from_measurements(
        cls,
        meas: BlouseMeasurements,
        model: ModelConfig,
        config: PatternConfig,
    ) -> "TopGrid":
        """Build and return a :class:`TopGrid` from the given measurements.

        Parameters
        ----------
        meas:
            Blouse-specific measurements (ease already included).
        model:
            Model-level design choices such as garment length (``MoL``) and
            hip adjustment (``BeckenAdjustment``).
        config:
            Pattern configuration supplying the anchor point and the gap
            between back and front halves (``margin``).
        """
        hip_adj = model.BeckenAdjustment * meas.AlT / meas.RüL
        bust_pos = meas.BrU / 10 + model.ZuBrA

        cg = ConstructionGrid(
            anchor=config.anchor,
            horizontals=[
                ("Shoulder Front", meas.RüL - meas.VL), # TODO check VL vs VL2
                ("Shoulder Back", 0),
                ("Chest",    meas.AlT),
                ("Waist",    meas.RüL),
                ("Hip",      meas.RüL + meas.HüT),
                ("Hem",      model.MoL),
            ],
            verticals=[
                ("Center Back",    0),
                ("Hip Adjustment", hip_adj),
                ("Neck",           0 + meas.HlB),
                ("Sleeve Back",    hip_adj + meas.RüB),
                ("Side Back",      hip_adj + meas.RüB + meas.ArD * 2 / 3),
                ("Side Front",     hip_adj + meas.RüB + meas.ArD * 2 / 3 + config.margin),
                ("Sleeve Front",   hip_adj + meas.RüB + meas.ArD + config.margin),
                ("Bustpoint",      hip_adj + meas.RüB + meas.ArD + meas.BrB - bust_pos + config.margin),
                ("Center Front",   hip_adj + meas.RüB + meas.ArD + meas.BrB + config.margin),
            ],
            part_name="Grid",
        )
        built = cg.build()

        def seg(name: str) -> Segment:
            return built.get_element(name).geometry  # type: ignore[return-value]

        return cls(
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
            sleeve_back=seg("Sleeve Back"),
            side_back=seg("Side Back"),
            side_front=seg("Side Front"),
            sleeve_front=seg("Sleeve Front"),
            bust_point=seg("Bustpoint"),
            center_front=seg("Center Front"),
        )
