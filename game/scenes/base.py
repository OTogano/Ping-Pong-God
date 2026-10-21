"""Base class for every screen (title, level select, match, pause, ...)."""


class Scene:
    # Set by App when the scene is shown. Gives access to switch/push/pop.
    app = None

    # An overlay (like the pause menu) is drawn on top of the scene below it,
    # and the scene below stops updating while the overlay is open.
    is_overlay = False

    def handle_event(self, event):
        pass

    def update(self, dt):
        pass

    def draw(self, surf):
        pass
