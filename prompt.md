### **New Start Prompt v0.9**

Hello! Your task is to continue the development of a Python command-line simulation game. The project follows Domain-Driven Design (DDD), Test-Driven Development (TDD), and Clean Architecture principles.

**Project Goal:** To build a robust, extensible, and well-architected simulation where complex emergent behaviors can be added safely.

**Core Methodologies:**

- **Domain-Driven Design (DDD):** Code is separated into `Presentation`, `Application`, and `Domain` layers. The `Domain` layer contains the core business logic and is completely independent.
- **Test-Driven Development (TDD):** New features and refactoring are driven by `pytest`. We write failing tests first, then implement the logic to make them pass. We meticulously fix and update tests to reflect new, correct behavior.
- **Clean Architecture:** Dependencies point inwards (`Presentation` -> `Application` -> `Domain`). The `GameService` exposes use cases, and the `World` class acts as a domain facade.

**Key Project Specifications:**

- **Technology:** Python, `numpy`, `perlin-noise`, `pytest`, `keyboard`.
- **Coordinate System:** Standardized on **`(y, x)` (row, column)** for all grid and position data, consistent with `numpy` array indexing. This is a non-negotiable standard.
- **Architecture:** Multi-threaded (fast render loop, slower logic tick), data-driven via `config.json`.
- **World:** A grid-based map with Land, Water, and Mountain tiles affecting movement.
- **Entities:**
  - `Human`: Navigates using a hybrid system: a centralized **Flow Field** for scalable food-seeking when hungry, and **A\*** for individual wandering when not. Has `saturation`, eats `Rice`, and reproduces.
  - `Sheep`: A simple animal that wanders using A\*, eats `Rice` when hungry, and reproduces. Its food-seeking is now a **long-range, radius-based search** using the spatial hash, and it can correctly filter for _mature_ rice.
  - `Rice`: Matures over time and spawns naturally.
  - **Optimization:** All entities are managed by a generic **Object Pooling** system. All entities are tracked by a **Spatial Hash** grid for fast, proximity-based lookups.

**Project File Hierarchy & Explanations:**

- `config.json`: **Data-driven core.** Defines all simulation parameters, including entity attributes, spawning rules, and AI behaviors like search radius.
- `cli_main.py`: **Minimal entry point.** Sets up Python path, calls main run function.
- `presentation/`: **Presentation Layer.**
  - `__init__.py`: Marks as a package.
  - `main.py`: Orchestrates the CLI app, initializes services, `shared_state`, and threads.
  - `input_handler.py`: Manages keyboard input, updates `keys_down`, and dispatches commands.
  - `renderer.py`: Contains the `display` function responsible for drawing the entire game state to the terminal.
  - `game_loop.py`: Contains the primary `game_loop`. It handles smooth camera movement, drains the `command_queue`, and controls the timed game tick.
- `application/`: **Application Layer.**
  - `__init__.py`: Marks as a package.
  - `config.py`: Singleton for loading `config.json`.
  - `game_service.py`: Exposes application use cases (e.g., `toggle_pause`, `execute_user_command`). Catches domain errors and translates them into user-facing log messages.
- `domain/`: **Domain Layer.**
  - `__init__.py`: Marks as a package.
  - `object_pool.py`: Generic `ObjectPool` and `PooledObjectMixin`.
  - `entity.py`: Base `Entity` class. `position` is a `numpy` array in `[y, x]` format.
  - `tile.py`: Defines `Tile` class and `TILES` dictionary.
  - `pathfinder.py`: A\* pathfinding logic, encapsulated in a `Pathfinder` class.
  - `flow_field_manager.py`: Generates vector fields using Dijkstra.
  - `spatial_hash.py`: **Updated.** A generic spatial hash grid. Now includes `find_closest_in_radius` for optimized single-target searches and `find_in_radius` for getting all entities within an area.
  - `entity_manager.py`: **Heavily refactored.** Manages entity lifecycle and object pools. **Crucially, it now uses Python's `inspect` module** to intelligently pass only the relevant attributes from the config to entity constructors, making it truly robust and generic. It also provides a powerful `find_closest_entity_in_radius` facade that correctly handles complex predicate-based searches over large distances.
  - `spawning_manager.py`: Manages entity spawning rules based on `config.json`.
  - `human.py`: Logic for the `Human` entity.
  - `sheep.py`: **Updated.** Logic for the `Sheep` entity. Now uses its `search_radius` attribute to call the `EntityManager`'s long-range search function.
  - `rice.py`: Logic for the `Rice` entity.
  - `world.py`: Central domain facade. Uses the refactored managers for all entity operations.
- `tests/`: **Testing Layer.**
  - `__init__.py`: Marks as a package.
  - `conftest.py`: Shared pytest fixtures, including `mock_config` and `world_no_spawn` (a deterministic World for integration testing). `mock_config` is updated to include `sheep` search radius.
  - `test_object_pool.py`: Unit tests for `ObjectPool`.
  - `test_pathfinder.py`: Unit tests for `Pathfinder`.
  - `test_flow_field_manager.py`: Unit tests for `FlowFieldManager`.
  - `test_spatial_hash.py`: **Updated.** Now includes tests for `find_closest_in_radius` and `find_in_radius`.
  - `test_entity_manager.py`: **Updated.** Includes a new, critical **integration test** (`test_find_closest_entity_in_radius_with_predicate`) that validates the manager's ability to perform a correct, filtered, long-range search without mocks.
  - `test_spawning_manager.py`: Tests for the generic initial spawning logic.
  - `test_human_logic.py`: Unit tests for `Human` logic.
  - `test_rice_logic.py`: **Updated.** Tests are now robust against unrelated config changes due to the `EntityManager` refactoring.
  - `test_sheep_logic.py`: **Updated.** Includes tests for the new long-range food-seeking AI. All test assertions are now correctly aligned with config keys.
  - `test_game_service.py`: Unit tests for `GameService`.
  - `test_world_logic.py`: Tests for `World` logic.
  - `test_domain_integration.py`: Integration tests for the whole domain layer.

**Recent Accomplishments & Key Learnings:**

1.  **Implemented Long-Range AI:** We successfully gave `Sheep` the ability to find food over long distances. This involved enhancing the `SpatialHash` and `EntityManager` with radius-based search capabilities.
2.  **Architectural Refactoring with `inspect`:** We encountered a critical `TypeError` when our `EntityManager` blindly passed all configured attributes to entity constructors. We fixed this by refactoring the `EntityManager` to use Python's `inspect` module. It now intelligently filters keyword arguments, ensuring a method only receives the parameters it explicitly defines. This makes the entity management system truly generic, robust, and data-driven, a major architectural improvement.
3.  **The Power of Integration Testing:** Our TDD process initially had a flaw where mocked tests for the `Sheep`'s AI passed, but the underlying implementation in `EntityManager` was incorrect. By adding a non-mocked **integration test** specifically for the `EntityManager`'s predicate search logic, we correctly identified and fixed the bug. This was a key learning moment: unit tests and mocked tests are essential, but targeted integration tests are invaluable for verifying the contracts between components.
4.  **Maintaining Test Suite Health:** We identified and fixed several minor bugs in the test suite itself, including incorrect assertion keys (`reproduction_cooldown_max`). This reinforces the importance of treating test code as first-class production code.

**IMPORTANT: Our Interaction Model**
**Development Workflow:**

- **Phase 1: The Plan:** I will first propose a high-level plan. This will include:
  1.  **Goal Definition:** A clear statement of what we are trying to achieve.
  2.  **Ambiguity Check:** I will analyze the task for any potential implicit or inconsistent standards (e.g., coordinate systems). If ambiguities exist, I will propose an explicit standard we must follow. This is our primary defense against architectural decay.
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
5.  Make sure you included the file path at the start of code, ex: `# tests/test_spatial_hash.py`
