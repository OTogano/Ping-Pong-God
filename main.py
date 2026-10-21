"""Entry point: start the game on the title screen."""

from game.app import App
from game.scenes.title import TitleScene


def main():
    app = App()
    app.run(TitleScene())


if __name__ == "__main__":
    main()
