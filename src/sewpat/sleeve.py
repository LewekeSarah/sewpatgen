"""Sleeve block construction measures.

This module provides the classes required to derive the full set of
construction measures for a sleeve block from a finished bodice block.

Three sleeve styles are supported — each with its own formula constants
stored in a :class:`SleeveBlockConfig` preset.  The NARROW style additionally
distinguishes two usage contexts (blouse/dress vs. jacket/coat):

* ``SleeveType.STRETCH``  — stretch sleeve; half-height cap derived from armscye circumference.
* ``SleeveType.WIDE``     — wider sleeve; flat cap derived from armscye height with offset.
* ``SleeveType.NARROW``   — narrow sleeve; high cap derived from armscye height and arm diameter.

Use ``SleeveBlockConfig.NARROW_BLOUSE`` or ``SleeveBlockConfig.NARROW_JACKET``
together with ``SleeveType.NARROW`` to select the appropriate constants.

Typical usage::

    from sewpat.sleeve import (
        SleeveArmhole,
        SleeveBlockConfig,
        SleeveConfig,
        SleeveConstructionMeasures,
        SleeveMeasurements,
        SleeveMode,
        SleeveType,
    )

    armhole = SleeveArmhole.from_block(block, grid)
    meas    = SleeveMeasurements.from_blouse_and_person(blouse_meas, person)
    config  = SleeveConfig(sleeve_length=60 * CM)
    cm      = SleeveConstructionMeasures.from_armhole(
        armhole, meas, config, SleeveBlockConfig.NARROW_BLOUSE, SleeveType.NARROW
    )
    print(
        f"armscye_height={cm.armscye_height:.1f} mm"
        f"  circumference={cm.armscye_circumference:.1f} mm"
        f"  cap_height={cm.cap_height:.1f} mm"
    )
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, ClassVar

from .geometry import CubicBezier, Point, Segment, intersect, seam_length
from .measurements import BlouseMeasurements
from .person import Person
from .units import CM

if TYPE_CHECKING:
    from .blocks import TopBlock
    from .grids import TopGrid


# ---------------------------------------------------------------------------
# SleeveType
# ---------------------------------------------------------------------------


class SleeveType(Enum):
    """Style variants for sleeve construction.

    Each variant selects a different set of formula constants from
    :class:`SleeveBlockConfig` to control the sleeve cap height and width.
    For ``NARROW``, combine with either ``SleeveBlockConfig.NARROW_BLOUSE``
    or ``SleeveBlockConfig.NARROW_JACKET`` to pick the appropriate constants.

    Attributes:
        STRETCH: Sleeve for stretch fabrics (knit or elastic woven) with a
            half-height cap derived from the armscye circumference.
            The reduced cap relies on the fabric's stretch to ease in.
        WIDE:   Wider sleeve with a flat cap derived from the armscye
            height plus a small offset.  Gives a relaxed, shirt-like
            silhouette.
        NARROW: Narrow sleeve with a high, structured cap derived from the
            armscye height minus an arm diameter correction term.  Used for
            tailored blouses, dresses, jackets, and coats.
    """

    STRETCH = "stretch"  # cap from armscye circumference — knit & elastic woven fabrics
    WIDE = "wide"  # cap from armscye height + offset — relaxed / shirt sleeve
    NARROW = "narrow"  # cap from armscye height − arm diameter fraction — tailored sleeve


# ---------------------------------------------------------------------------
# SleeveMode
# ---------------------------------------------------------------------------


class SleeveMode(Enum):
    """Precise construction mode for :class:`SleeveBlockConfig`.

    While :class:`SleeveType` describes the sleeve *shape* (three variants),
    ``SleeveMode`` describes the exact construction context — distinguishing
    the two NARROW sub-types — and is the single source of truth for:

    * which sleeve cap height base measurement to use (circumference vs. height),
    * the fixed formula coefficients (``cap_height_frac``, ``cap_arm_diameter_frac``),
    * the **precise** valid range for each user-configurable constant.

    Attributes:
        STRETCH:       Stretch fabrics; cap height = circumference / 3;
            upper_arm_ease ∈ [−1, +2] cm.
        WIDE:          Shirt-style; cap height = height / 3 + const;
            no sleeve width / hem width.
        NARROW_BLOUSE: Tailored blouse / dress;
            cap height = armscye height/2 − arm diameter/5 − const.
        NARROW_JACKET: Jacket / coat;
            cap height = armscye height/2 − arm diameter/10 − const.
    """

    STRETCH = "stretch"
    WIDE = "wide"
    NARROW_BLOUSE = "narrow_blouse"
    NARROW_JACKET = "narrow_jacket"


# ---------------------------------------------------------------------------
# SleeveBlockConfig — private validators (one per mode)
# ---------------------------------------------------------------------------


def _validate_stretch(cfg: SleeveBlockConfig) -> None:
    """Validate constants for STRETCH mode."""
    if abs(cfg.cap_offset) > 1e-9:
        raise ValueError(
            f"cap_offset={cfg.cap_offset / CM:.4f} cm must be 0 for STRETCH — "
            "the formula is cap_height = armscye_circumference / 3 with no additive constant."
        )
    if cfg.upper_arm_ease is None:
        raise ValueError(
            "upper_arm_ease must not be None for STRETCH "
            "(sleeve_width = upper_arm_circumference + upper_arm_ease)."
        )
    if not (-1.0 * CM - 1e-9 <= cfg.upper_arm_ease <= 2.0 * CM + 1e-9):
        raise ValueError(
            f"upper_arm_ease={cfg.upper_arm_ease / CM:.2f} cm is outside the valid range "
            "[−1, +2] cm for STRETCH (sleeve_width = upper_arm_circumference + upper_arm_ease)."
        )
    if cfg.hem_ease is not None and not (-1e-9 <= cfg.hem_ease <= 5.0 * CM + 1e-9):
        raise ValueError(
            f"hem_ease={cfg.hem_ease / CM:.2f} cm is outside the valid range "
            "[0, 5] cm for STRETCH "
            "(sleeve_hem_width = wrist_circumference + hem_ease; target 15–22 cm)."
        )


def _validate_wide(cfg: SleeveBlockConfig) -> None:
    """Validate constants for WIDE mode."""
    if not (-2.0 * CM - 1e-9 <= cfg.cap_offset <= 1e-9):
        raise ValueError(
            f"cap_offset={cfg.cap_offset / CM:.2f} cm is outside the valid range "
            "[−2, 0] cm for WIDE (cap_height = armscye_height / 3 + const, const ∈ [−2, 0] cm)."
        )
    if cfg.upper_arm_ease is not None:
        raise ValueError(
            "upper_arm_ease must be None for WIDE — "
            "sleeve width is not defined for this sleeve type."
        )
    if cfg.hem_ease is not None:
        raise ValueError(
            "hem_ease must be None for WIDE — sleeve hem width is not defined for this sleeve type."
        )


def _validate_narrow_blouse(cfg: SleeveBlockConfig) -> None:
    """Validate constants for NARROW_BLOUSE mode."""
    if not (-1.5 * CM - 1e-9 <= cfg.cap_offset <= -0.5 * CM + 1e-9):
        raise ValueError(
            f"cap_offset={cfg.cap_offset / CM:.2f} cm is outside the valid range "
            "[−0.5, −1.5] cm for NARROW_BLOUSE "
            "(cap_height = armscye_height/2 − arm_diameter/5 − const, const ∈ [0.5, 1.5] cm)."
        )
    if cfg.upper_arm_ease is not None and not (
        2.0 * CM - 1e-9 <= cfg.upper_arm_ease <= 4.0 * CM + 1e-9
    ):
        raise ValueError(
            f"upper_arm_ease={cfg.upper_arm_ease / CM:.2f} cm is outside the valid range "
            "[2, 4] cm for NARROW_BLOUSE (sleeve_width = upper_arm_circumference + upper_arm_ease)."
        )
    if cfg.hem_ease is not None and not (2.0 * CM - 1e-9 <= cfg.hem_ease <= 10.0 * CM + 1e-9):
        raise ValueError(
            f"hem_ease={cfg.hem_ease / CM:.2f} cm is outside the valid range "
            "[2, 10] cm for NARROW_BLOUSE "
            "(sleeve_hem_width = wrist_circumference + hem_ease; target 18–26 cm)."
        )


def _validate_narrow_jacket(cfg: SleeveBlockConfig) -> None:
    """Validate constants for NARROW_JACKET mode."""
    if not (-2.0 * CM - 1e-9 <= cfg.cap_offset <= -1.0 * CM + 1e-9):
        raise ValueError(
            f"cap_offset={cfg.cap_offset / CM:.2f} cm is outside the valid range "
            "[−1, −2] cm for NARROW_JACKET "
            "(cap_height = armscye_height/2 − arm_diameter/10 − const, const ∈ [1, 2] cm)."
        )
    if cfg.upper_arm_ease is not None and not (
        4.0 * CM - 1e-9 <= cfg.upper_arm_ease <= 8.0 * CM + 1e-9
    ):
        raise ValueError(
            f"upper_arm_ease={cfg.upper_arm_ease / CM:.2f} cm is outside the valid range "
            "[4, 8] cm for NARROW_JACKET (sleeve_width = upper_arm_circumference + upper_arm_ease)."
        )
    if cfg.hem_ease is not None and not (8.0 * CM - 1e-9 <= cfg.hem_ease <= 16.0 * CM + 1e-9):
        raise ValueError(
            f"hem_ease={cfg.hem_ease / CM:.2f} cm is outside the valid range "
            "[8, 16] cm for NARROW_JACKET "
            "(sleeve_hem_width = wrist_circumference + hem_ease; target 26–34 cm)."
        )


# ---------------------------------------------------------------------------
# SleeveBlockConfig
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SleeveBlockConfig:
    """Construction constants for the sleeve cap and width formulas.

    The :attr:`mode` field selects the formula structure and fixes the
    coefficients ``cap_height_frac``, ``cap_arm_diameter_frac``, and
    ``cap_uses_circumference`` — those are **derived properties**, not
    user-configurable fields.  The user only sets the three constants whose
    valid ranges depend on the chosen mode:

    +-----------------+----------------------------------+---------------+-----------------+
    | Mode            | cap height formula               | upper_arm_ease range | hem_ease range  |
    +=================+==================================+======================+=================+
    | STRETCH         | circumference / 3                | [−1, +2] cm          | [0, 5] cm       |
    +-----------------+----------------------------------+----------------------+-----------------+
    | WIDE            | height / 3 + const               | must be None         | must be None    |
    |                 | const ∈ [−2, 0] cm               |                      |                 |
    +-----------------+----------------------------------+----------------------+-----------------+
    | NARROW_BLOUSE   | height/2 − diam/5 − const        | [2, 4] cm            | [2, 10] cm      |
    |                 | const ∈ [0.5, 1.5] cm            |                      |                 |
    +-----------------+----------------------------------+----------------------+-----------------+
    | NARROW_JACKET   | height/2 − diam/10 − const       | [4, 8] cm            | [8, 16] cm      |
    |                 | const ∈ [1, 2] cm                |                      |                 |
    +-----------------+----------------------------------+----------------------+-----------------+

    Use the pre-built class-level presets instead of constructing manually:

    * ``SleeveBlockConfig.STRETCH``       — stretch sleeve, circumference-based cap.
    * ``SleeveBlockConfig.WIDE``          — wider sleeve, height-based cap + offset.
    * ``SleeveBlockConfig.NARROW_BLOUSE`` — narrow sleeve for blouses / dresses.
    * ``SleeveBlockConfig.NARROW_JACKET`` — narrow sleeve for jackets / coats.

    Attributes:
        mode: :class:`SleeveMode` — determines formula structure, fixed
            coefficients, and valid constant ranges.
        cap_offset: Additive constant (mm) in the sleeve cap height formula.
            Must be 0 for STRETCH, [−2, 0] cm for WIDE, [−0.5, −1.5] cm for
            NARROW_BLOUSE, and [−1, −2] cm for NARROW_JACKET.
        upper_arm_ease: Constant (mm) added to upper arm circumference for sleeve
            width.  Must be ``None`` for WIDE; may be ``None`` for NARROW
            (skips sleeve width computation).
        hem_ease: Constant (mm) added to wrist circumference for sleeve hem
            width.  Must be ``None`` for WIDE; may be ``None`` for NARROW
            (skips hem width computation).
    """

    # ── Presets (class-level, not dataclass fields) ───────────────────────────
    STRETCH: ClassVar[SleeveBlockConfig]
    WIDE: ClassVar[SleeveBlockConfig]
    NARROW_BLOUSE: ClassVar[SleeveBlockConfig]
    NARROW_JACKET: ClassVar[SleeveBlockConfig]

    # ── User-configurable fields ──────────────────────────────────────────────
    mode: SleeveMode
    cap_offset: float  # additive constant in sleeve cap height formula
    upper_arm_ease: float | None  # ease added to upper arm circumference; None → not applicable
    hem_ease: float | None  # ease added to wrist circumference for hem width; None → not applicable

    # ── Derived properties (fixed by mode, not user-configurable) ─────────────

    @property
    def cap_uses_circumference(self) -> bool:
        """``True`` for STRETCH (circumference base); ``False`` for WIDE / NARROW (height base)."""
        return self.mode == SleeveMode.STRETCH

    @property
    def cap_height_frac(self) -> float:
        """Coefficient for the base measurement: ``1/3`` for STRETCH / WIDE, ``1/2`` for NARROW."""
        return 1.0 / 3.0 if self.mode in (SleeveMode.STRETCH, SleeveMode.WIDE) else 0.5

    @property
    def cap_arm_diameter_frac(self) -> float:
        """Arm diameter correction coefficient.

        Returns ``1/5`` for NARROW_BLOUSE, ``1/10`` for NARROW_JACKET, ``0`` otherwise.
        """
        if self.mode == SleeveMode.NARROW_BLOUSE:
            return 1.0 / 5.0
        if self.mode == SleeveMode.NARROW_JACKET:
            return 1.0 / 10.0
        return 0.0

    # ── Validation ────────────────────────────────────────────────────────────

    def __post_init__(self) -> None:
        """Validate constants against the precise ranges for :attr:`mode`.

        Raises:
            ValueError: When any constant falls outside its mode-specific range.
        """
        _VALIDATORS = {
            SleeveMode.STRETCH: _validate_stretch,
            SleeveMode.WIDE: _validate_wide,
            SleeveMode.NARROW_BLOUSE: _validate_narrow_blouse,
            SleeveMode.NARROW_JACKET: _validate_narrow_jacket,
        }
        _VALIDATORS[self.mode](self)

    # ── Preset factory methods ────────────────────────────────────────────────

    @classmethod
    def _make_stretch(cls) -> SleeveBlockConfig:
        """STRETCH: cap from armscye_circumference/3; for knit & elastic woven fabrics."""
        return cls(
            mode=SleeveMode.STRETCH,
            cap_offset=0.0,
            upper_arm_ease=0.5 * CM,  # mid of range [−1, +2] cm
            hem_ease=2.5 * CM,  # mid of range [0, 5] cm; sleeve hem width target 15–22 cm
        )

    @classmethod
    def _make_wide(cls) -> SleeveBlockConfig:
        """WIDE preset: armscye_height/3 + offset; shirt-style; no sleeve width / hem formulas."""
        return cls(
            mode=SleeveMode.WIDE,
            cap_offset=-1.0 * CM,  # mid of range [−2, 0] cm
            upper_arm_ease=None,
            hem_ease=None,
        )

    @classmethod
    def _make_narrow_blouse(cls) -> SleeveBlockConfig:
        """NARROW_BLOUSE: cap from armscye_height/2 − arm_diameter/5 − const; blouses & dresses."""
        return cls(
            mode=SleeveMode.NARROW_BLOUSE,
            cap_offset=-1.0 * CM,  # mid of range [−0.5, −1.5] cm
            upper_arm_ease=3.0 * CM,  # mid of range [2, 4] cm
            hem_ease=6.0 * CM,  # mid of range [2, 10] cm; sleeve hem width target 18–26 cm
        )

    @classmethod
    def _make_narrow_jacket(cls) -> SleeveBlockConfig:
        """NARROW_JACKET: cap from armscye_height/2 − arm_diameter/10 − const; jackets & coats."""
        return cls(
            mode=SleeveMode.NARROW_JACKET,
            cap_offset=-1.5 * CM,  # mid of range [−1, −2] cm
            upper_arm_ease=6.0 * CM,  # mid of range [4, 8] cm
            hem_ease=12.0 * CM,  # mid of range [8, 16] cm; sleeve hem width target 26–34 cm
        )


# Presets — frozen dataclass instances assigned after class body.
SleeveBlockConfig.STRETCH = SleeveBlockConfig._make_stretch()
SleeveBlockConfig.WIDE = SleeveBlockConfig._make_wide()
SleeveBlockConfig.NARROW_BLOUSE = SleeveBlockConfig._make_narrow_blouse()
SleeveBlockConfig.NARROW_JACKET = SleeveBlockConfig._make_narrow_jacket()


# ---------------------------------------------------------------------------
# SleeveConfig
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SleeveConfig:
    """Garment-design choices for a sleeve — independent of body measurements.

    Attributes:
        sleeve_length: ArL — Ärmellänge (finished sleeve length in mm,
            measured from the shoulder point to the hem).
    """

    sleeve_length: float  # ArL — Ärmellänge


# ---------------------------------------------------------------------------
# SleeveMeasurements
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SleeveMeasurements:
    """Body measurements required for sleeve construction.

    All values are in mm (the project's internal unit).

    Attributes:
        armscye_width: ArD — Armdurchmesser (arm diameter / armscye width,
            taken from :attr:`~sewpat.measurements.BlouseMeasurements.armscye_width`).
        upper_arm: OaU — Oberarmumfang (upper arm circumference, taken from
            :attr:`~sewpat.person.Person.upper_arm`).
        wrist: HgU — Handgelenksumfang (wrist circumference, taken from
            :attr:`~sewpat.person.Person.wrist`).
    """

    armscye_width: float  # ArD — Armdurchmesser
    upper_arm: float  # OaU — Oberarmumfang
    wrist: float  # HgU — Handgelenksumfang

    @classmethod
    def from_blouse_and_person(
        cls,
        meas: BlouseMeasurements,
        person: Person,
    ) -> SleeveMeasurements:
        """Build :class:`SleeveMeasurements` from blouse measurements and a person.

        Args:
            meas:   Ease-adjusted blouse measurements — provides ``armscye_width``
                    (ArD, already includes ease).
            person: Raw body measurements — provides ``upper_arm`` (OaU) and
                    ``wrist`` (HgU).

        Returns:
            :class:`SleeveMeasurements` with all three fields populated.

        Raises:
            ValueError: If ``person.upper_arm`` or ``person.wrist`` is ``None``.
        """
        if person.upper_arm is None:
            raise ValueError(
                "person.upper_arm (OaU — Oberarmumfang) must be set for sleeve construction."
            )
        if person.wrist is None:
            raise ValueError(
                "person.wrist (HgU — Handgelenksumfang) must be set for sleeve construction."
            )
        return cls(
            armscye_width=meas.armscye_width,
            upper_arm=person.upper_arm,
            wrist=person.wrist,
        )


# ---------------------------------------------------------------------------
# SleeveArmhole
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SleeveArmhole:
    """Armhole geometry derived from a finished bodice block.

    Holds the stitch-line Bézier curves and key notch points from both the
    back and front bodice pieces, together with the construction-grid lines
    needed to derive the armscye height and circumference for sleeve construction.

    Build via :meth:`from_block` to extract the data directly from a
    completed :class:`~sewpat.blocks.TopBlock` and
    :class:`~sewpat.grids.TopGrid`.

    Attributes:
        back_armscye_lower: Lower back armscye Bézier stitch line — from the
            side-seam point at bust level up to the back armscye notch (hÄP).
        back_armscye_upper: Upper back armscye Bézier stitch line — from hÄP
            up to the shoulder endpoint.
        front_armscye:      Front armscye Bézier stitch line.
        hAeP:               hÄP — Hinterer Ärmellochpunkt (back armscye notch
            point, where the sleeve notch will be placed).
        vAeP:               vÄP — Vorderer Ärmellochpunkt (front armscye notch
            point).
        bust_line:          Brustlinie — horizontal chest/bust grid line, used
            to locate the deepest point of the armscye.
        armscye_back_line:  Vertical grid line at the back armscye position —
            its intersection with ``bust_line`` gives the bottom of the
            armscye height measurement.
        armscye_front_line: Vertical grid line at the front armscye position.
    """

    # ── Stitch lines ──────────────────────────────────────────────────────────
    back_armscye_lower: CubicBezier
    back_armscye_upper: CubicBezier
    front_armscye: CubicBezier

    # ── Notch points ──────────────────────────────────────────────────────────
    hAeP: Point  # hÄP — Hinterer Ärmellochpunkt
    vAeP: Point  # vÄP — Vorderer Ärmellochpunkt

    # ── Grid lines ────────────────────────────────────────────────────────────
    bust_line: Segment  # Brustlinie
    armscye_back_line: Segment  # Armloch-Hintere Linie
    armscye_front_line: Segment  # Armloch-Vordere Linie

    # ── Derived measures ──────────────────────────────────────────────────────

    @property
    def armscye_height(self) -> float:
        """AlH — Armlöcherhöhe: vertical height of the armscye opening (mm).

        Computed as the absolute vertical distance between:

        * **bottom** — the intersection of ``armscye_back_line`` with
          ``bust_line`` (the deepest point of the armscye at construction
          grid level).
        * **top** — ``back_armscye_upper.p3``, the actual shoulder endpoint
          of the back armscye stitch line (includes all shoulder-raise and
          shoulder-drop adjustments).
        """
        pt_bottom = intersect(self.armscye_back_line, self.bust_line)[0]
        pt_top = self.back_armscye_upper.p3
        return abs(pt_bottom.y - pt_top.y)

    @property
    def armscye_circumference(self) -> float:
        """AlU — Armlochümfang: total armscye seam arc length (mm).

        Sum of the arc lengths of the three stitch-line curves:
        ``back_armscye_lower`` + ``back_armscye_upper`` + ``front_armscye``.
        """
        return seam_length([self.back_armscye_lower, self.back_armscye_upper, self.front_armscye])

    @classmethod
    def from_block(
        cls,
        block: TopBlock,
        grid: TopGrid,
    ) -> SleeveArmhole:
        """Extract the armhole geometry from a finished bodice block.

        Args:
            block: The completed bodice block — provides stitch-line curves
                   and armscye notch points.
            grid:  The construction grid used to build *block* — provides the
                   bust line and vertical armscye guide lines.

        Returns:
            :class:`SleeveArmhole` ready for sleeve construction.
        """
        return cls(
            back_armscye_lower=block.back.armscye_lower,
            back_armscye_upper=block.back.armscye_upper,
            front_armscye=block.front.armscye,
            hAeP=block.back.armscye_control,
            vAeP=block.front.armscye_control,
            bust_line=grid.chest,
            armscye_back_line=grid.armscye_back,
            armscye_front_line=grid.armscye_front,
        )


# ---------------------------------------------------------------------------
# SleeveConstructionMeasures
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SleeveConstructionMeasures:
    """Full set of construction measures for a sleeve block.

    All lengths are in mm (the project's internal unit).  The measures split
    into three groups:

    * **From armhole geometry** — ``armscye_height``, ``armscye_circumference``
      (computed from the stitch lines).
    * **From body measurements / garment config** — ``armscye_width``,
      ``wrist_circumference``, ``upper_arm_circumference``, ``sleeve_length``.
    * **Derived by formula** — ``cap_height``, ``sleeve_width``,
      ``sleeve_hem_width``, ``upper_arm_ease``.

    ``sleeve_width``, ``sleeve_hem_width`` and ``upper_arm_ease`` are ``None``
    for ``SleeveType.WIDE`` because
    that style does not specify upper-arm or hem-width formulas.

    Build via :meth:`from_armhole`.

    Attributes:
        armscye_height:         Armlöcherhöhe — vertical height of the armscye
                                opening (from armhole geometry).
        armscye_circumference:  Armlochümfang — total armscye seam arc length
                                (from armhole geometry).
        armscye_width:          Armdurchmesser — arm diameter / armscye width
                                (from body measurements).
        wrist_circumference:    Handgelenksumfang — wrist circumference.
        upper_arm_circumference: Oberarmumfang — upper arm circumference.
        sleeve_length:          Ärmellänge — finished sleeve length (from garment config).
        cap_height:             Ärmelkopfhöhe — sleeve cap height (derived by formula).
        sleeve_width:           Oberarmweite — upper arm width (derived); ``None`` for WIDE.
        sleeve_hem_width:       Ärmelaufschlagweite — sleeve hem width (derived);
                                ``None`` for WIDE.
        upper_arm_ease:         Erleichterungszugabe — ease constant used in the sleeve width
                                formula (= ``block_config.upper_arm_ease``); ``None`` for WIDE.
        sleeve_type: The :class:`SleeveType` used to select the formula constants.
    """

    # ── From armhole geometry ─────────────────────────────────────────────────
    armscye_height: float  # AlH Armlöcherhöhe
    armscye_circumference: float  # AlU Armlochümfang

    # ── From body measurements ────────────────────────────────────────────────
    armscye_width: float  # ArD Armdurchmesser
    wrist_circumference: float  # HgU Handgelenksumfang
    upper_arm_circumference: float  # OaU Oberarmumfang

    # ── From garment config ───────────────────────────────────────────────────
    sleeve_length: float  # ArL Ärmellänge

    # ── Derived by formula ────────────────────────────────────────────────────
    cap_height: float  # Ärmelkopfhöhe (AekH)
    sleeve_width: float | None  # OaW Oberarmweite — None for WIDE
    sleeve_hem_width: float | None  # AeSaW Ärmelaufschlagweite — None for WIDE
    upper_arm_ease: float | None  # Erleichterungszugabe (ease used) — None for WIDE

    # ── Meta ──────────────────────────────────────────────────────────────────
    sleeve_type: SleeveType

    @classmethod
    def from_armhole(
        cls,
        armhole: SleeveArmhole,
        meas: SleeveMeasurements,
        config: SleeveConfig,
        block_config: SleeveBlockConfig,
        sleeve_type: SleeveType,
    ) -> SleeveConstructionMeasures:
        """Compute all sleeve construction measures from geometry and measurements.

        Args:
            armhole:      Armhole geometry — provides ``armscye_height``
                          and ``armscye_circumference``.
            meas:         Sleeve body measurements — provides ``armscye_width``,
                          ``upper_arm_circumference``, ``wrist_circumference``.
            config:       Garment config — provides ``sleeve_length``.
            block_config: Formula constants — selects the cap height formula mode,
                          coefficients, and ease values.
            sleeve_type:  Sleeve style, stored for reference on the result.

        Returns:
            :class:`SleeveConstructionMeasures` with all fields populated.
        """
        armhole_h = armhole.armscye_height
        armhole_u = armhole.armscye_circumference

        # Sleeve cap height: circumference-based (STRETCH / WIDE)
        # or height-based with arm diameter correction (NARROW)
        if block_config.cap_uses_circumference:
            cap_height = armhole_u * block_config.cap_height_frac + block_config.cap_offset
        else:
            cap_height = (
                armhole_h * block_config.cap_height_frac
                - meas.armscye_width * block_config.cap_arm_diameter_frac
                + block_config.cap_offset
            )

        # Sleeve width = upper arm circumference + ease constant  (None for WIDE)
        sleeve_width: float | None = (
            meas.upper_arm + block_config.upper_arm_ease
            if block_config.upper_arm_ease is not None
            else None
        )

        # Sleeve hem width = wrist circumference + hem ease  (None for WIDE)
        sleeve_hem_width: float | None = (
            meas.wrist + block_config.hem_ease if block_config.hem_ease is not None else None
        )

        return cls(
            armscye_height=armhole_h,
            armscye_circumference=armhole_u,
            armscye_width=meas.armscye_width,
            wrist_circumference=meas.wrist,
            upper_arm_circumference=meas.upper_arm,
            sleeve_length=config.sleeve_length,
            cap_height=cap_height,
            sleeve_width=sleeve_width,
            sleeve_hem_width=sleeve_hem_width,
            upper_arm_ease=block_config.upper_arm_ease,
            sleeve_type=sleeve_type,
        )
