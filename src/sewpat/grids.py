"""Pre-built construction grids for common garment blocks.

Each grid is a class whose attributes are the named construction lines, so
callers never have to use fragile ``get_element("…")`` string lookups.
The corresponding :class:`~sewpat.pattern.ConstructionGridPart` is available
as ``.part`` for adding to a :class:`~sewpat.pattern.Pattern`.

Grids provided:

* :class:`TopGrid`      — orthogonal construction grid for a sleeveless top / blouse block.
* :class:`WideSleeveGrid` — orthogonal construction grid for the wide sleeve block.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar

from .fitclass import FitClass
from .geometry import Segment
from .measurements import BlouseMeasurements, GarmentConfig
from .pattern import ConstructionGrid, ConstructionGridPart, PatternConfig
from .sleeve import SleeveBlockConfig, SleeveConstructionMeasures, SleeveMode, SleeveType
from .units import CM

if TYPE_CHECKING:
    from .sleeve import SleeveArmhole, SleeveConfig


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
    # Presets (class-level, not dataclass fields)
    # ------------------------------------------------------------------
    WAISTED_DART: ClassVar[GridConfig]
    CASUAL: ClassVar[GridConfig]

    @classmethod
    def _make_waisted_dart(cls) -> GridConfig:
        """Return the waisted-dart preset (bust-point ease from FitClass)."""
        return cls(
            bust_point_ease=None,  # taken from FitClass
            hip_adj_denominator="back_length",
        )

    @classmethod
    def _make_casual(cls) -> GridConfig:
        """Return the casual preset (fixed 1 cm bust-point ease, deeper hip denominator)."""
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


# Presets — frozen dataclass instances assigned after class body.
GridConfig.WAISTED_DART = GridConfig._make_waisted_dart()
GridConfig.CASUAL = GridConfig._make_casual()


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
            """Return the built grid element *name* as a :class:`Segment`."""
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


# ---------------------------------------------------------------------------
# WideSleeveGrid
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WideSleeveGrid:
    """Orthogonal construction grid for the wide sleeve block.

    Build via :meth:`from_armhole`; then add ``.part`` to your pattern and
    use the typed segment attributes directly — no string lookups.

    The grid is anchored at the top-left corner of the sleeve bounding box:

    * **Horizontal lines** — measured downward from the anchor (y increases ↓):

      - ``cap_line``           — at ``cap_height`` below the anchor; marks the
        bottom of the sleeve cap (cap crown is at the anchor level).
      - ``sleeve_length_line`` — at ``sleeve_length`` below the anchor; the
        hem edge.
      - ``hem_line``           — 1 cm above ``sleeve_length_line``; marks the
        start of the hem fold / allowance.

    * **Vertical lines** — measured rightward from the anchor (x increases →):

      - ``left_sleeve``   — at the left edge  (``x = anchor.x``).
      - ``center_sleeve`` — at the sleeve fold / center line
        (``x = anchor.x + sleeve_width``).
      - ``right_sleeve``  — at the right edge
        (``x = anchor.x + 2 * sleeve_width``).

    The cap height and sleeve width are derived from the armhole geometry and
    the two wide-sleeve constants stored in :class:`~sewpat.sleeve.SleeveConfig`::

        cap_height   = armscye_height / 3 − cap_offset
        sleeve_width = sqrt((armscye_circumference / 2 − ease)² − cap_height²)

    ``sleeve_width`` is the **half-width** (centre fold → side seam); the full
    sleeve spans ``2 × sleeve_width``.

    Attributes:
        part: The :class:`~sewpat.pattern.ConstructionGridPart` ready to add
            to a :class:`~sewpat.pattern.Pattern`.
        cap_line: Horizontal guide at the bottom of the sleeve cap.
        sleeve_length_line: Horizontal guide at the sleeve hem edge.
        hem_line: Horizontal guide 1 cm above ``sleeve_length_line``.
        left_sleeve: Vertical guide at the left sleeve-width edge.
        center_sleeve: Vertical guide along the sleeve centre / fold line.
        right_sleeve: Vertical guide at the right sleeve-width edge.
        cap_height: Ärmelkopfhöhe — sleeve cap height in mm (derived).
        sleeve_width: Ärmelbreite — full sleeve width in mm (derived).
    """

    part: ConstructionGridPart

    # ── Construction measures (single source of truth for derived values) ──────
    construction_measures: SleeveConstructionMeasures

    # ── Horizontals ───────────────────────────────────────────────────────────
    cap_line: Segment
    sleeve_length_line: Segment
    hem_line: Segment

    # ── Verticals ─────────────────────────────────────────────────────────────
    left_sleeve: Segment
    center_sleeve: Segment
    right_sleeve: Segment

    # ── Convenience accessors (mirror construction_measures) ──────────────────
    @property
    def cap_height(self) -> float:
        """Ärmelkopfhöhe — sleeve cap height in mm (from construction measures)."""
        return self.construction_measures.cap_height

    @property
    def sleeve_width(self) -> float:
        """Ärmelbreite — half sleeve width in mm (centre fold → side seam).

        The full sleeve spans ``2 × sleeve_width``.
        """
        assert self.construction_measures.sleeve_width is not None
        return self.construction_measures.sleeve_width

    @classmethod
    def from_armhole(
        cls,
        armhole: SleeveArmhole,
        sleeve_config: SleeveConfig,
        layout: PatternConfig | None = None,
    ) -> WideSleeveGrid:
        """Build the wide sleeve construction grid from armhole geometry.

        The ``cap_offset`` and ``ease`` values are taken directly from
        *sleeve_config*, so no separate wide-sleeve config class is needed::

            config    = SleeveConfig(sleeve_length=60 * CM, cap_offset=1 * CM, ease=0.5 * CM)
            wide_grid = WideSleeveGrid.from_armhole(armhole, config)
            pattern.add_part(wide_grid.part)

        Internally delegates the cap height and sleeve width computation to
        :meth:`~sewpat.sleeve.SleeveConstructionMeasures.from_wide_armhole`
        so that the full audit trail is available on ``grid.construction_measures``.

        Args:
            armhole:      Armhole geometry — provides ``armscye_height`` and
                          ``armscye_circumference``.
            sleeve_config: Garment config — provides ``sleeve_length``,
                          ``cap_offset``, and ``ease``.
            layout:       Pattern layout configuration (anchor position).
                          Defaults to :class:`~sewpat.pattern.PatternConfig`.

        Returns:
            :class:`WideSleeveGrid` with all lines and derived measures populated.

        Raises:
            ValueError: propagated from
                :meth:`~sewpat.sleeve.SleeveConstructionMeasures.from_wide_armhole`
                when the geometry is infeasible.
        """
        layout = layout or PatternConfig()

        # ── All formula work delegated to SleeveConstructionMeasures ─────────
        # sleeve_config.cap_offset is [0, 2] cm (user-facing: positive = shorter cap).
        # SleeveBlockConfig.cap_offset is [−2, 0] cm (formula convention: additive).
        # Convert the sign so the original uniform formula handles WIDE without
        # any special-casing.
        cm = SleeveConstructionMeasures.from_armhole(
            armhole,
            None,
            sleeve_config,
            SleeveBlockConfig(
                mode=SleeveMode.WIDE,
                cap_offset=-sleeve_config.cap_offset,  # [0, 2] → [−2, 0] cm
                upper_arm_ease=None,
                hem_ease=None,
            ),
            SleeveType.WIDE,
        )

        assert cm.sleeve_width is not None, "WIDE sleeve_width must be a float after from_armhole"
        cg = ConstructionGrid(
            anchor=layout.anchor,
            horizontals=[
                ("Cap Line", cm.cap_height),
                ("Sleeve Length", sleeve_config.sleeve_length),
                ("Hem Line", sleeve_config.sleeve_length - 1.0 * CM),
            ],
            verticals=[
                ("Left Sleeve", 0.0),
                ("Center Sleeve", cm.sleeve_width),
                ("Right Sleeve", cm.sleeve_width * 2),
            ],
            part_name="Wide Sleeve Grid",
        )
        built = cg.build()

        def seg(name: str) -> Segment:
            geom = built.get_element(name).geometry
            assert isinstance(geom, Segment), f"Grid element {name!r} must be a Segment"
            return geom

        return cls(
            part=built,
            construction_measures=cm,
            cap_line=seg("Cap Line"),
            sleeve_length_line=seg("Sleeve Length"),
            hem_line=seg("Hem Line"),
            left_sleeve=seg("Left Sleeve"),
            center_sleeve=seg("Center Sleeve"),
            right_sleeve=seg("Right Sleeve"),
        )
