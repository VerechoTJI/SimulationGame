# tests/test_rice_logic.py
import pytest
import numpy as np
from unittest.mock import MagicMock


class MockWorld:
    """A more faithful mock of the World, providing what Rice.tick() needs."""

    def __init__(self):
        # The FlowFieldManager can be a MagicMock that we can inspect.
        self.flow_field_manager = MagicMock()
        # The get_grid_position method needs a tile size to do its conversion.
        self.tile_size_meters = 10.0

    def get_grid_position(self, world_position_yx):
        """A simple, predictable implementation for the mock."""
        grid_y = int(world_position_yx[0] / self.tile_size_meters)
        grid_x = int(world_position_yx[1] / self.tile_size_meters)
        return (grid_y, grid_x)


class TestRice:
    def test_rice_get_eaten_sets_flag(self, rice_plant):
        assert rice_plant.is_eaten is False
        rice_plant.get_eaten()
        assert rice_plant.is_eaten is True

    def test_rice_is_not_alive_after_being_eaten(self, rice_plant):
        assert rice_plant.is_alive() is True
        rice_plant.get_eaten()
        assert rice_plant.is_alive() is False

    def test_rice_matures_age_and_notifies_ffm(self, rice_plant):
        """
        Tests that rice matures at the correct age AND notifies the
        FlowFieldManager exactly once upon maturation.
        """
        # ARRANGE
        mock_world = MockWorld()
        rice_plant.age = 0
        # Give it a predictable world position for the test
        rice_plant.position = np.array([75.0, 75.0])

        assert not rice_plant.matured, "New rice plant should not be mature"

        # ACT 1: Tick until just before mature
        for _ in range(rice_plant.mature_age - 1):
            rice_plant.tick(mock_world)

        # ASSERT 1: Should not be mature and should not have notified the FFM
        assert not rice_plant.matured
        mock_world.flow_field_manager.add_goal.assert_not_called()

        # ACT 2: The final tick that causes maturation
        rice_plant.tick(mock_world)

        # ASSERT 2: Should now be mature and should have called add_goal once
        assert rice_plant.matured, "Rice at mature_age should be mature"
        # The mock world uses a tile_size of 10.0. Position (75, 75) -> Grid (7, 7)
        expected_grid_pos = (7, 7)
        mock_world.flow_field_manager.add_goal.assert_called_once_with(
            expected_grid_pos
        )

        # ACT 3: Tick again when already mature
        # Reset the mock to ensure we're only checking for new calls
        mock_world.flow_field_manager.reset_mock()
        rice_plant.tick(mock_world)

        # ASSERT 3: Should not call add_goal again
        mock_world.flow_field_manager.add_goal.assert_not_called()
