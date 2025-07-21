# tests/test_rice_logic.py
import pytest  # Keep pytest import


# The MockWorld can be removed if it's not used, but let's keep it for now
# in case some tests need a simpler world than the full instance.
class MockWorld:
    pass


# The rice_plant fixture is now provided by conftest.py, so we can remove it from here.


class TestRice:
    # --- MODIFIED: The test now uses the globally available 'rice_plant' fixture ---
    def test_rice_get_eaten_sets_flag(self, rice_plant):
        assert rice_plant.is_eaten is False
        rice_plant.get_eaten()
        assert rice_plant.is_eaten is True

    def test_rice_is_not_alive_after_being_eaten(self, rice_plant):
        assert rice_plant.is_alive() is True
        rice_plant.get_eaten()
        assert rice_plant.is_alive() is False

    def test_rice_matures_at_half_max_age(self, rice_plant):
        # The tick method needs a world-like object, even a simple one.
        mock_world = MockWorld()
        rice_plant.age = 0

        assert not rice_plant.matured, "New rice plant should not be mature"
        assert rice_plant.age == 0

        # Tick until just before mature
        # max_age is now 16 from the config, so half is 8. Tick 7 times.
        for _ in range(7):
            rice_plant.tick(mock_world)

        assert not rice_plant.matured, "Rice at age 7 should not be mature"
        rice_plant.tick(mock_world)
        assert rice_plant.matured, "Rice at age 8 should be mature"
        assert rice_plant.age == 8
