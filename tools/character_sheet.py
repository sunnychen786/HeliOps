# -*- coding: utf-8 -*-
"""角色图鉴：把游戏里所有角色 / NPC 的当前画法渲染成一张对照图。

用途：改美术之前看清现状，改完之后做前后对比。

实现要点：
- game.py 没有 main guard，import 即跑主循环，所以按
  pygame-headless-screenshots 技能的套路，包一层 display.flip 钩子，
  在第一帧里借用 game 的绘制函数离屏作画，然后立刻 QUIT。
- 通过改写 G.cam_x / G.cam_y（负数）把 world 原点推到临时画布中间，
  再把 G.screen 临时换成小画布，角色就画到离屏 surface 上了。
"""
import os
import sys
import shutil
import traceback

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

FRESH_HOME = "/tmp/heliops_sheet_home"
os.makedirs(FRESH_HOME, exist_ok=True)
shutil.rmtree(os.path.join(FRESH_HOME, "Documents"), ignore_errors=True)
os.environ["HOME"] = FRESH_HOME

GAME_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(GAME_DIR, "screenshots")
OUT = os.path.join(OUT_DIR, "角色图鉴_当前.png")
sys.path.insert(0, GAME_DIR)

import pygame

PAD = 44            # 临时画布留白，避免血条/状态符号被裁掉
FRAME = 168         # 卡片里放大显示的正方形边长
CW, CH = 244, 300   # 卡片尺寸
COLS = 4
GAP = 20
MARGIN = 36

BG = (22, 24, 30)
CARD = (33, 36, 45)
WHITE = (236, 240, 248)
DIM = (146, 154, 170)

frames = [0]
_orig_flip = pygame.display.flip


def render_unit(G, draw_call, size):
    """在离屏画布上画一个单位，返回 (放大图, 原始尺寸图)。"""
    inner = size + PAD * 2
    tmp = pygame.Surface((inner, inner), pygame.SRCALPHA)
    tmp.fill((0, 0, 0, 0))

    old_screen, old_cam = G.screen, (G.cam_x, G.cam_y)
    G.screen = tmp
    G.cam_x, G.cam_y = -PAD, -PAD          # world(0,0) -> screen(PAD, PAD)
    try:
        draw_call()
    finally:
        G.screen = old_screen
        G.cam_x, G.cam_y = old_cam

    # 裁掉留白：36px 的小人摊在 124px 画布里只剩中间一小撮，直接放大会看不清
    rects = pygame.mask.from_surface(tmp).get_bounding_rects()
    if rects:
        x0 = max(0, min(r.x for r in rects) - 3)
        y0 = max(0, min(r.y for r in rects) - 3)
        x1 = min(inner, max(r.right for r in rects) + 3)
        y1 = min(inner, max(r.bottom for r in rects) + 3)
        crop = tmp.subsurface(pygame.Rect(x0, y0, max(1, x1 - x0), max(1, y1 - y0))).copy()
    else:
        crop = tmp

    w, h = crop.get_size()
    s = FRAME / max(w, h)                  # 等比撑满，不拉伸变形
    big = pygame.transform.smoothscale(crop, (max(1, int(w * s)), max(1, int(h * s))))
    return big, crop


def draw_card(G, sheet, card_x, card_y, title, note, big, raw, size):
    pygame.draw.rect(sheet, CARD, (card_x, card_y, CW, CH), border_radius=10)
    sheet.blit(G.font_small.render(title, True, WHITE), (card_x + 16, card_y + 12))
    sheet.blit(G.font_small.render(note, True, DIM), (card_x + 16, card_y + 38))

    bw, bh = big.get_size()
    sheet.blit(big, (card_x + (CW - bw) // 2, card_y + 66 + (FRAME - bh) // 2))

    rw, rh = raw.get_size()
    rx = card_x + 16
    ry = card_y + CH - 16 - max(rh, 24)
    sheet.blit(raw, (rx, ry))
    sheet.blit(G.font_small.render("实际 %dpx" % size, True, DIM),
               (rx + rw + 10, ry + 2))


def build(G):
    def mk_player(gun):
        def f():
            G.current_gun = gun
            G.face_angle = 0
            G.draw_player(0, 0)
        return f

    def mk_enemy(state):
        def f():
            G.draw_enemy(0, 0, state)
        return f

    def mk_boss():
        def f():
            hp = G.BOSS_MAX_HP
            G.draw_boss([0, 0, hp, 0, True, hp])
        return f

    roles = [
        ("玩家 · 手枪", "待机 / 持枪侧身", mk_player("pistol"), G.player_size),
        ("玩家 · 步枪", "枪管更长", mk_player("rifle"), G.player_size),
        ("玩家 · 霰弹", "粗短枪管", mk_player("shotgun"), G.player_size),
        ("玩家 · 狙击", "带瞄准镜", mk_player("sniper"), G.player_size),
        ("敌人 · 巡逻", "未发现玩家", mk_enemy("patrol"), G.enemy_size),
        ("敌人 · 警戒", "听到动静", mk_enemy("alert"), G.enemy_size),
        ("敌人 · 追击", "头顶感叹号", mk_enemy("chase"), G.enemy_size),
        ("敌人 · 疲惫", "失去目标 Z", mk_enemy("tired"), G.enemy_size),
        ("Boss", "高血量 · 开火散布", mk_boss(), G.BOSS_SIZE),
        ("猎手 Chaser", "同速追击 · 不死不休",
         lambda: G.draw_chaser([0, 0, G.CHASER_HP, True]), G.CHASER_SIZE),
        ("超级猎手", "无敌 · 锁定光环",
         lambda: G.draw_super_chaser([0, 0, True]), G.SUPER_CHASER_SIZE),
    ]

    rows = (len(roles) + COLS - 1) // COLS
    W = MARGIN * 2 + COLS * CW + (COLS - 1) * GAP
    H = MARGIN * 2 + rows * CH + (rows - 1) * GAP + 40
    sheet = pygame.Surface((W, H))
    sheet.fill(BG)

    head = G.font_normal.render("HeliOps 角色图鉴 · 当前美术（改版前）", True, WHITE)
    sheet.blit(head, (MARGIN, 8))

    for i, (title, note, call, size) in enumerate(roles):
        c, r = i % COLS, i // COLS
        x = MARGIN + c * (CW + GAP)
        y = MARGIN + r * (CH + GAP) + 40
        try:
            big, raw = render_unit(G, call, size)
        except Exception:
            traceback.print_exc()
            continue
        draw_card(G, sheet, x, y, title, note, big, raw, size)

    pygame.image.save(sheet, OUT)
    print("saved:", OUT, sheet.get_size())


def flip_hook():
    frames[0] += 1
    if frames[0] == 1:
        try:
            build(sys.modules["game"])
        except Exception:
            traceback.print_exc()
        pygame.event.post(pygame.event.Event(pygame.QUIT))
    _orig_flip()


pygame.display.flip = flip_hook
import game  # noqa: E402  — 触发主循环，靠上面的钩子收尾
