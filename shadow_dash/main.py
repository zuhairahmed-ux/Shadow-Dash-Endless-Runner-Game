"""Entry point for Shadow Dash: Endless Escape."""

import os
import sys

import pygame

import settings
from game import Game


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    pygame.mixer.pre_init(44100, -16, 1, 512)
    pygame.init()

    flags = 0
    if settings.FULLSCREEN:
        flags = pygame.FULLSCREEN | pygame.SCALED
    screen = pygame.display.set_mode((settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT), flags)
    pygame.display.set_caption(settings.TITLE)
    clock = pygame.time.Clock()

    game = Game(screen)

    while game.running:
        dt = clock.tick(settings.FPS) / 1000.0
        if dt > 0.05:
            dt = 0.05
        game.handle_events()
        game.update(dt)
        game.draw()
        pygame.display.flip()

    game.shutdown()
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
