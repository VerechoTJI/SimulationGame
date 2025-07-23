### **New Start Prompt v0.6**

Hello! Your task is to continue the development of a Python command-line simulation game. The project follows Domain-Driven Design (DDD), Test-Driven Development (TDD), and Clean Architecture principles.

**Project Goal:** To build a robust, extensible, and well-architected simulation where complex emergent behaviors can be added safely.

**Core Methodologies:**

- **Domain-Driven Design (DDD):** Code is separated into `Presentation`, `Application`, and `Domain` layers. The `Domain` layer contains the core business logic and is completely independent.
- **Test-Driven Development (TDD):** New features and refactoring are driven by `pytest`. We write failing tests first (or ensure existing tests fail correctly before a fix), then implement the logic to make them pass.
- **Clean Architecture:** Dependencies point inwards (`Presentation` -> `Application` -> `Domain`). The `GameService` exposes use cases, and the `World` class acts as a domain facade.

**Key Project Specifications:**

- **Technology:** Python, `numpy`, `perlin-noise`, `pytest`, `keyboard`.
- **Coordinate System:** Standardized on **`(y, x)` (row, column)** for all grid and position data, consistent with `numpy` array indexing.
- **Architecture:** Multi-threaded (fast render loop, slower logic tick), data-driven via `config.json`.
- **World:** A grid-based map with Land, Water, and Mountain tiles affecting movement.
- **Entities:**
  - `Human`: Navigates using a hybrid system: a centralized **Flow Field** for scalable food-seeking when hungry, and **A\*** for individual wandering when not. Has `saturation`, eats `Rice`, and reproduces.
  - `Rice`: Matures over time and spawns naturally.
  - **Optimization:** All entities are managed by a generic **Object Pooling** system (`domain/object_pool.py`) to reduce runtime overhead.

**Project File Hierarchy & Explanations:**

- `config.json`: Data file for all simulation parameters.
- `cli_main.py`: **Minimal entry point.** Sets up Python path, calls main run function.
- `presentation/`: **Presentation Layer.**
  - `__init__.py`: Marks as a package.
  - `main.py`: Orchestrates the CLI app, initializes services, `shared_state`, and threads.
  - `input_handler.py`: Manages keyboard input, updates `keys_down`, and dispatches commands.
  - `renderer.py`: Contains the `display` function responsible for drawing the entire game state to the terminal. Now includes logic to conditionally render the `food_flow_field` as a grid of arrows for debugging purposes.
  - `game_loop.py`: Contains the primary `game_loop`. It handles smooth camera movement, drains the `command_queue` for logic commands, and controls the timed game tick. It processes the `__TOGGLE_FLOW_FIELD__` command by calling the appropriate service method.
- `application/`: **Application Layer.**
  - `__init__.py`: Marks as a package.
  - `config.py`: Singleton for loading `config.json`.
  - `game_service.py`: Exposes application use cases (e.g., `toggle_pause`, `speed_up`). It orchestrates the domain layer and now manages the state for debug visualizations (e.g., `toggle_flow_field_visibility`).
- `domain/`: **Domain Layer.**
  - `__init__.py`: Marks as a package.
  - `object_pool.py`: Generic `ObjectPool` and `PooledObjectMixin`.
  - `entity.py`: Base `Entity` class. `position` is a `numpy` array in `[y, x]` format.
  - `tile.py`: Defines `Tile` class and `TILES` dictionary.
  - `pathfinder.py`: A\* pathfinding logic, used by `Human` entities for non-food-related wandering.
  - `flow_field_manager.py`: Generates vector fields using BFS. Expects goal positions as `(y, x)` tuples.
  - `entity_manager.py`: Manages entity lifecycle: object pools, creation (`create_human`), storage (`entities` list), and cleanup.
  - `spawning_manager.py`: Manages spawning rules. All methods use `(y, x)` coordinates.
  - `human.py`: Logic for the `Human` entity. Implements a hybrid movement model, switching between following the `World`'s flow field and using A\* for wandering.
  - `rice.py`: Logic for the `Rice` entity.
  - `world.py`: Central domain facade. It holds the map `grid` and orchestrates the `game_tick`, delegating tasks to its managers and periodically regenerating the `food_flow_field`.
- `tests/`: **Testing Layer.**
  - `__init__.py`: Marks as a package.
  - `conftest.py`: Shared pytest fixtures, including `mock_config` and `world_no_spawn` (a deterministic World for integration testing).
  - `test_object_pool.py`: Unit tests for `ObjectPool`.
  - `test_pathfinder.py`: Unit tests for `Pathfinder`, using `(y, x)` coordinates.
  - `test_flow_field_manager.py`: Unit tests for `FlowFieldManager`.
  - `test_entity_manager.py`: Unit tests for `EntityManager`, using `(y, x)` coordinates.
  - `test_spawning_manager.py`: Unit tests for `SpawningManager`, using `(y, x)` coordinates.
  - `test_human_logic.py`: Unit tests for `Human` logic.
  - `test_rice_logic.py`: Unit tests for `Rice` logic.
  - `test_game_service.py`: Unit tests for `GameService`.
  - `test_world_logic.py`: Integration tests for `World` logic, now using `(y, x)`.
  - `test_domain_integration.py`: Crucial integration tests, now using `(y, x)`.

**Recent Accomplishments & Key Learnings:**

1.  **Architectural Refactoring: Coordinate System Unification:** We successfully resolved a "spiral bug" in the flow field visualization. The investigation revealed the root cause was not an algorithmic flaw, but a systemic data inconsistency due to mixed use of `(x, y)` and `(y, x)` coordinate formats across different layers.
2.  **Systematic Correction:** We performed a major refactoring, standardizing the entire codebase on the **`(y, x)`** format. This involved a methodical, TDD-style update of the domain, application, and presentation layers, along with all corresponding tests.
3.  **Reinforced Architectural Principles:** This process was a powerful demonstration of Clean Architecture. The bug lived in the "seams" between layers, and fixing it required enforcing a strict, unambiguous data contract (the `(y, x)` standard) for all interactions. The successful outcome validated the importance of this architectural discipline for building a robust system.

**IMPORTANT: Our Interaction Model**
**Development Workflow:**

- **Phase 1: The Plan:** I will first propose a high-level plan. This will include:
  1.  **Goal Definition:** A clear statement of what we are trying to achieve.
  2.  **Ambiguity Check (New Rule):** I will analyze the task for any potential implicit or inconsistent standards (e.g., coordinate systems, data units, naming). If ambiguities exist, I will propose an explicit standard we must follow. This is our primary defense against architectural decay.
  3.  **Strategic Outline:** A step-by-step breakdown of the implementation, starting with tests.
  4.  **Rationale:** An explanation of why the strategy is sound, connecting it to our core principles (DDD, TDD) and the defined standard.
- **Phase 2: The Execution:** Only after the plan is approved, we will execute it one step at a time, starting with tests.

**Context-Limited Mode & Our Core Rule:**
To ensure accuracy, you operate in a context-limited mode and do not have persistent memory of file contents. Therefore, we will adhere to this strict process:

1.  Before writing any test or implementation code, you MUST first identify the primary file to modify and its critical dependencies. You will then request the full code for all these files at once.
    - _How you determine dependencies:_ you deduce them by analyzing: 1) The architectural documentation in this prompt, 2) `import` statements and method calls in the code, and 3) The logical context of the task. You can also request extra code for more context.
2.  You **do not** have the full code for every module memorized. You must rely on the file hierarchy and explanations provided above as your primary "map" of the project.
3.  **Before you suggest any modifications to an existing file, you MUST first ask me to provide its full and current code.** For example, say: "Understood. We need to modify `domain/human.py` and `domain/world.py`. Please provide me with the full contents of both files."
4.  When providing code, you will typically only post the modified part unless a full file replacement is necessary.
