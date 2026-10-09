# -*- coding: utf-8 -*-
"""
角色精灵总览 v1.2
----------------
game.py 没有 main guard（import 即启动主循环），所以这里不 import game，
而是把 game.py 里 "v1.2 Pixel-art sprite system" 那一段源码抽出来单独 exec，
只拿到精灵数据，完全不启动游戏。

用途：检查行宽、验证配色与轮廓、做改版前后对比。
"""
import os
import re
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "screenshots")

import pygame  # noqa: E402

START = "# v1.2 Pixel-art sprite system"
END = "# Helper functions"


def load_sprite_module():
    src = open(os.path.join(ROOT, "game.py"), encoding="utf-8").read()
    i = src.index(START)
    j = src.index(END, i)
    block = src[i:j]
    # 砍掉最后那行 "# ====..." 分隔注释
    block = block.rsplit("# ==============================", 1)[0]
    ns = {"pygame": pygame}
    exec(compile(block, "game.py:sprite-block", "exec"), ns)
    return ns


def main():
    pygame.init()
    pygame.display.set_mode((64, 64))
    SPR = load_sprite_module()

    UNITS = [("player", "玩家"), ("enemy", "敌人"), ("chaser", "猎手"),
             ("super", "超级猎手"), ("boss", "Boss")]
    POSES = [("front", "正面"), ("side", "侧面"), ("back", "背面")]
    STATE_LABEL = {"patrol": "巡逻", "alert": "警戒", "chase": "追击", "tired": "疲惫"}

    print("=== 行宽 / 行数校验 ===")
    bad = 0
    for u, _ in UNITS:
        for p, _ in POSES:
            body, legs = SPR["SPR_UNITS"][u][p]
            for name, rows in [("body", body)] + [("leg%d" % i, L) for i, L in enumerate(legs)]:
                w = set(len(r) for r in rows)
                if len(w) != 1:
                    bad += 1
                    print("  !! %s/%s/%s 行宽不一致 %s" % (u, p, name, sorted(w)))
    print("  不一致项:", bad)

    SCALE, PAD, HDR = 6, 12, 28
    font = pygame.font.Font("/System/Library/Fonts/Supplemental/Arial Unicode.ttf", 15)

    rows_meta = []
    for u, uname in UNITS:
        variants = [(pn, p, None) for p, pn in POSES]
        if u == "enemy":
            for k, cn in STATE_LABEL.items():
                variants.append((cn, "front", {"v": SPR["SPR_ENEMY_STATE_COLOR"][k]}))
        if u in ("chaser", "super"):
            variants.append(("锁定", "front", {"k": (255, 120, 0) if u == "chaser" else (140, 255, 170)}))
        rows_meta.append((u, uname, variants))

    # 每行用自己的精灵尺寸，避免被 Boss 撑大导致小人看不清
    def max_size(variants):
        w = h = 0
        for _, p, _ in variants:
            for fr in (0, 1):
                s = SPR["get_sprite"](u, p, fr)
                w, h = max(w, s.get_width()), max(h, s.get_height())
        return w, h

    row_sizes = []
    for u, _, variants in rows_meta:
        w, h = max_size(variants)
        row_sizes.append((w * SCALE + PAD * 2, h * SCALE + PAD * 2 + HDR))

    max_cols = max(len(v) for _, _, v in rows_meta)
    sheet_w = max(r[0] for r in row_sizes) * max_cols
    sheet_h = sum(r[1] for r in row_sizes)
    sheet = pygame.Surface((int(sheet_w), int(sheet_h)))
    BG_GREEN, BG_DARK = (45, 140, 50), (24, 24, 30)

    oy = 0
    for ri, (u, uname, variants) in enumerate(rows_meta):
        cell_w, cell_h = row_sizes[ri]
        for ci, (vname, pose, tint) in enumerate(variants):
            ox = ci * cell_w
            half = cell_w // 2
            pygame.draw.rect(sheet, BG_DARK, (ox, oy, half, cell_h))
            pygame.draw.rect(sheet, BG_GREEN, (ox + half, oy, cell_w - half, cell_h))
            spr = SPR["get_sprite"](u, pose, 0, tint)
            sheet.blit(spr, (ox + (cell_w - spr.get_width()) // 2,
                             oy + HDR + (cell_h - HDR - spr.get_height()) // 2))
            lab = font.render("%s·%s" % (uname, vname), True, (255, 255, 255))
            sheet.blit(lab, (ox + (cell_w - lab.get_width()) // 2, oy + 6))
        oy += cell_h

    out = os.path.join(OUT, "角色精灵总览_v1.2.png")
    pygame.image.save(sheet, out)
    print("saved:", out, sheet.get_size())


if __name__ == "__main__":
    main()
