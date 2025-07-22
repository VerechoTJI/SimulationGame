### **New Start Prompt** v0.4

Hello! Your task is to continue the development of a Python command-line simulation game. The project follows Domain-Driven Design (DDD), Test-Driven Development (TDD), and Clean Architecture principles.

**Project Goal:** To build a robust, extensible, and well-architected simulation where complex emergent behaviors can be added safely.

**Core Methodologies:**

- **Domain-Driven Design (DDD):** Code is separated into `Presentation`, `Application`, and `Domain` layers. The `Domain` layer contains the core business logic and is completely independent.
- **Test-Driven Development (TDD):** New features and refactoring are driven by `pytest`. We write failing tests first (or ensure existing tests fail correctly before a fix), then implement the logic to make them pass.
- **Clean Architecture:** Dependencies point inwards (`Presentation` -> `Application` -> `Domain`). The `GameService` exposes use cases, and the `World` class acts as a domain facade.

**Key Project Specifications:**

- **Technology:** Python, `numpy`, `perlin-noise`, `pytest`, `keyboard`.
- **Architecture:** Multi-threaded (fast render loop, slower logic tick), data-driven via `config.json`.
- **World:** A grid-based map with Land, Water, and Mountain tiles affecting movement.
- **Entities:**
  - `Human`: Navigates using a hybrid system: a centralized **Flow Field** for scalable food-seeking when hungry, and **A\*** for individual wandering when not. Has `saturation`, eats `Rice`, and reproduces.
  - `Rice`: Matures over time and spawns naturally.
  - **Optimization:** All entities are managed by a generic **Object Pooling** system (`domain/object_pool.py`) to reduce runtime overhead.

**Project File Hierarchy & Explanations:**

- `config.json`: Data file for all simulation parameters, including the `flow_field_update_interval`.
- `cli_main.py`: **Minimal entry point.** Only responsible for setting up the Python path and calling the main run function.
- `presentation/`: **Presentation Layer.** Responsible for all user-facing logic (rendering, input).
  - `__init__.py`: Marks as a package.
  - `main.py`: Orchestrates the CLI application. Initializes services, the `shared_state` dictionary (including `keys_down`), and threads, and handles application startup/teardown.
  - `input_handler.py`: Uses the `keyboard` library's event hooks (`on_press`/`on_release`) to manage user input. For movement keys (`w,a,s,d`), it updates a `keys_down` dictionary in `shared_state`. For all other keys, it manages the text input buffer or places commands on the `command_queue`.
  - `renderer.py`: Contains the `display` function responsible for drawing the entire game state to the terminal.
  - `game_loop.py`: Contains the primary `game_loop`. On every frame, it reads the `shared_state['keys_down']` for smooth camera movement. It also drains the `command_queue` for game logic commands and controls the timed game tick, cleanly separating UI updates from logic updates.
- `application/`: **Application Layer.**
  - `__init__.py`: Marks as a package.
  - `config.py`: Singleton for loading `config.json`.
  - `game_service.py`: Exposes application use cases (e.g., `toggle_pause`, `speed_up`, `execute_user_command`). It orchestrates the domain layer by interacting with the `World` facade.
- `domain/`: **Domain Layer.**
  - `__init__.py`: Marks as a package.
  - `object_pool.py`: Contains the generic `ObjectPool` and `PooledObjectMixin`.
  - `entity.py`: Base `Entity` class, inheriting from `PooledObjectMixin`.
  - `tile.py`: Defines the `Tile` class and the `TILES` dictionary (Land, Water, Mountain).
  - `pathfinder.py`: Contains the A\* pathfinding logic, now used by `Human` entities for non-food-related wandering.
  - `flow_field_manager.py`: **(New)** A domain service that uses Breadth-First Search (BFS) to generate a vector field (flow field) pointing towards goals (e.g., food).
  - `entity_manager.py`: Manages entity lifecycle: object pools, creation (`create_human`), storage (`entities` list), and cleanup.
  - `spawning_manager.py`: Manages all rules for entity spawning: natural rice spawning, reproduction placement, and the replanting queue.
  - `human.py`: Logic for the `Human` entity. Implements a **hybrid movement model**, switching between following the `World`'s flow field when hungry and using the `Pathfinder` to generate its own `path` for wandering when sated.
  - `rice.py`: Logic for the `Rice` entity. Implements a `get_eaten()` method.
  - `world.py`: Acts as the central **coordinator/facade** for the domain. It holds the map `grid` and orchestrates the `game_tick`, delegating tasks to its managers. It now owns the `FlowFieldManager` and is responsible for periodically regenerating the `food_flow_field`.
- `tests/`: **Testing Layer.**
  - `__init__.py`: Marks as a package.
  - `conftest.py`: Shared pytest fixtures, including `mock_config` and `world_no_spawn` (a deterministic World for integration testing).
  - `test_object_pool.py`: Unit tests for the `ObjectPool`.
  - `test_pathfinder.py`: Unit tests for the `Pathfinder` class.
  - `test_flow_field_manager.py`: **(New)** Unit tests for the `FlowFieldManager`, verifying correct vector generation.
  - `test_entity_manager.py`: Unit tests for `EntityManager`, including pooling and finding entities.
  - `test_spawning_manager.py`: Unit tests for `SpawningManager` rules and replanting.
  - `test_human_logic.py`: Unit tests for `Human` logic, using a `MockWorld` that can provide a mock flow field to test the new hybrid movement logic.
  - `test_rice_logic.py`: Unit tests for `Rice` logic.
  - `test_world_logic.py`: High-level integration tests for the `World`'s orchestration logic. (This file might be merged or deprecated in favor of `test_domain_integration`).
  - `test_domain_integration.py`: **Crucial** mid-level integration tests that verify collaboration between domain components, now including tests for the `World`'s flow field generation and the `Human`'s correct interaction with it.

**Recent Accomplishments & Key Learnings:**

1.  **Implemented a Scalable Flow Field System:** We replaced inefficient, per-entity A\* pathfinding for food with a centralized flow field system. The new `FlowFieldManager` generates a single, efficient vector field from all food sources, which hungry entities can follow. This solves the "thundering herd" performance bottleneck.
2.  **Developed a Hybrid AI Model:** We evolved the `Human`'s AI from a simple model to a more sophisticated hybrid one. It now intelligently switches between two behaviors: following the flow field when hungry and using its own A\* path for wandering when sated. This provides both performance and behavioral richness.
3.  **Strict TDD Process Proved Effective:** The development was rigorously driven by tests. This process was instrumental in discovering and fixing several subtle bugs in the implementation, test logic, and entity lifecycle interactions, leading to a much more robust final product.
4.  **Maintained Architectural Discipline:** We successfully introduced a new domain service while adhering to our architectural principles. We also consciously deferred a potential optimization (a Quadtree for proximity checks) to avoid scope creep, demonstrating a pragmatic approach to managing technical debt.

**IMPORTANT: Our Interaction Model**
**Development Workflow:**

- **Phase 1: The Plan:** I will first propose a high-level plan. This will include:
  1.  A clear goal definition.
  2.  A strategic outline (steps, files to modify).
  3.  The rationale, connecting the strategy to our core principles (DDD, TDD).
      This plan must be reviewed and approved before we proceed.
- **Phase 2: The Execution:** Once the plan is approved, we will execute it one step at a time, starting with tests.

**Context-Limited Mode & Our Core Rule:**
To ensure accuracy, you operate in a context-limited mode and do not have persistent memory of file contents. Therefore, we will adhere to this strict process:

1.  Before writing any test or implementation code, you MUST first identify the primary file to modify and its critical dependencies. You will then request the full code for all these files at once.
    - _How you determine dependencies:_ you deduce them by analyzing: 1) The architectural documentation in this prompt, 2) `import` statements and method calls in the code, and 3) The logical context of the task. You can also request extra code for more context.
2.  You **do not** have the full code for every module memorized. You must rely on the file hierarchy and explanations provided above as your primary "map" of the project.
3.  **Before you suggest any modifications to an existing file, you MUST first ask me to provide its full and current code.** For example, say: "Understood. We need to modify `domain/human.py` and `domain/world.py`. Please provide me with the full contents of both files."
4.  When providing code, you will typically only post the modified part unless a full file replacement is necessary.
