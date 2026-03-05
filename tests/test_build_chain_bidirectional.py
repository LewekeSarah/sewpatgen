"""Tests for the bidirectional build_chain fix."""
import pytest
from sewpat.geometry import Segment, Point, build_chain, geom_start, geom_end


def _xs(chain):
    """Extract (start_x, end_x) tuples from chain for easy assertions."""
    return [(round(geom_start(g).x, 4), round(geom_end(g).x, 4)) for g in chain]


A = Point(0, 0)
B = Point(10, 0)
C = Point(20, 0)
D = Point(30, 0)


def test_forward_chain_unchanged():
    """A->B, B->C stays as-is."""
    chain = build_chain([Segment(A, B), Segment(B, C)])
    assert _xs(chain) == [(0, 10), (10, 20)]


def test_second_element_reversed():
    """A->B, C->B  →  A->B, B->C (second reversed)."""
    chain = build_chain([Segment(A, B), Segment(C, B)])
    assert _xs(chain) == [(0, 10), (10, 20)]


def test_all_three_user_issue():
    """A->B, C->B, C->A  →  A->B, B->C (reversed), C->A."""
    chain = build_chain([Segment(A, B), Segment(C, B), Segment(C, A)])
    # g1 forward, g2 reversed (B->C), g3 forward (C->A closes the loop)
    assert _xs(chain) == [(0, 10), (10, 20), (20, 0)]


def test_head_extension():
    """B->C, A->B  →  first element should get A->B prepended."""
    chain = build_chain([Segment(B, C), Segment(A, B)])
    assert _xs(chain) == [(0, 10), (10, 20)]


def test_head_extension_reversed():
    """B->C, B->A  →  B->A reversed = A->B prepended."""
    chain = build_chain([Segment(B, C), Segment(B, A)])
    assert _xs(chain) == [(0, 10), (10, 20)]


def test_four_elements_scrambled():
    """D->C, A->B, C->B, C->A  →  full closed chain A->B->C->D->...A."""
    chain = build_chain([Segment(D, C), Segment(A, B), Segment(C, B), Segment(D, A)])
    xs = _xs(chain)
    # All four segments must be present and connected
    for i in range(len(xs) - 1):
        assert xs[i][1] == xs[i + 1][0], f"gap between {xs[i]} and {xs[i+1]}"


def test_disconnected_remainder_appended():
    """Genuinely disconnected element is still appended at end (dart case)."""
    far = Point(999, 999)
    chain = build_chain([Segment(A, B), Segment(B, C), Segment(far, far.translate(1, 0))])
    assert len(chain) == 3
    assert _xs(chain)[:2] == [(0, 10), (10, 20)]

