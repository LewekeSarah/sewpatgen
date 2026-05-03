"""Shared helper factories for the tests/pattern test suite.

All functions are plain factory functions (not fixtures) so they can be
called directly from any test file without injecting them as parameters.
"""

import pytest

from sewpat.geometry import Dart, Point, Segment
from sewpat.pattern import Pattern, PatternPart


@pytest.fixture
def square_part() -> PatternPart:
    return _square_part(100)


def _square_part(side: float = 100.0) -> PatternPart:
    """Axis-aligned square from (0, 0) to (side, side) with is_outline=True."""
    part = PatternPart(name="Square")
    part.append(Segment(Point(0, 0), Point(side, 0)), is_outline=True)
    part.append(Segment(Point(side, 0), Point(side, side)), is_outline=True)
    part.append(Segment(Point(side, side), Point(0, side)), is_outline=True)
    part.append(Segment(Point(0, side), Point(0, 0)), is_outline=True)
    return part


def _rect_part(x0, y0, x1, y1) -> PatternPart:
    """Rectangular PatternPart from corner (x0, y0) to (x1, y1)."""
    part = PatternPart(name="Rect")
    part.append(Segment(Point(x0, y0), Point(x1, y0)), is_outline=True)
    part.append(Segment(Point(x1, y0), Point(x1, y1)), is_outline=True)
    part.append(Segment(Point(x1, y1), Point(x0, y1)), is_outline=True)
    part.append(Segment(Point(x0, y1), Point(x0, y0)), is_outline=True)
    return part


@pytest.fixture(name="_rect_part")
def _rect_part_fixture():
    """Fixture wrapper that returns the `_rect_part` factory function.

    Tests may either import `_rect_part` directly from this module, or accept
    a fixture parameter named `_rect_part` which yields the same callable.
    """
    return _rect_part


@pytest.fixture
def square_part_with_sa() -> PatternPart:
    return _square_part_with_sa(10)


def _square_part_with_sa(sa_dist: float = 10.0) -> PatternPart:
    """100x100 mm square with seam allowance already added."""
    part = _square_part(100.0)
    part.add_seam_allowance(sa_dist)
    return part


@pytest.fixture
def square_part_with_dart() -> PatternPart:
    """100x100 mm square with a triangle dart on the left edge, SA not yet added."""
    part = PatternPart(name="DartSquare")
    dart_edge = Segment(Point(0, 100), Point(0, 0))
    part.append(Segment(Point(0, 0), Point(100, 0)), is_outline=True)
    part.append(Segment(Point(100, 0), Point(100, 100)), is_outline=True)
    part.append(Segment(Point(100, 100), Point(0, 100)), is_outline=True)
    part.append(dart_edge, is_outline=True)
    dart = Dart.from_edge_at_legs(
        tip=Point(50, 80),
        leg_a=Point(40, 0),
        leg_b=Point(60, 0),
        edge=dart_edge,
    )
    part.add_dart(dart)
    return part


@pytest.fixture
def pattern_with_square_part() -> tuple[Pattern, PatternPart]:
    return _pattern_with_square_part(200)


def _pattern_with_square_part(size: float = 200.0) -> tuple[Pattern, PatternPart]:
    """A Pattern with one square PatternPart of the given side length."""
    part = _square_part(size)
    part.name = "Body"
    pat = Pattern(name="P")
    pat.add_part(part)
    return pat, part


def _make_side_part(name: str, side_len: float, hem_len: float = 50.0) -> PatternPart:
    """PatternPart with role-tagged outline segments for seam-validation tests.

    Contains:
    - one ``is_outline`` segment of *side_len* mm with ``role="side"``
    - one ``is_outline`` segment of *hem_len* mm with ``role="hem"``
    - one construction line of 999 mm with ``role="side"`` (must never be counted)
    """
    part = PatternPart(name=name)
    part.append(Segment(Point(0, 0), Point(side_len, 0)), is_outline=True, role="side")
    part.append(Segment(Point(0, 0), Point(hem_len, 0)), is_outline=True, role="hem")
    part.append(Segment(Point(0, 0), Point(999, 0)), is_construction=True, role="side")
    return part


def _simple_pattern(back_side: float, front_side: float) -> Pattern:
    """Pattern with a 'Back' and 'Front' part, each built by :func:`_make_side_part`."""
    pat = Pattern(name="TestPattern")
    pat.add_part(_make_side_part("Back", back_side))
    pat.add_part(_make_side_part("Front", front_side))
    return pat
