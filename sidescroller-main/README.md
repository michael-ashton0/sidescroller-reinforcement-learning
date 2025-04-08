# Overview
Welcome to my fun little side-scrolling shooter game! You play as a Rambo-style hero, armed with a gun and grenades, facing off against enemy soldiers who are relentless in their pursuit. Enemies patrol their platforms and if they see you, they’ll shoot! Scattered across each level, you’ll find health packs and useful power-ups. These are essential for survival because the game is reasonably difficult. Stay alert, keep moving, and don’t run out of ammo!

## Acknowledgements ##
This was my first game of any significance. I owe a lot of credit to **[Coding With Russ](https://github.com/russs123/Shooter)** and his fantastic tutorials. I watched several of his [YouTube videos](https://www.youtube.com/watch?v=DHgj5jhMJKg&list=PLjcN1EyupaQm20hlUE11y9y8EY2aXLpnv) and borrowed (err, ...copied) his graphics and sounds verbatim. That said, I designed the code from scratch and used a completely different architecture.

## Structure ##
Although there are a handful of small files, the majority of my game is contained in these three files:
* `shooter.py:` This is the main game loop. It creates the game controller, screen, and game engine objects. It can run in menu mode, where it displays a basic menu with Start and Exit buttons. If the user clicks Start, then it switches to interactive mode by running the game loop.
* `solder.py:` Defines the Soldier class, which is the base object for all characters in the game. The file contains two additional classes, Player and Enemy, both of which inherit from Soldier and have a few customizations. Most of the code is pretty straight-forward with the possible exception of 
* `engine.py:` The largest and most confusing file of them all. This file loads the maps, maintains the overall game state, and calculates

## PyGame ##
For anyone who is new to PyGame, there are a few concepts that you need to know to get started: Sprites, Collisions, Events, and Blitting.
For those who want to become experts, there are a lot of additional details to understand. You don’t need to master everything right away. You can learn these as you go!
### Sprites ###
Sprites are the most important object in PyGame. Every character, item, and piece of terrain is a sprite and inherits from the sprite class. It's possible to have some background graphics and shapes that are something other than a sprite, but pretty much every object that the user interacts with will be a sprite. Sprites have an image and a rectangle (`rect`). The image defines what the sprite looks like on the screen. The rectangle is used to interact with other sprites. Usually, the rectangle is the exact same size as the image, but there are reasons to make them different sizes, and my game occasionally makes the rectangle slightly smaller than the image.
You can put sprites into groups, which makes the code a lot simpler because you can apply certain operations to every sprite in the group. For instance, you might have a group for all of the enemies or the ground terrain, power-ups, and so on.
#### Images ####
You can load a few different types of image files into PyGame, but PNGs seem to be the most common because they provide transparency, which greatly improves the graphics for any sprite that is not rectangular. The image namespace includes a lot of helper functions for transforming the images (flipping, scaling, etc). Make sure that you convert image files with the `convert_alpha()` function. This will help your game to render faster.
#### Rectangles ####
Rectangles define the boundaries of the sprite. As the rectangle goes, so does the sprite. This means that you move the rectangle to move the sprite. Rectangles from many different anchor points, such as their centers, top-left corners, right sides (x-coordinate only), bottoms (y-coordinate only), and so on.
### Collisions ###
PyGame includes a bunch of built-in functions that detect collisions between different sprites. It does this through the sprite's rectangle. Most of the time, you just work with the sprite object and trust the underlying framework to keep track of the rectangles. But you can directly check the rectangles for collisions, and occasionally, this is helpful.
In my game, you'll notice times when I check for collisions between a single sprite and a group of sprites. For example, I check to see if our hero has collided with any bullets. I also handle collisions between the player and water (unfortunately, he can't swim and quickly drowns). And my very simple physics engine uses the ground terrain sprites to stop the hero from falling when he hits the ground.
### Events ###
Most user input is passed to PyGame through events. These events include keystrokes and mouse clicks. PyGame allows you to define your own custom events and this is helpful for using timers that execute code on some sort of timed or repeated basis. For games, the keyboard is a common input device that can be used almost like a video game controller. You can quickly check for keys to be pressed down, let up, or held. It turns out that there are certain keyboard with certain key combinations that cannot be detected simultaneously. If you are trying to check for a whole bunch of keys simultaneously, and it seems like there are certain keys that are not being registered, this might be the culprit. Doh.
### Blitting ###
'Blit' is a new word for most non-game programmers. Blitting means drawing images on the screen. PyGame does not automatically update the screen, so you must manually draw everything each frame. A bunch of blit operations can occur in sequence and when all of the operations are finished, the resulting image can be drawn. This is good because PyGame must do a lot of expensive calculations to render your game. If a graphics library were to draw each image individually, the game would lag significantly. By only drawing one single image, the game is much faster. PyGame will determine which images should be in the background and which ones are in the foreground. Whenever two images overlap, it will show the correct portions of each image. You just need to make sure that you blit the images in the correct order.

## Conclusion ##
This game is a fun way to learn PyGame, and it taught me a lot about game programming. If you’re new to PyGame, start small, experiment, and learn as you go. Have fun coding!
