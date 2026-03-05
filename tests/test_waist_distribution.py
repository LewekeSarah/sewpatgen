"""Tests for calculate_waist_distribution() and WaistDistribution."""

import pytest

from sewpat.geometry import Point
from sewpat.measurements import (
    WaistDistribution,
    _FRONT_FRACTION,
    _SN_FRACTION,
    calculate_waist_distribution,
)
from sewpat.units import CM


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_meas(waist_width: float):
    """Return a minimal BlouseMeasurements stub for waist_width testing."""
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
        waist_width=waist_width,
        hip_width=105.0 * CM,
        armscye_depth=17.0 * CM,
        back_width=17.0 * CM,
        armscye_width=18.0 * CM,
        chest_width=13.25 * CM,
        gender=Gender.female,
    )


def _make_points(front_waist_width: float, back_waist_width: float):
    """Build four collinear waist-line points spanning front and back widths."""
    # Layout: CF ---front--- SF | SB ---back--- CB
    pt_cf = Point(0.0, 39.0 * CM)
    pt_sf = pt_cf.translate(front_waist_width, 0)
    pt_sb = pt_sf.translate(5 * CM, 0)
    pt_cb = pt_sb.translate(back_waist_width, 0)
    return pt_cf, pt_sf, pt_sb, pt_cb


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestWaistDistributionGeometry:
    def test_tab_equals_vtab_plus_htab(self):
        fww = 22.0 * CM
        bww = 18.0 * CM
        ww  = 78.0 * CM
        meas = _make_meas(ww)
        pts  = _make_points(fww, bww)
        wd   = calculate_waist_distribution(meas, *pts)

        assert wd.front_waist_width == pytest.approx(fww, rel=1e-5)
        assert wd.back_waist_width  == pytest.approx(bww, rel=1e-5)
        assert wd.total_waist_width == pytest.approx(fww + bww, rel=1e-5)

    def test_ausfallbetrag_formula(self):
        fww = 22.0 * CM
        bww = 18.0 * CM
        ww  = 78.0 * CM
        meas = _make_meas(ww)
        pts  = _make_points(fww, bww)
        wd   = calculate_waist_distribution(meas, *pts)

        expected = (fww + bww) - ww / 2
        assert wd.hip_shortfall == pytest.approx(expected, rel=1e-5)


class TestWaistDistributionRanges:
    """All outputs must stay within the allowed dressmaking ranges."""

    def _wd(self, front=22 * CM, back=18 * CM, ww=60 * CM):
        meas = _make_meas(ww)
        pts  = _make_points(front, back)
        return calculate_waist_distribution(meas, *pts)

    def test_saeinzug_within_range(self):
        wd = self._wd()
        assert 0 <= wd.side_seam_intake <= 2 * CM

    def test_vabi_within_range(self):
        wd = self._wd()
        assert 1 * CM <= wd.front_dart_width <= 3 * CM

    def test_habi_within_range(self):
        wd = self._wd()
        assert 2 * CM <= wd.back_dart_width <= 4 * CM

    def test_ranges_with_large_excess(self):
        wd = self._wd(front=40 * CM, back=40 * CM, ww=30 * CM)
        assert 0 <= wd.side_seam_intake <= 2 * CM
        assert 1 * CM <= wd.front_dart_width <= 3 * CM
        assert 2 * CM <= wd.back_dart_width <= 4 * CM

    def test_ranges_with_small_excess(self):
        wd = self._wd(front=20 * CM, back=20 * CM, ww=79 * CM)
        assert 0 <= wd.side_seam_intake <= 2 * CM
        assert 0 <= wd.front_dart_width <= 3 * CM
        assert 0 <= wd.back_dart_width <= 4 * CM


class TestWaistDistributionBalance:
    def test_distribution_sums_to_ausfallbetrag(self):
        """2·side_seam_intake + front_dart + back_dart + remainder == hip_shortfall."""
        fww = 22.0 * CM
        bww = 18.0 * CM
        ww  = 78.0 * CM
        meas = _make_meas(ww)
        pts  = _make_points(fww, bww)
        wd   = calculate_waist_distribution(meas, *pts)

        total = 2 * wd.side_seam_intake + wd.front_dart_width + wd.back_dart_width + wd.remainder
        assert total == pytest.approx(wd.hip_shortfall, abs=1e-9)

    def test_no_negative_remainder(self):
        for ww in [60 * CM, 70 * CM, 80 * CM, 90 * CM]:
            meas = _make_meas(ww)
            pts  = _make_points(22 * CM, 18 * CM)
            wd   = calculate_waist_distribution(meas, *pts)
            assert wd.remainder >= 0.0


class TestWaistDistributionClamping:
    def test_remainder_is_non_negative(self):
        meas = _make_meas(10 * CM)
        pts  = _make_points(40 * CM, 40 * CM)
        wd   = calculate_waist_distribution(meas, *pts)
        assert wd.remainder >= 0.0

    def test_normal_excess_no_remainder(self):
        meas = _make_meas(78 * CM)
        pts  = _make_points(22 * CM, 18 * CM)
        wd   = calculate_waist_distribution(meas, *pts)
        assert wd.remainder < 0.5 * CM
