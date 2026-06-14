"""Tests for Dart geometry and PatternPart.add_dart()."""

import math
import warnings

import numpy as np
import pytest

from sewpat import CubicBezier, Dart, DartType, Point, Segment
from sewpat.element import PatternElement
from sewpat.geometry import Line, Ray
from sewpat.geometry._dart import (
    _resolve_edge_center_normal,
    dart_from_edge_free_tip,
    dart_from_tip_center_width,
)
from sewpat.pattern import PatternPart
from sewpat.style import STYLE_DART_FOLD, STYLE_DART_STITCH, StyleOptions

# Fixtures
# ---------------------------------------------------------------------------


def _simple_dart() -> Dart:
    leg_a = Point(40.0, 0.0)
    leg_b = Point(60.0, 0.0)
    center = Point(50.0, 0.0)
    tip = Point(50.0, 80.0)  # 80 mm deep
    return Dart(leg_a=leg_a, leg_b=leg_b, center=center, tip=tip, name="Bustnaht")


def _square_part() -> PatternPart:
    part = PatternPart("Vorderteil")
    o, tl, tr, br = Point(0, 0), Point(0, 200), Point(200, 200), Point(200, 0)
    part.append(Segment(o, tl), is_outline=True)
    part.append(Segment(tl, tr), is_outline=True)
    part.append(Segment(tr, br), is_outline=True)
    part.append(Segment(br, o), is_outline=True)
    return part


# ---------------------------------------------------------------------------
# Dart geometry
# ---------------------------------------------------------------------------


class TestDartGeometry:
    def test_width(self) -> None:
        assert _simple_dart().width == pytest.approx(20.0)

    def test_depth(self) -> None:
        assert _simple_dart().depth == pytest.approx(80.0)

    def test_fold_line_endpoints(self) -> None:
        fl = _simple_dart().fold_line
        assert fl.p1.x == pytest.approx(50.0)
        assert fl.p1.y == pytest.approx(0.0)
        assert fl.p2.x == pytest.approx(50.0)
        assert fl.p2.y == pytest.approx(80.0)

    def test_stitch_line_a_tip_to_leg(self) -> None:
        sl = _simple_dart().stitch_line_a
        assert sl.p1.x == pytest.approx(50.0)  # tip
        assert sl.p1.y == pytest.approx(80.0)
        assert sl.p2.x == pytest.approx(40.0)  # leg_a

    def test_stitch_line_b_tip_to_leg(self) -> None:
        sl = _simple_dart().stitch_line_b
        assert sl.p1.x == pytest.approx(50.0)  # tip
        assert sl.p2.x == pytest.approx(60.0)  # leg_b

    def test_intake_angle(self) -> None:
        expected = 2 * math.atan(10.0 / 80.0)
        assert _simple_dart().intake_angle == pytest.approx(expected, rel=1e-4)

    def test_translate(self) -> None:
        dt = _simple_dart().translate(10.0, 5.0)
        assert dt.center.x == pytest.approx(60.0)
        assert dt.tip.y == pytest.approx(85.0)

    def test_rotate_preserves_angle(self) -> None:
        d = _simple_dart()
        rotated = d.rotate(d.tip, math.pi / 4)
        assert rotated.intake_angle == pytest.approx(d.intake_angle, rel=1e-6)
        assert rotated.depth == pytest.approx(d.depth, rel=1e-6)

    def test_invalid_dart_type(self) -> None:
        with pytest.raises(ValueError, match="dart_type"):
            Dart(
                Point(0, 0),
                Point(1, 0),
                Point(0.5, 0),
                Point(0.5, 5),
                dart_type="sideways",
            )

    def test_stitch_curve_overrides_straight_leg(self) -> None:
        d = _simple_dart()
        curve = Segment(d.tip, d.leg_a)
        d2 = Dart(d.leg_a, d.leg_b, d.center, d.tip, stitch_curve_a=curve)
        assert d2.stitch_line_a is curve

    def test_effective_second_tip_defaults_to_mirror(self) -> None:
        d = Dart(Point(40, 0), Point(60, 0), Point(50, 0), Point(50, 80), dart_type="rhombus")
        assert d.effective_second_tip.x == pytest.approx(50.0)
        assert d.effective_second_tip.y == pytest.approx(-80.0)

    def test_effective_second_tip_explicit(self) -> None:
        explicit = Point(50, -50)
        d = Dart(
            Point(40, 0),
            Point(60, 0),
            Point(50, 0),
            Point(50, 80),
            dart_type="rhombus",
            second_tip=explicit,
        )
        assert d.effective_second_tip is explicit

    def test_intake_angle_deg(self) -> None:
        d = _simple_dart()
        assert d.intake_angle_deg == pytest.approx(math.degrees(d.intake_angle), rel=1e-9)

    def test_intake_angle_deg_45(self) -> None:
        """A dart with width == 2*depth has a 90° total intake angle."""
        d = Dart(Point(40, 0), Point(60, 0), Point(50, 0), Point(50, 10))
        assert d.intake_angle_deg == pytest.approx(2 * math.degrees(math.atan(1.0)), rel=1e-6)

    def test_roof_displaced_outward(self) -> None:
        """roof must be beyond center (away from tip) along the fold direction."""
        d = _simple_dart()
        # center is at y=0, tip at y=80 → outward means y < 0
        assert d.roof.y < d.center.y
        # height = tan(intake_angle) * (width/2)
        expected_h = math.tan(d.intake_angle) * (d.width / 2)
        assert d.center.distance_to(d.roof) == pytest.approx(expected_h, rel=1e-4)

    def test_translate_preserves_stitch_curves(self) -> None:
        d = _simple_dart()
        curve_a = Segment(d.tip, d.leg_a)
        curve_b = Segment(d.tip, d.leg_b)
        d2 = Dart(
            d.leg_a,
            d.leg_b,
            d.center,
            d.tip,
            stitch_curve_a=curve_a,
            stitch_curve_b=curve_b,
        )
        dt = d2.translate(5.0, 10.0)
        assert dt.stitch_curve_a is not None
        assert dt.stitch_curve_b is not None
        assert dt.stitch_curve_a.p1.x == pytest.approx(d.tip.x + 5.0)
        assert dt.stitch_curve_b.p2.x == pytest.approx(d.leg_b.x + 5.0)

    def test_rotate_preserves_stitch_curves(self) -> None:
        d = _simple_dart()
        curve_a = Segment(d.tip, d.leg_a)
        curve_b = Segment(d.tip, d.leg_b)
        d2 = Dart(
            d.leg_a,
            d.leg_b,
            d.center,
            d.tip,
            stitch_curve_a=curve_a,
            stitch_curve_b=curve_b,
        )
        dr = d2.rotate(d.tip, math.pi / 4)
        assert dr.stitch_curve_a is not None
        assert dr.stitch_curve_b is not None
        # After rotation around the tip, p1 (= tip) stays fixed; p2 (leg end) moves
        assert dr.stitch_curve_a.p1.x == pytest.approx(d.tip.x)
        assert dr.stitch_curve_a.p2.x != pytest.approx(d.leg_a.x)

    def test_eq_same_dart(self) -> None:
        d1 = _simple_dart()
        d2 = _simple_dart()
        assert d1 == d2

    def test_eq_different_tip(self) -> None:
        d1 = _simple_dart()
        d2 = Dart(d1.leg_a, d1.leg_b, d1.center, Point(50.0, 90.0), name="Bustnaht")
        assert d1 != d2

    def test_eq_different_name(self) -> None:
        d1 = _simple_dart()
        d2 = Dart(d1.leg_a, d1.leg_b, d1.center, d1.tip, name="AndererName")
        assert d1 != d2

    def test_eq_non_dart(self) -> None:
        assert _simple_dart().__eq__("not a dart") is NotImplemented

    def test_hash_equal_darts_same_hash(self) -> None:
        d1 = _simple_dart()
        d2 = _simple_dart()
        assert hash(d1) == hash(d2)

    def test_dart_in_set(self) -> None:
        d1 = _simple_dart()
        d2 = _simple_dart()
        assert len({d1, d2}) == 1


# ---------------------------------------------------------------------------
# second_tip warning
# ---------------------------------------------------------------------------


class TestDartSecondTipWarning:
    """Dart emits a UserWarning when second_tip is supplied for a non-rhombus type."""

    _second_tip = Point(50, -40)

    # --- should warn ---

    def test_direct_init_triangle_warns(self) -> None:
        with pytest.warns(UserWarning, match="second_tip"):
            Dart(
                Point(40, 0),
                Point(60, 0),
                Point(50, 0),
                Point(50, 80),
                dart_type=DartType.TRIANGLE,
                second_tip=self._second_tip,
            )

    def test_from_tip_center_width_triangle_warns(self) -> None:
        with pytest.warns(UserWarning, match="second_tip"):
            Dart.from_tip_center_width(
                tip=Point(50, 80),
                center=Point(50, 0),
                width=20.0,
                dart_type=DartType.TRIANGLE,
                second_tip=self._second_tip,
            )

    def test_from_tip_and_legs_triangle_warns(self) -> None:
        with pytest.warns(UserWarning, match="second_tip"):
            Dart.from_tip_and_legs(
                Point(50, 80),
                Point(40, 0),
                Point(60, 0),
                dart_type=DartType.TRIANGLE,
                second_tip=self._second_tip,
            )

    def test_warning_message_mentions_dart_type(self) -> None:
        with pytest.warns(UserWarning, match="triangle"):
            Dart(
                Point(40, 0),
                Point(60, 0),
                Point(50, 0),
                Point(50, 80),
                dart_type=DartType.TRIANGLE,
                second_tip=self._second_tip,
            )

    def test_warning_is_user_warning(self) -> None:
        with pytest.warns(UserWarning):
            Dart(
                Point(40, 0),
                Point(60, 0),
                Point(50, 0),
                Point(50, 80),
                dart_type=DartType.TRIANGLE,
                second_tip=self._second_tip,
            )

    # --- should NOT warn ---

    def test_rhombus_with_second_tip_no_warning(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            Dart(
                Point(40, 0),
                Point(60, 0),
                Point(50, 0),
                Point(50, 80),
                dart_type=DartType.RHOMBUS,
                second_tip=self._second_tip,
            )

    def test_triangle_without_second_tip_no_warning(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            Dart(Point(40, 0), Point(60, 0), Point(50, 0), Point(50, 80))

    def test_rhombus_without_second_tip_no_warning(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            Dart(
                Point(40, 0),
                Point(60, 0),
                Point(50, 0),
                Point(50, 80),
                dart_type=DartType.RHOMBUS,
            )

    def test_from_tip_center_width_rhombus_no_warning(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            Dart.from_tip_center_width(
                tip=Point(50, 80),
                center=Point(50, 0),
                width=20.0,
                dart_type=DartType.RHOMBUS,
                second_tip=self._second_tip,
            )

    def test_from_tip_and_legs_rhombus_no_warning(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            Dart.from_tip_and_legs(
                Point(50, 80),
                Point(40, 0),
                Point(60, 0),
                dart_type=DartType.RHOMBUS,
                second_tip=self._second_tip,
            )

    def test_rhombus_with_second_tip(self) -> None:
        d = Dart(
            Point(40, 0),
            Point(60, 0),
            Point(50, 0),
            Point(50, 80),
            dart_type=DartType.RHOMBUS,
            second_tip=self._second_tip,
        )
        assert d.second_tip == self._second_tip

    def test_triangle_without_second_tip(self) -> None:
        d = Dart(Point(40, 0), Point(60, 0), Point(50, 0), Point(50, 80))
        assert d.second_tip is None


class TestDartUnequalLegLengthsWarning:
    """Dart emits a UserWarning when the stitch lines differ by more than 1 mm."""

    def test_unequal_legs_warns(self) -> None:
        with pytest.warns(UserWarning, match="unequal lengths"):
            Dart(Point(40, 0), Point(70, 0), Point(55, 0), Point(50, 80))

    def test_equal_legs_no_warning(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            Dart(Point(40, 0), Point(60, 0), Point(50, 0), Point(50, 80))


class TestDartSplit:
    def test_split_equal(self) -> None:
        d = _simple_dart()
        a, b = d.split(0.5)
        assert a.tip.x == pytest.approx(d.tip.x)
        assert a.intake_angle + b.intake_angle == pytest.approx(d.intake_angle, rel=1e-4)

    def test_split_asymmetric(self) -> None:
        d = _simple_dart()
        a, b = d.split(0.3)
        assert a.intake_angle == pytest.approx(0.3 * d.intake_angle, rel=1e-3)
        assert b.intake_angle == pytest.approx(0.7 * d.intake_angle, rel=1e-3)

    def test_split_invalid_ratio(self) -> None:
        d = _simple_dart()
        with pytest.raises(ValueError):
            d.split(0.0)
        with pytest.raises(ValueError):
            d.split(1.0)

    def test_split_preserves_dart_type_rhombus(self) -> None:
        d = Dart(
            Point(40, 0),
            Point(60, 0),
            Point(50, 0),
            Point(50, 80),
            dart_type=DartType.RHOMBUS,
            name="Raute",
        )
        a, b = d.split(0.5)
        assert a.dart_type is DartType.RHOMBUS
        assert b.dart_type is DartType.RHOMBUS

    def test_split_rhombus_named_suffixes(self) -> None:
        """RHOMBUS dart with a name must receive ' A' / ' B' suffixes, same as
        TRIANGLE — dart_type must not suppress the name suffix logic."""
        d = Dart(
            Point(40, 0),
            Point(60, 0),
            Point(50, 0),
            Point(50, 80),
            dart_type=DartType.RHOMBUS,
            name="Raute",
        )
        a, b = d.split(0.5)
        assert a.name == "Raute A"
        assert b.name == "Raute B"

    def test_split_rhombus_unnamed_no_suffix(self) -> None:
        """Unnamed RHOMBUS dart must produce None names after split."""
        d = Dart(
            Point(40, 0),
            Point(60, 0),
            Point(50, 0),
            Point(50, 80),
            dart_type=DartType.RHOMBUS,
        )
        a, b = d.split(0.5)
        assert a.name is None
        assert b.name is None

    def test_split_named_suffixes(self) -> None:
        d = _simple_dart()  # name="Bustnaht"
        a, b = d.split(0.5)
        assert a.name == "Bustnaht A"
        assert b.name == "Bustnaht B"

    def test_split_unnamed_no_suffix(self) -> None:
        d = Dart(Point(40, 0), Point(60, 0), Point(50, 0), Point(50, 80))
        a, b = d.split(0.5)
        assert a.name is None
        assert b.name is None


# ---------------------------------------------------------------------------
# Dart factory class methods
# ---------------------------------------------------------------------------


class TestDartFactories:
    def test_from_tip_center_width(self) -> None:
        tip = Point(50, 80)
        center = Point(50, 0)
        d = Dart.from_tip_center_width(tip, center, width=20.0)
        assert d.center.x == pytest.approx(50.0)
        assert d.width == pytest.approx(20.0)
        assert d.depth == pytest.approx(80.0)
        # Mouth must be orthogonal to fold line
        fold_vec = (center.x - tip.x, center.y - tip.y)
        leg_vec = (d.leg_b.x - d.leg_a.x, d.leg_b.y - d.leg_a.y)
        dot = fold_vec[0] * leg_vec[0] + fold_vec[1] * leg_vec[1]
        assert dot == pytest.approx(0.0, abs=1e-9)

    def test_from_tip_and_legs(self) -> None:
        tip = Point(50, 80)
        leg_a, leg_b = Point(40, 0), Point(60, 0)
        d = Dart.from_tip_and_legs(tip, leg_a, leg_b)
        assert d.center.x == pytest.approx(50.0)
        assert d.center.y == pytest.approx(0.0)
        assert d.tip is tip

    def test_from_tip_and_legs_explicit_second_tip(self) -> None:
        st = Point(50, -40)
        d = Dart.from_tip_and_legs(
            Point(50, 80),
            Point(40, 0),
            Point(60, 0),
            dart_type="rhombus",
            second_tip=st,
        )
        assert d.effective_second_tip is st

    def test_from_edge_at_t(self) -> None:
        edge = PatternElement(Segment(Point(0, 0), Point(100, 0)))
        d = Dart.from_edge_at_t(edge, t=0.5, width=20.0, depth=50.0)
        assert d.center.x == pytest.approx(50.0)
        assert d.width == pytest.approx(20.0)
        assert d.depth == pytest.approx(50.0)
        assert d.leg_a.x == pytest.approx(40.0)
        assert d.leg_b.x == pytest.approx(60.0)

    def test_from_edge_at_t_inherits_edge_element(self) -> None:
        elem = PatternElement(Segment(Point(0, 0), Point(100, 0)))
        d = Dart.from_edge_at_t(elem, t=0.5, width=20.0, depth=50.0)
        assert d._edge_element is elem

    def test_from_edge_at_t_invalid_t(self) -> None:
        edge = PatternElement(Segment(Point(0, 0), Point(100, 0)))
        with pytest.raises(ValueError, match="t must be"):
            Dart.from_edge_at_t(edge, t=1.5, width=20.0, depth=50.0)

    def test_from_edge_at_point(self) -> None:
        edge = PatternElement(Segment(Point(0, 0), Point(100, 0)))
        d = Dart.from_edge_at_point(edge, Point(50, 0), width=20.0, depth=50.0)
        assert d.center.x == pytest.approx(50.0, abs=1.0)
        assert d.depth == pytest.approx(50.0, abs=1.0)

    def test_from_edge_at_point_ray(self) -> None:
        from sewpat.geometry import Ray as _Ray

        ray = _Ray(Point(0, 0), (1, 0))
        d = Dart.from_edge_at_point(ray, Point(50, 0), width=20.0, depth=50.0)
        assert d.center.x == pytest.approx(50.0, abs=1e-9)
        assert d.depth == pytest.approx(50.0, abs=1e-9)
        assert d.leg_a.x == pytest.approx(40.0, abs=1e-9)
        assert d.leg_b.x == pytest.approx(60.0, abs=1e-9)

    def test_from_edge_at_point_line(self) -> None:
        from sewpat.geometry import Line as _Line

        line = _Line(Point(0, 0), (1, 0))
        d = Dart.from_edge_at_point(line, Point(75, 0), width=20.0, depth=30.0)
        assert d.center.x == pytest.approx(75.0, abs=1e-9)
        assert d.depth == pytest.approx(30.0, abs=1e-9)

    def test_from_edge_free_tip(self) -> None:
        edge = PatternElement(Segment(Point(0, 0), Point(100, 0)))
        bust = Point(50, 100)
        d = Dart.from_edge_free_tip(
            edge, t=0.5, width=20.0, reference_point=bust, tip_shortfall=20.0
        )
        assert d.tip.y == pytest.approx(80.0)
        assert d.depth == pytest.approx(80.0)

    def test_from_edge_free_tip_invalid_t(self) -> None:
        edge = PatternElement(Segment(Point(0, 0), Point(100, 0)))
        with pytest.raises(ValueError, match="t must be"):
            Dart.from_edge_free_tip(edge, t=-0.1, width=20.0, reference_point=Point(50, 100))

    def test_from_edge_at_t_bezier(self) -> None:
        bez = CubicBezier(Point(0, 0), Point(33.3, 0), Point(66.6, 0), Point(100, 0))
        d = Dart.from_edge_at_t(bez, t=0.5, width=10.0, depth=30.0)
        assert d.center.x == pytest.approx(50.0, abs=1.0)
        assert d.depth == pytest.approx(30.0, abs=1.0)

    def test_from_edge_rejects_bad_geometry(self) -> None:
        from sewpat.geometry import Circle

        edge = PatternElement(Circle(Point(0, 0), radius=10.0))
        with pytest.raises(ValueError, match="Segment, CubicBezier, Ray or Line"):
            Dart.from_edge_at_t(edge, t=0.5, width=20.0, depth=50.0)

    def test_from_edge_rejects_unknown_type(self) -> None:
        with pytest.raises(TypeError):
            Dart.from_edge_at_t("not-an-edge", t=0.5, width=20.0, depth=50.0)

    def test_from_edge_at_legs_normalized(self) -> None:
        edge = Segment(Point(-50, 0), Point(50, 0))
        leg_a, leg_b = Point(0, 0), Point(10, 4)
        tip_line = Line(Point(0, 20), (1, 0))
        d = Dart.from_edge_at_legs_normalized(edge, leg_a, leg_b, tip_line)
        assert d.leg_a is leg_a
        assert d.leg_b is leg_b
        assert tip_line.contains_point(d.tip)
        assert d.stitch_line_a.length == pytest.approx(d.stitch_line_b.length)

    def test_from_edge_at_legs_normalized_inherits_edge_element(self) -> None:
        elem = PatternElement(Segment(Point(-50, 0), Point(50, 0)))
        leg_a, leg_b = Point(0, 0), Point(10, 4)
        tip_line = Line(Point(0, 20), (1, 0))
        d = Dart.from_edge_at_legs_normalized(elem, leg_a, leg_b, tip_line)
        assert d._edge_element is elem

    def test_from_edge_at_legs_normalized_parallel_tip_line_raises(self) -> None:
        edge = Segment(Point(-50, 0), Point(50, 0))
        leg_a, leg_b = Point(0, 0), Point(10, 0)
        tip_line = Line(Point(20, 0), (0, 1))
        with pytest.raises(ValueError, match="parallel"):
            Dart.from_edge_at_legs_normalized(edge, leg_a, leg_b, tip_line)


# ---------------------------------------------------------------------------
# PatternPart.add_dart()
# ---------------------------------------------------------------------------


class TestAddDartOuter:
    def test_elements_created(self) -> None:
        part = _square_part()
        baseline = len(part.elements)
        part.add_dart(_simple_dart(), notches=True, precision_tip=True)
        assert len(part.elements) > baseline

    def test_add_dart_returns_none(self) -> None:
        part = _square_part()
        assert part.add_dart(_simple_dart(), notches=False, precision_tip=False) is None

    def test_roles_present(self) -> None:
        part = _square_part()
        part.add_dart(_simple_dart(), notches=True, precision_tip=True)
        roles = {e.role for e in part.elements if e.role is not None}
        assert {"dart_stitch", "dart_fold", "dart_roof", "dart_tip"} <= roles

    def test_stitch_count(self) -> None:
        part = _square_part()
        part.add_dart(_simple_dart(), notches=False, precision_tip=False)
        stitches = [e for e in part.elements if e.role == "dart_stitch"]
        assert len(stitches) == 2

    def test_fold_count(self) -> None:
        part = _square_part()
        part.add_dart(_simple_dart(), notches=False, precision_tip=False)
        folds = [e for e in part.elements if e.role == "dart_fold"]
        assert len(folds) == 1

    def test_roof_is_outline(self) -> None:
        part = _square_part()
        part.add_dart(_simple_dart(), notches=False, precision_tip=False)
        roofs = [e for e in part.elements if e.role == "dart_roof"]
        assert len(roofs) == 2
        for r in roofs:
            assert r.is_outline is True

    def test_roof_miter_style(self) -> None:
        part = _square_part()
        part.add_dart(_simple_dart(), notches=False, precision_tip=False)
        for r in [e for e in part.elements if e.role == "dart_roof"]:
            assert r.style.corner_join == "miter"

    def test_roof_inherits_edge_style(self) -> None:
        from sewpat.style import STYLE_CUT, Marker

        part = _square_part()
        # Replace the bottom edge with a STYLE_CUT segment so the dart's
        # _edge_element is actually in the part and the roof can inherit its style.
        edge_elem = part.append(
            Segment(Point(40, 0), Point(60, 0)), style=STYLE_CUT, is_outline=True
        )
        dart = Dart.from_edge_at_t(edge_elem, t=0.5, width=20.0, depth=80.0, name="test")
        part.add_dart(dart, notches=False, precision_tip=False)
        for r in [e for e in part.elements if e.role == "dart_roof"]:
            assert r.style.marker_end == Marker.SCISSOR

    def test_stitch_style_override(self) -> None:
        my_style = StyleOptions(stroke_color="red")
        part = _square_part()
        part.add_dart(_simple_dart(), stitch_style=my_style, notches=False, precision_tip=False)
        for s in [e for e in part.elements if e.role == "dart_stitch"]:
            assert s.style.stroke_color == "red"

    def test_no_notches_when_disabled(self) -> None:
        part = _square_part()
        part.add_dart(_simple_dart(), notches=False, precision_tip=False)
        assert not any(e.role == "dart_notch" for e in part.elements)

    def test_no_tip_when_disabled(self) -> None:
        part = _square_part()
        part.add_dart(_simple_dart(), notches=False, precision_tip=False)
        assert not any(e.role == "dart_tip" for e in part.elements)


class TestAddDartRhombus:
    def _rhombus_dart(self) -> Dart:
        return Dart(
            leg_a=Point(40, 0),
            leg_b=Point(60, 0),
            center=Point(50, 0),
            tip=Point(50, 80),
            dart_type=DartType.RHOMBUS,
            name="Raute",
        )

    def test_four_stitch_segments(self) -> None:
        part = _square_part()
        part.add_dart(self._rhombus_dart(), notches=False, precision_tip=False)
        stitches = [e for e in part.elements if e.role == "dart_stitch"]
        assert len(stitches) == 4

    def test_diamond_is_closed(self) -> None:
        part = _square_part()
        part.add_dart(self._rhombus_dart(), notches=False, precision_tip=False)
        segs = [e.geometry for e in part.elements if e.role == "dart_stitch"]
        assert segs[0].p1.distance_to(segs[-1].p2) == pytest.approx(0.0, abs=1e-6)

    def test_mirror_apex_position(self) -> None:
        part = _square_part()
        part.add_dart(self._rhombus_dart(), notches=False, precision_tip=False)
        segs = [e.geometry for e in part.elements if e.role == "dart_stitch"]
        mirror = segs[2].p2
        assert mirror.x == pytest.approx(50.0, abs=1e-6)
        assert mirror.y == pytest.approx(-80.0, abs=1e-6)

    def test_fold_line_always_present(self) -> None:
        part = _square_part()
        part.add_dart(self._rhombus_dart(), notches=False, precision_tip=False)
        assert any(e.role == "dart_fold" for e in part.elements)

    def test_no_roof_for_rhombus(self) -> None:
        part = _square_part()
        part.add_dart(self._rhombus_dart(), notches=False, precision_tip=False)
        assert not any(e.role == "dart_roof" for e in part.elements)

    def test_no_notches_for_rhombus(self) -> None:
        part = _square_part()
        part.add_dart(self._rhombus_dart(), notches=True, precision_tip=False)
        assert not any(e.role == "dart_notch" for e in part.elements)

    def test_explicit_second_tip(self) -> None:
        second = Point(50, -40)
        d = Dart(
            Point(40, 0),
            Point(60, 0),
            Point(50, 0),
            Point(50, 80),
            dart_type="rhombus",
            second_tip=second,
        )
        part = _square_part()
        part.add_dart(d, notches=False, precision_tip=False)
        segs = [e.geometry for e in part.elements if e.role == "dart_stitch"]
        assert segs[2].p2.y == pytest.approx(-40.0, abs=1e-6)


class TestAddDartElements:
    """add_dart() appends correctly role-tagged elements to part.elements."""

    def test_elements_added_to_part(self) -> None:
        part = _square_part()
        part.add_dart(_simple_dart(), notches=True, precision_tip=True)
        roles = {e.role for e in part.elements if e.role is not None}
        assert roles >= {"dart_stitch", "dart_fold", "dart_roof", "dart_tip", "dart_notch"}

    def test_stitch_elements_filterable_by_role(self) -> None:
        part = _square_part()
        part.add_dart(_simple_dart(), notches=False, precision_tip=False)
        stitch = [e for e in part.elements if e.role == "dart_stitch"]
        assert len(stitch) == 2

    def test_add_dart_returns_none(self) -> None:
        part = _square_part()
        assert part.add_dart(_simple_dart(), notches=False, precision_tip=False) is None


class TestAddDartCurved:
    """add_dart() must use stitch_curve_a/b geometry when set."""

    def test_curved_stitch_elements_are_not_segments(self) -> None:
        d = _simple_dart()
        cp1a = Point(50, 60)
        cp2a = Point(43, 20)
        curve_a = CubicBezier(d.tip, cp1a, cp2a, d.leg_a)
        cp1b = Point(50, 60)
        cp2b = Point(57, 20)
        curve_b = CubicBezier(d.tip, cp1b, cp2b, d.leg_b)
        d_curved = Dart(
            d.leg_a,
            d.leg_b,
            d.center,
            d.tip,
            stitch_curve_a=curve_a,
            stitch_curve_b=curve_b,
        )
        part = _square_part()
        part.add_dart(d_curved, notches=False, precision_tip=False)
        stitch_geoms = [e.geometry for e in part.elements if e.role == "dart_stitch"]
        assert len(stitch_geoms) == 2
        assert all(isinstance(g, CubicBezier) for g in stitch_geoms)


class TestDartSeamAllowance:
    """Dart stitch / fold lines must carry seam_allowance=0 so they are
    never offset during add_seam_allowance()."""

    def test_dart_stitch_style_no_seam_allowance(self) -> None:
        assert STYLE_DART_STITCH.seam_allowance == 0.0

    def test_dart_fold_style_no_seam_allowance(self) -> None:
        assert STYLE_DART_FOLD.seam_allowance is None or STYLE_DART_FOLD.seam_allowance == 0.0

    def test_sa_chain_not_disrupted_by_dart_roof(self) -> None:
        """SA polygon must cover every outline edge — dart roofs must not hijack ordering.

        Regression: build_chain() re-sorted by proximity and followed dart roof
        V-shapes instead of the next through-edge, silently dropping SA sides.
        The fix preserves part.elements order, which is already the correct seam
        sequence from _assemble_*_part + add_dart in-place insertion.
        """
        from sewpat.geometry import dart_from_edge_at_t
        from sewpat.units import CM

        # 4-sided outline with a dart on the top edge (mimics shoulder dart on back block)
        tl, tr = Point(0, 0), Point(200, 0)
        br, bl = Point(200, 300), Point(0, 300)
        part = PatternPart("Back")
        top = part.append(Segment(tl, tr), is_outline=True)
        part.append(Segment(tr, br), is_outline=True)
        part.append(Segment(br, bl), is_outline=True)
        part.append(Segment(bl, tl), is_outline=True)

        dart = dart_from_edge_at_t(
            edge=top,
            t=0.5,
            width=20,
            depth=80,
            dart_type=DartType.TRIANGLE,
        )
        part.add_dart(dart)

        sa_elems = part.add_seam_allowance(1.5 * CM)

        # Every SA element must be a Segment (no Béziers in this outline).
        sa_segs = [e for e in sa_elems if isinstance(e.geometry, Segment)]
        assert len(sa_segs) > 0

        # The bottom edge runs at y=300; its SA must be at y > 300.
        sa_bottom = [e for e in sa_segs if e.geometry.start.y > 295 and e.geometry.end.y > 295]
        assert sa_bottom, "SA chain skipped the bottom outline edge — ordering was broken"

        # The right edge runs at x=200; its SA must be at x > 200.
        sa_right = [e for e in sa_segs if e.geometry.start.x > 195 and e.geometry.end.x > 195]
        assert sa_right, "SA chain skipped the right outline edge — ordering was broken"


class TestAddDartRhombusPrecisionTip:
    """Rhombus darts with precision_tip=True must mark both apices."""

    def test_two_tip_marks_for_rhombus(self) -> None:
        d = Dart(
            leg_a=Point(40, 0),
            leg_b=Point(60, 0),
            center=Point(50, 0),
            tip=Point(50, 80),
            dart_type=DartType.RHOMBUS,
            name="Raute",
        )
        part = _square_part()
        part.add_dart(d, notches=False, precision_tip=True)
        tip_elems = [e for e in part.elements if e.role == "dart_tip"]
        assert len(tip_elems) >= 2


# ---------------------------------------------------------------------------
# _resolve_edge_center_normal — Ray/Line branch (lines 100-101)
# ---------------------------------------------------------------------------


class TestResolveEdgeCenterNormal:
    def test_with_ray(self) -> None:
        """Ray edge uses point_at_distance — t is treated as arc-length (line 100)."""
        ray = Ray(Point(0, 0), np.array([1.0, 0.0]))
        center, normal = _resolve_edge_center_normal(ray, 50.0)

        assert center.x == pytest.approx(50.0)
        assert center.y == pytest.approx(0.0)
        assert abs(normal[0]) < 1e-9
        assert abs(abs(normal[1]) - 1.0) < 1e-9

    def test_with_line(self) -> None:
        """Line edge uses point_at_distance — t is treated as arc-length (line 100)."""
        ln = Line(Point(0, 0), np.array([0.0, 1.0]))
        center, normal = _resolve_edge_center_normal(ln, 30.0)

        assert center.x == pytest.approx(0.0)
        assert center.y == pytest.approx(30.0)
        assert abs(abs(normal[0]) - 1.0) < 1e-9
        assert abs(normal[1]) < 1e-9


# ---------------------------------------------------------------------------
# dart_from_tip_center_width — coincident tip + center → ValueError (line 130)
# ---------------------------------------------------------------------------


class TestDartFromTipCenterWidthCoincident:
    def test_function_raises(self) -> None:
        """dart_from_tip_center_width raises ValueError when tip == center."""
        p = Point(50.0, 50.0)
        with pytest.raises(ValueError, match="tip and center must be distinct"):
            dart_from_tip_center_width(tip=p, center=p, width=20.0)

    def test_class_method_raises(self) -> None:
        """Dart.from_tip_center_width propagates the ValueError."""
        p = Point(10.0, 10.0)
        with pytest.raises(ValueError, match="tip and center must be distinct"):
            Dart.from_tip_center_width(tip=p, center=p, width=15.0)


# ---------------------------------------------------------------------------
# dart_from_edge_free_tip — unsupported edge type → TypeError (line 245)
# ---------------------------------------------------------------------------


class TestDartFromEdgeFreeTipTypeError:
    def test_ray_edge_raises(self) -> None:
        """dart_from_edge_free_tip raises TypeError for a Ray edge (line 245)."""
        ray = Ray(Point(0, 0), np.array([1.0, 0.0]))
        with pytest.raises(TypeError, match="Segment or CubicBezier"):
            dart_from_edge_free_tip(edge=ray, t=0.5, width=20.0, reference_point=Point(50.0, 50.0))

    def test_line_edge_raises(self) -> None:
        """dart_from_edge_free_tip raises TypeError for a Line edge (line 245)."""
        ln = Line(Point(0, 0), np.array([1.0, 0.0]))
        with pytest.raises(TypeError, match="Segment or CubicBezier"):
            dart_from_edge_free_tip(edge=ln, t=0.5, width=20.0, reference_point=Point(50.0, 50.0))


# ---------------------------------------------------------------------------
# Dart._transform_curve — CubicBezier branch (line 554)
# ---------------------------------------------------------------------------


class TestDartTransformCurveBezier:
    def _dart_with_bezier_stitches(self) -> Dart:
        tip = Point(50.0, 80.0)
        leg_a = Point(40.0, 0.0)
        leg_b = Point(60.0, 0.0)
        return Dart(
            leg_a=leg_a,
            leg_b=leg_b,
            center=Point(50.0, 0.0),
            tip=tip,
            stitch_curve_a=CubicBezier(tip, Point(48, 40), Point(43, 20), leg_a),
            stitch_curve_b=CubicBezier(tip, Point(52, 40), Point(57, 20), leg_b),
        )

    def test_translate_transforms_bezier_stitch_curves(self) -> None:
        """translate() shifts all four control points of CubicBezier stitch curves."""
        d = self._dart_with_bezier_stitches()
        translated = d.translate(10.0, 5.0)

        assert isinstance(translated.stitch_curve_a, CubicBezier)
        assert isinstance(translated.stitch_curve_b, CubicBezier)
        assert translated.stitch_curve_a.p0 == Point(60.0, 85.0)
        assert translated.stitch_curve_a.p3 == Point(50.0, 5.0)
        assert translated.stitch_curve_b.p3 == Point(70.0, 5.0)

    def test_rotate_transforms_bezier_stitch_curves(self) -> None:
        """rotate() applies the rotation to CubicBezier stitch control points."""
        d = self._dart_with_bezier_stitches()
        rotated = d.rotate(pivot=d.tip, angle_rad=math.pi / 2)

        assert isinstance(rotated.stitch_curve_a, CubicBezier)
        assert isinstance(rotated.stitch_curve_b, CubicBezier)
        # tip rotated around itself stays at tip
        assert rotated.stitch_curve_a.p0.x == pytest.approx(d.tip.x, abs=1e-9)
        assert rotated.stitch_curve_a.p0.y == pytest.approx(d.tip.y, abs=1e-9)


# ---------------------------------------------------------------------------
# Dart.__repr__ (line 642)
# ---------------------------------------------------------------------------


class TestDartRepr:
    def test_repr_contains_key_fields(self) -> None:
        """__repr__ includes name, leg_a, leg_b, tip."""
        d = Dart(
            leg_a=Point(40.0, 0.0),
            leg_b=Point(60.0, 0.0),
            center=Point(50.0, 0.0),
            tip=Point(50.0, 80.0),
            name="Bustnaht",
        )
        r = repr(d)
        assert "Dart(" in r
        assert "Bustnaht" in r
        assert "leg_a" in r
        assert "leg_b" in r
        assert "tip" in r

    def test_repr_unnamed_shows_none(self) -> None:
        """__repr__ for an unnamed dart contains 'None'."""
        d = Dart(
            leg_a=Point(0.0, 0.0),
            leg_b=Point(20.0, 0.0),
            center=Point(10.0, 0.0),
            tip=Point(10.0, 50.0),
        )
        r = repr(d)
        assert "Dart(" in r
        assert "None" in r


def test_dart_rep_point_is_mouth_centre() -> None:
    d = Dart.from_tip_center_width(tip=Point(0, 50), center=Point(0, 0), width=20.0)
    rep = d.rep_point()
    assert rep.x == pytest.approx(d.center.x)
    assert rep.y == pytest.approx(d.center.y)
