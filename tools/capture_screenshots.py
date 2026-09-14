# -*- coding: utf-8 -*-
"""Headless screenshot capture for HeliOps (action-oriented set, v2).

Off-screen rendering (SDL dummy) + isolated HOME (clean save, real save untouched).
The player is steered directly toward the nearest ENEMY (fallback: nearest supply)
by writing module globals, so the shots actually show combat: enemies on screen,
tracer bullets, kills and a rising score. SPACE is held via a patched key state
so the auto-aim weapon keeps firing. Lives are topped up to avoid a game-over
frame during the long capture run.
"""
import os
import sys
import math
import shutil

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

GAME_DIR = "/Users/Admin/WorkBuddy/2026-05-31-19-56-04"
OUT_DIR = os.path.join(GAME_DIR, "screenshots")
FRESH_HOME = "/tmp/heliops_shot_home"
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(FRESH_HOME, exist_ok=True)
# wipe the isolated save dir so every capture run starts from a virgin profile
# (otherwise the previous run's auto-save leaks score / tutorial-seen state in)
shutil.rmtree(os.path.join(FRESH_HOME, "Documents"), ignore_errors=True)
os.environ["HOME"] = FRESH_HOME
sys.path.insert(0, GAME_DIR)

import pygame  # noqa: E402

frames = [0]
held = [set()]

SPACE = pygame.K_SPACE


class KeyState:
    def __init__(self, down):
        self.down = set(down)

    def __getitem__(self, key):
        return key in self.down

    def __len__(self):
        return 512


pygame.key.get_pressed = lambda: KeyState(held[0])

ESC, RET, M, D, P, S, K6, K8 = (
    pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_m, pygame.K_d,
    pygame.K_p, pygame.K_s, pygame.K_6, pygame.K_8,
)

FLY_FROM, FLY_TO = 180, 1590        # steer + shoot during this window
RING_RADIUS = 300.0                 # orbit radius around a target enemy (world px)
SUPPLY_STANDOFF = 4.0               # fly straight onto a crate when no enemy is around

SCHEDULE = {
    60:   [("save", "01_主菜单")],
    65:   [("key", RET)],
    130:  [("save", "02_新手教程")],
    140:  [("key", RET)],
    420:  [("save", "03_游戏内战斗_a")],
    720:  [("save", "03_游戏内战斗_b")],
    1020: [("save", "03_游戏内战斗_c")],
    1320: [("save", "03_游戏内战斗_d")],
    1600: [("key", ESC)],
    1660: [("save", "04_暂停菜单")],
    1670: [("key", ESC)],
    1680: [("key", ESC)],
    1690: [("key", M)],
    1750: [("save", "05_主菜单")],
    1760: [("key", D)],
    1770: [("key", D)],
    1780: [("key", P)],
    1860: [("save", "06_极难任务面板")],
    1870: [("key", K6)],
    1880: [("key", S)],
    1940: [("save", "07_设置与操作说明")],
    1950: [("key", ESC)],
    1960: [("key", K8)],
    2030: [("save", "08_补给站商店")],
}

report = {"frames": 0, "moves": 0, "kills_seen": 0}
state = {"angle": 0.0}


def _safe(g, x, y):
    """Clamp into the camera-safe inner rectangle.

    The game clamps its camera to the world, so a helicopter near a world edge
    ends up drawn under the HUD / behind the bottom bar. Keeping the flight
    inside half-a-screen of the edges keeps the camera unclamped and the
    helicopter centred in every screenshot.
    """
    x = max(float(g.WIDTH // 2), min(float(g.WORLD_W - g.WIDTH // 2), x))
    y = max(float(g.HEIGHT // 2), min(float(g.WORLD_H - g.HEIGHT // 2), y))
    return x, y


def _blocked(g, x, y):
    rect = pygame.Rect(int(x), int(y), g.player_size, g.player_size)
    for w in g.walls:
        if rect.colliderect(pygame.Rect(int(w[0]), int(w[1]), int(w[2]), int(w[3]))):
            return True
    return False


def _try_move(g, mx, my):
    """Step the helicopter, skipping moves that would wedge it inside a wall."""
    px, py = g.player_x, g.player_y
    for cand in ((px + mx, py + my), (px + mx, py), (px, py + my)):
        x, y = _safe(g, cand[0], cand[1])
        if not _blocked(g, x, y):
            g.player_x, g.player_y = x, y
            return True
    return False


def _orbit_spot(g, tx, ty, start_angle):
    """Return a valid orbit position around (tx, ty), or None if none exists."""
    for k in range(12):
        a = start_angle + k * (math.pi / 6.0)
        cx, cy = _safe(g, tx + math.cos(a) * RING_RADIUS, ty + math.sin(a) * RING_RADIUS)
        if math.hypot(cx - tx, cy - ty) < RING_RADIUS * 0.5:
            continue                      # clamped onto the target (target hugs an edge)
        if _blocked(g, cx, cy):
            continue
        return cx, cy
    return None


def _pick_target(g):
    """Nearest *orbitable* enemy (preferred), else nearest supply crate.

    Enemies that spawn hard against the map edge cannot be circled inside the
    camera-safe area, so they are skipped -- otherwise the helicopter would sit
    pinned against an invisible boundary and consecutive shots would look identical.
    """
    px, py = g.player_x, g.player_y
    best, best_d2 = None, None
    fallback, fb_d2 = None, None
    for e in g.enemies:
        ex = e[0] + g.enemy_size / 2.0
        ey = e[1] + g.enemy_size / 2.0
        d2 = (ex - px) ** 2 + (ey - py) ** 2
        if fb_d2 is None or d2 < fb_d2:
            fallback, fb_d2 = (ex, ey), d2
        if _orbit_spot(g, ex, ey, state["angle"]) is None:
            continue
        if best_d2 is None or d2 < best_d2:
            best, best_d2 = (ex, ey), d2
    if best is not None:
        return best[0], best[1], "enemy"
    supplies = getattr(g, "supplies", None) or []
    for s in supplies:
        d2 = (s[0] - px) ** 2 + (s[1] - py) ** 2
        if best_d2 is None or d2 < best_d2:
            best, best_d2 = (s[0], s[1]), d2
    if best is not None:
        return best[0], best[1], "supply"
    if fallback is not None:
        return fallback[0], fallback[1], "chase"
    return None, None, "none"


def steer():
    """Circle the current target (enemy first, else supply crate) by writing globals.

    The helicopter slides around the target on a ring so both it and the target
    stay on screen and the auto-aim weapon keeps connecting -- the shot reads as
    real combat instead of an empty map. Moves are collision-checked so the
    helicopter never wedges itself inside a wall (which would freeze the shot).
    """
    g = sys.modules.get("game")
    if g is None:
        return
    try:
        tx, ty, tag = _pick_target(g)
        px, py = g.player_x, g.player_y
        if tx is not None and tag == "enemy":
            state["angle"] += 0.055
            spot = _orbit_spot(g, tx, ty, state["angle"])
            motion = False
            if spot is not None:
                dx, dy = spot[0] - px, spot[1] - py
                dist = max((dx * dx + dy * dy) ** 0.5, 0.001)
                if dist > 18:
                    step = min(13.0, dist)
                    motion = _try_move(g, dx / dist * step, dy / dist * step)
            if not motion:
                # stand-off: never let a chasing enemy sit on top of the helicopter
                dx, dy = tx - px, ty - py
                dist = max((dx * dx + dy * dy) ** 0.5, 0.001)
                if dist < RING_RADIUS * 0.6:
                    motion = _try_move(g, -dx / dist * 9.0, -dy / dist * 9.0)
            if motion:
                report["moves"] += 1
        elif tx is not None and tag == "chase":       # edge enemy: close in, hold fire
            dx, dy = tx - px, ty - py
            dist = max((dx * dx + dy * dy) ** 0.5, 0.001)
            keep = RING_RADIUS * 0.8
            if dist > keep:
                step = min(12.0, dist - keep)
                if _try_move(g, dx / dist * step, dy / dist * step):
                    report["moves"] += 1
        elif tx is not None:                      # supply crate: fly straight onto it
            dx, dy = tx - px, ty - py
            dist = max((dx * dx + dy * dy) ** 0.5, 0.001)
            if dist > SUPPLY_STANDOFF:
                step = min(11.0, dist)
                if _try_move(g, dx / dist * step, dy / dist * step):
                    report["moves"] += 1
        elif tx is not None:                      # supply crate: fly straight onto it
            dx, dy = tx - px, ty - py
            dist = max((dx * dx + dy * dy) ** 0.5, 0.001)
            if dist > SUPPLY_STANDOFF:
                step = min(11.0, dist)
                if _try_move(g, dx / dist * step, dy / dist * step):
                    report["moves"] += 1
        # keep the camera centred on the helicopter
        g.cam_x = g.player_x - g.WIDTH // 2
        g.cam_y = g.player_y - g.HEIGHT // 2
        # survive the whole capture run
        if g.lives < g.max_lives:
            g.lives = g.max_lives
        report["kills_seen"] = max(report["kills_seen"], len(g.enemies))
    except Exception:
        pass


def _enemy_on_screen(g):
    """True when at least one enemy is comfortably inside the viewport."""
    if g is None:
        return False
    for e in g.enemies:
        sx = e[0] + g.enemy_size / 2.0 - g.cam_x
        sy = e[1] + g.enemy_size / 2.0 - g.cam_y
        if 130 < sx < g.WIDTH - 130 and 150 < sy < g.HEIGHT - 150:
            return True
    return False


pending = [None]          # (acts, scheduled_frame) waiting for an on-screen enemy


def keep_alive(g):
    """Top the helicopter's lives back up every frame while it is on the field.

    The fly window is short but the pause/menu shots come later; without this the
    parked helicopter gets rammed by the Super Chaser after the flight script ends
    and the run latches the death screen, ruining every later screenshot.
    """
    if g is None:
        return
    try:
        if g.lives < g.max_lives:
            g.lives = g.max_lives
    except Exception:
        pass


def clear_field(g):
    """Wipe threats before the pause/menu screenshots (keeps the run deterministic)."""
    if g is None:
        return
    try:
        g.lives = g.max_lives
        g.enemies = []
        g.enemy_bullets = []
        g.super_chaser = None
        g.chaser = None
        g.super_chaser_broadcast = ""
        g.super_chaser_broadcast_timer = 0
    except Exception:
        pass


def _actions(acts):
    for kind, val in acts:
        if kind == "save":
            surf = pygame.display.get_surface()
            path = os.path.join(OUT_DIR, f"{val}.png")
            pygame.image.save(surf, path)
            print("[shot]", os.path.basename(path), flush=True)
        else:
            pygame.event.post(
                pygame.event.Event(pygame.KEYDOWN, key=val, mod=0, unicode="", scancode=0)
            )


_orig_flip = pygame.display.flip


def flip_hook():
    frames[0] += 1
    n = frames[0]
    g = sys.modules.get("game")
    held[0] = {SPACE} if FLY_FROM <= n < FLY_TO else set()
    if FLY_FROM <= n < FLY_TO:
        steer()
        keep_alive(g)
    if n == 1595:                    # just before the pause: clear the battlefield
        clear_field(g)
    if n in SCHEDULE:
        acts = SCHEDULE[n]
        if acts[0][0] == "key":           # a key press ends the combat phase
            pending[0] = None
        combat = acts[0][0] == "save" and acts[0][1].startswith("03_")
        if combat and not _enemy_on_screen(sys.modules.get("game")):
            pending[0] = (acts, n)        # hold the shot until an enemy is in view
        else:
            _actions(acts)
    if pending[0] is not None:
        acts, sched = pending[0]
        if _enemy_on_screen(sys.modules.get("game")) or n - sched > 120:
            _actions(acts)
            pending[0] = None
    if n >= 2100:
        pygame.event.post(pygame.event.Event(pygame.QUIT))
    _orig_flip()


pygame.display.flip = flip_hook

import game  # noqa: E402,F401

print("capture finished, frames =", frames[0], "moves:", report["moves"],
      "max enemies on screen:", report["kills_seen"])
