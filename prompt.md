### **New Start Prompt v0.8**

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
  - `Sheep`: **(New)** A simple animal that wanders using A\*, eats `Rice` when hungry (using a localized spatial hash search), and reproduces.
  - `Rice`: Matures over time and spawns naturally.
  - **Optimization:** All entities are managed by a generic **Object Pooling** system to reduce runtime overhead. All entities are tracked by a **Spatial Hash** grid for fast, proximity-based lookups.

**Project File Hierarchy & Explanations:**

- `config.json`: **Data-driven core.** Defines all simulation parameters, including entity attributes and spawning rules.
- `cli_main.py`: **Minimal entry point.** Sets up Python path, calls main run function.
- `presentation/`: **Presentation Layer.**
  - `__init__.py`: Marks as a package.
  - `main.py`: Orchestrates the CLI app, initializes services, `shared_state`, and threads.
  - `input_handler.py`: Manages keyboard input, updates `keys_down`, and dispatches commands.
  - `renderer.py`: Contains the `display` function responsible for drawing the entire game state to the terminal. Now handles rendering `Sheep`.
  - `game_loop.py`: Contains the primary `game_loop`. It handles smooth camera movement, drains the `command_queue` for logic commands, and controls the timed game tick.
- `application/`: **Application Layer.**
  - `__init__.py`: Marks as a package.
  - `config.py`: Singleton for loading `config.json`.
  - `game_service.py`: Exposes application use cases (e.g., `toggle_pause`, `execute_user_command`). Catches domain errors and translates them into user-facing log messages. Orchestrates the domain layer and prepares render data.
- `domain/`: **Domain Layer.**
  - `__init__.py`: Marks as a package.
  - `object_pool.py`: Generic `ObjectPool` and `PooledObjectMixin`.
  - `entity.py`: Base `Entity` class. `position` is a `numpy` array in `[y, x]` format.
  - `tile.py`: Defines `Tile` class and `TILES` dictionary.
  - `pathfinder.py`: A\* pathfinding logic, encapsulated in a `Pathfinder` class.
  - `flow_field_manager.py`: Generates vector fields using Dijkstra.
  - `spatial_hash.py`: A generic spatial hash grid for fast, proximity-based entity lookups. Configured with a cell size.
  - `entity_manager.py`: **Heavily refactored.** Manages entity lifecycle and object pools dynamically based on `config.json`. It no longer has hardcoded logic for specific entities. It holds a dictionary of object pools and a dictionary of spatial hashes, one for each entity type defined in the config.
  - `spawning_manager.py`: **Refactored.** Manages entity spawning rules. Now reads the `spawning` section of `config.json` to handle initial population of any entity type.
  - `human.py`: Logic for the `Human` entity.
  - `sheep.py`: **(New)** Logic for the `Sheep` entity. Includes a `reset()` method for object pool compatibility.
  - `rice.py`: Logic for the `Rice` entity.
  - `world.py`: **Refactored.** Central domain facade. Now uses the refactored managers to populate the world and handle reproduction generically. Has a clean `spawn_entity` facade for application-layer commands.
- `tests/`: **Testing Layer.**
  - `__init__.py`: Marks as a package.
  - `conftest.py`: Shared pytest fixtures. The `mock_config` now includes `sheep` attributes. The `world_no_spawn` fixture is updated to provide a truly empty world by overriding initial spawn counts, including `mock_config` and `world_no_spawn` (a deterministic World for integration testing).
  - `test_object_pool.py`: Unit tests for `ObjectPool`.
  - `test_pathfinder.py`: Unit tests for `Pathfinder`.
  - `test_flow_field_manager.py`: Unit tests for `FlowFieldManager`.
  - `test_spatial_hash.py`: **(New)** Unit tests verifying the `SpatialHash` component's logic (add, remove, find_nearby, update).
  - `test_entity_manager.py`: **Heavily updated.** All tests refactored to validate the new data-driven `EntityManager` and its generic `create_entity` method.
  - `test_spawning_manager.py`: Updated with tests for the generic initial spawning logic.
  - `test_human_logic.py`: Unit tests for `Human` logic. **Now mocks the `EntityManager`'s search method** to properly test the `Human` in isolation.
  - `test_rice_logic.py`: Logic unit tests for entities.
  - `test_sheep_logic.py`: **(New)** Comprehensive unit tests for all `Sheep` behaviors (movement, eating, reproduction).
  - `test_game_service.py`: Unit tests for `GameService`, now testing the `execute_user_command` error handling.
  - `test_world_logic.py`: **Updated.** Tests refactored to use the new `EntityManager` interface and to test the `world.spawn_entity` facade.
  - `test_domain_integration.py`: **Updated.** Tests refactored to use the new `EntityManager` interface. Added a new smoke test to ensure all entity types can coexist in the world.

**Recent Accomplishments & Key Learnings:**

1.  **Added `Sheep` Entity:** We successfully added a new, autonomous `Sheep` entity to the simulation, complete with wandering, eating, and reproduction logic, driven entirely by TDD.
2.  **Data-Driven Entity Management:** In the process of adding `Sheep`, we refactored the `EntityManager` and `SpawningManager` away from hardcoded logic. They now dynamically configure themselves based _entirely_ on the contents of `config.json`. This makes adding future entities incredibly simple, often requiring only a config change and a new entity logic file.
3.  **Refined Architectural Boundaries:** We had a critical learning moment where we initially placed application-level logic (user feedback/logging) inside the domain layer (`World`). We corrected this by having the domain layer raise an exception (`ValueError`) and letting the application layer (`GameService`) catch it and create the appropriate log message. This strictly enforces the Clean Architecture principle of keeping the domain pure.
4.  **Robust Test-Driven Debugging:** We demonstrated the power of a comprehensive test suite. The tests correctly caught numerous regressions and inconsistencies introduced during our refactoring, including issues with object pool `reset` methods, outdated test assumptions, and subtle misconfigurations between test fixtures and production code. This validated our TDD approach.

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
