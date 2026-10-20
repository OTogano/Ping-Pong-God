import sys

import pygame

import settings as S
from match import Match


def main():
    pygame.init()
    window = pygame.display.set_mode((S.WIDTH * S.SCALE, S.HEIGHT * S.SCALE))
    pygame.display.set_caption(S.TITLE)

    # We draw everything on this small canvas, then blow it up to the window.
    # That keeps every pixel crisp and the art consistent.
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
            scene.handle_event(event)

        scene.update(dt)
        scene.draw(canvas)
        pygame.transform.scale(canvas, window.get_size(), window)
        pygame.display.flip()


if __name__ == "__main__":
    main()
