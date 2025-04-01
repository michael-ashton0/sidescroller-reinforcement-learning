# Overview
The game elements of this repository are a fork of my professor's repo containing the game engine, sprites, and data. This repo is an addition to that where I will be adding a reinforcement learning agent on top to play the game. I have made a few slight changes to the game, the most prominent of which is compounding speed while airborne since I am interested in seeing how the model may come to use that

# Current progress and Ideas

- 6 possible controls: jump, left, right, jump + left, jump + right, left + right
- plus shoot and grenade?

- Rewards and penalties:
    + x_distance from goal (do we really need y distance?)
    + death (I think this removes the need to keep track of health unless I want a bot that doesn't take damage)
    + finish level
    + time taken (if I want fast over 'perfect')
    + num_bullets
    + num_nades
I am currently unsure if I want to see purely how fast it can get from the start to the end, or if it can play a 'perfect' game; not taking damage, killing all enemies, etc.
