# tests/conftest.py
import pytest
import numpy as np

from domain.world import World
from domain.human import Human
from domain.rice import Rice


@pytest.fixture(scope="session")
def mock_config():
    """Provides a session-wide mock configuration dictionary."""
    return {
        "simulation": {"grid_width": 10, "grid_height": 10, "tile_size_meters": 10},
        "entities": {
            "human": {
                "max_age": 100,
                "move_speed": 1.4,
                "max_saturation": 100,
                "hungry_threshold": 40,
            },
            "rice": {
                "max_age": 16,
                "natural_spawn_chance": 0.1,
                "saturation_yield": 50,  # Moved here
            },
        },
    }


@pytest.fixture
def human_config(mock_config):
    """Provides just the human-specific part of the config."""
    return mock_config["entities"]["human"]


@pytest.fixture
def rice_config(mock_config):
    """Provides just the rice-specific part of the config."""
    return mock_config["entities"]["rice"]


@pytest.fixture
def human(human_config):
    """Provides a Human instance created with mock config."""
    return Human(
        pos_x=50,
        pos_y=50,
        max_age=human_config["max_age"],
        move_speed=human_config["move_speed"],
        max_saturation=human_config["max_saturation"],
        hungry_threshold=human_config["hungry_threshold"],
    )


@pytest.fixture
def rice_plant(rice_config):
    """Provides a Rice instance created with mock config."""
    return Rice(
        pos_x=0,
        pos_y=0,
        max_age=rice_config["max_age"],
        saturation_yield=rice_config["saturation_yield"],
    )


@pytest.fixture
def world_factory(mock_config):
    """
    Provides a function to create a World instance with optional overrides.
    This is more flexible than a static fixture.
    """

    def _create_world(width=None, height=None, custom_config=None):
        config_to_use = custom_config if custom_config else mock_config

        sim_config = config_to_use["simulation"]

        # Allow overriding dimensions for specific tests
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
