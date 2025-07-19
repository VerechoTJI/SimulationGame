# tests/test_domain_logic.py
import pytest

# We import directly from the domain to test it in isolation
from domain.rice import Rice


# A dummy "mock" world class, just enough for the test to run
class MockWorld:
    pass


# --- FIXTURES ---
# A fixture is a setup function that provides a resource to tests.
# Pytest re-runs the fixture for every test that uses it, guaranteeing isolation.


@pytest.fixture
def rice_plant() -> Rice:
    """Provides a brand new Rice plant instance for each test."""
    return Rice(pos_x=0, pos_y=0)  # max_age is 16


@pytest.fixture
def mock_world() -> MockWorld:
    """Provides a new MockWorld instance for each test."""
    return MockWorld()


# --- TESTS ---
# The test functions now ask for the fixtures they need by name as arguments.
# We can still group them in a class for organization if we want.


class TestRice:
    def test_rice_replant(self, rice_plant, mock_world):
        """Test that replanting resets the age to 0."""
        # This 'rice_plant' is a fresh instance provided by the fixture
        rice_plant.age = rice_plant.max_age - 1
        rice_plant.replant()
        assert rice_plant.age == 0

    def test_rice_matures_at_half_max_age(self, rice_plant, mock_world):
        """
        Test that a Rice plant's 'matured' property becomes True
        at the correct age.
        """
        # This 'rice_plant' is a DIFFERENT, fresh instance
        # Pre-condition Assertions
        assert not rice_plant.matured, "New rice plant should not be mature"
        assert rice_plant.age == 0

        # Action: Tick the plant until it's just about to mature
        for _ in range(7):  # Age becomes 1...7
            rice_plant.tick(mock_world)

        assert not rice_plant.matured, "Rice at age 7 should not be mature"

        # The tick that makes it mature (age 8)
        rice_plant.tick(mock_world)

        # Post-condition Assertions
        assert rice_plant.matured, "Rice at age 8 should be mature"
        assert rice_plant.age == 8
