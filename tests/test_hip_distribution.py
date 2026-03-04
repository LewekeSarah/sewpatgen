"""Tests for calculate_hip_distribution() and HipDistribution."""

import pytest

from sewpat.geometry import Point
from sewpat.measurements import HipDistribution, calculate_hip_distribution
from sewpat.units import CM


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_meas(HüW: float):
    """Return a minimal BlouseMeasurements-like stub just for HüW testing."""
    from sewpat.measurements import BlouseMeasurements
    from sewpat.person import Gender

    return BlouseMeasurements(
        BrU=96.5 * CM,
        TaU=77.5 * CM,
        HüU=99.0 * CM,
        HüT=24.0 * CM,
        BrT=27.5 * CM,
        HlB=6.5 * CM,
        BrPA=8.3 * CM,
        SuB=12.1 * CM,
        RüL=39.0 * CM,
        VL=43.4 * CM,
        BrW=96.5 * CM,
        TaW=83.5 * CM,
        HüW=HüW,
        AlT=17.0 * CM,
        RüB=17.0 * CM,
        ArD=18.0 * CM,
        BrB=13.25 * CM,
        gender=Gender.female,
    )


def _make_points(vHüB: float, hHüB: float):
    """Build four collinear hip-line points spanning vHüB front and hHüB back."""
    pt_cf = Point(0.0, 63.0 * CM)
    pt_sf = pt_cf.translate(vHüB, 0)
    pt_sb = pt_sf.translate(5 * CM, 0)  # gap between front and back panels
    pt_cb = pt_sb.translate(hHüB, 0)
    return pt_cf, pt_sf, pt_sb, pt_cb


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestHipDistributionGeometry:
    def test_hub_equals_vhub_plus_hhub(self):
        vHüB = 26.0 * CM
        hHüB = 26.0 * CM
        HüW = 99.0 * CM
        meas = _make_meas(HüW)
        pts = _make_points(vHüB, hHüB)
        hd = calculate_hip_distribution(meas, *pts)

        assert hd.vHüB == pytest.approx(vHüB, rel=1e-5)
        assert hd.hHüB == pytest.approx(hHüB, rel=1e-5)
        assert hd.HüB == pytest.approx(vHüB + hHüB, rel=1e-5)

    def test_fehlbetrag_formula(self):
        vHüB = 26.0 * CM
        hHüB = 26.0 * CM
        HüW = 99.0 * CM
        meas = _make_meas(HüW)
        pts = _make_points(vHüB, hHüB)
        hd = calculate_hip_distribution(meas, *pts)

        expected = (vHüB + hHüB) - HüW / 2
        assert hd.Fehlbetrag == pytest.approx(expected, rel=1e-5)

    def test_fehlbetrag_positive_when_pattern_wider_than_half_measurement(self):
        """Pattern wider than HüW/2 → positive Fehlbetrag."""
        vHüB = 30.0 * CM
        hHüB = 30.0 * CM
        HüW = 99.0 * CM          # HüW/2 = 49.5 cm < 60 cm
        meas = _make_meas(HüW)
        pts = _make_points(vHüB, hHüB)
        hd = calculate_hip_distribution(meas, *pts)

        assert hd.Fehlbetrag > 0

    def test_fehlbetrag_negative_when_pattern_narrower_than_half_measurement(self):
        """Pattern narrower than HüW/2 → negative Fehlbetrag."""
        vHüB = 20.0 * CM
        hHüB = 20.0 * CM
        HüW = 99.0 * CM          # HüW/2 = 49.5 cm > 40 cm
        meas = _make_meas(HüW)
        pts = _make_points(vHüB, hHüB)
        hd = calculate_hip_distribution(meas, *pts)

        assert hd.Fehlbetrag < 0

    def test_fehlbetrag_zero_when_pattern_matches_half_measurement(self):
        vHüB = 24.75 * CM
        hHüB = 24.75 * CM
        HüW = 99.0 * CM          # HüW/2 = 49.5 cm == 49.5 cm
        meas = _make_meas(HüW)
        pts = _make_points(vHüB, hHüB)
        hd = calculate_hip_distribution(meas, *pts)

        assert hd.Fehlbetrag == pytest.approx(0.0, abs=1e-9)

    def test_returns_hip_distribution_instance(self):
        meas = _make_meas(99.0 * CM)
        pts = _make_points(26.0 * CM, 26.0 * CM)
        hd = calculate_hip_distribution(meas, *pts)
        assert isinstance(hd, HipDistribution)

