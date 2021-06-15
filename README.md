# simpleland

## TODO:
Better design would be:
- create references for objects during serialization and reassign during deserialization.
- only send updated data
- use event listners
- object event listender

## Overview
This is a simple 2d game engine written completely in python with client/server multiplayer support. It's primary purpose is to provide a flexilble test-bed for development of **reinforcement learning agents**.

**Version: 0.1-alpha**: This is an alpha release.  *Only limited documentation and functionality.*

![Game Screenshot](https://raw.githubusercontent.com/bkusenda/simpleland/master/assets/game_screen1.png "Game screenshot")

## Features
- Realtime client server networking support for multiple agents/players
- Very simple demo game provided with agent perspective viewing (as oppose to environment perspective)
- Openai gym interface

## Known Issues
- Only agent perspective view
- Most configuration is hardcoded
- Uses inefficient JSON for network serialization
- Objects are not yet purged from memory after being deleted resulting in a slow memory leak
- Performance degrades with large number of objects or on poor network connections.
- Incomplete documentation and testing
- Assets are not mine(Grabbed off the web) and should be replaced ASAP

## Requirements
- Only tested on Linux
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
### Run Server and Local Client

```bash
 python simpleland/runner.py --enable_client --resolution=640x480 --hostname=localhost --game_id=space_ship1  --fps=60 --enable_server --tick_rate=60
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
