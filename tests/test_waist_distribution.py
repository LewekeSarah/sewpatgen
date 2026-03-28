"""Tests for calculate_waist_distribution() and WaistDistribution."""

from dataclasses import replace

import pytest

from sewpat.geometry import Point
from sewpat.measurements import BlouseMeasurements, calculate_waist_distribution
from sewpat.units import CM

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_points(front_waist_width: float, back_waist_width: float):
    """Build four collinear waist-line points spanning front and back widths."""
    pt_cf = Point(0.0, 39.0 * CM)
    pt_sf = pt_cf.translate(front_waist_width, 0)
    pt_sb = pt_sf.translate(5 * CM, 0)
    pt_cb = pt_sb.translate(back_waist_width, 0)
    return pt_cf, pt_sf, pt_sb, pt_cb


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestWaistDistributionGeometry:
    def test_tab_equals_vtab_plus_htab(self, standard_blouse_measurements: BlouseMeasurements):
        """front + back waist widths sum to total_waist_width."""
        fww = 22.0 * CM
        bww = 18.0 * CM
        meas = replace(standard_blouse_measurements, waist_width=78.0 * CM)
        wd = calculate_waist_distribution(meas, *_make_points(fww, bww))

        assert wd.front_waist_width == pytest.approx(fww, rel=1e-5)
        assert wd.back_waist_width == pytest.approx(bww, rel=1e-5)
        assert wd.total_waist_width == pytest.approx(fww + bww, rel=1e-5)

    def test_ausfallbetrag_formula(self, standard_blouse_measurements: BlouseMeasurements):
        """hip_shortfall == (front + back) - waist_width / 2."""
        fww = 22.0 * CM
        bww = 18.0 * CM
        ww = 78.0 * CM
        meas = replace(standard_blouse_measurements, waist_width=ww)
        wd = calculate_waist_distribution(meas, *_make_points(fww, bww))

        assert wd.hip_shortfall == pytest.approx((fww + bww) - ww / 2, rel=1e-5)


class TestWaistDistributionRanges:
    """All outputs must stay within the allowed dressmaking ranges."""

    def _wd(self, standard_blouse_measurements, front=22 * CM, back=18 * CM, ww=60 * CM):
        meas = replace(standard_blouse_measurements, waist_width=ww)
        return calculate_waist_distribution(meas, *_make_points(front, back))

    def test_saeinzug_within_range(self, standard_blouse_measurements: BlouseMeasurements):
        """side_seam_intake is within [0, 2 cm]."""
        wd = self._wd(standard_blouse_measurements)
        assert 0 <= wd.side_seam_intake <= 2 * CM

    def test_vabi_within_range(self, standard_blouse_measurements: BlouseMeasurements):
        """front_dart_width is within [1, 3 cm]."""
        wd = self._wd(standard_blouse_measurements)
        assert 1 * CM <= wd.front_dart_width <= 3 * CM

    def test_habi_within_range(self, standard_blouse_measurements: BlouseMeasurements):
        """back_dart_width is within [2, 4 cm]."""
        wd = self._wd(standard_blouse_measurements)
        assert 2 * CM <= wd.back_dart_width <= 4 * CM

    def test_ranges_with_large_excess(self, standard_blouse_measurements: BlouseMeasurements):
        """Clamping holds when waist excess is very large."""
        wd = self._wd(standard_blouse_measurements, front=40 * CM, back=40 * CM, ww=30 * CM)
        assert 0 <= wd.side_seam_intake <= 2 * CM
        assert 1 * CM <= wd.front_dart_width <= 3 * CM
        assert 2 * CM <= wd.back_dart_width <= 4 * CM

    def test_ranges_with_small_excess(self, standard_blouse_measurements: BlouseMeasurements):
        """Clamping holds when waist excess is very small."""
        wd = self._wd(standard_blouse_measurements, front=20 * CM, back=20 * CM, ww=79 * CM)
        assert 0 <= wd.side_seam_intake <= 2 * CM
        assert 0 <= wd.front_dart_width <= 3 * CM
        assert 0 <= wd.back_dart_width <= 4 * CM


class TestWaistDistributionBalance:
    def test_distribution_sums_to_ausfallbetrag(
        self, standard_blouse_measurements: BlouseMeasurements
    ):
        """2·side_seam_intake + front_dart + back_dart + remainder == hip_shortfall."""
        meas = replace(standard_blouse_measurements, waist_width=78.0 * CM)
        wd = calculate_waist_distribution(meas, *_make_points(22.0 * CM, 18.0 * CM))

        total = 2 * wd.side_seam_intake + wd.front_dart_width + wd.back_dart_width + wd.remainder
        assert total == pytest.approx(wd.hip_shortfall, abs=1e-9)

    def test_no_negative_remainder(self, standard_blouse_measurements: BlouseMeasurements):
        """remainder is never negative across a range of waist widths."""
        for ww in [60 * CM, 70 * CM, 80 * CM, 90 * CM]:
            meas = replace(standard_blouse_measurements, waist_width=ww)
            wd = calculate_waist_distribution(meas, *_make_points(22 * CM, 18 * CM))
            assert wd.remainder >= 0.0


class TestWaistDistributionClamping:
    def test_remainder_is_non_negative(self, standard_blouse_measurements: BlouseMeasurements):
        """Extreme excess does not produce a negative remainder."""
        meas = replace(standard_blouse_measurements, waist_width=10 * CM)
        wd = calculate_waist_distribution(meas, *_make_points(40 * CM, 40 * CM))
        assert wd.remainder >= 0.0

    def test_normal_excess_no_remainder(self, standard_blouse_measurements: BlouseMeasurements):
        """Normal excess leaves only a negligible remainder."""
        meas = replace(standard_blouse_measurements, waist_width=78 * CM)
        wd = calculate_waist_distribution(meas, *_make_points(22 * CM, 18 * CM))
        assert wd.remainder < 0.5 * CM


class TestWaistDistributionCasual:
    """Behaviour when side_seam_intake_max is reduced (casual / no-dart block)."""

    def _wd(
        self,
        standard_blouse_measurements,
        front=22 * CM,
        back=18 * CM,
        ww=78 * CM,
        max_intake=1 * CM,
    ):
        meas = replace(standard_blouse_measurements, waist_width=ww)
        return calculate_waist_distribution(
            meas,
            *_make_points(front, back),
            side_seam_intake_max=max_intake,
        )

    def test_side_seam_intake_capped_at_max(self, standard_blouse_measurements):
        """side_seam_intake never exceeds the provided cap."""
        for cap in [0.0, 0.5 * CM, 1.0 * CM]:
            wd = self._wd(standard_blouse_measurements, max_intake=cap)
            assert wd.side_seam_intake <= cap + 1e-9

    def test_zero_cap_all_in_darts(self, standard_blouse_measurements):
        """With cap=0 the side seam intake is zero; all excess goes to darts."""
        wd = self._wd(standard_blouse_measurements, max_intake=0.0)
        assert wd.side_seam_intake == pytest.approx(0.0, abs=1e-9)

    def test_balance_holds_with_custom_max(self, standard_blouse_measurements):
        """Distribution still sums to hip_shortfall with a custom cap."""
        wd = self._wd(standard_blouse_measurements)
        total = 2 * wd.side_seam_intake + wd.front_dart_width + wd.back_dart_width + wd.remainder
        assert total == pytest.approx(wd.hip_shortfall, abs=1e-9)

    def test_default_max_unchanged(self, standard_blouse_measurements):
        """Calling without side_seam_intake_max gives the same result as max=2 cm."""
        meas = replace(standard_blouse_measurements, waist_width=78 * CM)
        pts = _make_points(22 * CM, 18 * CM)
        wd_default = calculate_waist_distribution(meas, *pts)
        wd_explicit = calculate_waist_distribution(meas, *pts, side_seam_intake_max=2 * CM)
        assert wd_default.side_seam_intake == pytest.approx(wd_explicit.side_seam_intake)
