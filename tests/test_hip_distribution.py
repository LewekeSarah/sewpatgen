"""Tests for calculate_hip_distribution() and HipDistribution."""

import pytest

from sewpat.geometry import Point
from sewpat.measurements import HipDistribution, calculate_hip_distribution
from sewpat.units import CM

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_meas(hip_width: float):
    """Return a minimal BlouseMeasurements stub for hip_width testing."""
    from sewpat.measurements import BlouseMeasurements
    from sewpat.person import Gender

    return BlouseMeasurements(
        bust=96.5 * CM,
        waist=77.5 * CM,
        hip=99.0 * CM,
        hip_depth=24.0 * CM,
        bust_depth=27.5 * CM,
        neck_size=6.5 * CM,
        bust_span=8.3 * CM,
        shoulder_width=12.1 * CM,
        back_length=39.0 * CM,
        front_length=43.4 * CM,
        bust_width=96.5 * CM,
        waist_width=83.5 * CM,
        hip_width=hip_width,
        armscye_depth=17.0 * CM,
        back_width=17.0 * CM,
        armscye_width=18.0 * CM,
        chest_width=13.25 * CM,
        gender=Gender.female,
    )


def _make_points(front_hip_width: float, back_hip_width: float):
    """Build four collinear hip-line points spanning front and back widths."""
    pt_cf = Point(0.0, 63.0 * CM)
    pt_sf = pt_cf.translate(front_hip_width, 0)
    pt_sb = pt_sf.translate(5 * CM, 0)
    pt_cb = pt_sb.translate(back_hip_width, 0)
    return pt_cf, pt_sf, pt_sb, pt_cb


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestHipDistributionGeometry:
    def test_hub_equals_vhub_plus_hhub(self):
        fhw = 26.0 * CM
        bhw = 26.0 * CM
        hw = 99.0 * CM
        meas = _make_meas(hw)
        pts = _make_points(fhw, bhw)
        hd = calculate_hip_distribution(meas, *pts)

        assert hd.front_hip_width == pytest.approx(fhw, rel=1e-5)
        assert hd.back_hip_width == pytest.approx(bhw, rel=1e-5)
        assert hd.total_hip_width == pytest.approx(fhw + bhw, rel=1e-5)

    def test_fehlbetrag_formula(self):
        fhw = 26.0 * CM
        bhw = 26.0 * CM
        hw = 99.0 * CM
        meas = _make_meas(hw)
        pts = _make_points(fhw, bhw)
        hd = calculate_hip_distribution(meas, *pts)

        expected = (fhw + bhw) - hw / 2
        assert hd.hip_shortfall == pytest.approx(expected, rel=1e-5)

    def test_fehlbetrag_positive_when_pattern_wider_than_half_measurement(self):
        """Pattern wider than hip_width/2 → positive hip_shortfall."""
        hd = calculate_hip_distribution(_make_meas(99.0 * CM), *_make_points(30.0 * CM, 30.0 * CM))
        assert hd.hip_shortfall > 0

    def test_fehlbetrag_negative_when_pattern_narrower_than_half_measurement(self):
        """Pattern narrower than hip_width/2 → negative hip_shortfall."""
        hd = calculate_hip_distribution(_make_meas(99.0 * CM), *_make_points(20.0 * CM, 20.0 * CM))
        assert hd.hip_shortfall < 0

    def test_fehlbetrag_zero_when_pattern_matches_half_measurement(self):
        hd = calculate_hip_distribution(
            _make_meas(99.0 * CM), *_make_points(24.75 * CM, 24.75 * CM)
        )
        assert hd.hip_shortfall == pytest.approx(0.0, abs=1e-9)

    def test_returns_hip_distribution_instance(self):
        hd = calculate_hip_distribution(_make_meas(99.0 * CM), *_make_points(26.0 * CM, 26.0 * CM))
        assert isinstance(hd, HipDistribution)
