# tests/test_spawning_manager.py

import pytest
import random
from domain.spawning_manager import SpawningManager
from domain.entity_manager import EntityManager
from domain.tile import TILES
from domain.rice import Rice

# --- FIXTURES ---


@pytest.fixture
def simple_spawn_grid():
    """A deterministic 3x3 grid for basic spawning rules."""
    return [
        [TILES["land"], TILES["land"], TILES["water"]],
        [TILES["land"], TILES["land"], TILES["water"]],
        [TILES["land"], TILES["land"], TILES["land"]],
    ]


@pytest.fixture
def complex_spawn_grid():
    """A predictable 5x5 grid for more complex natural spawning tests."""
    return [
        [TILES["water"]] * 5,
        [TILES["water"], TILES["land"], TILES["land"], TILES["land"], TILES["water"]],
        [
            TILES["water"],
            TILES["land"],
            TILES["mountain"],
            TILES["land"],
            TILES["water"],
        ],
        [TILES["water"], TILES["land"], TILES["land"], TILES["land"], TILES["water"]],
        [TILES["water"]] * 5,
    ]


@pytest.fixture
def simple_spawning_manager(simple_spawn_grid, mock_config):
    """Provides a SpawningManager with the simple 3x3 grid."""
    return SpawningManager(grid=simple_spawn_grid, config_data=mock_config)


@pytest.fixture
def complex_spawning_manager(complex_spawn_grid, mock_config):
    """Provides a SpawningManager with the complex 5x5 grid."""
    return SpawningManager(grid=complex_spawn_grid, config_data=mock_config)


# --- TEST CLASSES ---


class TestReproductionAndReplanting:
    def test_replant_queue_logic(self, simple_spawning_manager):
        """Tests that the replant queue adds and processes coordinates correctly."""
        assert simple_spawning_manager.process_replant_queue() == []
        simple_spawning_manager.add_to_replant_queue((1, 1))
        simple_spawning_manager.add_to_replant_queue((2, 0))
        assert sorted(simple_spawning_manager.process_replant_queue()) == sorted(
            [(1, 1), (2, 0)]
        )
        assert simple_spawning_manager.process_replant_queue() == []

    def test_reproduction_spawn_location(self, simple_spawning_manager):
        """Tests finding a valid adjacent tile for a newborn."""
        occupied_tiles = {(1, 1)}
        spawn_pos = simple_spawning_manager.get_reproduction_spawn_location(
            parent_grid_pos=(0, 0), occupied_tiles=occupied_tiles
        )
        assert spawn_pos is not None
        assert spawn_pos in [(0, 1), (1, 0)]

    def test_reproduction_spawn_location_fully_blocked(self, simple_spawning_manager):
        """Tests that no location is returned if the parent is surrounded."""
        occupied_tiles = {(1, 0), (0, 1), (1, 1)}
        spawn_pos = simple_spawning_manager.get_reproduction_spawn_location(
            parent_grid_pos=(0, 0), occupied_tiles=occupied_tiles
        )
        assert spawn_pos is None


class TestNaturalSpawning:
    # These tests are moved from test_world_spawning.py and refactored
    def test_rice_spawns_on_valid_tile(self, complex_spawning_manager, monkeypatch):
        monkeypatch.setattr(random, "random", lambda: 0.0)  # Force spawn

        # ACT: Ask the manager for a spawn location
        spawn_pos = complex_spawning_manager.get_natural_rice_spawn_location(
            occupied_tiles=set()
        )

        # ASSERT
        assert spawn_pos is not None
        valid_spawn_points = {
            (1, 1),
            (2, 1),
            (3, 1),  # Top row of land
            (1, 3),
            (2, 3),
            (3, 3),  # Bottom row of land
            (1, 2),
            (3, 2),  # Middle row (excluding mountain)
        }
        assert spawn_pos in valid_spawn_points

    def test_rice_does_not_spawn_if_chance_fails(
        self, complex_spawning_manager, monkeypatch
    ):
        monkeypatch.setattr(random, "random", lambda: 0.99)  # Fail spawn chance

        # ACT
        spawn_pos = complex_spawning_manager.get_natural_rice_spawn_location(
            occupied_tiles=set()
        )

        # ASSERT
        assert spawn_pos is None

    def test_rice_does_not_spawn_on_occupied_tiles(
        self, complex_spawning_manager, monkeypatch
    ):
        monkeypatch.setattr(random, "random", lambda: 0.0)  # Force spawn

        # ARRANGE: Occupy all possible valid spawn locations
        occupied_tiles = {
            (1, 1),
            (2, 1),
            (3, 1),
            (1, 3),
            (2, 3),
            (3, 3),
            (1, 2),
            (3, 2),
        }

        # ACT
        spawn_pos = complex_spawning_manager.get_natural_rice_spawn_location(
            occupied_tiles
        )

        # ASSERT
        assert spawn_pos is None


class TestSpawningIntegration:
    def test_eaten_rice_is_replanted_via_managers(
        self, simple_spawning_manager, mock_config
    ):
        """Tests the full replanting loop using EntityManager and SpawningManager."""
        # ARRANGE
        tile_size = mock_config["simulation"]["tile_size_meters"]
        entity_manager = EntityManager(mock_config, tile_size)

        rice = entity_manager.create_rice(x=1, y=1)
        rice_pos = (1, 1)
        rice.get_eaten()

        # ACT 1: Cleanup and Queueing
        removed_entities = entity_manager.cleanup_dead_entities()
        for entity in removed_entities:
            if hasattr(entity, "is_eaten") and entity.is_eaten:
                grid_x = int(entity.position[0] / tile_size)
                grid_y = int(entity.position[1] / tile_size)
                simple_spawning_manager.add_to_replant_queue((grid_x, grid_y))

        # ASSERT 1: State is correct before the next tick
        assert len(entity_manager.entities) == 0
        assert len(simple_spawning_manager.replant_queue) == 1
        assert simple_spawning_manager.replant_queue[0] == rice_pos

        # ACT 2: Process the queue and respawn
        coords_to_replant = simple_spawning_manager.process_replant_queue()
        for x, y in coords_to_replant:
            entity_manager.create_rice(x, y)

        # ASSERT 2: A new rice plant exists
        assert len(simple_spawning_manager.replant_queue) == 0
        assert len(entity_manager.entities) == 1
        new_rice = next(e for e in entity_manager.entities if isinstance(e, Rice))
        assert new_rice is not None
        assert new_rice.age == 0
