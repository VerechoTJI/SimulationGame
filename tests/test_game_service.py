# tests/test_game_service.py
import pytest
import numpy as np
from application.game_service import GameService


@pytest.fixture
def mock_config_for_service(monkeypatch):
    """Provides a mock config object for initializing GameService."""
    config_data = {
        "simulation": {
            "grid_width": 10,
            "grid_height": 10,
            "tile_size_meters": 10,
            "tick_seconds": 0.1,
            "map_seed": 12345,
        },
        "performance": {"flow_field_node_budget": 100},
        "controls": {
            "speed_adjust_factor": 1.25,
            "min_tick_seconds": 0.01,
            "max_tick_seconds": 2.0,
        },
        "entities": {
            "human": {},
            "rice": {},
            "sheep": {},
        },
    }

    class MockConfig:
        data = config_data

        def get(self, *keys, default=None):
            value = self.data
            try:
                for key in keys:
                    value = value[key]
                return value
            except (KeyError, TypeError):
                return default

    monkeypatch.setattr("application.game_service.config", MockConfig())


def test_toggle_flow_field_visibility(mock_config_for_service):
    """
    Tests that the GameService can toggle the flow field visibility state
    and includes relevant data in the render payload only when active.
    """
    # Arrange
    service = GameService(grid_width=10, grid_height=10, tile_size=10)

    # --- THE FINAL, DEFINITIVE FIX ---
    # Mock the flow field data in its NEW, CORRECT location.
    mock_flow_field = np.ones((10, 10, 2), dtype=np.int8)
    service.world.flow_field_manager.flow_field = mock_flow_field

    # Act 1: Check initial state
    render_data_off = service.get_render_data()

    # Assert 1: Ensure it's off by default and no extra data is sent
    assert "show_flow_field" in render_data_off
    assert not render_data_off["show_flow_field"]
    assert "flow_field_data" not in render_data_off

    # Act 2: Toggle on
    service.toggle_flow_field_visibility()
    render_data_on = service.get_render_data()

    # Assert 2: Ensure it's on and the flow field data is included
    assert "show_flow_field" in render_data_on
    assert render_data_on["show_flow_field"]
    assert "flow_field_data" in render_data_on
    assert isinstance(render_data_on["flow_field_data"], np.ndarray)

    # This assertion now correctly compares the data from the render payload
    # with the mock data we placed in the correct location.
    np.testing.assert_array_equal(render_data_on["flow_field_data"], mock_flow_field)

    # Act 3: Toggle off again
    service.toggle_flow_field_visibility()
    render_data_off_again = service.get_render_data()

    # Assert 3: Ensure it's off and the extra data is gone
    assert "show_flow_field" in render_data_off_again
    assert not render_data_off_again["show_flow_field"]
    assert "flow_field_data" not in render_data_off_again
