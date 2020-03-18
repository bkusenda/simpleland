# Simpleland

## Overview
This is a simple 2d game engine written completely in python with client/server multiplayer support. It's primary purpose is to provide a flexilble test-bed for development of **reinforcement learning agents**.

**VERSION: 0.1-ALPHA**: This is an alpha release.  *Only limited documentation and functionality.*

![alt text](https://raw.githubusercontent.com/bkusenda/simpleland/master/assets/game_screen1.png "Game screenshot")

## Features
- 2d Physics and collision detection using pymunk
- Realtime client server networking support for multiple agents/players
- Very simple demo game provided

## Known Issues
- Openai gym interface not yet added
- Most configuration is hardcoded
- Yses inefficient JSON for network serialization
- Objects are not yet purged from memory after being deleted resulting in a slow memory leak
- Performance degrades with large number of objects or on poor network connections.
- Incomplete documentation and testing
- Assets are not mine(Grabbed off the web) and should be replaced ASAP

## Requirements
- Only tested on Linux
- python 3.7
- pygame
- pymunk
- pyinstrument 

## Installation

1. Make sure python 3.7 is installed
1. Download Repo:  ```git clone https://github.com/bkusenda/simpleland```
1. enter repo directory ```cd simpleland```
1. (Optional if using Anaconda) ```conda create -n simpleland python=3.7```
1. Install requirements via pip: ```pip install pygame pymunk pyinstrument``` (...may be others too: TODO)
1. Update path: ```export PYTHONPATH=${PYTHONPATH}:./```
1. See below for usage


## Usage
### Run Server

```bash
python simpleland/game_server.py
```

### Start Client
```bash
python simpleland/game_client.py --client_id 2  --resolution=800x600 --hostname=YOURHOSTNAME
```

## Customization

- Configuration: [config.py](simpleland/config.py)
- Game logic: [content_manager.py](simpleland/content_manager.py)
- Assets: [asset_manager.py](simpleland/asset_manager.py)