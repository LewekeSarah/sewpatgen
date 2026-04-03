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

All sleeve styles share the single :class:`SleeveConfig` garment config.  The
``cap_offset`` and ``ease`` fields on :class:`SleeveConfig` are consumed only
by :class:`~sewpat.grids.WideSleeveGrid`; they are ignored for other styles:

* ``SleeveConfig.cap_offset`` ∈ [0, 2] cm — 0 cm → highest / narrowest cap,
  2 cm → lowest / widest cap.
* ``SleeveConfig.ease`` ∈ [0, 1] cm — larger ease → narrower sleeve.

Typical usage::

    from sewpat.grids import WideSleeveGrid
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

    # Narrow blouse sleeve construction measures:
    cm = SleeveConstructionMeasures.from_armhole(
        armhole, meas, config, SleeveBlockConfig.NARROW_BLOUSE, SleeveType.NARROW
    )

    # Wide sleeve construction grid (cap_offset and ease taken from config):
    wide_config = SleeveConfig(sleeve_length=60 * CM, cap_offset=1 * CM, ease=0.5 * CM)
    wide_grid   = WideSleeveGrid.from_armhole(armhole, wide_config)
    pattern.add_part(wide_grid.part)
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, ClassVar

from .geometry import CubicBezier, Point, Segment, intersect, seam_length
from .measurements import BlouseMeasurements
from .person import Person
from .pleat import PleatConfig
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
# ButtonConfig
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ButtonConfig:
    """Button and buttonhole placement for a cuff pattern piece.

    Up to two horizontal rows are supported.  Each row produces one button
    mark (a circle) and one buttonhole mark (a short horizontal line).

    **Placement rules** — depend on which lap extensions are present:

    *Only overlap* (``cuff_overlap > 0``, no underlap):
        Button in the main cuff body at ``overlap/2`` from the main|overlap
        boundary, so that when the overlap is folded closed the button appears
        centred in the overlap.  Buttonhole centred in the overlap section.

    *Only underlap* (``cuff_underlap > 0``, no overlap):
        Button AT the underlap|main closure line.
        Buttonhole in the main cuff body, starting at the closure line and
        extending inward (fully inside the cuff).

    *Both underlap and overlap*:
        Button AT the underlap|main closure line.
        Buttonhole AT the main|overlap closure line.

    *No extensions*:
        Both marks centred in the main cuff body.

    *Two buttons* (``num_buttons = 2``) with an underlap wide enough for
    ``button_diameter``:
        Row 1 button at the centre of the underlap; Row 2 button in the cuff
        at the same distance from the closure line (symmetric around the
        underlap|main boundary).  Both rows share the same buttonhole
        X position.  Falls back to single-column placement when no underlap
        is present.

    A row is skipped only when the cuff height band is too small for the
    *margin* constraint.

    Attributes:
        num_buttons:     Number of buttons — 0, 1, or 2.
        button_diameter: Diameter of the button mark circle in mm.
                         Typical cuff buttons are 10–15 mm.
        margin:          Minimum distance from the top edge (Cuff Opening) and
                         from the fold line in mm.  Rows are distributed within
                         the band ``[margin, cuff_height − margin]``.
                         Default 10 mm (1 cm).
        buttonhole_ease: Extra length added to *button_diameter* to obtain the
                         buttonhole line length in mm (standard allowance for
                         the knot bar at each end).  Default 2 mm.
    """

    num_buttons: int = 1  # 0, 1, or 2
    button_diameter: float = 10.0  # mm — typical cuff button diameter
    margin: float = 10.0  # mm — min distance from top edge / fold line
    buttonhole_ease: float = 2.0  # mm — added to button_diameter for buttonhole line length

    def __post_init__(self) -> None:
        """Validate fields.

        Raises:
            ValueError: When *num_buttons* is not 0, 1, or 2, or when any
                        dimension field violates its constraint.
        """
        if self.num_buttons not in (0, 1, 2):
            raise ValueError(f"num_buttons must be 0, 1, or 2; got {self.num_buttons}.")
        if self.button_diameter <= 0:
            raise ValueError(f"button_diameter must be positive; got {self.button_diameter} mm.")
        if self.margin < 10:
            raise ValueError(f"margin must be grater then 10 mm; got {self.margin} mm.")
        if self.buttonhole_ease < 0:
            raise ValueError(
                f"buttonhole_ease must be non-negative; got {self.buttonhole_ease} mm."
            )


# ---------------------------------------------------------------------------
# CuffConfig
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CuffConfig:
    """Dimensions and closure configuration for the cuff pattern piece.

    Groups all cuff-specific settings: the physical dimensions of the band,
    the optional lap extensions for the button closure, and the button/buttonhole
    placement.  Pass a ``CuffConfig`` instance to
    :attr:`SleeveConfig.cuff_config` to activate cuff-piece generation.

    Attributes:
        length:        Bündchenlänge — flat circumference of the main cuff body
                       (mm).  Used to shorten the sleeve hem.
        width:         Bündchenbreite — height of one layer of the folded cuff
                       band (mm).  Full cut height is ``2 × width``.
        overlap:       Überschlag — width of the overlap extension (mm).
                       Default 0 (no overlap).
        underlap:      Unterschlag — width of the underlap extension (mm).
                       Default 0 (no underlap).
        button_config: Button and buttonhole placement.
                       ``None`` → no button marks are drawn.
    """

    length: float  # Bündchenlänge
    width: float  # Bündchenbreite (single height; cut = 2×)
    overlap: float = 0.0  # Überschlag
    underlap: float = 0.0  # Unterschlag
    button_config: ButtonConfig | None = None

    def __post_init__(self) -> None:
        """Validate all fields.

        Raises:
            ValueError: When any dimension is out of range.
        """
        if self.length <= 0:
            raise ValueError(f"length must be positive; got {self.length / CM:.2f} cm.")
        if self.width <= 0:
            raise ValueError(f"width must be positive; got {self.width / CM:.2f} cm.")
        if self.overlap < 0:
            raise ValueError(f"overlap must be non-negative; got {self.overlap / CM:.2f} cm.")
        if self.underlap < 0:
            raise ValueError(f"underlap must be non-negative; got {self.underlap / CM:.2f} cm.")


# ---------------------------------------------------------------------------
# SleeveConfig
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SleeveConfig:
    """Garment-design choices for a sleeve — independent of body measurements.

    ``sleeve_length`` applies to all sleeve styles.  ``cap_offset`` and
    ``ease`` are consumed only by :class:`~sewpat.grids.WideSleeveGrid`; they
    are ignored for other styles.

    +--------------+--------------------+-------------------------------------+
    | Field        | Used by            | Effect                              |
    +==============+====================+=====================================+
    | sleeve_length| all styles         | finished sleeve length (mm)         |
    +--------------+--------------------+-------------------------------------+
    | cap_offset   | wide sleeve grid   | [0, 2] cm; 0 → highest/narrowest;  |
    |              |                    | 2 cm → lowest/widest cap            |
    +--------------+--------------------+-------------------------------------+
    | ease         | wide sleeve grid   | [0, 1] cm; larger → narrower sleeve |
    +--------------+--------------------+-------------------------------------+
    | cuff_config  | wide sleeve hem    | cuff dimensions + closure config;   |
    |              | + cuff piece       | ``None`` → no cuff piece            |
    +--------------+--------------------+-------------------------------------+
    | slit_height  | wide sleeve slit   | height of the slit (8–10 cm);       |
    |              |                    | ``None`` = no slit                  |
    +--------------+--------------------+-------------------------------------+
    | pleat_config | wide sleeve hem    | pleat layout; ``None`` = no pleats  |
    +--------------+--------------------+-------------------------------------+

    Attributes:
        sleeve_length: ArL — Ärmellänge (finished sleeve length in mm).
        cap_offset: Reduction applied to ``armscye_height / 3`` to derive the
            wide sleeve cap height.  Only used by
            :class:`~sewpat.grids.WideSleeveGrid`.
        ease: Circumference ease subtracted from ``armscye_circumference``
            before computing the wide sleeve width.  Only used by
            :class:`~sewpat.grids.WideSleeveGrid`.
        cuff_config: All cuff dimensions and closure settings in one object.
            ``None`` → no cuff pattern piece is generated and no hem shortening
            is applied.
        slit_height: Schlitzhöhe — height of the sleeve slit in mm (typically
            80–100 mm).  ``None`` → no slit.
        pleat_config: Pleat layout for the hem.  ``None`` → no pleats.
    """

    sleeve_length: float  # ArL — Ärmellänge

    # ── Wide sleeve grid constants ────────────────────────────────────────────
    cap_offset: float = 1.0 * CM  # [0, 2] cm — mid of range
    ease: float = 0.5 * CM  # [0, 1] cm — mid of range

    # ── Cuff piece + hem shortening ───────────────────────────────────────────
    cuff_config: CuffConfig | None = None  # None → no cuff piece

    # ── Slit & pleats ─────────────────────────────────────────────────────────
    slit_height: float | None = None  # Schlitzhöhe; None → no slit
    pleat_config: PleatConfig | None = None  # pleat layout; None → no pleats

    def __post_init__(self) -> None:
        """Validate fields against their allowed ranges."""
        if not (-1e-9 <= self.cap_offset <= 2.0 * CM + 1e-9):
            raise ValueError(f"cap_offset={self.cap_offset / CM:.2f} cm is outside [0, 2] cm.")
        if not (-1e-9 <= self.ease <= 1.0 * CM + 1e-9):
            raise ValueError(f"ease={self.ease / CM:.2f} cm is outside [0, 1] cm.")
        if self.slit_height is not None and self.slit_height < -1e-9:
            raise ValueError(f"slit_height={self.slit_height / CM:.2f} cm must be non-negative.")
        # CuffConfig and PleatConfig validate themselves in their own __post_init__


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
        back_armscye_notch: hÄP — Hinterer Ärmellochpunkt (back armscye notch
            point, where the sleeve notch will be placed).
        front_armscye_notch: vÄP — Vorderer Ärmellochpunkt (front armscye notch
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
    back_armscye_notch: Point  # hÄP — Hinterer Ärmellochpunkt
    front_armscye_notch: Point  # vÄP — Vorderer Ärmellochpunkt

    # ── Grid lines ────────────────────────────────────────────────────────────
    bust_line: Segment  # Brustlinie
    armscye_back_line: Segment  # Armloch-Hintere Linie
    armscye_front_line: Segment  # Armloch-Vordere Linie

    # ── Derived measures ──────────────────────────────────────────────────────

    @property
    def back_armscye_height(self) -> float:
        """Back component of the armscye height (mm).

        Orthogonal distance from the back-armscye shoulder endpoint
        (``back_armscye_upper.p3``) to the bust line, computed via
        :meth:`~sewpat.geometry.Segment.project_point` so the result is
        correct regardless of the bust line's orientation in the coordinate
        system.
        """
        pt = self.back_armscye_upper.p3
        return pt.distance_to(self.bust_line.project_point(pt))

    @property
    def front_armscye_height(self) -> float:
        """Front component of the armscye height (mm).

        Euclidean distance from the upper endpoint of the front armscye curve
        (``front_armscye.p0``, the shoulder-armscye junction) to the
        intersection of ``armscye_front_line`` with ``bust_line`` (the front
        armscye grid reference at bust level).
        """
        pt_shoulder = self.front_armscye.p0
        pt_bottom = intersect(self.armscye_front_line, self.bust_line)[0]
        return pt_shoulder.distance_to(pt_bottom)

    @property
    def armscye_height(self) -> float:
        """AlH — Armlöcherhöhe: total armscye height in mm.

        Sum of :attr:`back_armscye_height` and :attr:`front_armscye_height`.
        Each component is measured from the respective shoulder endpoint to the
        bust line.
        """
        return self.back_armscye_height + self.front_armscye_height

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
            back_armscye_notch=block.back.armscye_control,
            front_armscye_notch=block.front.armscye_control,
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
    # None for SleeveType.WIDE — body circumferences are not required by the wide-sleeve formulas.
    armscye_width: float | None  # ArD Armdurchmesser
    wrist_circumference: float | None  # HgU Handgelenksumfang
    upper_arm_circumference: float | None  # OaU Oberarmumfang

    # ── From garment config ───────────────────────────────────────────────────
    sleeve_length: float  # ArL Ärmellänge

    # ── Derived by formula ────────────────────────────────────────────────────
    cap_height: float  # Ärmelkopfhöhe (AekH)
    sleeve_width: float | None  # OaW Oberarmweite — None for WIDE via from_armhole
    sleeve_hem_width: float | None  # AeSaW Ärmelaufschlagweite — None for WIDE
    upper_arm_ease: float | None  # Erleichterungszugabe (ease used) — None for WIDE

    # ── Meta ──────────────────────────────────────────────────────────────────
    sleeve_type: SleeveType

    @classmethod
    def from_armhole(
        cls,
        armhole: SleeveArmhole,
        meas: SleeveMeasurements | None,
        config: SleeveConfig,
        block_config: SleeveBlockConfig,
        sleeve_type: SleeveType,
    ) -> SleeveConstructionMeasures:
        """Compute all sleeve construction measures from armhole geometry.

        For **WIDE** sleeves ``meas`` may be ``None`` — body circumferences are
        not needed because the wide sleeve width is derived purely from armscye
        geometry via the Pythagorean formula.  When ``meas`` is ``None`` the
        body-measurement fields (``armscye_width``, ``wrist_circumference``,
        ``upper_arm_circumference``) are stored as ``None``.

        For **STRETCH** and **NARROW** sleeves ``meas`` is required; a
        :exc:`ValueError` is raised when it is ``None``.

        .. note::
            For WIDE mode ``meas`` may be ``None`` because
            ``cap_arm_diameter_frac = 0`` — the arm-diameter term drops out of
            the cap height formula and body circumferences are not needed.
            When ``meas`` is ``None`` the body-measurement fields
            (``armscye_width``, ``wrist_circumference``,
            ``upper_arm_circumference``) are stored as ``None``.

        Args:
            armhole:      Armhole geometry — provides ``armscye_height``
                          and ``armscye_circumference``.
            meas:         Sleeve body measurements. May be ``None`` for WIDE;
                          required for STRETCH and NARROW.
            config:       Garment config — provides ``sleeve_length`` and
                          ``ease`` (for the WIDE sleeve width formula).
            block_config: Formula constants — selects the formula path and
                          coefficients.  For WIDE, ``block_config.cap_offset``
                          is the additive constant for cap height.
            sleeve_type:  Sleeve style, stored for reference on the result.

        Returns:
            :class:`SleeveConstructionMeasures` with all fields populated.

        Raises:
            ValueError: When ``meas`` is ``None`` for a non-WIDE mode, or
                when the WIDE geometry is infeasible.
        """
        armhole_h = armhole.armscye_height
        armhole_u = armhole.armscye_circumference
        is_wide = block_config.mode == SleeveMode.WIDE

        if meas is None and not is_wide:
            raise ValueError(
                "meas (SleeveMeasurements) is required for non-WIDE sleeve types "
                f"(mode={block_config.mode.value!r})."
            )

        # ── Cap height ────────────────────────────────────────────────────────
        # The original formula covers all modes uniformly:
        #   STRETCH:        circumference / 3  (cap_arm_diameter_frac = 0)
        #   WIDE:           height / 3 + block_config.cap_offset
        #                   (cap_arm_diameter_frac = 0, so armscye_w drops out)
        #   NARROW_BLOUSE:  height / 2 − armscye_w / 5 + block_config.cap_offset
        #   NARROW_JACKET:  height / 2 − armscye_w / 10 + block_config.cap_offset
        if block_config.cap_uses_circumference:
            cap_height = armhole_u * block_config.cap_height_frac + block_config.cap_offset
        else:
            armscye_w = meas.armscye_width if meas is not None else 0.0
            cap_height = (
                armhole_h * block_config.cap_height_frac
                - armscye_w * block_config.cap_arm_diameter_frac
                + block_config.cap_offset
            )

        # ── Sleeve width ──────────────────────────────────────────────────────
        sleeve_width: float | None
        if is_wide:
            # Pythagorean formula: sleeve_width = sqrt((armscye_circ/2 − ease)² − cap_height²)
            # sleeve_width is the HALF-width (centre fold → side seam); the full
            # sleeve spans 2 × sleeve_width.
            radicand = (armhole_u / 2 - config.ease) ** 2 - cap_height**2
            if radicand < 0:
                raise ValueError(
                    f"Infeasible wide sleeve geometry: "
                    f"(armscye_circumference − ease)² − cap_height² = {radicand:.2f} mm² < 0. "
                    f"Reduce cap_offset or ease, or verify that the armhole belongs to a real "
                    f"bodice block."
                )
            sleeve_width = math.sqrt(radicand)
        elif block_config.upper_arm_ease is not None and meas is not None:
            sleeve_width = meas.upper_arm + block_config.upper_arm_ease
        else:
            sleeve_width = None

        # ── Sleeve hem width ──────────────────────────────────────────────────────
        # WIDE: derived from cuff garment config (not wrist circumference).
        #   sleeve_hem_width = cuff_length + pleat_config.depth × pleat_config.num_pleats
        # Other modes: wrist circumference + hem ease from block config.
        sleeve_hem_width: float | None
        if is_wide and config.cuff_config is not None:
            pleat_total = (
                config.pleat_config.depth * config.pleat_config.num_pleats
                if config.pleat_config is not None
                else 0.0
            )
            sleeve_hem_width = config.cuff_config.length + pleat_total
        elif not is_wide and meas is not None and block_config.hem_ease is not None:
            sleeve_hem_width = meas.wrist + block_config.hem_ease
        else:
            sleeve_hem_width = None

        return cls(
            armscye_height=armhole_h,
            armscye_circumference=armhole_u,
            armscye_width=meas.armscye_width if meas is not None else None,
            wrist_circumference=meas.wrist if meas is not None else None,
            upper_arm_circumference=meas.upper_arm if meas is not None else None,
            sleeve_length=config.sleeve_length,
            cap_height=cap_height,
            sleeve_width=sleeve_width,
            sleeve_hem_width=sleeve_hem_width,
            upper_arm_ease=block_config.upper_arm_ease,
            sleeve_type=sleeve_type,
        )
