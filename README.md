# simpleland

## TODO:
Better design would be:
- create references for objects during serialization and reassign during deserialization.
- only send updated data
- use event listners
- object event listender

## Overview
A simple 2d game engine written in python designed to provide a flexilble test-bed for **reinforcement learning** research.  Contains

**Version: 0.1-alpha**: This is an alpha release.  *Only limited documentation and functionality.*

![Game Screenshot](xxx "Game screenshot")

## Features
- Multi Agent Support
- Configuration driven
- Openai gym interface for Single Agent Play
- Reasonably good FPS for software rendering
- Support for concurrent tasks
- 3rd person perspective view
- Game Modes Available
    - Tag
    - Simple Survival (collect food or die)
- Network Play support (Early Development)
- Crafting Support
- Hackable, easy to add:
    - game object types
    - game modes
    - maps

### Planned Features
- Game Modes
    - Tag
    - Infection Tag
    - Hide and Seek
    - Survival with Crafting/Hunting
    - Random Mazes
    - Multi Task Obstatcle courses
    - Block moving puzzles   
- 1st person perspective view (coming soon)
- 2d physics support
- Admin UI for dynamic world changes
- World state saving
- Support for concurrent RL agent and human players
- Better/faster network play
- Async agent play i.e. environment doesn't block when waiting for action form agent

### Performance
When tested on i7 laptop
- 3k+ state observations per second 
- 300+ RGB frame observations per second
- Small memory footprint. Less than 1MB per instance
## Known Issues
- Performance degrades with large number of objects or on poor network connections.
- Incomplete documentation and testing
- Network play uses more bandwidth than needed.

## Requirements
- python 3.7
- pygame (rendering)
- l4z (network compression)
- pyinstrument (performance profiling)
- gym (usage of OpenAI Gym spaces and env interface)

## Installation

1. Make sure python 3.7 is installed
1. Download Repo:  ```git clone https://github.com/bkusenda/simpleland```
1. enter repo directory: ```cd simpleland```
1. (Optional) if using Anaconda, create conda environment: ```conda create -n simpleland python=3.7```
1. Install requirements via pip: ```pip install pygame pyinstrument``` (...may be others too: TODO)
1. Update path: ```export PYTHONPATH=${PYTHONPATH}:./```
1. See below for usage


## Usage


### Run Random Agent Test
```bash
PYTHONPATH=${PYTHONPATH}:./  python simpleland/env.py  --agent_count=2 --mem_profile --max_steps=800000
```

### Run Server and Local Client

```bash
PYTHONPATH=${PYTHONPATH}:./  python simpleland/runner.py --game_id=survival_grid  --tick_rate=60 --tile_size=16 --enable_server  --resolution 1280x720  --disable_sound --enable_client
```

### Start Remote Client
```bash
 python simpleland/runner.py --enable_client --resolution=640x480 --hostname=SERVER_HOSTNAME --game_id=space_ship1  --fps=60 --remote_client
```

### Run Server Only
```bash
 python simpleland/runner.py --game_id=space_ship1  --enable_server --tick_rate=60 --port=10001
```


### Using the OpenAI Gym Env interface

TODO
```

## Configuration/Customization

- Space Ship 1 Game: [simpleland/contentbundles/space_ship1.py](simpleland/environments/space_ship1.py)
- Game Registration: [simpleland/registry.py](simpleland/registry.py)
