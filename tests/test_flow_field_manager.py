# tests/test_flow_field_manager.py

import pytest
import numpy as np
import math
from domain.flow_field_manager import FlowFieldManager
from domain.tile import TILES


@pytest.fixture
def test_grid():
    """
    Provides a 5x5 grid with a 'U' shaped obstacle.
    L L L L L
    L W W W L
    L L G W L  (G = Goal will be at (2,2))
    L W W W L
    L L L L L
    """
    grid = [
        [TILES["land"]] * 5,
        [TILES["land"], TILES["water"], TILES["water"], TILES["water"], TILES["land"]],
        [TILES["land"], TILES["land"], TILES["land"], TILES["water"], TILES["land"]],
        [TILES["land"], TILES["water"], TILES["water"], TILES["water"], TILES["land"]],
        [TILES["land"]] * 5,
    ]
    return grid


@pytest.fixture
def flow_manager(test_grid):
    return FlowFieldManager(test_grid)


class TestFlowFieldManager:
    def test_field_generation_single_goal(self, flow_manager):
        # ARRANGE
        goal_pos = [(2, 2)]  # The 'G' in the diagram

        # ACT
        flow_field = flow_manager.generate_flow_field(goal_pos)

        # ASSERT
        # With corner-cutting prevention, some paths change.
        # (1,0) must go to (2,0) then (2,1). Path is now (1,0)->(2,0). Vector is [1,0]
        # not SE.
        assert np.array_equal(
            flow_field[0, 0], [1, 0]
        ), "From (0,0) should be S (dy=1, dx=0)"
        assert np.array_equal(
            flow_field[1, 0], [1, 0]
        ), "From (1,0) should be S (dy=1, dx=0), not SE, to avoid water corner"
        assert np.array_equal(
            flow_field[2, 0], [0, 1]
        ), "From (2,0) should be E (dy=0, dx=1)"

        assert np.array_equal(
            flow_field[4, 4], [0, -1]
        ), "From (4,4) should be W (dy=0, dx=-1)"

        # Position of the goal itself should be (0,0) as it has nowhere to go
        assert np.array_equal(
            flow_field[2, 2], [0, 0]
        ), "Goal tile vector should be zero"

        # Impassable water tiles should have a (0,0) vector
        assert np.array_equal(
            flow_field[1, 1], [0, 0]
        ), "Impassable tile vector should be zero"
        assert np.array_equal(
            flow_field[1, 2], [0, 0]
        ), "Impassable tile vector should be zero"

    def test_no_goals_results_in_zero_field(self, flow_manager):
        # ARRANGE
        goal_pos = []

        # ACT
        flow_field = flow_manager.generate_flow_field(goal_pos)

        # ASSERT
        assert np.all(flow_field == 0)

    def test_unreachable_area_has_zero_vector(self):
        # ARRANGE
        grid = [
            [TILES["land"], TILES["water"], TILES["land"]],
            [TILES["land"], TILES["water"], TILES["land"]],
            [TILES["land"], TILES["water"], TILES["land"]],
        ]
        manager = FlowFieldManager(grid)
        goal_pos = [(1, 2)]

        # ACT
        flow_field = manager.generate_flow_field(goal_pos)

        # ASSERT
        assert np.array_equal(flow_field[0, 0], [0, 0])
        assert np.array_equal(flow_field[1, 0], [0, 0])
        assert np.array_equal(flow_field[2, 0], [0, 0])
        assert np.array_equal(flow_field[0, 2], [1, 0])
        assert np.array_equal(flow_field[1, 2], [0, 0])
        assert np.array_equal(flow_field[2, 2], [-1, 0])

    def test_field_generation_multiple_goals(self, flow_manager):
        """
        Tests that the flow field correctly points to the NEAREST of two goals.
        This test is updated to account for corner-cutting prevention.
        """
        # ARRANGE
        goal_positions = [(0, 4), (4, 0)]  # Goal A (top-right), Goal B (bottom-left)

        # ACT
        flow_field = flow_manager.generate_flow_field(goal_positions)

        # ASSERT
        assert np.array_equal(flow_field[0, 3], [0, 1]), "Should point East to Goal A"
        assert np.array_equal(flow_field[1, 4], [-1, 0]), "Should point North to Goal A"
        assert np.array_equal(flow_field[4, 1], [0, -1]), "Should point West to Goal B"
        assert np.array_equal(flow_field[3, 0], [1, 0]), "Should point South to Goal B"

        # (2,2) must now go (2,1)->(2,0)->... to reach Goal B. It points West.
        assert np.array_equal(
            flow_field[2, 2], [0, -1]
        ), "Should point West towards path to Goal B"

        # (0,0) is equidistant. The path is non-deterministic based on tie-breaks.
        # The vector should be South [1,0] or East [0,1].
        vector_at_0_0 = flow_field[0, 0]
        is_valid_vector = np.array_equal(vector_at_0_0, [1, 0]) or np.array_equal(
            vector_at_0_0, [0, 1]
        )
        assert (
            is_valid_vector
        ), f"From (0,0) vector should be [1,0] or [0,1], but was {vector_at_0_0}"

        assert np.array_equal(flow_field[0, 4], [0, 0]), "Goal A vector should be zero"
        assert np.array_equal(flow_field[4, 0], [0, 0]), "Goal B vector should be zero"

    def test_differentiated_cardinal_diagonal_cost(self):
        # ... (This test remains unchanged) ...
        # ARRANGE
        grid = [[TILES["land"]] * 3 for _ in range(3)]
        manager = FlowFieldManager(grid)
        goal_pos = [(1, 1)]  # Center goal
        _, cost_field = manager.generate_flow_field(goal_pos, return_cost_field=True)
        assert cost_field[1, 1] == 0
        assert np.isclose(cost_field[1, 0], 1.0)
        sqrt_2 = math.sqrt(2)
        assert np.isclose(cost_field[0, 0], sqrt_2)

    def test_generate_flow_field_with_tile_costs(self):
        # ... (This test remains unchanged) ...
        # ARRANGE
        grid = [
            [TILES["land"], TILES["land"], TILES["land"]],
            [TILES["land"], TILES["mountain"], TILES["land"]],
            [TILES["land"], TILES["land"], TILES["land"]],
        ]
        manager = FlowFieldManager(grid)
        goal_pos = [(1, 2)]
        flow_field = manager.generate_flow_field(goal_pos)
        vector_at_1_0 = flow_field[1, 0]
        is_correct_vector = np.array_equal(vector_at_1_0, [-1, 1]) or np.array_equal(
            vector_at_1_0, [1, 1]
        )
        assert (
            is_correct_vector
        ), f"Vector at (1,0) should be [-1, 1] or [1, 1] (detour), but was {vector_at_1_0}"

    def test_flow_field_avoids_diagonal_corner_cutting(self):
        """
        Tests that flow field generation avoids paths that cut corners
        of impassable tiles.
        Grid:
          L L G   G=Goal(0,2)
          L W L   W=Water(1,1)
          L L L
        The vector at (1,0) should point North to (0,0), not diagonally NE,
        as that path is blocked by the corner of the water tile.
        """
        # ARRANGE
        grid = [
            [TILES["land"], TILES["land"], TILES["land"]],
            [TILES["land"], TILES["water"], TILES["land"]],
            [TILES["land"], TILES["land"], TILES["land"]],
        ]
        manager = FlowFieldManager(grid)
        goal_pos = [(0, 2)]

        # ACT
        flow_field = manager.generate_flow_field(goal_pos)

        # ASSERT
        # The incorrect vector at (1,0) would be (-1, 1) as it cuts the corner.
        # The correct vector must be (-1, 0) to go North first.
        vector_at_1_0 = flow_field[1, 0]
        expected_vector = np.array([-1, 0])
        assert np.array_equal(
            vector_at_1_0, expected_vector
        ), f"Vector at (1,0) should be {expected_vector} to avoid corner, but was {vector_at_1_0}"
