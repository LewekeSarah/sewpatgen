"""Pleat markings for sewing patterns.

A :class:`PleatConfig` holds every layout parameter for a group of pleats.
A :class:`Pleat` stores six pre-computed endpoint pairs and renders the
standard notation onto any :class:`~sewpat.pattern.PatternPart` via
:meth:`Pleat.apply_to`.  Use the class-method :meth:`Pleat.build_along_seam`
to turn a :class:`PleatConfig` into a list of :class:`Pleat` objects anchored
to a concrete seam edge.

The design mirrors :class:`~sewpat.geometry.Dart`: geometry is resolved at
construction time from the concrete seam edge, so :class:`Pleat` itself is
coordinate-system-free and reusable across any pattern context (sleeve hems,
bodice backs, trouser waistbands, …).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar

from .geometry import Segment
from .style import STYLE_FOLD, STYLE_PLEAT_ARROW, STYLE_PLEAT_FOLD
from .units import CM

if TYPE_CHECKING:
    from collections.abc import Callable

    from .geometry import Point
    from .pattern import PatternPart

__all__ = ["Pleat", "PleatConfig"]


# ---------------------------------------------------------------------------
# PleatConfig
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PleatConfig:
    """Layout parameters for a group of pleats along a seam edge.

    Holds every piece of information needed by :meth:`Pleat.build_along_seam`
    to position and size the pleats.  Separating configuration from geometry
    makes it easy to share the same pleat layout across different blocks or
    re-use it in tests.

    Layout convention (matches the wide-sleeve hem):

    * **1 right pleat** — placed ``slit_offset`` to the right of the anchor
      point (the slit), folds away from the anchor (rightward).
    * **``num_pleats − 1`` left pleats** — placed to the left of the anchor,
      spaced ``depth + spacing`` centre-to-centre, each folding leftward
      (away from the anchor).

    Attributes:
        depth:       Total pleat width in mm (left fold edge to right fold edge).
        num_pleats:  Total number of pleats (1 right + remaining left).
        slit_offset: Gap in mm from the slit / anchor edge to the nearest
                     fold edge of the nearest pleat on each side.  Default 15 mm.
        spacing:     Edge-to-edge gap in mm between consecutive left pleats.
                     Must be ≥ ``depth / 2`` when ``num_pleats > 2`` (so
                     adjacent left pleats cannot overlap).  Default 0 mm.
        height:      Height of the pleat start line above the straight seam in
                     mm.  All fold lines for this group share this height.
                     Default 40 mm (4 cm).
    """

    depth: float  # total pleat width (left fold to right fold)
    num_pleats: int  # 1 right pleat + (num_pleats - 1) left pleats
    slit_offset: float = 1.5 * CM  # gap: slit edge → nearest pleat fold edge
    spacing: float = 0.0  # edge-to-edge gap between consecutive left pleats
    height: float = 4.0 * CM  # pleat start line height above straight seam

    def __post_init__(self) -> None:
        """Validate all fields.

        Raises:
            ValueError: When any field is outside its valid range.
        """
        if self.depth < -1e-9:
            raise ValueError(f"depth={self.depth / CM:.2f} cm must be non-negative.")
        if self.num_pleats < 0:
            raise ValueError(f"num_pleats={self.num_pleats} must be non-negative.")
        if self.slit_offset < -1e-9:
            raise ValueError(f"slit_offset={self.slit_offset / CM:.2f} cm must be non-negative.")
        if self.spacing < -1e-9:
            raise ValueError(f"spacing={self.spacing / CM:.2f} cm must be non-negative.")
        if self.num_pleats > 2 and self.depth > 1e-9 and self.spacing < self.depth / 2 - 1e-9:
            raise ValueError(
                f"spacing={self.spacing / CM:.2f} cm must be ≥ "
                f"depth/2={self.depth / (2 * CM):.2f} cm "
                "(edge-to-edge gap between consecutive left pleats must be at least "
                "half the pleat depth when num_pleats > 2)."
            )
        if self.height < 1e-9:
            raise ValueError(f"height={self.height / CM:.2f} cm must be positive.")


# ---------------------------------------------------------------------------
# Pleat
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Pleat:
    """Pleat marking anchored to a curved seam edge.

    Each pleat is defined by **six points** — the three fold lines each run
    from a shared *pleat start line* (inside the garment piece) down to the
    curved seam edge.  All points are resolved before the ``Pleat`` is
    created, mirroring how :class:`~sewpat.geometry.Dart` stores its leg
    points on the seam edge.

    Rendering via :meth:`apply_to` produces:

    * **Three fold lines** — from the seam edge (bottom) to the pleat start
      line (top), one each for the left / centre / right fold positions.
      Rendered in the standard fold-line style (grey dashed).
    * **Direction arrow** — at the pleat start line, spanning from the outer
      edge *opposite* to the fold direction to the fold-direction edge, so
      the arrowhead clearly indicates which way the fabric folds.
    * **Three roof markers** (∧) — stacked inside the fold area with apex on
      the centre fold line and feet on the left / right fold lines.

    Prefer building instances via :meth:`build_along_seam` rather than
    constructing directly.

    Attributes:
        bottom_left:   Left fold line foot on the curved seam edge.
        bottom_center: Centre fold line foot on the curved seam edge.
        bottom_right:  Right fold line foot on the curved seam edge.
        top_left:      Left fold line top at the pleat start line.
        top_center:    Centre fold line top at the pleat start line.
        top_right:     Right fold line top at the pleat start line.
        fold_left:     ``True`` → pleat folds toward ``top_left`` (away from
                       the slit for left-side pleats); ``False`` → toward
                       ``top_right``.
    """

    # ── Seam-edge points (bottom of fold lines) ───────────────────────────────
    bottom_left: Point
    bottom_center: Point
    bottom_right: Point

    # ── Pleat-start-line points (top of fold lines, shared height) ────────────
    top_left: Point
    top_center: Point
    top_right: Point

    # ── Folding direction ─────────────────────────────────────────────────────
    fold_left: bool  # True → fold toward top_left; False → toward top_right

    # ── Rendering constants (absolute mm, class-level) ───────────────────────
    _ROOF_FEET: ClassVar[tuple[float, ...]] = (6.0, 12.0, 18.0)  # mm above seam edge
    _ROOF_H: ClassVar[float] = 5.0  # mm, apex above each pair of feet

    # ── Factory ───────────────────────────────────────────────────────────────

    @classmethod
    def build_along_seam(
        cls,
        config: PleatConfig,
        straight_seam: Segment,
        curved_seam_fn: Callable[[float], Point],
        anchor_proj: float,
        d_inward: Point,
    ) -> list[Pleat]:
        """Build a list of :class:`Pleat` objects from a :class:`PleatConfig`.

        Positions all pleats relative to *anchor_proj* (the slit projection)
        and resolves their six endpoint pairs from the concrete seam geometry.

        Layout: 1 pleat to the right of the anchor (folds right), then
        ``config.num_pleats − 1`` pleats to the left (each folds left).

        Args:
            config:         Pleat layout parameters.
            straight_seam:  The straight seam reference segment (used for
                            arc-length projections and top-point computation).
            curved_seam_fn: Callable that maps a projection along
                            *straight_seam* to the corresponding point on the
                            curved seam edge (e.g. the shaped hem Bézier).
            anchor_proj:    Arc-length projection of the slit / anchor point
                            on *straight_seam* from its p1.
            d_inward:       Unit :class:`~sewpat.geometry.Point` pointing from
                            the seam edge inward into the garment piece
                            (perpendicular to seam, toward the cap for a sleeve
                            hem).

        Returns:
            Ordered list of :class:`Pleat` instances, right pleat first.
        """
        half = config.depth / 2.0
        step = config.depth + config.spacing

        # Centre projections and fold directions for each pleat
        positions: list[tuple[float, bool]] = []
        # Right pleat (folds right = away from slit)
        if config.num_pleats >= 1:
            positions.append((anchor_proj + config.slit_offset + half, False))
        # Left pleats (each folds left = away from slit)
        for i in range(config.num_pleats - 1):
            positions.append((anchor_proj - config.slit_offset - half - i * step, True))

        pleats: list[Pleat] = []
        for centre_proj, fold_left in positions:
            left_proj = centre_proj - half
            right_proj = centre_proj + half

            # Bottom points: exact intersections with the curved seam edge
            bot_l = curved_seam_fn(left_proj)
            bot_c = curved_seam_fn(centre_proj)
            bot_r = curved_seam_fn(right_proj)

            # Top points: on the pleat start line (config.height above straight seam)
            top_l = straight_seam.point_at_distance(left_proj) + d_inward * config.height
            top_c = straight_seam.point_at_distance(centre_proj) + d_inward * config.height
            top_r = straight_seam.point_at_distance(right_proj) + d_inward * config.height

            pleats.append(
                cls(
                    bottom_left=bot_l,
                    bottom_center=bot_c,
                    bottom_right=bot_r,
                    top_left=top_l,
                    top_center=top_c,
                    top_right=top_r,
                    fold_left=fold_left,
                )
            )

        return pleats

    # ── Rendering ─────────────────────────────────────────────────────────────

    def apply_to(self, part: PatternPart) -> None:
        """Render fold lines, direction arrow, and roof markers onto *part*.

        Args:
            part: The :class:`~sewpat.pattern.PatternPart` to append elements to.
        """
        # Fold segments run bottom→top so that t=0 is at the seam edge and
        # t=1 is at the pleat start line — used for roof-marker interpolation.
        seg_l = Segment(self.bottom_left, self.top_left)
        seg_c = Segment(self.bottom_center, self.top_center)
        seg_r = Segment(self.bottom_right, self.top_right)

        # ── Three fold lines ──────────────────────────────────────────────
        for seg in (seg_l, seg_c, seg_r):
            part.append(seg, style=STYLE_FOLD)

        # ── Direction arrow at pleat start line ───────────────────────────
        arrow_start = self.top_right if self.fold_left else self.top_left
        arrow_end = self.top_left if self.fold_left else self.top_right
        part.append(Segment(arrow_start, arrow_end), style=STYLE_PLEAT_ARROW)

        # ── Roof (∧) markers inside the fold ─────────────────────────────
        # t-parameter: 0 = seam edge, 1 = pleat start line.
        fold_h = self.bottom_center.distance_to(self.top_center)
        if fold_h < 1e-9:
            return
        for foot_h in self._ROOF_FEET:
            apex_h = foot_h + self._ROOF_H
            if apex_h > fold_h:
                break  # roof would exceed fold height — stop
            t_foot = foot_h / fold_h
            t_apex = apex_h / fold_h
            foot_l = seg_l.point_at_t(t_foot)
            foot_r = seg_r.point_at_t(t_foot)
            apex = seg_c.point_at_t(t_apex)
            part.append(Segment(foot_l, apex), style=STYLE_PLEAT_FOLD)
            part.append(Segment(apex, foot_r), style=STYLE_PLEAT_FOLD)
