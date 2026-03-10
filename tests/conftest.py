"""Shared pytest fixtures for the sewpat test suite.

This module provides reusable test data factories for common domain objects:
- Standard body measurements (`Person`)
- Ease-adjusted garment measurements (`BlouseMeasurements`)
- Fit classes (`FitClass`)
- Pattern parts (placeholder for future addition)

All fixtures use the 80–89 cm bust range (PK 4) as the reference size.
"""

import pytest

from sewpat.fitclass import FitClass
from sewpat.measurements import BlouseMeasurements
from sewpat.person import Person
from sewpat.units import CM

# ---------------------------------------------------------------------------
# Factory functions (importable by unittest tests)
# ---------------------------------------------------------------------------


def make_standard_person() -> Person:
    """Return a fully-specified Person in the 80–89 cm bust range (PK 4).

    Returns:
        Person with bust=86 cm, waist=70 cm, hip=96 cm, and all construction
        measurements populated according to Mueller & Sohn formulas.
    """
    bust = 86 * CM
    return Person(
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
        body_rise=27 * CM,
        inseam=80 * CM,
        back_width=bust / 8 + 5.5 * CM,
        armscye_depth=bust / 10 + 11 * CM,
        armscye_width=bust / 8 - 1.5 * CM,
        chest_width=bust / 4 - 4.0 * CM,
        height=168 * CM,
    )


def make_standard_blouse_measurements() -> BlouseMeasurements:
    """Return ease-adjusted blouse measurements for the standard 86 cm bust.

    Returns:
        BlouseMeasurements with ease already applied, suitable for constructing
        a women's top block in PK 4.
    """
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


def make_standard_fitclass() -> FitClass:
    """Return FitClass for PK 4 (80–89 cm bust, normal fit).

    Returns:
        FitClass instance with all ease values from the Mueller & Sohn PK 4 table.
    """
    return FitClass(pk=4)


# ---------------------------------------------------------------------------
# Pytest fixtures (wrap factory functions)
# ---------------------------------------------------------------------------


@pytest.fixture
def standard_person() -> Person:
    """Pytest fixture for standard Person (PK 4, 86 cm bust)."""
    return make_standard_person()


@pytest.fixture
def standard_blouse_measurements() -> BlouseMeasurements:
    """Pytest fixture for standard BlouseMeasurements (PK 4, 86 cm bust)."""
    return make_standard_blouse_measurements()


@pytest.fixture
def standard_fitclass() -> FitClass:
    """Pytest fixture for standard FitClass (PK 4)."""
    return make_standard_fitclass()
