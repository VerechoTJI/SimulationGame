# domain/spatial_hash.py
import numpy as np
from collections import defaultdict


class SpatialHash:
    """
    A spatial hash grid for fast entity lookups in a 2D space.

    The grid divides the world into cells of a fixed size. Entities are stored
    in a dictionary mapping cell coordinates to a list of entities within that cell.
    This allows for efficient querying of nearby entities by only checking the
    entity's current cell and its immediate neighbors.
    """

    def __init__(self, cell_size):
        self.cell_size = cell_size
        # Use defaultdict to simplify adding to new cells
        self.grid = defaultdict(list)

    def _get_cell_coords(self, position: np.ndarray) -> tuple[int, int]:
        """Calculates the cell coordinates for a given world position."""
        return (int(position[0] // self.cell_size), int(position[1] // self.cell_size))

    def add(self, entity):
        """Adds an entity to the spatial hash."""
        coords = self._get_cell_coords(entity.position)
        self.grid[coords].append(entity)

    def remove(self, entity):
        """Removes an entity from the spatial hash."""
        coords = self._get_cell_coords(entity.position)
        cell = self.grid.get(coords)
        if cell:
            try:
                cell.remove(entity)
                # If the cell is now empty, remove it from the grid to save memory
                if not cell:
                    del self.grid[coords]
            except ValueError:
                # Entity was not in the cell, which can happen. Ignore.
                pass

    def update(self, entity, old_position: np.ndarray, new_position: np.ndarray):
        """
        Updates an entity's position in the grid.

        This is more efficient than a simple remove and add, as it avoids
        recalculating the new position and only performs operations if the
        entity has actually moved to a new cell.
        """
        old_coords = self._get_cell_coords(old_position)
        new_coords = self._get_cell_coords(new_position)

        if old_coords != new_coords:
            # Remove from the old cell
            cell = self.grid.get(old_coords)
            if cell:
                try:
                    cell.remove(entity)
                    if not cell:
                        del self.grid[old_coords]
                except ValueError:
                    # This can happen if state is inconsistent, but we can recover
                    # by just adding it to the new cell.
                    pass

            # Add to the new cell
            self.grid[new_coords].append(entity)

    def find_nearby(self, position: np.ndarray) -> list:
        """
        Finds all entities in the same cell as the given position and in the
        eight neighboring cells.
        """
        center_coords = self._get_cell_coords(position)
        nearby_entities = []

        for y_offset in range(-1, 2):
            for x_offset in range(-1, 2):
                check_coords = (
                    center_coords[0] + y_offset,
                    center_coords[1] + x_offset,
                )
                # .get() is used to safely handle cells that don't exist (are empty)
                nearby_entities.extend(self.grid.get(check_coords, []))

        return nearby_entities
