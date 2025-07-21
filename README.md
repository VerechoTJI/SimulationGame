# SimulationGame

A simple simulation game demonstrating Domain-Driven Design (DDD) principles in Python. The game simulates a world with humans and rice plants, where entities interact, move, and evolve over time. The project is organized into clear domain and application layers, with a CLI-based presentation.

## Features

- **Domain-Driven Design**: Separation of domain logic, application services, and presentation.
- **Entities**: Humans and rice plants, each with their own logic and lifecycle.
- **World Generation**: Procedural map generation using Perlin noise.
- **Simulation Loop**: Time advances in ticks, with entities acting autonomously.
- **Command Interface**: Spawn entities and interact with the world via CLI commands.
- **Colorful Output**: Uses ANSI colors for a more readable CLI experience.
- **Testing**: Pytest-based unit tests for core logic.

## Project Structure

```
SimulationGame/
├── application/
│   ├── __init__.py
│   ├── config.py               # Singleton config loader
│   └── game_service.py         # Application service layer, simulation orchestrator
├── domain/
│   ├── __init__.py
│   ├── entity.py               # Base entity and color definitions
│   ├── human.py                # Human entity logic
│   ├── rice.py                 # Rice entity logic
│   ├── object_pool.py          # Generic object pooling system
│   ├── entity_manager.py       # Entity lifecycle manager
│   ├── pathfinder.py           # A* pathfinding logic
│   ├── spawning_manager.py     # Spawning and replanting logic
│   ├── tile.py                 # Tile types and movement factors
│   └── world.py                # World, map, and simulation logic
├── tests/
│   ├── __init__.py
│   ├── conftest.py             # Global fixtures and config
│   ├── test_domain_integration.py
│   ├── test_entity_manager.py
│   ├── test_human_logic.py
│   ├── test_object_pool.py
│   ├── test_pathfinder.py
│   ├── test_rice_logic.py
│   ├── test_spawning_manager.py
│   ├── test_world_logic.py
│   └── test_world_helpers.py
├── cli_main.py                 # CLI entry point and presentation layer
├── config.json                 # Simulation parameters
├── requirements.txt
├── README.md                   # You are here
└── prompt.md                   # Project instructions and methodology
```

## Getting Started

### Prerequisites

- Python 3.11+
- Recommended: Use a virtual environment

### Installation

1. Clone the repository or copy the project files.
2. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```

### Running the Game

Run the CLI main file:

```sh
python cli_main.py
```

### Controls & Commands

- `sp human <x> <y>`: Spawn a human at grid coordinates (x, y)
- `sp rice <x> <y>`: Spawn a rice plant at grid coordinates (x, y)
- `q`: Quit the game

The simulation advances automatically. Humans will seek food (rice), move, and their status is displayed. Rice matures over time and can be eaten by humans.

## Testing

Run all tests with:

```sh
pytest
```

## Design Overview

- **Domain Layer**: Contains all business logic (entities, world, rules).
- **Application Layer**: Orchestrates domain logic and exposes services to the presentation layer.
- **Presentation Layer**: CLI interface in `cli_main.py`.

## Dependencies

- `numpy`: Math and array operations
- `perlin_noise`: Procedural map generation
- `pytest`: Testing
- `colorama`: (Optional) Color support for Windows terminals

## License

This project is for educational and demonstration purposes.
