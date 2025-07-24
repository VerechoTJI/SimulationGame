# test/test_spatial_hash.py
import numpy as np
import pytest

# We will create this class in the next step. For now, we assume it exists.
from domain.spatial_hash import SpatialHash


# A simple mock entity class for testing purposes
class MockEntity:
    def __init__(self, y, x):
        self.position = np.array([y, x])
        self.id = id(self)  # Unique identifier

    def __repr__(self):
        return f"MockEntity({self.position[0]}, {self.position[1]})"


@pytest.fixture
def spatial_hash():
    """Returns a SpatialHash instance with a cell size of 10."""
    return SpatialHash(cell_size=10)


class TestSpatialHash:
    def test_initialization(self, spatial_hash):
        assert spatial_hash.cell_size == 10
        assert spatial_hash.grid == {}

    def test_get_cell_coords(self, spatial_hash):
        position = np.array([25, 58])
        cell_coords = spatial_hash._get_cell_coords(position)
        assert cell_coords == (2, 5)

        position_zero = np.array([0, 0])
        cell_coords_zero = spatial_hash._get_cell_coords(position_zero)
        assert cell_coords_zero == (0, 0)

        position_edge = np.array([9, 19])
        cell_coords_edge = spatial_hash._get_cell_coords(position_edge)
        assert cell_coords_edge == (0, 1)

    def test_add_entity(self, spatial_hash):
        entity = MockEntity(15, 25)
        spatial_hash.add(entity)

        cell_coords = (1, 2)
        assert cell_coords in spatial_hash.grid
        assert entity in spatial_hash.grid[cell_coords]
        assert len(spatial_hash.grid[cell_coords]) == 1

    def test_add_multiple_entities_to_same_cell(self, spatial_hash):
        entity1 = MockEntity(12, 22)
        entity2 = MockEntity(18, 28)
        spatial_hash.add(entity1)
        spatial_hash.add(entity2)

        cell_coords = (1, 2)
        assert cell_coords in spatial_hash.grid
        assert entity1 in spatial_hash.grid[cell_coords]
        assert entity2 in spatial_hash.grid[cell_coords]
        assert len(spatial_hash.grid[cell_coords]) == 2

    def test_remove_entity(self, spatial_hash):
        entity = MockEntity(33, 44)
        spatial_hash.add(entity)
        cell_coords = (3, 4)

        assert entity in spatial_hash.grid[cell_coords]

        spatial_hash.remove(entity)
        assert not spatial_hash.grid[cell_coords]  # Cell list should be empty

    def test_remove_nonexistent_entity(self, spatial_hash):
        # This should not raise an error
        entity = MockEntity(10, 10)
        spatial_hash.remove(entity)

    def test_find_nearby_returns_entities_in_same_and_adjacent_cells(
        self, spatial_hash
    ):
        # Center entity
        entity_center = MockEntity(55, 55)

        # Entities in the same cell (5, 5)
        entity_same_cell = MockEntity(51, 51)

        # Entities in adjacent cells
        # (4, 4), (4, 5), (4, 6)
        # (5, 4), (5, 5), (5, 6)
        # (6, 4), (6, 5), (6, 6)
        entity_adj_1 = MockEntity(45, 45)  # Cell (4, 4)
        entity_adj_2 = MockEntity(65, 65)  # Cell (6, 6)

        # Entity in a far cell, should not be found
        entity_far = MockEntity(101, 101)  # Cell (10, 10)

        entities = [
            entity_center,
            entity_same_cell,
            entity_adj_1,
            entity_adj_2,
            entity_far,
        ]
        for e in entities:
            spatial_hash.add(e)

        nearby_entities = spatial_hash.find_nearby(entity_center.position)

        assert entity_center in nearby_entities
        assert entity_same_cell in nearby_entities
        assert entity_adj_1 in nearby_entities
        assert entity_adj_2 in nearby_entities
        assert entity_far not in nearby_entities
        assert len(nearby_entities) == 4

    def test_find_nearby_at_origin(self, spatial_hash):
        entity1 = MockEntity(2, 2)  # Cell (0, 0)
        entity2 = MockEntity(5, 15)  # Cell (0, 1)
        entity3 = MockEntity(15, 5)  # Cell (1, 0)
        entity4 = MockEntity(15, 15)  # Cell (1, 1)
        entity_far = MockEntity(35, 35)  # Cell (3, 3)

        entities = [entity1, entity2, entity3, entity4, entity_far]
        for e in entities:
            spatial_hash.add(e)

        nearby_entities = spatial_hash.find_nearby(entity1.position)

        # Should find all entities except the far one
        assert len(nearby_entities) == 4
        assert entity_far not in nearby_entities

    def test_update_entity_position(self, spatial_hash):
        entity = MockEntity(25, 25)  # Cell (2, 2)
        spatial_hash.add(entity)

        # Check initial state
        assert entity in spatial_hash.grid[(2, 2)]
        assert len(spatial_hash.grid[(2, 2)]) == 1

        # Move the entity to a new position in a different cell
        new_position = np.array([45, 45])  # Cell (4, 4)
        spatial_hash.update(
            entity, old_position=entity.position, new_position=new_position
        )
        entity.position = new_position  # Don't forget to update the mock entity

        # Check new state
        assert not spatial_hash.grid[(2, 2)]  # Old cell should be empty
        assert entity in spatial_hash.grid[(4, 4)]
        assert len(spatial_hash.grid[(4, 4)]) == 1

    def test_update_entity_position_same_cell(self, spatial_hash):
        entity = MockEntity(25, 25)  # Cell (2, 2)
        spatial_hash.add(entity)

        # Move the entity to a new position within the same cell
        new_position = np.array([28, 28])  # Still cell (2, 2)
        spatial_hash.update(
            entity, old_position=entity.position, new_position=new_position
        )
        entity.position = new_position

        # Check state
        assert len(spatial_hash.grid) == 1
        assert entity in spatial_hash.grid[(2, 2)]
        assert len(spatial_hash.grid[(2, 2)]) == 1
