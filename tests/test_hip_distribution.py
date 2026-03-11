"""Tests for calculate_hip_distribution() and HipDistribution."""

from dataclasses import replace

import pytest

from sewpat.geometry import Point
from sewpat.measurements import BlouseMeasurements, HipDistribution, calculate_hip_distribution
from sewpat.units import CM

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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
    def test_hub_equals_vhub_plus_hhub(self, standard_blouse_measurements: BlouseMeasurements):
        """front + back hip widths sum to total_hip_width."""
        fhw = 26.0 * CM
        bhw = 26.0 * CM
        meas = replace(standard_blouse_measurements, hip_width=99.0 * CM)
        hd = calculate_hip_distribution(meas, *_make_points(fhw, bhw))

        assert hd.front_hip_width == pytest.approx(fhw, rel=1e-5)
        assert hd.back_hip_width == pytest.approx(bhw, rel=1e-5)
        assert hd.total_hip_width == pytest.approx(fhw + bhw, rel=1e-5)

    def test_fehlbetrag_formula(self, standard_blouse_measurements: BlouseMeasurements):
        """hip_shortfall == (front + back) - hip_width / 2."""
        fhw = 26.0 * CM
        bhw = 26.0 * CM
        hw = 99.0 * CM
        meas = replace(standard_blouse_measurements, hip_width=hw)
        hd = calculate_hip_distribution(meas, *_make_points(fhw, bhw))

        assert hd.hip_shortfall == pytest.approx((fhw + bhw) - hw / 2, rel=1e-5)

    def test_fehlbetrag_positive_when_pattern_wider_than_half_measurement(
        self, standard_blouse_measurements: BlouseMeasurements
    ):
        """Pattern wider than hip_width/2 → positive hip_shortfall."""
        meas = replace(standard_blouse_measurements, hip_width=99.0 * CM)
        hd = calculate_hip_distribution(meas, *_make_points(30.0 * CM, 30.0 * CM))
        assert hd.hip_shortfall > 0

    def test_fehlbetrag_negative_when_pattern_narrower_than_half_measurement(
        self, standard_blouse_measurements: BlouseMeasurements
    ):
        """Pattern narrower than hip_width/2 → negative hip_shortfall."""
        meas = replace(standard_blouse_measurements, hip_width=99.0 * CM)
        hd = calculate_hip_distribution(meas, *_make_points(20.0 * CM, 20.0 * CM))
        assert hd.hip_shortfall < 0

    def test_fehlbetrag_zero_when_pattern_matches_half_measurement(
        self, standard_blouse_measurements: BlouseMeasurements
    ):
        """hip_shortfall is zero when each half exactly matches hip_width/2."""
        meas = replace(standard_blouse_measurements, hip_width=99.0 * CM)
        hd = calculate_hip_distribution(meas, *_make_points(24.75 * CM, 24.75 * CM))
        assert hd.hip_shortfall == pytest.approx(0.0, abs=1e-9)

    def test_returns_hip_distribution_instance(
        self, standard_blouse_measurements: BlouseMeasurements
    ):
        """Returns a HipDistribution instance."""
        meas = replace(standard_blouse_measurements, hip_width=99.0 * CM)
        hd = calculate_hip_distribution(meas, *_make_points(26.0 * CM, 26.0 * CM))
        assert isinstance(hd, HipDistribution)
