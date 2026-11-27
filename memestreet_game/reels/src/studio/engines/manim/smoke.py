"""The studio's smallest Manim scene: studio.py demo renders it to prove the engine works."""
from manim import *

config.pixel_width, config.pixel_height, config.frame_rate = 1080, 1920, 30
config.frame_height = 16.0; config.frame_width = 9.0; config.background_color = "#101426"


class Smoke(Scene):
    def construct(self):
        ax = Axes(x_range=[0, 6, 1], y_range=[0, 4, 1], x_length=7, y_length=6, tips=False).set_color(GREY_B)
        g = ax.plot(lambda x: 1 + .4 * x + .5 * np.sin(2 * x), x_range=[0, 6], color=GREEN)
        self.play(Create(ax, run_time=.5), Create(g, run_time=1))
