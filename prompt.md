### **New Start Prompt** v0.5

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
  - `input_handler.py`: Uses the `keyboard` library's event hooks to manage user input. It updates a `keys_down` dictionary for smooth camera movement and places commands (like hotkeys) on the `command_queue`. It now recognizes the 'f' key to dispatch a `__TOGGLE_FLOW_FIELD__` command.
  - `renderer.py`: Contains the `display` function responsible for drawing the entire game state to the terminal. Now includes logic to conditionally render the `food_flow_field` as a grid of arrows for debugging purposes.
  - `game_loop.py`: Contains the primary `game_loop`. It handles smooth camera movement, drains the `command_queue` for logic commands, and controls the timed game tick. It processes the `__TOGGLE_FLOW_FIELD__` command by calling the appropriate service method.
- `application/`: **Application Layer.**
  - `__init__.py`: Marks as a package.
  - `config.py`: Singleton for loading `config.json`.
  - `game_service.py`: Exposes application use cases (e.g., `toggle_pause`, `speed_up`). It orchestrates the domain layer and now manages the state for debug visualizations (e.g., `toggle_flow_field_visibility`).
- `domain/`: **Domain Layer.**
  - `__init__.py`: Marks as a package.
  - `object_pool.py`: Contains the generic `ObjectPool` and `PooledObjectMixin`.
  - `entity.py`: Base `Entity` class, inheriting from `PooledObjectMixin`.
  - `tile.py`: Defines the `Tile` class and the `TILES` dictionary (Land, Water, Mountain).
  - `pathfinder.py`: Contains the A\* pathfinding logic, used by `Human` entities for non-food-related wandering.
  - `flow_field_manager.py`: A domain service that uses Breadth-First Search (BFS) to generate a vector field (flow field) pointing towards goals.
  - `entity_manager.py`: Manages entity lifecycle: object pools, creation (`create_human`), storage (`entities` list), and cleanup.
  - `spawning_manager.py`: Manages all rules for entity spawning: natural rice spawning, reproduction placement, and the replanting queue.
  - `human.py`: Logic for the `Human` entity. Implements a hybrid movement model, switching between following the `World`'s flow field and using A\* for wandering.
  - `rice.py`: Logic for the `Rice` entity, including a `get_eaten()` method.
  - `world.py`: Acts as the central **coordinator/facade** for the domain. It holds the map `grid` and orchestrates the `game_tick`, delegating tasks to its managers and periodically regenerating the `food_flow_field`.
- `tests/`: **Testing Layer.**
  - `__init__.py`: Marks as a package.
  - `conftest.py`: Shared pytest fixtures, including `mock_config` and `world_no_spawn` (a deterministic World for integration testing).
  - `test_object_pool.py`: Unit tests for the `ObjectPool`.
  - `test_pathfinder.py`: Unit tests for the `Pathfinder` class.
  - `test_flow_field_manager.py`: Unit tests for the `FlowFieldManager`.
  - `test_entity_manager.py`: Unit tests for `EntityManager`.
  - `test_spawning_manager.py`: Unit tests for `SpawningManager`.
  - `test_human_logic.py`: Unit tests for `Human` logic, using a `MockWorld`.
  - `test_rice_logic.py`: Unit tests for `Rice` logic.
  - `test_game_service.py`: **(New)** Unit tests for the `GameService`, ensuring application use cases like state toggles work correctly.
  - `test_world_logic.py`: Legacy integration tests. (To be reviewed/merged).
  - `test_domain_integration.py`: Crucial integration tests verifying collaboration between domain components.

**Recent Accomplishments & Key Learnings:**

1.  **Implemented Flow Field Visualization:** To address a bug with AI movement, we added a toggleable debug view (`'f'` key) that renders the `food_flow_field` directly on the map. This provides immediate visual feedback on the AI's pathfinding data.
2.  **Reinforced Architectural Principles:** The visualization feature was implemented without compromising Clean Architecture. The toggle state (`_show_flow_field`) lives in the `GameService` (Application), and rendering logic is confined to the `Renderer` (Presentation). The `Domain` layer remains completely unaware of any visualization concerns, demonstrating the strength of our separated architecture.
3.  **Expanded TDD to the Application Layer:** We created `test_game_service.py` to drive the implementation of the toggle feature. This successfully validated the state management logic within the `GameService` before we even wrote the rendering code, proving the value of TDD for non-domain-logic layers.
4.  **Embraced the Power of Debug Tools:** This task highlighted that for complex simulations, building internal visualization tools is not just a "nice-to-have" but a critical component for effective debugging and understanding emergent behavior.

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
