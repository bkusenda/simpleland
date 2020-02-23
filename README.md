# Goal
- create survival an environment for training RL agents

# Features
- survival types features
- for multiple agents
- eat
- grow
- increase mass and strength
- don't eat too much 
- expend energy
- solve puzzles
- complete for food/resources
- cooperative situations
- start with simple controlled situations and increase difficulty and risk overtime as agent learns
- allows human players to do things like teaching
- 2d
- each agent gets locallized view


# Current status
- can move a circle with [wsda]
- TODO: was about to implement the physics engine 
 to allow movement by applying force and conservation of momentum
- starting 2d

# ideas
- game within game (same game or subset but with different actions) +1
- reproduce? (hyper param search??), but not for physical features 

# Next steps
 - populate space
 - create simple designer
 - add game elements
 - on collision
 
 
 
## Game elements
- mouse mazes/ obstacles
- object types
    - structures  - not movable or edible
    - lifeforms
        - require energy to live
        - moving costs energy
        - animals 
            - multiple types: preditor prey
            - can move
            - interact with env and each other
            - food source
            - eat plants or animals
        - plants
            - multiple types
            - grow and duplicate
            - food source
            - grow over time unless completely devo


# TODOS
- add entity concept