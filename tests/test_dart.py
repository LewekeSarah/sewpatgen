"""Tests for Dart geometry and PatternPart.add_dart()."""

import math

import pytest

from sewpat import CM, MM, Dart, DartResult, Point, Segment, transfer_dart
from sewpat.geometry import CubicBezier
from sewpat.part import PatternElement, PatternPart
from sewpat.style import STYLE_DART_FOLD, STYLE_DART_STITCH


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _simple_dart() -> Dart:
    """A simple dart with known geometry for deterministic tests."""
    leg_a = Point(40.0, 0.0)
    leg_b = Point(60.0, 0.0)
    center = Point(50.0, 0.0)
    tip = Point(50.0, 80.0)  # 80 mm deep
    return Dart(leg_a=leg_a, leg_b=leg_b, center=center, tip=tip, name="Bustnaht")


def _square_part() -> PatternPart:
    """A 200×200 mm square PatternPart with a closed outline."""
    part = PatternPart("Vorderteil")
    o = Point(0.0, 0.0)
    tl = Point(0.0, 200.0)
    tr = Point(200.0, 200.0)
    br = Point(200.0, 0.0)
    part.append(Segment(o, tl), is_outline=True)
    part.append(Segment(tl, tr), is_outline=True)
    part.append(Segment(tr, br), is_outline=True)
    part.append(Segment(br, o), is_outline=True)
    return part


# ---------------------------------------------------------------------------
# Dart geometry tests
# ---------------------------------------------------------------------------

class TestDartGeometry:
    def test_width(self) -> None:
        d = _simple_dart()
        assert d.width == pytest.approx(20.0)

    def test_depth(self) -> None:
        d = _simple_dart()
        assert d.depth == pytest.approx(80.0)

    def test_fold_line_endpoints(self) -> None:
        d = _simple_dart()
        fl = d.fold_line
        assert fl.p1.x == pytest.approx(50.0)
        assert fl.p1.y == pytest.approx(0.0)
        assert fl.p2.x == pytest.approx(50.0)
        assert fl.p2.y == pytest.approx(80.0)

    def test_stitch_line_a(self) -> None:
        d = _simple_dart()
        sl = d.stitch_line_a
        assert sl.p1.x == pytest.approx(40.0)
        assert sl.p2.x == pytest.approx(50.0)
        assert sl.p2.y == pytest.approx(80.0)

    def test_stitch_line_b(self) -> None:
        d = _simple_dart()
        sl = d.stitch_line_b
        assert sl.p1.x == pytest.approx(60.0)

    def test_intake_angle(self) -> None:
        d = _simple_dart()
        # leg_a is at (-10, -80) and leg_b at (10, -80) relative to tip
        # angle = 2 * atan(10/80) ≈ 14.04°
        expected = 2 * math.atan(10.0 / 80.0)
        assert d.intake_angle == pytest.approx(expected, rel=1e-4)

    def test_translate(self) -> None:
        d = _simple_dart()
        dt = d.translate(10.0, 5.0)
        assert dt.center.x == pytest.approx(60.0)
        assert dt.center.y == pytest.approx(5.0)
        assert dt.tip.y == pytest.approx(85.0)

    def test_rotate_preserves_angle(self) -> None:
        d = _simple_dart()
        pivot = d.tip
        rotated = d.rotate(pivot, math.pi / 4)
        assert rotated.intake_angle == pytest.approx(d.intake_angle, rel=1e-6)
        assert rotated.depth == pytest.approx(d.depth, rel=1e-6)

    def test_invalid_fold_direction(self) -> None:
        with pytest.raises(ValueError, match="fold_direction"):
            Dart(Point(0, 0), Point(1, 0), Point(0.5, 0), Point(0.5, 5), fold_direction="sideways")


class TestDartSplit:
    def test_split_equal(self) -> None:
        d = _simple_dart()
        a, b = d.split(0.5)
        # Sub-darts share the same tip
        assert a.tip.x == pytest.approx(d.tip.x)
        assert a.tip.y == pytest.approx(d.tip.y)
        assert b.tip.x == pytest.approx(d.tip.x)
        # Total intake angle is preserved
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


class TestDartFromEdge:
    def test_from_edge_explicit_depth(self) -> None:
        edge = Segment(Point(0.0, 0.0), Point(100.0, 0.0))
        d = Dart.from_edge(edge, position_t=0.5, width=20.0, depth=50.0)
        assert d.center.x == pytest.approx(50.0)
        assert d.center.y == pytest.approx(0.0)
        assert d.width == pytest.approx(20.0)
        assert d.depth == pytest.approx(50.0)
        # Legs should be symmetric
        assert d.leg_a.x == pytest.approx(40.0)
        assert d.leg_b.x == pytest.approx(60.0)

    def test_from_edge_reference_point(self) -> None:
        edge = Segment(Point(0.0, 0.0), Point(100.0, 0.0))
        bust_point = Point(50.0, 100.0)
        d = Dart.from_edge(edge, position_t=0.5, width=20.0, reference_point=bust_point, tip_shortfall=20.0)
        # Tip should be 20 mm short of bust_point along the direction center→bust
        # distance from center (50,0) to bust (50,100) = 100 mm; tip at 80 mm
        assert d.tip.y == pytest.approx(80.0)
        assert d.depth == pytest.approx(80.0)

    def test_from_edge_both_params_raises(self) -> None:
        edge = Segment(Point(0.0, 0.0), Point(100.0, 0.0))
        with pytest.raises(ValueError, match="exactly one"):
            Dart.from_edge(edge, position_t=0.5, width=20.0, depth=50.0, reference_point=Point(50, 50))

    def test_from_edge_no_params_raises(self) -> None:
        edge = Segment(Point(0.0, 0.0), Point(100.0, 0.0))
        with pytest.raises(ValueError, match="exactly one"):
            Dart.from_edge(edge, position_t=0.5, width=20.0)

    def test_from_edge_out_of_range_t(self) -> None:
        edge = Segment(Point(0.0, 0.0), Point(100.0, 0.0))
        with pytest.raises(ValueError, match="position_t"):
            Dart.from_edge(edge, position_t=1.5, width=20.0, depth=50.0)

    def test_from_edge_bezier(self) -> None:
        # A straight-ish Bézier for a simple sanity check
        p0, p3 = Point(0.0, 0.0), Point(100.0, 0.0)
        bez = CubicBezier(p0, Point(33.3, 0.0), Point(66.6, 0.0), p3)
        d = Dart.from_edge(bez, position_t=0.5, width=10.0, depth=30.0)
        # Center should be near the midpoint
        assert d.center.x == pytest.approx(50.0, abs=1.0)
        assert d.depth == pytest.approx(30.0, abs=1.0)


# ---------------------------------------------------------------------------
# PatternPart.add_dart() element count tests
# ---------------------------------------------------------------------------

class TestAddDartOuter:
    def test_element_count_outer(self) -> None:
        part = _square_part()
        baseline = len(part.elements)
        d = _simple_dart()
        result = part.add_dart(d, notches=True, precision_tip=True)
        # 2 stitch + 1 fold + 2 cut + 1 mouth notch + 2 tip circles + 2 leg notches = 10
        assert len(result.stitch_elements) == 2
        assert result.fold_element is not None
        assert len(result.cut_elements) == 2
        # 2 precision circles + 1 InfoBox name label (dart has a name)
        assert len(result.tip_elements) == 3
        # Mouth notch + 2 leg notches (at least one triangle each)
        assert len(result.notch_elements) >= 3
        assert len(part.elements) > baseline

    def test_cut_elements_are_outline(self) -> None:
        part = _square_part()
        d = _simple_dart()
        result = part.add_dart(d, notches=False, precision_tip=False)
        for ce in result.cut_elements:
            assert ce.is_outline is True

    def test_cut_elements_have_zero_sa(self) -> None:
        part = _square_part()
        d = _simple_dart()
        result = part.add_dart(d, notches=False, precision_tip=False)
        for ce in result.cut_elements:
            assert ce.style.seam_allowance == 0.0

    def test_cut_elements_miter_corner(self) -> None:
        part = _square_part()
        d = _simple_dart()
        result = part.add_dart(d, notches=False, precision_tip=False)
        for ce in result.cut_elements:
            assert ce.style.corner_join == "miter"

    def test_cut_elements_based_on_style_cut(self) -> None:
        """Cut segments inherit edge_style stored on the dart."""
        from sewpat.style import STYLE_CUT, Marker
        part = _square_part()
        d = Dart(
            leg_a=Point(40, 0), leg_b=Point(60, 0),
            center=Point(50, 0), tip=Point(50, 80),
            fold_direction="inward", name="Bustnaht",
            edge_style=STYLE_CUT,
        )
        result = part.add_dart(d, notches=False, precision_tip=False)
        for ce in result.cut_elements:
            assert ce.style.marker_end == Marker.SCISSOR

    def test_cut_elements_default_no_edge_style(self) -> None:
        """Without edge_style, cut segments use plain StyleOptions as base."""
        part = _square_part()
        d = _simple_dart()  # edge_style=None by default
        result = part.add_dart(d, notches=False, precision_tip=False)
        for ce in result.cut_elements:
            assert ce.style.marker_end is None

    def test_stitch_elements_style(self) -> None:
        part = _square_part()
        d = _simple_dart()
        result = part.add_dart(d, notches=False, precision_tip=False)
        for se in result.stitch_elements:
            assert se.style == STYLE_DART_STITCH

    def test_fold_element_style(self) -> None:
        part = _square_part()
        d = _simple_dart()
        result = part.add_dart(d, notches=False, precision_tip=False)
        assert result.fold_element is not None
        assert result.fold_element.style == STYLE_DART_FOLD

    def test_no_notches(self) -> None:
        part = _square_part()
        d = _simple_dart()
        result = part.add_dart(d, notches=False, precision_tip=False)
        # Only the mouth center notch is added when notches=False
        # (mouth notch is always added for outer darts)
        assert len(result.notch_elements) >= 1

    def test_no_precision_tip(self) -> None:
        part = _square_part()
        d = _simple_dart()
        result = part.add_dart(d, notches=False, precision_tip=False)
        assert result.tip_elements == []


class TestAddDartInner:
    def _inner_dart(self) -> Dart:
        """A simple dart with fold_direction='outward' (inner/rhombus)."""
        return Dart(
            leg_a=Point(40, 0), leg_b=Point(60, 0),
            center=Point(50, 0), tip=Point(50, 80),
            fold_direction="outward", name="Bustnaht",
        )

    def test_rhombus_element_count(self) -> None:
        part = _square_part()
        d = self._inner_dart()
        result = part.add_dart(d, notches=False, precision_tip=False)
        assert len(result.rhombus_elements) == 4
        assert result.fold_element is None
        assert result.cut_elements == []

    def test_rhombus_is_closed(self) -> None:
        """leg_a → tip → leg_b → center → leg_a — start of first = end of last."""
        part = _square_part()
        d = self._inner_dart()
        result = part.add_dart(d, notches=False, precision_tip=False)
        segs = [e.geometry for e in result.rhombus_elements]
        first_start = segs[0].p1
        last_end = segs[-1].p2
        assert first_start.distance_to(last_end) == pytest.approx(0.0, abs=1e-6)

    def test_all_elements(self) -> None:
        part = _square_part()
        d = self._inner_dart()
        result = part.add_dart(d, notches=True, precision_tip=True)
        # 4 rhombus + 2 tip circles + leg notches
        assert len(result.all_elements) >= 6


# ---------------------------------------------------------------------------
# DartResult.all_elements ordering
# ---------------------------------------------------------------------------

class TestDartResult:
    def test_all_elements_outer(self) -> None:
        part = _square_part()
        d = _simple_dart()
        result = part.add_dart(d, notches=True, precision_tip=True)
        total = len(result.all_elements)
        assert total >= 10  # minimum expected for outer dart with all features

    def test_repr(self) -> None:
        part = _square_part()
        d = _simple_dart()
        result = part.add_dart(d, notches=False, precision_tip=False)
        r = repr(result)
        assert "DartResult" in r


# ---------------------------------------------------------------------------
# transfer_dart
# ---------------------------------------------------------------------------

class TestTransferDart:
    def test_preserves_intake_angle(self) -> None:
        d = _simple_dart()
        new_edge = Segment(Point(0.0, 200.0), Point(200.0, 200.0))
        transferred = transfer_dart(d, new_edge, new_position_t=0.5)
        assert transferred.intake_angle == pytest.approx(d.intake_angle, rel=1e-4)

    def test_new_center_on_edge(self) -> None:
        d = _simple_dart()
        new_edge = Segment(Point(0.0, 200.0), Point(200.0, 200.0))
        transferred = transfer_dart(d, new_edge, new_position_t=0.5)
        # The mouth center should land on the new edge (y = 200)
        assert transferred.center.y == pytest.approx(200.0, abs=1e-4)
        assert transferred.center.x == pytest.approx(100.0, abs=1e-4)

    def test_new_leg_width(self) -> None:
        # After a pivot transfer the legs are purely rotated around the tip,
        # so the distance from each leg to the tip is preserved exactly.
        d = _simple_dart()
        new_edge = Segment(Point(0.0, 200.0), Point(200.0, 200.0))
        transferred = transfer_dart(d, new_edge, new_position_t=0.5)
        dist_orig = d.leg_a.distance_to(d.tip)
        dist_new = transferred.leg_a.distance_to(transferred.tip)
        assert dist_new == pytest.approx(dist_orig, rel=1e-4)

    def test_invalid_position_t(self) -> None:
        d = _simple_dart()
        new_edge = Segment(Point(0.0, 200.0), Point(200.0, 200.0))
        with pytest.raises(ValueError):
            transfer_dart(d, new_edge, new_position_t=2.0)

