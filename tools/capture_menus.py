# -*- coding: utf-8 -*-
"""Screenshot every full-screen menu so the trailer's dark-grid language can be
checked across the whole game (main menu / stats / settings / tutorial / pause).

game.py has no __main__ guard, so all instrumentation lives in the flip hook.
Screens are captured by forcing the relevant flag and letting one frame render.
"""
import os
import shutil
import sys

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

GAME_DIR = "/Users/Admin/WorkBuddy/2026-05-31-19-56-04"
FRESH_HOME = "/tmp/heliops_menu_home"
os.makedirs(FRESH_HOME, exist_ok=True)
shutil.rmtree(os.path.join(FRESH_HOME, "Documents"), ignore_errors=True)
os.environ["HOME"] = FRESH_HOME
sys.path.insert(0, GAME_DIR)

OUT = "/tmp/menu_shots"
os.makedirs(OUT, exist_ok=True)

import pygame  # noqa: E402

frames = [0]
# (frame, name, flag setter) -- one shot per flag, then back to the menu
SHOTS = [
    (5, "01_main_menu", None),
    (20, "02_stats", "stats"),
    (35, "03_settings", "settings"),
    (50, "04_tutorial", "tutorial"),
    (65, "05_pause", "pause"),
]
captured = []


def apply_flag(g, which):
    if which == "stats":
        g.in_main_menu = False
        g.in_stats = True
    elif which == "settings":
        g.in_stats = False
        g.in_main_menu = False
        g.in_settings = True
    elif which == "tutorial":
        g.in_settings = False
        g.showing_tutorial = True
    elif which == "pause":
        g.showing_tutorial = False
        g.in_main_menu = False
        g.paused = True


def reset_flags(g):
    g.in_stats = False
    g.in_settings = False
    g.showing_tutorial = False
    g.paused = False
    g.in_main_menu = True


_orig_flip = pygame.display.flip


def flip_hook():
    """Capture the frame that was just drawn.

    The hook runs *inside* pygame.display.flip(), i.e. before the screen
    contents are handed to the driver, so the surface still holds what the
    game drew during this frame -- capture it here, not after the flip.
    """
    frames[0] += 1
    n = frames[0]
    g = sys.modules.get("game")
    if g is not None:
        for at, name, flag in SHOTS:
            if n == at - 1:            # flag lands on the *next* rendered frame
                if flag is None:
                    reset_flags(g)
                else:
                    apply_flag(g, flag)
            if n == at:
                surf = pygame.display.get_surface()
                path = os.path.join(OUT, name + ".png")
                pygame.image.save(surf, path)
                captured.append(path)
        if n >= SHOTS[-1][0] + 2:
            pygame.event.post(pygame.event.Event(pygame.QUIT))
    _orig_flip()


pygame.display.flip = flip_hook

try:
    import game  # noqa: E402,F401
except SystemExit:
    pass

print("captured:", len(captured))
for p in captured:
    print(" ", p)
