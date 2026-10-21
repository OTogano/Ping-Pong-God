"""Entry point: window, renderer and the main loop."""

import sys

import pygame

from game import settings as S
from game.gfx.effects import fx
from game.gfx.renderer import create_renderer
from game.scenes.match import Match


def main():
    pygame.init()
    pygame.display.set_caption(S.TITLE)
    renderer = create_renderer((S.WIDTH * S.SCALE, S.HEIGHT * S.SCALE))
    print(f"Renderer: {renderer.name}")

    # We draw everything on this small canvas; the renderer scales it up to
    # the window and applies the shader effects.
    canvas = pygame.Surface((S.WIDTH, S.HEIGHT))
    clock = pygame.time.Clock()
    scene = Match()

    while True:
        dt = min(
            clock.tick(S.FPS) / 1000, 0.05
        )  # cap dt so a lag spike can't skip a hit window

        for event in pygame.event.get():
            if event.type == pygame.QUIT or (
                event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
            ):
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN and event.key == S.CRT_TOGGLE_KEY:
                fx.crt = not fx.crt
            scene.handle_event(event)

        scene.update(dt)
        fx.update(dt)
        scene.draw(canvas)
        renderer.present(canvas)


if __name__ == "__main__":
    main()
