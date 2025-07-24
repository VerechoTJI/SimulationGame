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
            "grid_height": 10,
            "grid_width": 10,
            "tile_size_meters": 10,
            # Add map_seed to base config for consistency
            "map_seed": 12345,
        },
        "performance": {"spatial_hash_cell_size": 2},
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
            "sheep": {
                "attributes": {
                    "max_age": 80,
                    "move_speed": 0.7,
                    "max_saturation": 80,
                    "hungry_threshold": 50,
                    "reproduction_threshold": 70,
                    "reproduction_cost": 20,
                    "reproduction_cooldown": 30,
                    "newborn_saturation_endowment": 20,
                    "search_radius": 100.0,
                }
            },
            "rice": {
                "attributes": {
                    "max_age": 16,
                    "mature_age": 8,
                    "saturation_yield": 50,
                },
                "spawning": {
                    "natural_spawn_chance": 0.1,
                },
            },
        },
    }


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

    def _create_world(height=None, width=None, custom_config=None):
        config_to_use = custom_config if custom_config else mock_config
        sim_config = config_to_use["simulation"]
        final_height = height if height is not None else sim_config["grid_height"]
        final_width = width if width is not None else sim_config["grid_width"]

        world = World(
            height=final_height,
            width=final_width,
            tile_size=sim_config["tile_size_meters"],
            config_data=config_to_use,
        )
        return world

    return _create_world


@pytest.fixture
def world_no_spawn(world_factory, mock_config):
    """
    A global fixture for a world with all spawning (initial and natural) disabled
    and a fixed map seed for deterministic tests.
    """
    # Use deepcopy to ensure test isolation
    test_config = copy.deepcopy(mock_config)

    # --- THIS IS THE FIX ---
    # Disable initial population spawning
    test_config["spawning"] = {
        "human": {"initial_spawn_count": 0},
        "sheep": {"initial_spawn_count": 0},
        "rice": {"natural_spawn_chance": 0.0},  # Keep this for clarity
    }

    # Also disable natural rice spawning (which is now redundant but safe)
    if "spawning" not in test_config["entities"]["rice"]:
        test_config["entities"]["rice"]["spawning"] = {}
    test_config["entities"]["rice"]["spawning"]["natural_spawn_chance"] = 0.0

    # The map_seed is already in the base mock_config for predictability
    return world_factory(custom_config=test_config)
