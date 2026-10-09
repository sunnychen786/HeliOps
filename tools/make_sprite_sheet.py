# -*- coding: utf-8 -*-
"""
生成 v1.2 角色图鉴（最终交付图）。
从 game.py 抽取精灵代码段渲染，不启动游戏。
"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "screenshots", "v1.2_角色图鉴.png")

import pygame  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

ZOOM = 7
PAD = 10
GAP = 16
ROW_GAP = 10
HDR = 24
BG = (45, 140, 50)          # 游戏里的草地底色
LABEL = (255, 255, 255)

FONT_PATH = "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"


def load_sprites():
    src = open(os.path.join(ROOT, "game.py"), encoding="utf-8").read()
    i = src.index("# v1.2 Pixel-art sprite system")
    j = src.index("# Helper functions", i)
    block = src[i:j].rsplit("# ==============================", 1)[0]
    ns = {"pygame": pygame}
    exec(compile(block, "game.py:sprite-block", "exec"), ns)
    return ns


def to_pil(surf):
    return Image.frombytes("RGBA", surf.get_size(),
                           pygame.image.tostring(surf, "RGBA"))


def main():
    pygame.init()
    pygame.display.set_mode((64, 64))
    SPR = load_sprites()
    font = ImageFont.truetype(FONT_PATH, 15)
    font_row = ImageFont.truetype(FONT_PATH, 18)

    ENEMY_STATES = [("巡逻", "patrol"), ("警戒", "alert"),
                    ("追击", "chase"), ("疲惫", "tired")]

    rows = []
    rows.append(("玩家", [("正面", "player", "front", None),
                          ("侧面", "player", "side", None),
                          ("背面", "player", "back", None)]))
    enemy_variants = [("正面", "enemy", "front", None)]
    for cn, key in ENEMY_STATES:
        enemy_variants.append((cn, "enemy", "front",
                               {"v": SPR["SPR_ENEMY_STATE_COLOR"][key]}))
    rows.append(("敌人", enemy_variants))
    rows.append(("猎手", [("正面", "chaser", "front", None),
                          ("侧面", "chaser", "side", None),
                          ("锁定", "chaser", "front", {"k": (255, 130, 20)})]))
    rows.append(("超级猎手", [("正面", "super", "front", None),
                              ("侧面", "super", "side", None),
                              ("锁定", "super", "front", {"k": (140, 255, 170)})]))
    rows.append(("Boss", [("正面", "boss", "front", None)]))

    # 预渲染
    rendered = []
    for uname, variants in rows:
        cells = []
        for vname, unit, pose, tint in variants:
            im = to_pil(SPR["get_sprite"](unit, pose, 0, tint))
            im = im.resize((im.width * ZOOM, im.height * ZOOM), Image.NEAREST)
            cells.append((vname, im))
        rendered.append((uname, cells))

    # 行尺寸
    row_meta = []
    for uname, cells in rendered:
        cw = max(im.width for _, im in cells)
        ch = max(im.height for _, im in cells)
        row_meta.append((cw, ch, len(cells)))

    width = max(sum(cw * n + GAP * (n - 1) for cw, ch, n in [rm]) for rm in row_meta) + PAD * 2
    width = max(width, 600)
    height = sum(ch + HDR + ROW_GAP + PAD for cw, ch, n in row_meta)

    sheet = Image.new("RGB", (width, height), BG)
    dr = ImageDraw.Draw(sheet)

    y = 0
    for (uname, cells), (cw, ch, n) in zip(rendered, row_meta):
        x = PAD
        # 行标题
        dr.text((x, y + 2), uname, font=font_row, fill=(255, 255, 255),
                stroke_width=2, stroke_fill=(20, 40, 20))
        y += HDR
        for vname, im in cells:
            ox = x + (cw - im.width) // 2
            oy = y + (ch - im.height) // 2
            sheet.paste(im, (ox, oy), im)
            tw = dr.textlength(vname, font=font)
            dr.text((x + (cw - tw) / 2, y + ch + 2), vname, font=font,
                    fill=(255, 255, 255), stroke_width=2, stroke_fill=(20, 40, 20))
            x += cw + GAP
        y += ch + ROW_GAP + PAD

    sheet.save(OUT)
    print("saved:", OUT, sheet.size)


if __name__ == "__main__":
    main()
