"""Tests for grids.py — TopGrid construction and validation."""

import unittest

from sewpat.fitclass import FitClass
from sewpat.geometry import Segment
from sewpat.grids import TopGrid
from sewpat.measurements import BlouseMeasurements, GarmentConfig
from sewpat.pattern import PatternConfig
from sewpat.units import CM


def _make_blouse_meas() -> BlouseMeasurements:
    bust = 86 * CM
    bw = bust / 8 + 5.5 * CM
    aw = bust / 8 - 1.5 * CM
    cw = bust / 4 - 4.0 * CM
    bust_width = 2 * (bw + aw + cw)
    return BlouseMeasurements(
        bust=bust, waist=70 * CM, hip=96 * CM, hip_depth=20 * CM,
        bust_depth=26 * CM, neck_size=7 * CM, bust_span=9 * CM,
        shoulder_width=13 * CM, back_length=41 * CM, front_length=43 * CM,
        armscye_depth=bust / 10 + 11 * CM, bust_width=bust_width,
        waist_width=72 * CM, hip_width=98 * CM,
        back_width=bw, armscye_width=aw, chest_width=cw,
    )


class TestTopGrid(unittest.TestCase):
    """Tests for TopGrid.from_measurements."""

    def setUp(self):
        self.meas = _make_blouse_meas()
        self.fc = FitClass(pk=4)
        self.config = GarmentConfig(length=70 * CM)
        self.grid = TopGrid.from_measurements(
            meas=self.meas, fit_class=self.fc, config=self.config
        )

    def test_returns_top_grid_instance(self):
        """from_measurements returns a TopGrid."""
        self.assertIsInstance(self.grid, TopGrid)

    def test_part_is_not_none(self):
        """The grid part is populated."""
        self.assertIsNotNone(self.grid.part)

    def test_all_segments_are_segments(self):
        """Every named grid attribute is a Segment."""
        attrs = [
            "shoulder_front", "shoulder_back", "chest", "waist", "hip", "hem",
            "center_back", "hip_adj", "neck", "dart_back", "armscye_back",
            "side_back", "side_front", "armscye_front", "bust_point", "center_front",
        ]
        for attr in attrs:
            with self.subTest(attr=attr):
                self.assertIsInstance(getattr(self.grid, attr), Segment)

    def test_chest_width_constraint_satisfied(self):
        """The chest-width check passes (would raise ValueError otherwise)."""
        # No assertion needed — construction already ran _check_chest_width.
        pass

    def test_hip_offset_shifts_verticals(self):
        """A non-zero hip_offset shifts the hip_adj line position."""
        grid_default = self.grid
        grid_offset = TopGrid.from_measurements(
            meas=self.meas, fit_class=self.fc, config=self.config,
            hip_offset=1.0 * CM,
        )
        # hip_adj.p1.x should differ by the scaled offset
        self.assertNotAlmostEqual(
            grid_default.hip_adj.p1.x,
            grid_offset.hip_adj.p1.x,
        )

    def test_custom_layout_anchor_applied(self):
        """Custom PatternConfig anchor shifts the grid origin."""
        from sewpat.geometry import Point
        layout = PatternConfig(anchor=Point(20 * CM, 20 * CM))
        grid = TopGrid.from_measurements(
            meas=self.meas, fit_class=self.fc, config=self.config,
            layout=layout,
        )
        # shoulder_back (y=0 offset) should start at anchor y
        self.assertAlmostEqual(grid.shoulder_back.p1.y, 20 * CM, places=3)

    def test_chest_width_mismatch_raises(self):
        """_check_chest_width raises ValueError when the grid is inconsistent."""
        from sewpat.grids import _check_chest_width
        # Corrupt the grid by passing wrong expected width
        with self.assertRaises(ValueError):
            _check_chest_width(self.grid, 9999 * CM)


if __name__ == "__main__":
    unittest.main()

