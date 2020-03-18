# Simpleland

## Overview
This is a simple 2d game engine with client/server multiplayer or agent. It's primary purpose is to provide a flexilble test-bed for development of **reinforcement learning agents**.

**This is an Alpha Release:** Only limited documentation and functionality

![alt text](https://raw.githubusercontent.com/bkusenda/simpleland/master/assets/game_screen1.png "Game screenshot")

## Features
- 2d Physics and collision detection using pymunk
- Realtime client server networking support for multiple agents/players
- Very simple demo game provided

## Known Issues/ Things to fix
- Openai gym interface not yet added
- Most configuration is currently hardcoded
- Currently uses inefficient JSON for network serialization
- Incomplete documentation
- Objects are not yet purged from memory after being deleted resulting in a slow memory leak
- Performance degrades with large number of objects or on poor network connections.
- Incomplete tests

## Requirements
- python 3.7
- pygame
- pymunk
- pyinstrument 