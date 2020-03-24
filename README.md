# Simpleland

## Overview
This is a simple 2d game engine written completely in python with client/server multiplayer support. It's primary purpose is to provide a flexilble test-bed for development of **reinforcement learning agents**.

**VERSION: 0.1-ALPHA**: This is an alpha release.  *Only limited documentation and functionality.*

![Game Screenshot](https://raw.githubusercontent.com/bkusenda/simpleland/master/assets/game_screen1.png "Game screenshot")

## Features
- 2d Physics and collision detection using pymunk
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
- pymunk (physics)
- l4z (network compression)
- pyinstrument (performance profiling)
- gym (usage of OpenAI Gym spaces and env interface)

## Installation

1. Make sure python 3.7 is installed
1. Download Repo:  ```git clone https://github.com/bkusenda/simpleland```
1. enter repo directory: ```cd simpleland```
1. (Optional) if using Anaconda, create conda environment: ```conda create -n simpleland python=3.7```
1. Install requirements via pip: ```pip install pygame pymunk pyinstrument``` (...may be others too: TODO)
1. Update path: ```export PYTHONPATH=${PYTHONPATH}:./```
1. See below for usage


## Usage
### Run Server

```bash
python simpleland/server.py --env_id=g1
```

### Start Client
```bash
python simpleland/client.py --client_id 2  --resolution=800x600 --hostname=YOURHOSTNAME --env_id=g1
```

### Using the OpenAI Gym Env interface

```python
from simpleland.client import SimpleLandEnv

env = SimpleLandEnv(
    resolution=(30, 30), 
    env_id="g1", 
    client_id = 'agent', 
    hostname = 'localhost', 
    port = 10001, 
    dry_run=False, 
    keymap = [0,23,19,1,4]):

# initialize
env.reset()

# take step
observation, reward, is_done, _ = env.step(action=1)

```

## Configuration/Customization

- G1 Environment: [simpleland/environments/g1.py](simpleland/environments/g1.py)
- Environment Registration: [simpleland/environment.py](simpleland/environment.py)
