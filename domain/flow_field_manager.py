# domain/flow_field_manager.py
import numpy as np
from queue import PriorityQueue
import math
import collections
import random


class FlowFieldManager:
    """
    Manages the creation and incremental update of flow fields using a
    double-buffered, chunk-based system to ensure responsive, non-blocking updates.
    """

    def __init__(self, grid, chunk_size: int = 16):
        self.grid = grid
        self.height = len(grid)
        self.width = len(grid[0]) if self.height > 0 else 0
        self.CARDINAL_COST = 1.0
        self.DIAGONAL_COST = math.sqrt(2)
        self.NEIGHBORS = [
            (-1, 0),
            (1, 0),
            (0, -1),
            (0, 1),
            (-1, -1),
            (-1, 1),
            (1, -1),
            (1, 1),
        ]

        # Chunking attributes for vector field updates
        self.chunk_size = chunk_size
        self.chunks_high = math.ceil(self.height / self.chunk_size)
        self.chunks_wide = math.ceil(self.width / self.chunk_size)
        self.dirty_chunks = collections.deque()

        # Core data fields
        self.goal_positions = set()
        self.flow_field = np.zeros((self.height, self.width, 2), dtype=np.int8)

        # --- DOUBLE BUFFERED COST FIELD ---
        # The 'active' field is the last known good one, used for vector generation.
        self.active_cost_field = np.full(
            (self.height, self.width), np.inf, dtype=np.float32
        )
        # The 'recalculating' field is the back-buffer we work on.
        self.recalculating_cost_field = np.full(
            (self.height, self.width), np.inf, dtype=np.float32
        )

        # --- REFINED STATE MACHINE ---
        self.recalculation_needed = False
        self.recalculation_in_progress = False
        self.dijkstra_pq = PriorityQueue()

    def _is_passable(self, y, x):
        return self.grid[y][x].tile_move_speed_factor > 0

    def add_goal(self, position_yx: tuple[int, int]):
        if position_yx not in self.goal_positions:
            self.goal_positions.add(position_yx)
            self.recalculation_needed = True

    def remove_goal(self, position_yx: tuple[int, int]):
        if position_yx in self.goal_positions:
            self.goal_positions.discard(position_yx)
            self.recalculation_needed = True

    def _start_cost_field_recalculation(self):
        """Initializes Dijkstra on the 'recalculating' back-buffer."""
        self.recalculating_cost_field.fill(np.inf)
        self.dijkstra_pq = PriorityQueue()

        for y, x in self.goal_positions:
            if 0 <= y < self.height and 0 <= x < self.width and self._is_passable(y, x):
                self.recalculating_cost_field[y, x] = 0
                self.dijkstra_pq.put((0, (y, x)))

        self.recalculation_in_progress = True
        self.recalculation_needed = False

    def _continue_cost_field_recalculation(self, node_budget: int):
        """Processes nodes, writing to the 'recalculating' back-buffer."""
        nodes_processed = 0
        while not self.dijkstra_pq.empty() and nodes_processed < node_budget:
            current_cost, (y, x) = self.dijkstra_pq.get()
            nodes_processed += 1

            if current_cost > self.recalculating_cost_field[y, x]:
                continue

            for dy, dx in self.NEIGHBORS:
                ny, nx = y + dy, x + dx
                if not (
                    0 <= ny < self.height and 0 <= nx < self.width
                ) or not self._is_passable(ny, nx):
                    continue
                if (
                    dy != 0
                    and dx != 0
                    and (
                        not self._is_passable(y + dy, x)
                        or not self._is_passable(y, x + dx)
                    )
                ):
                    continue

                neighbor_tile = self.grid[ny][nx]
                tile_cost = 1.0 / neighbor_tile.tile_move_speed_factor
                move_cost = (
                    self.DIAGONAL_COST if dx != 0 and dy != 0 else self.CARDINAL_COST
                )
                new_cost = current_cost + (move_cost * tile_cost)

                if new_cost < self.recalculating_cost_field[ny, nx]:
                    self.recalculating_cost_field[ny, nx] = new_cost
                    self.dijkstra_pq.put((new_cost, (ny, nx)))

        if self.dijkstra_pq.empty():
            # Calculation is finished! Perform the atomic swap.
            self.recalculation_in_progress = False
            self.active_cost_field = self.recalculating_cost_field
            # Create a new back-buffer for the next calculation.
            self.recalculating_cost_field = np.full(
                (self.height, self.width), np.inf, dtype=np.float32
            )
            # Signal that the vector field needs a full update based on the new data.
            self._dirty_all_chunks()

    def _dirty_all_chunks(self):
        """Marks all chunks as dirty in a random order."""
        self.dirty_chunks.clear()
        all_chunks = [
            (cy, cx) for cy in range(self.chunks_high) for cx in range(self.chunks_wide)
        ]
        random.shuffle(all_chunks)
        self.dirty_chunks.extend(all_chunks)

    def _process_one_dirty_chunk_vectors(self):
        """Recalculates vectors for a chunk, ALWAYS reading from the stable active_cost_field."""
        if not self.dirty_chunks:
            return

        cy, cx = self.dirty_chunks.popleft()
        y_start, x_start = cy * self.chunk_size, cx * self.chunk_size
        y_end = min(y_start + self.chunk_size, self.height)
        x_end = min(x_start + self.chunk_size, self.width)

        for y in range(y_start, y_end):
            for x in range(x_start, x_end):
                if np.isinf(self.active_cost_field[y, x]):
                    self.flow_field[y, x] = [0, 0]
                    continue

                min_cost = self.active_cost_field[y, x]
                best_move = (0, 0)
                for dy, dx in self.NEIGHBORS:
                    ny, nx = y + dy, x + dx
                    if not (0 <= ny < self.height and 0 <= nx < self.width):
                        continue
                    if (
                        dy != 0
                        and dx != 0
                        and (
                            not self._is_passable(y + dy, x)
                            or not self._is_passable(y, x + dx)
                        )
                    ):
                        continue
                    if self.active_cost_field[ny, nx] < min_cost:
                        min_cost = self.active_cost_field[ny, nx]
                        best_move = (dy, dx)
                self.flow_field[y, x] = best_move

    def process_flow_field_update(self, node_budget: int = 256, chunk_budget=16):
        """
        The main update function. It can process BOTH the background cost field
        and the foreground vector field in the same tick.
        """
        # --- DECOUPLED PROCESSING ---
        # 1. Start or continue the background cost field calculation.
        if self.recalculation_needed and not self.recalculation_in_progress:
            self._start_cost_field_recalculation()

        if self.recalculation_in_progress:
            self._continue_cost_field_recalculation(node_budget)

        # 2. Independently, update one chunk of the vector field.
        # This is non-blocking because it reads from the stable active_cost_field.
        if self.dirty_chunks:
            counter = 0
            while len(self.dirty_chunks) > 0 and counter < chunk_budget:
                self._process_one_dirty_chunk_vectors()
                counter += 1

    # generate_flow_field can be removed or left for legacy tests, but is not part of the main logic.
    def generate_flow_field(
        self, goal_positions_yx: list[tuple[int, int]], return_cost_field=False
    ):
        self.goal_positions = set(goal_positions_yx)
        self.recalculation_needed = True
        self.process_flow_field_update(
            node_budget=self.width * self.height * 8
        )  # Do full cost calc
        while self.recalculation_in_progress:
            self.process_flow_field_update(node_budget=self.width * self.height * 8)
        while self.dirty_chunks:  # Do full vector calc
            self.process_flow_field_update(node_budget=0)

        if return_cost_field:
            return self.flow_field, self.active_cost_field
        else:
            return self.flow_field
