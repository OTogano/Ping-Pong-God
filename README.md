# Ping Pong God

A top-down, reaction-based ping pong game built with pygame-ce, inspired by
*I'm Ping Pong King* and drawn in a NES-style palette.

Watch where your opponent stands as they hit. Their position tells you where
the ball will land on your side. Press the matching key inside a short hit
window to return it.

## Controls

| Key | Position     |
|-----|--------------|
| D   | Left edge    |
| F   | Bottom left  |
| J   | Bottom right |
| K   | Right edge   |

- **R** restarts after a match
- **Esc** quits

## How the telegraph works

- Opponent hits from an **edge**: the ball crosses to your **opposite edge**.
- Opponent hits from the **bottom left/right**: the ball comes **straight down** that side.

A wrong key, an early press or a late press loses the point.

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
pyinstaller --onefile --windowed --name PingPongGod main.py
```

The executable is created in `dist/`.

## Project layout

| File               | What it does                                             |
|--------------------|----------------------------------------------------------|
| `main.py`          | Window, pixel-perfect scaling and the main loop          |
| `settings.py`      | Palette, controls, positions and all gameplay timings     |
| `match.py`         | The rally state machine, input and placeholder drawing    |
| `nes_palette.hex`  | Game palette, also loadable in Aseprite                   |

The game renders to a 256×224 canvas and scales it up 3× for crisp pixels.

## Roadmap

- [x] Playable prototype: telegraphed shots, hit window, scoring
- [ ] Aseprite sprites and swing animations
- [ ] Title screen and level select
- [ ] Level 1: tutorial
- [ ] Levels 2–4: opponents with tricks (decoy balls, reversed shots, ...) ending in a boss
- [ ] Audio

## Built with

- [pygame-ce](https://pyga.me/)
- [Aseprite](https://www.aseprite.org/) for pixel art
- [PyInstaller](https://pyinstaller.org/) for packaging
