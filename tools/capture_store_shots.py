# -*- coding: utf-8 -*-
"""Capture store-ready screenshots of the CURRENT build (v1.3.3).

The screenshots/ folder was shot against v1.2 (green menus, four weapons, no
night lighting) and the entries on indienova / itch.io still show that old
look. This script drives the real game headlessly and saves the scenes that
actually sell v1.3:

  1. main menu (the new dark-grid look)
  2. career stats panel
  3. supply station
  4. daytime firefight with the grenade cannon
  5. night combat -- the 90-degree torch cone with hostiles inside it
  6. the Boss chase

Shots are taken on a CONDITION (a muzzle flash on screen, not reloading, a
target nearby) instead of a fixed frame number -- a fixed frame usually lands
on an empty field or on the reload animation.

Off-screen rendering (SDL dummy) + isolated HOME so the real save is untouched.
game.py has no __main__ guard, so everything lives in the pygame.display.flip
hook.

Game structures this relies on (checked against game.py):
  enemy = [wx, wy, patrol_start, patrol_end, state, alert_t, chase_t, hp, shoot_cd]
  boss  = [wx, wy, hp, shoot_cd, chasing]
"""
import math
import os
import shutil
import sys

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

GAME_DIR = "/Users/Admin/WorkBuddy/2026-05-31-19-56-04"
OUT_DIR = os.path.join(GAME_DIR, "screenshots")
FRESH_HOME = "/tmp/heliops_store_home"
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(FRESH_HOME, exist_ok=True)
shutil.rmtree(os.path.join(FRESH_HOME, "Documents"), ignore_errors=True)
os.environ["HOME"] = FRESH_HOME
sys.path.insert(0, GAME_DIR)

import pygame  # noqa: E402

frames = [0]
held = [set()]
pending = [None]
SPACE = pygame.K_SPACE


class KeyState:
    def __init__(self, down):
        self.down = set(down)

    def __getitem__(self, key):
        return key in self.down

    def __len__(self):
        return 512


pygame.key.get_pressed = lambda: KeyState(held[0])

RET, ESC, T_KEY, K8, K0 = (pygame.K_RETURN, pygame.K_ESCAPE, pygame.K_t,
                           pygame.K_8, pygame.K_0)

STATS_OPEN, STATS_BACK = 30, 70
SHOP_OPEN, SHOP_BACK = 90, 140
NEW_GAME, BRIEF_OK = 170, 200

# shot windows: (start_frame, end_frame, filename, kind)
WINDOWS = [
    (12, 12, "v1.3.3_主菜单.png", "fixed"),
    (50, 50, "v1.3.3_生涯战绩.png", "fixed"),
    (120, 120, "v1.3.3_补给站.png", "fixed"),
    (380, 560, "v1.3.3_白天战斗_榴弹炮.png", "combat"),
    (840, 1080, "v1.3.3_Boss追杀.png", "boss"),
    (1210, 1400, "v1.3.3_夜晚手电锥形.png", "combat"),
]
END = 1420

state = {"angle": 0.0, "shot": set()}


def _safe(g, x, y):
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
    px, py = g.player_x, g.player_y
    for cand in ((px + mx, py + my), (px + mx, py), (px, py + my)):
        x, y = _safe(g, cand[0], cand[1])
        if not _blocked(g, x, y):
            g.player_x, g.player_y = x, y
            return True
    return False


def _face_center(g, tx, ty):
    ang = math.degrees(math.atan2(ty - g.player_y, tx - g.player_x))
    state["angle"] = ang
    g.face_angle = ang


def _nearest_enemy(g, limit=1e9):
    best, bd = None, limit
    for e in g.enemies:
        d = math.hypot(e[0] - g.player_x, e[1] - g.player_y)
        if d < bd:
            best, bd = e, d
    return best


def steer_combat(g, radius=185.0):
    tgt = _nearest_enemy(g)
    if tgt is None:
        return
    ang = state["angle"] + 0.17
    tx = tgt[0] + math.cos(ang) * radius
    ty = tgt[1] + math.sin(ang) * radius
    nx, ny = _safe(g, tx, ty)
    dx, dy = nx - g.player_x, ny - g.player_y
    d = math.hypot(dx, dy) or 1
    _try_move(g, dx / d * 3.4, dy / d * 3.4)
    _face_center(g, tgt[0], tgt[1])


def keep_alive(g):
    """No HP pool: armor eats one hit each, then a life is lost."""
    if g.armor < 2:
        g.armor = 2
    if g.lives < 10:
        g.lives = 10


_seed = [7]


def ensure_enemies(g, want=4, radius=210.0):
    """Spawn hostiles with the game's own spawner, pull them close, and give
    them enough HP that they stay in frame instead of dying instantly."""
    while len(g.enemies) < want:
        _seed[0] = (_seed[0] * 1103515245 + 12345) % 2147483648
        ang = (_seed[0] % 1000) / 1000.0 * math.pi * 2
        d = radius * (0.45 + 0.5 * ((_seed[0] // 1000) % 1000) / 1000.0)
        g.spawn_enemy()
        e = g.enemies[-1]
        x, y = _safe(g, g.player_x + math.cos(ang) * d, g.player_y + math.sin(ang) * d)
        if _blocked(g, x, y):
            continue
        e[0], e[1] = x, y
        e[7] = 30          # hp: survives the auto-aim, so it stays on screen
        e[8] = 0


def stage_night(g):
    """Put the hostiles INSIDE the torch cone: a small cluster straight ahead
    of the player, and let the auto-aim light them up."""
    ang = math.radians(state["angle"])
    fx, fy = math.cos(ang), math.sin(ang)
    for i, e in enumerate(list(g.enemies)[:3]):
        off = 115 + i * 52
        side = (i - 1) * 34
        x = g.player_x + fx * off - fy * side
        y = g.player_y + fx * side + fy * off
        x, y = _safe(g, x, y)
        e[0], e[1] = x, y
        e[7] = 30
    if g.enemies:
        e = g.enemies[0]
        _face_center(g, e[0], e[1])


def arm_boss(g):
    """Use the game's own spawner (the boss record has 6 fields, index 4 is
    the "target acquired" flag and index 5 the max HP for the health bar),
    then park it next to the player so it is actually in the shot."""
    if g.boss is None:
        g.spawn_boss()
    b = g.boss
    b[0] = g.player_x + 150.0
    b[1] = g.player_y - 40.0
    b[3] = 30
    b[4] = True


def seed_career(g):
    """A stats panel full of zeros makes a poor store screenshot -- seed a
    plausible career so the panel shows what the feature is for."""
    g.total_runs = 37
    g.total_extractions = 24
    g.total_kills = 486
    g.best_score = 18640
    g.hard_mode_unlocked = True
    g.extreme_mode_unlocked = True


def capture(name):
    path = os.path.join(OUT_DIR, name)
    pygame.image.save(pygame.display.get_surface(), path, "PNG")
    print("saved %s" % path, flush=True)


def action_ready(g, kind, waited):
    """A frame worth putting on a store page.

    `g.muzzle_flashes` is empty by the time the flip hook runs (the draw pass
    retires the flashes), and a bullet that hits is removed in the same frame,
    so "a bullet in flight" only holds for a frame or two. Prefer that frame,
    but fall back to "the target is right there in the beam" after a short
    wait -- otherwise the capture window can pass without a single shot.
    """
    if g.reload_timer != 0:
        return False
    if kind == "boss":
        if g.boss is None:
            return False
        d = math.hypot(g.boss[0] - g.player_x, g.boss[1] - g.player_y)
        near = d < 430.0
    else:
        near = _nearest_enemy(g, 300.0) is not None
    if g.bullets:
        return True
    return waited > 45 and near


def flip_hook():
    n = frames[0]
    frames[0] = n + 1
    g = sys.modules.get("game")
    if g is None:
        return

    # ---- key events land on the NEXT rendered frame ----
    if pending[0] is not None:
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pending[0]))
        pending[0] = None

    if n == STATS_OPEN:
        seed_career(g)
        pending[0] = T_KEY
    elif n == STATS_BACK:
        pending[0] = ESC
    elif n == SHOP_OPEN:
        pending[0] = K8
    elif n == SHOP_BACK:
        pending[0] = K0
    elif n == NEW_GAME:
        pending[0] = RET
    elif n == BRIEF_OK:
        pending[0] = RET

    # ---- in-run behaviour ----
    if n > BRIEF_OK + 3:
        keep_alive(g)
        g.owned_guns.add("cannon")
        g.current_gun = "cannon"
        # fire in bursts: the gun has to be reloaded often, and a screenshot
        # taken mid-reload shows no muzzle flash
        holding = (n % 72) < 48
        held[0] = {SPACE} if holding else set()
        if n < 800:
            g.time_of_day = "day"
            # keep a loaded magazine so a firing frame always exists
            g.gun_mags["cannon"] = 4
            g.reload_timer = 0
            if n % 14 == 0:
                ensure_enemies(g, want=4, radius=215.0)
            steer_combat(g)
        elif n < 1120:
            g.time_of_day = "day"
            arm_boss(g)
            g.gun_mags["cannon"] = 4
            g.reload_timer = 0
            b = g.boss
            ang = state["angle"] + 0.13
            tx = b[0] + math.cos(ang) * 185
            ty = b[1] + math.sin(ang) * 185
            nx, ny = _safe(g, tx, ty)
            dx, dy = nx - g.player_x, ny - g.player_y
            d = math.hypot(dx, dy) or 1
            _try_move(g, dx / d * 3.0, dy / d * 3.0)
            _face_center(g, b[0], b[1])
            if n % 26 == 0:
                ensure_enemies(g, want=2, radius=230.0)
        else:
            # night combat: stage the hostiles inside the torch cone
            g.time_of_day = "night"
            # the cannon's reload takes 150 frames (5s) -- keep the magazine
            # full so there is always a firing frame to capture
            g.gun_mags["cannon"] = 4
            g.reload_timer = 0
            if n % 12 == 0:
                ensure_enemies(g, want=4, radius=150.0)
            stage_night(g)

    # ---- capture on a condition, not on a fixed frame ----
    for start, end, name, kind in WINDOWS:
        if start <= n <= end and name not in state["shot"]:
            if kind == "fixed" or action_ready(g, kind, n - start):
                state["shot"].add(name)
                capture(name)

    if n >= END:
        pygame.quit()
        sys.exit(0)


_orig_flip = pygame.display.flip
pygame.display.flip = flip_hook

try:
    import game  # noqa: E402,F401
except SystemExit:
    pass
print("capture done:", frames[0], "frames")
