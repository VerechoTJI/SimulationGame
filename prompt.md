Hello! Your task is to continue the development of a Python command-line simulation game. The project follows Domain-Driven Design (DDD), Test-Driven Development (TDD), and Clean Architecture principles.

**Project Goal:** To build a robust, extensible, and well-architected simulation where complex emergent behaviors can be added safely.

**Core Methodologies:**

- **Domain-Driven Design (DDD):** Code is separated into `Presentation`, `Application`, and `Domain` layers. The `Domain` layer contains the core business logic and is completely independent.
- **Test-Driven Development (TDD):** New features are developed by writing failing `pytest` tests first, then implementing the domain logic to make them pass.
- **Clean Architecture:** Dependencies point inwards (`Presentation` -> `Application` -> `Domain`). We use Dependency Injection and a command pattern to maintain separation.

**Key Project Specifications:**

- **Technology:** Python, `numpy`, `perlin-noise`, `pytest`.
- **Architecture:** Multi-threaded (fast render loop, slower logic tick), data-driven via `config.json`.
- **World:** A 64x32 grid with Land, Water, and Mountain tiles affecting movement.
- **Entities:**
  - `Human`: Navigates using A\*, has a `saturation` level, eats `Rice`, and reproduces.
  - `Rice`: Matures over time and spawns naturally.
  - **Optimization:** All entities are managed by a generic **Object Pooling** system (`domain/object_pool.py`) to reduce runtime overhead from object creation/destruction.

**Project File Hierarchy & Explanations:**

- `config.json`: Data file for all simulation parameters.
- `cli_main.py`: **Presentation Layer.** Renders game state and handles user input.
- `application/`: **Application Layer.**
  - `__init__.py`: Marks as a package.
  - `config.py`: Singleton for loading `config.json`.
  - `game_service.py`: Main entry point for the CLI, orchestrates domain logic.
- `domain/`: **Domain Layer.**
  - `__init__.py`: Marks as a package.
  - `object_pool.py`: Contains the `ObjectPool` and `PooledObjectMixin`. `ObjectPool.get()` is responsible for calling an object's `reset()` method. `release()` simply returns an object to the pool.
  - `entity.py`: Base `Entity` class, inherits from `PooledObjectMixin`.
  - `human.py`: `Human` entity logic.
  - `rice.py`: `Rice` entity logic, implements a `get_eaten()` method that sets an `is_eaten` flag.
  - `world.py`: Manages the grid, entities, and the main `game_tick`. Uses object pools for entity lifecycle and a `replant_queue` to handle rice replanting across ticks.
- `tests/`: **Testing Layer.**
  - `__init__.py`: Marks as a package.
  - `conftest.py`: Contains shared `pytest` fixtures, including `world_no_spawn` which creates a deterministic world instance with random spawning disabled.
  - `test_object_pool.py`: Unit tests for the generic `ObjectPool` and `PooledObjectMixin`.
  - `test_human_logic.py`: Unit tests for `Human` logic.
  - `test_rice_logic.py`: Unit tests for `Rice` logic.
  - `test_world_logic.py`: Unit tests for `World` methods. Contains key integration tests for object pooling and multi-tick behaviors like replanting.
  - `test_world_spawning.py`: Unit tests for natural spawning logic.

**Recent Accomplishments & Key Learnings:**
We have just successfully re-implemented the Rice replanting feature, making it compatible with the object pooling system.

- **The Solution:** The `domain/world.py` `game_tick` was refactored. When a Rice plant is eaten, its coordinates are added to a `replant_queue`. The queue is processed at the start of the _next_ tick, spawning a new rice plant. This decouples the "eating" and "replanting" events, making the simulation logic robust.
- **TDD Process:** The implementation was driven by `pytest`. We diagnosed and fixed several complex issues, including non-deterministic test failures (solved with a `world_no_spawn` fixture) and a race condition where new entities were being aged in the same tick they were created (solved by snapshotting the entity list at the start of a tick).

**IMPORTANT: Our Interaction Model**
**Development Workflow:**

- **Phase 1: The Plan:** I will first propose a high-level plan. This will include:
  1.  A clear goal definition.
  2.  A strategic outline (steps, files to modify).
  3.  The rationale, connecting the strategy to our core principles (DDD, TDD).
      This plan must be reviewed and approved before we proceed.
- **Phase 2: The Execution:** Once the plan is approved, we will execute it one step at a time, starting with tests.

**Context-Limited Mode & Our Core Rule:**
To ensure accuracy, I operate in a context-limited mode and do not have persistent memory of file contents. Therefore, we will adhere to the following strict process:

1.  Before writing any test or implementation code, you MUST first identify the primary file to be modified AND its critical dependencies. you will then request the full code for all of these files at once to understand their contracts.
    - _How you determine dependencies:_ you deduce them by analyzing: 1) The architectural documentation in this prompt, 2) `import` statements and method calls in the code, and 3) The logical context of the task 4) Extra code request.
2.  You **do not** have the full code for every module memorized. You must rely on the file hierarchy and explanations provided above as your primary "map" of the project.
3.  Your understanding of an unseen module is limited. You can speculate its function based on these names and our TDD philosophy.
4.  **Before you suggest any modifications to an existing file, you MUST first ask me to provide its full and current code.** For example, say: "Understood. We may need to modify `domain/world.py`, please provide me with the full contents of that file."
5.  When providing code, prefer to only post the modified part of the code to save context unless a full file replacement is necessary.
