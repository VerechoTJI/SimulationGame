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
        # Check vectors to ensure they point towards the goal, navigating the obstacle.
        # Vector format is (dy, dx). With new costs, shortest path logic holds.
        assert np.array_equal(
            flow_field[0, 0], [1, 0]
        ), "From (0,0) should be S (dy=1, dx=0)"
        assert np.array_equal(
            flow_field[1, 0], [1, 1]
        ), "From (0,0) should be SE (dy=1, dx=1)"
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

        # (2,2) is closer to Goal B, path starts by going West.
        assert np.array_equal(
            flow_field[2, 2], [0, -1]
        ), "Should point West towards path to Goal B"

        # (0,0) is equidistant step-wise, but closer to B (4,0) via diagonal path
        assert np.array_equal(
            flow_field[0, 0], [1, 0]
        ), "From (0,0) closer path is to Goal B"

        assert np.array_equal(flow_field[0, 4], [0, 0]), "Goal A vector should be zero"
        assert np.array_equal(flow_field[4, 0], [0, 0]), "Goal B vector should be zero"

    def test_differentiated_cardinal_diagonal_cost(self):
        """
        Tests that the cost field correctly assigns a higher cost to
        diagonal movement (~1.414) than to cardinal movement (1.0).
        This is the core fix for preventing flow field spirals on plateaus.
        """
        # ARRANGE
        grid = [[TILES["land"]] * 3 for _ in range(3)]
        manager = FlowFieldManager(grid)
        goal_pos = [(1, 1)]  # Center goal

        # ACT
        # Call the method requesting the cost_field for testing purposes.
        _, cost_field = manager.generate_flow_field(goal_pos, return_cost_field=True)

        # ASSERT
        # The goal itself has zero cost
        assert cost_field[1, 1] == 0, "Cost at the goal should be 0"

        # Cardinal neighbors (straight line) should have a cost of 1.0
        assert np.isclose(cost_field[1, 0], 1.0), "Cardinal cost should be 1.0"
        assert np.isclose(cost_field[0, 1], 1.0), "Cardinal cost should be 1.0"

        # Diagonal neighbors should have a cost of sqrt(2)
        sqrt_2 = math.sqrt(2)
        assert np.isclose(
            cost_field[0, 0], sqrt_2
        ), f"Diagonal cost should be ~{sqrt_2}"
        assert np.isclose(
            cost_field[2, 2], sqrt_2
        ), f"Diagonal cost should be ~{sqrt_2}"
