# tests/conftest.py
import pytest
import numpy as np
import copy  # <-- ADD THIS IMPORT

from domain.world import World
from domain.human import Human
from domain.rice import Rice


@pytest.fixture(scope="session")
def mock_config():
    """Provides a session-wide mock configuration dictionary with the new structure."""
    return {
        "simulation": {
            "grid_width": 10,
            "grid_height": 10,
            "tile_size_meters": 10,
            # Add map_seed to base config for consistency
            "map_seed": 12345,
        },
        "entities": {
            "human": {
                "attributes": {
                    "max_age": 100,
                    "move_speed": 1.4,
                    "max_saturation": 100,
                    "hungry_threshold": 40,
                    "reproduction_threshold": 90,
                    "reproduction_cost": 50,
                    "reproduction_cooldown": 20,
                    "newborn_saturation_endowment": 40,
                }
            },
            "rice": {
                "attributes": {
                    "max_age": 16,
                    "saturation_yield": 50,
                },
                "spawning": {
                    "natural_spawn_chance": 0.1,
                },
            },
        },
    }


# ... (human_config, rice_config, human, rice_plant fixtures are unchanged) ...


@pytest.fixture
def human_config(mock_config):
    """Provides just the human's INSTANCE ATTRIBUTES from the config."""
    return mock_config["entities"]["human"]["attributes"]


@pytest.fixture
def rice_config(mock_config):
    """Provides just the rice plant's INSTANCE ATTRIBUTES from the config."""
    return mock_config["entities"]["rice"]["attributes"]


@pytest.fixture
def human(human_config):
    """Provides a Human instance created with mock config."""
    return Human(pos_x=50, pos_y=50, **human_config)


@pytest.fixture
def rice_plant(rice_config):
    """Provides a Rice instance. Refactored to be more robust like the human fixture."""
    return Rice(pos_x=0, pos_y=0, **rice_config)


@pytest.fixture
def world_factory(mock_config):
    """
    Provides a function to create a World instance with optional overrides.
    This is more flexible than a static fixture.
    """

    def _create_world(width=None, height=None, custom_config=None):
        config_to_use = custom_config if custom_config else mock_config
        sim_config = config_to_use["simulation"]
        final_width = width if width is not None else sim_config["grid_width"]
        final_height = height if height is not None else sim_config["grid_height"]

        world = World(
            width=final_width,
            height=final_height,
            tile_size=sim_config["tile_size_meters"],
            config_data=config_to_use,
        )
        return world

    return _create_world


# --- NEW GLOBAL FIXTURE ---
@pytest.fixture
def world_no_spawn(world_factory, mock_config):
    """
    A global fixture for a world with natural spawning disabled
    and a fixed map seed for deterministic tests.
    """
    # Use deepcopy to ensure test isolation
    test_config = copy.deepcopy(mock_config)
    # Disable natural rice spawning
    test_config["entities"]["rice"]["spawning"]["natural_spawn_chance"] = 0.0
    # The map_seed is already in the base mock_config for predictability
    return world_factory(custom_config=test_config)
