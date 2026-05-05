# Shadow Dash: Endless Escape

Shadow Dash: Endless Escape is a polished 2D endless runner made with Python 3.9 and Pygame 2.x. The player runs through a cyberpunk city, jumps and double jumps over hazards, slides under threats, collects animated coins, and tries to beat the saved high score.

The project is intentionally small and beginner-friendly for an AI Lab final submission while still showing procedural generation, rule-based difficulty scaling, physics, particles, game states, and clean modular engineering.

## Features

- Smooth endless runner gameplay at 60 FPS
- Fullscreen presentation with scaled 960x540 gameplay
- Jump, double jump, and slide mechanics
- Toggleable A* AI demo runner with short-horizon action planning
- Improved AI safety with plan caching, collision margins, and emergency fallback
- State-based player animation: run, jump, double jump, slide, hurt, and death
- Four obstacle types: spike, rock, wall, and enemy drone
- Procedural obstacle generation with fair spacing
- Animated coins with line, arc, wave, and cluster spawn patterns
- Rule-based AI difficulty scaling that increases speed and challenge over time
- Visible difficulty labels: Easy, Medium, Hard, and Extreme
- Power-ups: shield, coin magnet, and slow motion
- Four-layer parallax cyberpunk background drawn with Pygame primitives
- Lightweight particles for jump dust, coin sparkle, speed trails, and collision bursts
- Subtle camera shake on landing and collision
- Main menu, pause screen, game over screen, and HUD
- High score persistence in `highscore.txt`
- Background music during gameplay
- Safe sound system with procedural fallback music and tones when asset files are missing

## Installation

1. Install Python 3.9.
2. Install Pygame 2.x:

```bash
pip install pygame
```

3. Run the game:

```bash
cd shadow_dash
python main.py
```

## Controls

- `Space`, `Up`, or `W`: Jump / double jump
- `Down` or `S`: Slide
- `A`: Toggle A* AI Runner demo mode
- `P`: Pause or resume
- `M`: Mute or unmute sound
- `Enter` or `Space`: Start / restart
- `Esc`: Pause during gameplay, quit from menu or game over

## AI Concepts Used

- **Rule-based difficulty scaling:** The game watches survival distance and gradually increases speed, spawn frequency, and obstacle combinations.
- **A* AI demo runner:** The AI searches a short future window using possible actions such as run, jump, double jump, and slide. It rejects paths that collide with obstacles, uses action costs and a survival heuristic, and executes the first action from the safest plan.
- **Real-time AI improvements:** The planner uses a longer horizon, smaller simulation steps, cached plans for a few frames, inflated collision margins for safety, obstacle-aware costs, and an emergency fallback when a threat is too close.
- **Procedural generation:** Obstacles and coin patterns are generated dynamically so each run feels different.
- **Fairness rules:** Obstacle groups use minimum spacing and staged unlocks so the early game is easy and late-game pressure rises without creating impossible situations.
- **State machines:** Player animation and game flow are controlled by clear states such as menu, playing, paused, game over, run, jump, slide, hurt, and death.
- **Power-up timers:** Temporary ability states are managed with countdown timers for shield, magnet, and slow motion effects.

## File Structure

```text
shadow_dash/
|
|-- main.py          # Pygame startup, fullscreen window, main loop, shutdown
|-- settings.py      # All configurable constants and tuning values
|-- game.py          # Game controller, states, spawning, scoring, UI, audio, high score
|-- entities.py      # Player, obstacles, coins, backgrounds, and particles
|-- README.md        # Project documentation
|
|-- assets/          # Optional replacement audio or future sprite assets
`-- highscore.txt    # Saved high score
```

## Optional Assets

The game works without external assets. To replace the procedural fallback sounds, place these files in `assets/`:

- `jump.wav`
- `coin.wav`
- `hit.wav`
- `music.ogg`

## Future Improvements

- Sprite sheets for the player and obstacles
- Power-ups such as shield, magnet, or slow motion
- Weather effects like rain and lightning
- More enemy types and obstacle formations
- A settings menu for volume and screen size
- Leaderboard support
