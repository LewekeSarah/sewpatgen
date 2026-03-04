"""Tests for calculate_waist_distribution() and WaistDistribution."""

import warnings

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


def _make_meas(TaW: float):
    """Return a minimal BlouseMeasurements-like stub just for TaW testing."""
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
        TaW=TaW,
        HüW=105.0 * CM,
        AlT=17.0 * CM,
        RüB=17.0 * CM,
        ArD=18.0 * CM,
        BrB=13.25 * CM,
        gender=Gender.female,
    )


def _make_points(vTaB: float, hTaB: float):
    """Build four collinear waist-line points spanning vTaB front and hTaB back."""
    # Layout: CF ---vTaB--- SF | SB ---hTaB--- CB
    # Use a small gap between SF and SB (margin) but for distribution it doesn't matter
    pt_cf = Point(0.0, 39.0 * CM)
    pt_sf = pt_cf.translate(vTaB, 0)
    pt_sb = pt_sf.translate(5 * CM, 0)   # 5 cm margin between front and back panels
    pt_cb = pt_sb.translate(hTaB, 0)
    return pt_cf, pt_sf, pt_sb, pt_cb


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestWaistDistributionGeometry:
    def test_tab_equals_vtab_plus_htab(self):
        vTaB = 22.0 * CM
        hTaB = 18.0 * CM
        TaW = 78.0 * CM
        meas = _make_meas(TaW)
        pts = _make_points(vTaB, hTaB)
        wd = calculate_waist_distribution(meas, *pts)

        assert wd.vTaB == pytest.approx(vTaB, rel=1e-5)
        assert wd.hTaB == pytest.approx(hTaB, rel=1e-5)
        assert wd.TaB == pytest.approx(vTaB + hTaB, rel=1e-5)

    def test_ausfallbetrag_formula(self):
        vTaB = 22.0 * CM
        hTaB = 18.0 * CM
        TaW = 78.0 * CM
        meas = _make_meas(TaW)
        pts = _make_points(vTaB, hTaB)
        wd = calculate_waist_distribution(meas, *pts)

        expected = (vTaB + hTaB) - TaW / 2
        assert wd.Ausfallbetrag == pytest.approx(expected, rel=1e-5)


class TestWaistDistributionRanges:
    """All outputs must stay within the allowed dressmaking ranges."""

    def _wd(self, vTaB=22 * CM, hTaB=18 * CM, TaW=60 * CM):
        meas = _make_meas(TaW)
        pts = _make_points(vTaB, hTaB)
        return calculate_waist_distribution(meas, *pts)

    def test_saeinzug_within_range(self):
        wd = self._wd()
        assert 0 <= wd.SaEinzug <= 2 * CM

    def test_vabi_within_range(self):
        wd = self._wd()
        assert 1 * CM <= wd.vAbI <= 3 * CM

    def test_habi_within_range(self):
        wd = self._wd()
        assert 2 * CM <= wd.hAbI <= 4 * CM

    def test_ranges_with_large_excess(self):
        """Very wide pattern waist → clamping kicks in for all values."""
        wd = self._wd(vTaB=40 * CM, hTaB=40 * CM, TaW=30 * CM)
        assert 0 <= wd.SaEinzug <= 2 * CM
        assert 1 * CM <= wd.vAbI <= 3 * CM
        assert 2 * CM <= wd.hAbI <= 4 * CM

    def test_ranges_with_small_excess(self):
        """Very narrow excess → values are bounded by what's available."""
        wd = self._wd(vTaB=20 * CM, hTaB=20 * CM, TaW=79 * CM)
        assert 0 <= wd.SaEinzug <= 2 * CM
        assert 0 <= wd.vAbI <= 3 * CM
        assert 0 <= wd.hAbI <= 4 * CM


class TestWaistDistributionBalance:
    def test_distribution_sums_to_ausfallbetrag(self):
        """2·SaEinzug + vAbI + hAbI + remainder == Ausfallbetrag."""
        vTaB = 22.0 * CM
        hTaB = 18.0 * CM
        TaW = 78.0 * CM
        meas = _make_meas(TaW)
        pts = _make_points(vTaB, hTaB)
        wd = calculate_waist_distribution(meas, *pts)

        total = 2 * wd.SaEinzug + wd.vAbI + wd.hAbI + wd.remainder
        assert total == pytest.approx(wd.Ausfallbetrag, abs=1e-9)

    def test_no_negative_remainder(self):
        """Remainder must never go negative."""
        for TaW in [60 * CM, 70 * CM, 80 * CM, 90 * CM]:
            meas = _make_meas(TaW)
            pts = _make_points(22 * CM, 18 * CM)
            wd = calculate_waist_distribution(meas, *pts)
            assert wd.remainder >= 0.0


class TestWaistDistributionClamping:
    def test_large_excess_produces_warning(self):
        """Excess so large that clamping leaves > 0.5 cm remainder → warning."""
        meas = _make_meas(TaW=10 * CM)  # almost no finished waist → huge excess
        pts = _make_points(40 * CM, 40 * CM)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            wd = calculate_waist_distribution(meas, *pts)
        # There should be at least one UserWarning about undistributed excess
        assert any("Ausfallbetrag" in str(w.message) for w in caught)
        assert wd.remainder > 0.5 * CM

    def test_normal_excess_no_warning(self):
        """Typical measurements produce no warning."""
        meas = _make_meas(TaW=78 * CM)
        pts = _make_points(22 * CM, 18 * CM)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            calculate_waist_distribution(meas, *pts)
        assert not any("Ausfallbetrag" in str(w.message) for w in caught)

