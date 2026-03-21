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
from .units import CM


@dataclass(frozen=True)
class GridConfig:
    """Block-specific construction constants for :class:`TopGrid`.

    Different garment blocks share the same grid geometry but differ in a
    handful of construction constants.  Rather than hard-coding these values
    inside :meth:`TopGrid.from_measurements` or scattering them across
    subclasses, they live here as a small, explicit dataclass that can be
    extended with future constants without changing any call sites.

    Use the pre-built class-level presets instead of constructing manually:

    * ``GridConfig.WAISTED_DART`` — waisted top with bust dart (default).
    * ``GridConfig.CASUAL``       — casual top without darts.

    Attributes:
        bust_point_ease: Fixed construction offset (ZuBrA) added to the
            bust-point horizontal position.  When ``None`` the value is taken
            from the :class:`~sewpat.fitclass.FitClass` (fit-class-dependent
            behaviour used by the waisted-dart block).  Set to a fixed ``float``
            (e.g. ``1 * CM``) for blocks where this constant does not vary
            with the fit class.
        hip_adj_denominator: Key describing the BlouseMeasurements field(s) used
            as the denominator when scaling the hip-offset (BeckenAdjustment).
            Plain attribute names (e.g. ``"back_length"``) are resolved directly;
            the composite key ``"back_length+hip_depth"`` is also supported.
    """

    bust_point_ease: float | None = None
    """Override for ZuBrA.  ``None`` → use fit-class value."""

    hip_adj_denominator: str = "back_length"
    """Denominator key for the hip-adj formula.

    Supported values:

    * ``"back_length"``           → ``meas.back_length``
    * ``"back_length+hip_depth"`` → ``meas.back_length + meas.hip_depth``
    * any plain attribute name on :class:`~sewpat.measurements.BlouseMeasurements`
    """

    # ------------------------------------------------------------------
    # Presets (assigned after class body as class-level attributes)
    # ------------------------------------------------------------------

    @classmethod
    def _make_waisted_dart(cls) -> GridConfig:
        return cls(
            bust_point_ease=None,  # taken from FitClass
            hip_adj_denominator="back_length",
        )

    @classmethod
    def _make_casual(cls) -> GridConfig:
        return cls(
            bust_point_ease=1 * CM,  # fixed 1 cm — independent of fit class
            hip_adj_denominator="back_length+hip_depth",
        )

    def resolve_bust_point_ease(self, fit_class: FitClass) -> float:
        """Return the effective bust-point ease.

        Returns the fixed override when set; falls back to
        ``fit_class.bust_point_ease`` otherwise.
        """
        if self.bust_point_ease is not None:
            return self.bust_point_ease
        return fit_class.bust_point_ease

    def resolve_hip_adj_denominator(self, meas: BlouseMeasurements) -> float:
        """Return the denominator value for the hip-offset formula."""
        value = 0.0
        for key in self.hip_adj_denominator.split("+"):
            value_add = getattr(meas, key, None)
            if value_add is None:
                raise AttributeError(
                    f"GridConfig.hip_adj_denominator={key!r} is not a valid "
                    f"BlouseMeasurements attribute."
                )
            value += value_add

        return float(value)


# Presets — frozen dataclass, so we assign after class body.
GridConfig.WAISTED_DART: GridConfig  # type: ignore[attr-defined,misc]  # noqa: B032
GridConfig.CASUAL: GridConfig  # type: ignore[attr-defined,misc]  # noqa: B032
GridConfig.WAISTED_DART = GridConfig._make_waisted_dart()  # type: ignore[attr-defined]
GridConfig.CASUAL = GridConfig._make_casual()  # type: ignore[attr-defined]


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
        grid_config: The :class:`GridConfig` preset used to build this grid.
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
    grid_config: GridConfig

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
        grid_config: GridConfig,
        hip_offset: float = 0.0,
        layout: PatternConfig | None = None,
    ) -> TopGrid:
        """Build and return a :class:`TopGrid` from the given measurements.

        Args:
            meas:        Blouse measurements (ease already included).
            fit_class:   :class:`~sewpat.fitclass.FitClass` for construction offsets.
            config:      Garment-design choices (length, seam allowance).
            grid_config: Block-specific construction constants — use
                         ``GridConfig.WAISTED_DART`` or ``GridConfig.CASUAL``.
            hip_offset:  Hip adjustment offset (BeckenAdjustment) in mm.
            layout:      Pattern layout configuration.
        """
        gc = grid_config

        bust_point_ease = gc.resolve_bust_point_ease(fit_class)
        length = config.length

        layout = layout or PatternConfig()

        hip_adj = hip_offset * meas.armscye_depth / gc.resolve_hip_adj_denominator(meas)
        bust_pos = meas.bust / 10 + bust_point_ease

        cg = ConstructionGrid(
            anchor=layout.anchor,
            horizontals=[
                (
                    "Shoulder Front",
                    meas.back_length - meas.front_length,
                ),  # VL2 offset: shoulder front sits (back_length - front_length) below anchor
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
            geom = built.get_element(name).geometry
            assert isinstance(geom, Segment), f"Grid element {name!r} must be a Segment"
            return geom

        grid = cls(
            part=built,
            grid_config=gc,
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
