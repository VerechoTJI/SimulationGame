### **New Start Prompt** v0.1

Hello! Your task is to continue the development of a Python command-line simulation game. The project follows Domain-Driven Design (DDD), Test-Driven Development (TDD), and Clean Architecture principles.

**Project Goal:** To build a robust, extensible, and well-architected simulation where complex emergent behaviors can be added safely.

**Core Methodologies:**

- **Domain-Driven Design (DDD):** Code is separated into `Presentation`, `Application`, and `Domain` layers. The `Domain` layer contains the core business logic and is completely independent.
- **Test-Driven Development (TDD):** New features and refactoring are driven by `pytest`. We write failing tests first (or ensure existing tests fail correctly before a fix), then implement the logic to make them pass.
- **Clean Architecture:** Dependencies point inwards (`Presentation` -> `Application` -> `Domain`). The `World` class acts as a facade, orchestrating specialized manager classes within the domain.

**Key Project Specifications:**

- **Technology:** Python, `numpy`, `perlin-noise`, `pytest`.
- **Architecture:** Multi-threaded (fast render loop, slower logic tick), data-driven via `config.json`.
- **World:** A grid-based map with Land, Water, and Mountain tiles affecting movement.
- **Entities:**
  - `Human`: Navigates using A\*, has `saturation`, eats `Rice`, and reproduces.
  - `Rice`: Matures over time and spawns naturally.
  - **Optimization:** All entities are managed by a generic **Object Pooling** system (`domain/object_pool.py`) to reduce runtime overhead.

**Project File Hierarchy & Explanations:**

- `config.json`: Data file for all simulation parameters.
- `cli_main.py`: **Presentation Layer.** Renders game state and handles user input.
- `application/`: **Application Layer.**
  - `__init__.py`: Marks as a package.
  - `config.py`: Singleton for loading `config.json`.
  - `game_service.py`: Main entry point for the CLI. Orchestrates the domain layer by interacting with the `World` facade.
- `domain/`: **Domain Layer.**
  - `__init__.py`: Marks as a package.
  - `object_pool.py`: Contains the generic `ObjectPool` and `PooledObjectMixin`.
  - `entity.py`: Base `Entity` class, inheriting from `PooledObjectMixin`.
  - `tile.py`: Defines the `Tile` class and the `TILES` dictionary (Land, Water, Mountain).
  - `pathfinder.py`: Contains the A\* pathfinding logic. `find_path` is its main method.
  - `entity_manager.py`: Manages entity lifecycle: object pools, creation (`create_human`), storage (`entities` list), and cleanup.
  - `spawning_manager.py`: Manages all rules for entity spawning: natural rice spawning, reproduction placement, and the replanting queue.
  - `human.py`: Logic for the `Human` entity. Collaborates with the `World` and its managers to find food and move.
  - `rice.py`: Logic for the `Rice` entity. Implements a `get_eaten()` method.
  - `world.py`: Acts as the central **coordinator/facade** for the domain. It holds the map `grid` and orchestrates the `game_tick`, delegating tasks to its managers (`EntityManager`, `Pathfinder`, `SpawningManager`).
- `tests/`: **Testing Layer.**
  - `__init__.py`: Marks as a package.
  - `conftest.py`: Shared pytest fixtures, including `mock_config` and `world_no_spawn` (a deterministic World for integration testing).
  - `test_object_pool.py`: Unit tests for the `ObjectPool`.
  - `test_pathfinder.py`: Unit tests for the `Pathfinder` class.
  - `test_entity_manager.py`: Unit tests for `EntityManager`, including pooling and finding entities.
  - `test_spawning_manager.py`: Unit tests for `SpawningManager` rules and replanting. (Incorporates tests from the deleted `test_world_spawning.py`).
  - `test_human_logic.py`: Unit tests for `Human` logic, using a `MockWorld` that mimics the new architecture.
  - `test_rice_logic.py`: Unit tests for `Rice` logic.
  - `test_world_logic.py`: High-level integration tests for the `World`'s orchestration logic (e.g., ensuring reproduction correctly uses all managers).
  - `test_domain_integration.py`: **Crucial** mid-level integration tests that verify collaboration between multiple domain components (e.g., a real `Human` finding food in a real `World`).

**Recent Accomplishments & Key Learnings:**

We have just completed a major, successful refactoring of the domain layer to improve its architecture and adhere to the Single Responsibility Principle.

- **The Accomplishment:** The `domain/world.py` "God Object" has been broken down. Its tangled responsibilities are now handled by clean, specialized, and independently testable manager classes.
- **The Solution:**
  1.  `Pathfinder` was created to handle all A\* pathfinding.
  2.  `EntityManager` was created to handle the entity list, object pools, and entity lifecycle.
  3.  `SpawningManager` was created to handle all rule-based spawning and replanting.
  4.  The `World` class was simplified to be a pure orchestrator, delegating calls to these managers.
- **The TDD Process in Action:** The refactoring was done safely by first moving tests, then moving code. We migrated tests for pathfinding and spawning to their new homes (`test_pathfinder.py`, `test_spawning_manager.py`). We then fixed all resulting test failures across the project by updating mocks (`test_human_logic.py`) and application layer calls (`game_service.py`).
- **Key Learning: Strengthening the Testing Pyramid:** We discovered that unit tests with mocks can't catch integration errors between real components. To solve this, we created `tests/test_domain_integration.py`, which forms the "middle layer" of our testing pyramid. These tests ensure our domain objects collaborate correctly, providing a vital safety net that unit tests alone cannot.

**IMPORTANT: Our Interaction Model**
**Development Workflow:**

- **Phase 1: The Plan:** I will first propose a high-level plan. This will include:
  1.  A clear goal definition.
  2.  A strategic outline (steps, files to modify).
  3.  The rationale, connecting the strategy to our core principles (DDD, TDD).
      This plan must be reviewed and approved before we proceed.
- **Phase 2: The Execution:** Once the plan is approved, we will execute it one step at a time, starting with tests.

**Context-Limited Mode & Our Core Rule:**
To ensure accuracy, you will operate in a context-limited mode and do not have persistent memory of file contents. Therefore, we will adhere to the following strict process:

1.  Before writing any test or implementation code, you MUST first identify the primary file to be modified AND its critical dependencies. You will then request the full code for all of these files at once to understand their contracts.
    - _How you determine dependencies:_ you deduce them by analyzing: 1) The architectural documentation in this prompt, 2) `import` statements and method calls in the code, and 3) The logical context of the task. You can also request extra code for more context.
2.  You **do not** have the full code for every module memorized. You must rely on the file hierarchy and explanations provided above as your primary "map" of the project.
3.  Your understanding of an unseen module is limited. You can speculate its function based on these names and our TDD philosophy.
4.  **Before you suggest any modifications to an existing file, you MUST first ask me to provide its full and current code.** For example, say: "Understood. We may need to modify `domain/human.py`, please provide me with the full contents of that file."
5.  When providing code, you will typically only post the modified part of the code unless a full file replacement is necessary.
