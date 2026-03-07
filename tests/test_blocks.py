"""Tests for blocks.py — TopBlock, TopBlockBack, TopBlockFront."""

import unittest

from sewpat.blocks import TopBlock, TopBlockBack, TopBlockFront
from sewpat.fitclass import FitClass
from sewpat.geometry import CubicBezier, Dart, Point, Segment
from sewpat.grids import TopGrid
from sewpat.measurements import BlouseMeasurements, GarmentConfig
from sewpat.pattern import PatternConfig, PatternPart
from sewpat.person import PersonalAdjustments
from sewpat.units import CM

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


def _make_blouse_meas() -> BlouseMeasurements:
    bust = 86 * CM
    bw = bust / 8 + 5.5 * CM
    aw = bust / 8 - 1.5 * CM
    cw = bust / 4 - 4.0 * CM
    bust_width = 2 * (bw + aw + cw)
    return BlouseMeasurements(
        bust=bust,
        waist=70 * CM,
        hip=96 * CM,
        hip_depth=20 * CM,
        bust_depth=26 * CM,
        neck_size=7 * CM,
        bust_span=9 * CM,
        shoulder_width=13 * CM,
        back_length=41 * CM,
        front_length=43 * CM,
        armscye_depth=bust / 10 + 11 * CM,
        bust_width=bust_width,
        waist_width=72 * CM,
        hip_width=98 * CM,
        back_width=bw,
        armscye_width=aw,
        chest_width=cw,
    )


def _make_block(seam_allowance: float = 0.0) -> TopBlock:
    meas = _make_blouse_meas()
    fc = FitClass(pk=4)
    config = GarmentConfig(length=70 * CM, seam_allowance=seam_allowance)
    return TopBlock.from_measurements(meas=meas, config=config, fit_class=fc)


# ---------------------------------------------------------------------------
# TopBlock construction
# ---------------------------------------------------------------------------


class TestTopBlockConstruction(unittest.TestCase):
    """Tests for TopBlock.from_measurements."""

    def setUp(self):
        self.block = _make_block()

    def test_returns_top_block(self):
        """from_measurements returns a TopBlock."""
        self.assertIsInstance(self.block, TopBlock)

    def test_back_is_top_block_back(self):
        """block.back is a TopBlockBack."""
        self.assertIsInstance(self.block.back, TopBlockBack)

    def test_front_is_top_block_front(self):
        """block.front is a TopBlockFront."""
        self.assertIsInstance(self.block.front, TopBlockFront)

    def test_back_part_is_pattern_part(self):
        """block.back.part is a PatternPart."""
        self.assertIsInstance(self.block.back.part, PatternPart)

    def test_front_part_is_pattern_part(self):
        """block.front.part is a PatternPart."""
        self.assertIsInstance(self.block.front.part, PatternPart)

    def test_back_has_elements(self):
        """The back part contains at least one element."""
        self.assertGreater(len(self.block.back.part.elements), 0)

    def test_front_has_elements(self):
        """The front part contains at least one element."""
        self.assertGreater(len(self.block.front.part.elements), 0)


# ---------------------------------------------------------------------------
# TopBlockBack typed attributes
# ---------------------------------------------------------------------------


class TestTopBlockBackAttributes(unittest.TestCase):
    """Tests for typed geometry attributes on TopBlockBack."""

    def setUp(self):
        self.back = _make_block().back

    def test_armscye_lower_is_cubic_bezier(self):
        self.assertIsInstance(self.back.armscye_lower, CubicBezier)

    def test_armscye_upper_is_cubic_bezier(self):
        self.assertIsInstance(self.back.armscye_upper, CubicBezier)

    def test_neckline_is_cubic_bezier(self):
        self.assertIsInstance(self.back.neckline, CubicBezier)

    def test_shoulder_is_segment(self):
        self.assertIsInstance(self.back.shoulder, Segment)

    def test_side_chest_waist_is_segment(self):
        self.assertIsInstance(self.back.side_chest_waist, Segment)

    def test_side_waist_hip_is_cubic_bezier(self):
        self.assertIsInstance(self.back.side_waist_hip, CubicBezier)

    def test_side_hip_hem_is_segment(self):
        self.assertIsInstance(self.back.side_hip_hem, Segment)

    def test_waist_dart_is_dart(self):
        self.assertIsInstance(self.back.waist_dart, Dart)

    def test_shoulder_dart_is_dart(self):
        self.assertIsInstance(self.back.shoulder_dart, Dart)

    def test_armscye_control_is_point(self):
        self.assertIsInstance(self.back.armscye_control, Point)

    def test_waist_indent_is_point(self):
        self.assertIsInstance(self.back.waist_indent, Point)

    def test_hip_outset_is_point(self):
        self.assertIsInstance(self.back.hip_outset, Point)


# ---------------------------------------------------------------------------
# TopBlockFront typed attributes
# ---------------------------------------------------------------------------


class TestTopBlockFrontAttributes(unittest.TestCase):
    """Tests for typed geometry attributes on TopBlockFront."""

    def setUp(self):
        self.front = _make_block().front

    def test_armscye_is_cubic_bezier(self):
        self.assertIsInstance(self.front.armscye, CubicBezier)

    def test_neckline_is_cubic_bezier(self):
        self.assertIsInstance(self.front.neckline, CubicBezier)

    def test_shoulder_armscye_is_segment(self):
        self.assertIsInstance(self.front.shoulder_armscye, Segment)

    def test_shoulder_neckline_is_segment(self):
        self.assertIsInstance(self.front.shoulder_neckline, Segment)

    def test_side_chest_waist_is_segment(self):
        self.assertIsInstance(self.front.side_chest_waist, Segment)

    def test_side_waist_hip_is_cubic_bezier(self):
        self.assertIsInstance(self.front.side_waist_hip, CubicBezier)

    def test_side_hip_hem_is_segment(self):
        self.assertIsInstance(self.front.side_hip_hem, Segment)

    def test_waist_dart_is_dart(self):
        self.assertIsInstance(self.front.waist_dart, Dart)

    def test_shoulder_dart_is_dart(self):
        self.assertIsInstance(self.front.shoulder_dart, Dart)

    def test_armscye_control_is_point(self):
        self.assertIsInstance(self.front.armscye_control, Point)

    def test_bust_point_is_point(self):
        self.assertIsInstance(self.front.bust_point, Point)


# ---------------------------------------------------------------------------
# Optional parameters
# ---------------------------------------------------------------------------


class TestTopBlockOptions(unittest.TestCase):
    """Tests for optional constructor parameters."""

    def test_with_seam_allowance(self):
        """Building with seam_allowance > 0 does not raise."""
        block = _make_block(seam_allowance=1.0 * CM)
        self.assertIsInstance(block, TopBlock)

    def test_with_personal_adjustments(self):
        """PersonalAdjustments are accepted without error."""
        meas = _make_blouse_meas()
        fc = FitClass(pk=4)
        config = GarmentConfig(length=70 * CM)
        adj = PersonalAdjustments(hip_offset=2.0 * CM, shoulder_drop=1.5 * CM)
        block = TopBlock.from_measurements(meas=meas, config=config, fit_class=fc, adjustments=adj)
        self.assertIsInstance(block, TopBlock)

    def test_with_pre_built_grid(self):
        """A pre-built TopGrid is reused instead of building a new one."""
        meas = _make_blouse_meas()
        fc = FitClass(pk=4)
        config = GarmentConfig(length=70 * CM)
        grid = TopGrid.from_measurements(meas=meas, fit_class=fc, config=config)
        block = TopBlock.from_measurements(meas=meas, config=config, fit_class=fc, grid=grid)
        self.assertIsInstance(block, TopBlock)

    def test_custom_part_names(self):
        """Custom back_name and front_name are applied to the parts."""
        meas = _make_blouse_meas()
        fc = FitClass(pk=4)
        config = GarmentConfig(length=70 * CM)
        block = TopBlock.from_measurements(
            meas=meas,
            config=config,
            fit_class=fc,
            back_name="Rückenteil",
            front_name="Vorderteil",
        )
        self.assertEqual(block.back.part.name, "Rückenteil")
        self.assertEqual(block.front.part.name, "Vorderteil")

    def test_custom_layout(self):
        """Custom PatternConfig layout is accepted."""
        meas = _make_blouse_meas()
        fc = FitClass(pk=4)
        config = GarmentConfig(length=70 * CM)
        layout = PatternConfig(anchor=Point(10 * CM, 10 * CM))
        block = TopBlock.from_measurements(meas=meas, config=config, fit_class=fc, layout=layout)
        self.assertIsInstance(block, TopBlock)


if __name__ == "__main__":
    unittest.main()
