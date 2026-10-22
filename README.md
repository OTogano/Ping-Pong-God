# Ping Pong God

A top-down, reaction-based ping pong game built with pygame-ce, inspired by
*I'm Ping Pong King* and drawn in a NES-style palette.

Watch where your opponent stands as they hit. Their position tells you where
the ball will land on your side. Press the matching key inside a short hit
window to return it. Beat five opponents, each with their own tricks, to
become the Ping Pong God.

## Controls

**In a match**

| Key | Position     |
|-----|--------------|
| D   | Left edge    |
| F   | Bottom left  |
| J   | Bottom right |
| K   | Right edge   |

- **Esc** pauses (resume, restart, level select, CRT filter on/off)

**In menus**

- **Arrows** or **W A S D** to move
- **Enter** or **Space** to choose
- **Esc** to go back

## How the telegraph works

- Opponent hits from an **edge**: the ball crosses to your **opposite edge**.
- Opponent hits from the **bottom left/right**: the ball comes **straight down** that side.

A wrong key, an early press or a late press loses the point. You score when
your opponent misses one of your returns.

## The opponents

Beat a level to unlock the next. Progress is saved to
`%APPDATA%\PingPongGod\save.json` (Windows) or `~/.local/share/PingPongGod/save.json`.

| Level    | Opponent       | Stage              | Tricks |
|----------|----------------|--------------------|--------|
| Tutorial | Coach Greg     | School gym         | Key hints until your first point; the odd belly bump |
| Level 2  | Esmeralda      | Commercial gym     | **Smash**: red eyes and a grin, then a flaming shot twice as fast |
| Level 3  | Captain Squidy | Pirate ship        | **Juggle** between his four paddles, then a fast shot from the last one; **grab**: press the right key to break free, then again to hit |
| Level 4  | BOT            | Test lab           | **Portal** (watch where the exit opens); **invisible ball** (follow the shadow); **charge shot**, the fastest in the game |
| Final    | ♑□♎            | Floating throne    | Every hit is a shockwave. **Redirect** (follow his hand), **illusions** (fakes cast no shadow), **rewind** followed by a spike |

Every trick is readable: the ball always lands by the telegraph rule, from
wherever the shot is really taken.

## Getting started

Requires Python 3.12 or 3.13.

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux
pip install -r requirements.txt
python main.py
```

## Building the .exe

```bash
pyinstaller --clean --onefile --windowed --name PingPongGod --add-data "assets;assets" main.py
```

The executable is created in `dist/`. `--add-data` bundles the art into the exe
(on macOS/Linux write `assets:assets`). `--clean` stops PyInstaller reusing an
old build that's missing new assets.

## Project layout

```
main.py                  # entry point
game/
  app.py                 # window, main loop, scene stack (switch / push / pop)
  settings.py            # palette, controls, table layout, shared timings
  controls.py            # menu keys (arrows / WASD, Enter, Esc)
  levels.py              # the five levels: speed, points, stage, props, opponent kind
  save.py                # which levels you've beaten
  scenes/
    title.py             # title screen
    level_select.py      # scrolling row of level cards, locks and stars
    match.py             # one match: rally state machine, input, scoring, drawing
    pause.py             # pause menu (overlay)
    result.py            # win / lose screen (overlay)
  opponents/
    base.py              # Opponent: the hooks the match calls (choose a trick, on hit, mid-flight, draw...)
    greg.py              # belly bump
    esmeralda.py         # smash
    squidy.py            # juggle, grab (Bezier tentacle)
    bot.py               # robot movement, portals, invisible ball, charge shot
    odin.py              # floating, redirect, illusions, rewind + spike, storm
  gfx/
    sprites.py           # Aseprite sheet loading, recolouring, Animator
    text.py              # pixel-font text from assets/ui/font.png
    ui.py                # flip-board scoreboard, key icons, menus
    renderer.py          # OpenGL (ModernGL) renderer + software fallback
    effects.py           # shake, flash, shockwave ripple, rewind, CRT toggle
    geometry.py          # lerp and Bezier curves
assets/
  sprites/               # characters, stage props and portraits (sheet .png + Aseprite .json)
  backgrounds/           # one stage per level
  ui/                    # title, logo, flip-board, digits, key icons, pixel font
  palettes/
    nes_palette.hex      # game palette, also loadable in Aseprite
  shaders/
    present.vert         # full-screen quad + screen shake
    present.frag         # flash, shockwave ripple, rewind (sepia + wave), CRT
```

### Adding an opponent

1. Add their sprite sheet (Aseprite export with tags such as `idle`, `windup`,
   `swing_d`...`swing_k`, `point_won`, `match_lost`) and a 24x24 portrait to
   `assets/sprites/`.
2. Create `game/opponents/<name>.py` with a class based on `Opponent` that
   overrides only the hooks it needs. Their tuning numbers go at the top of
   that file.
3. Register the class in `KINDS` in `game/opponents/__init__.py`.
4. Add a `Level(...)` to `LEVELS` in `game/levels.py` with `kind="<name>"`.

## Rendering and shaders

The game draws each frame on a 256x224 pygame surface. `GLRenderer` uploads it
to the GPU as a texture and draws it on a full-screen quad with OpenGL 3.3
shaders (via ModernGL):

- **Vertex shader:** moves the quad for screen shake.
- **Fragment shader:**
  - nearest-neighbour scaling for crisp pixels
  - a coloured flash (returns, smashes, lightning)
  - a **shockwave ripple** that bends the picture outward from a hit
  - the **rewind** effect: sepia, swaying rows and rolling bands
  - an optional CRT filter (curvature, scanlines, vignette)

Other effects are drawn on the canvas: Squidy's tentacle (a tapering cubic
Bezier), Odin's bent shots (quadratic Bezier), flame and glow trails, portals
and lightning.

If OpenGL 3.3 isn't available, the game falls back to `SoftwareRenderer`
(shake, flash and a rewind tint still work; no ripple or CRT). The terminal
prints which one is in use.

## Roadmap

- [x] Playable prototype: telegraphed shots, hit window, scoring
- [x] Player sprite with idle, ready, swing and reaction animations
- [x] Title screen, level select with unlocking and saving, pause menu, result screen
- [x] Persistent assets: table, net, ball, umpire flip-board, pixel font, key icons
- [x] OpenGL renderer: shake, flash, shockwave ripple, rewind and CRT shaders
- [x] Tutorial: Coach Greg
- [x] Levels 2–4: Esmeralda, Captain Squidy, BOT
- [x] Final boss
- [x] Opponents split into their own modules
- [ ] Audio: music and sound effects
- [ ] Balance pass across all five levels

## Built with

- [pygame-ce](https://pyga.me/)
- [ModernGL](https://github.com/moderngl/moderngl) for the OpenGL renderer
- [Aseprite](https://www.aseprite.org/) for pixel art
- [PyInstaller](https://pyinstaller.org/) for packaging
