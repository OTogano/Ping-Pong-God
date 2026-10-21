"""Puts the 256x224 game canvas on the window.

GLRenderer (default) uploads the canvas to the GPU as a texture and draws it
with our OpenGL shaders in assets/shaders/. That is where scaling, screen
shake, hit flashes and the CRT filter happen.

SoftwareRenderer is a fallback for machines without OpenGL 3.3, so the game
still runs (without the CRT filter).
"""

import os
import struct
import time

import moderngl
import pygame

from game import settings as S
from game.gfx.effects import fx


def _read_shader(name):
    with open(
        S.resource_path(os.path.join("assets", "shaders", name)), encoding="utf-8"
    ) as f:
        return f.read()


class GLRenderer:
    name = "OpenGL"
    supports_crt = True

    def __init__(self, window_size):
        # Ask for a modern (3.3 core) OpenGL context before opening the window.
        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, 3)
        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, 3)
        pygame.display.gl_set_attribute(
            pygame.GL_CONTEXT_PROFILE_MASK, pygame.GL_CONTEXT_PROFILE_CORE
        )
        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_FORWARD_COMPATIBLE_FLAG, True)
        pygame.display.set_mode(window_size, pygame.OPENGL | pygame.DOUBLEBUF)

        self.window_size = window_size
        self.ctx = moderngl.create_context()
        self.prog = self.ctx.program(
            vertex_shader=_read_shader("present.vert"),
            fragment_shader=_read_shader("present.frag"),
        )

        # A full-screen quad as a triangle strip: x, y, u, v per corner.
        # v is flipped because pygame's rows go top-down and OpenGL's go bottom-up.
        quad = struct.pack("16f", -1, -1, 0, 1, 1, -1, 1, 1, -1, 1, 0, 0, 1, 1, 1, 0)
        self.vbo = self.ctx.buffer(quad)
        self.vao = self.ctx.vertex_array(
            self.prog, [(self.vbo, "2f 2f", "in_pos", "in_uv")]
        )

        self.texture = self.ctx.texture((S.WIDTH, S.HEIGHT), 4)
        # NEAREST keeps the pixels sharp when scaled up; no blur.
        self.texture.filter = (moderngl.NEAREST, moderngl.NEAREST)
        self.texture.repeat_x = self.texture.repeat_y = False

        self._set("u_canvas", 0)
        self._set("u_canvas_size", (S.WIDTH, S.HEIGHT))
        self.start = time.perf_counter()

    def _set(self, name, value):
        """Set a shader uniform. prog[name] could also be an attribute or
        block, so check it really is a uniform (this also keeps type checkers
        happy) and fail clearly on a typo."""
        uniform = self.prog.get(name, None)
        if not isinstance(uniform, moderngl.Uniform):
            raise KeyError(f"Shader has no uniform called {name!r}")
        uniform.value = value

    def present(self, canvas):
        self.texture.write(pygame.image.tobytes(canvas, "RGBA"))
        self.texture.use(0)

        self._set("u_shake", fx.offset)
        self._set("u_time", time.perf_counter() - self.start)
        self._set("u_flash", fx.flash_amount)
        self._set("u_flash_color", fx.flash_color)
        self._set("u_crt", 1 if fx.crt else 0)
        self._set("u_ripple", fx.ripple_progress)
        self._set("u_ripple_center", fx.ripple_center)
        self._set("u_rewind", fx.rewind_amount)

        self.ctx.viewport = (0, 0, *self.window_size)
        self.ctx.clear(0.0, 0.0, 0.0)
        self.vao.render(mode=self.ctx.TRIANGLE_STRIP)
        pygame.display.flip()


class SoftwareRenderer:
    name = "software"
    supports_crt = False

    def __init__(self, window_size):
        self.window = pygame.display.set_mode(window_size)
        self.overlay = pygame.Surface(window_size)

    def present(self, canvas):
        self.window.fill((0, 0, 0))
        scaled = pygame.transform.scale(canvas, self.window.get_size())
        ox, oy = fx.offset
        self.window.blit(scaled, (ox * S.SCALE, oy * S.SCALE))
        if fx.flash_amount > 0:
            self.overlay.fill([round(c * 255) for c in fx.flash_color])
            self.overlay.set_alpha(round(fx.flash_amount * 255))
            self.window.blit(self.overlay, (0, 0))
            if fx.rewind_amount > 0:  # no shaders here: just a brownish tint
                self.overlay.fill((172, 124, 0))
                self.overlay.set_alpha(round(fx.rewind_amount * 90))
                self.window.blit(self.overlay, (0, 0))
        pygame.display.flip()


def create_renderer(window_size):
    """Try OpenGL first; fall back to plain pygame drawing if it fails."""
    if not S.FORCE_SOFTWARE_RENDERER:
        try:
            return GLRenderer(window_size)
        except Exception as err:  # no OpenGL 3.3, missing driver, ...
            print(f"OpenGL unavailable ({err}); using software renderer.")
            pygame.display.quit()
            pygame.display.init()
    return SoftwareRenderer(window_size)
