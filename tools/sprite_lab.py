# -*- coding: utf-8 -*-
"""
HeliOps 1.2 像素精灵实验室
--------------------------
参考 me-2.png 的画风：粗黑描边 + 头盔 + 迷彩制服 + 白脸黑眼窝。
ASCII 定义像素图 -> 渲染对照图 -> 反复调 -> 嵌进 game.py。

约定：
  - 每行一个字符串，'.' = 透明，同一精灵内所有行等宽
  - {'up': 头+躯干, 'legs': [帧A, 帧B]}，两帧腿 = 走路循环
"""
import os

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "screenshots")

PAL = {
    ".": None,
    "#": (18, 18, 22),        # 描边
    "h": (96, 100, 108),      # 头盔
    "H": (146, 152, 162),     # 头盔高光
    "s": (58, 60, 68),        # 头盔暗部
    "f": (242, 232, 212),     # 脸
    "k": (26, 26, 30),        # 眼窝 / 嘴
    "o": (104, 116, 68),      # 迷彩橄榄
    "O": (70, 80, 48),        # 迷彩深橄榄
    "b": (114, 86, 52),       # 迷彩棕
    "B": (78, 58, 38),        # 迷彩深棕
    "v": (40, 42, 50),        # 背心 / 织带
    "t": (28, 28, 34),        # 靴子
    "y": (120, 126, 138),     # 枪械金属
}

# ============================================================ 玩家 · 正面
PF = [
    "......######......",
    "....##hhhhhh##....",
    "...#hhhhhhhhhh#...",
    "..#hhhhhhhhhhhh#..",
    ".#hHHHHHHHHHHHHh#.",
    ".#hhhhhhhhhhhhhh#.",
    ".#ssssssssssssss#.",
    "..##############..",
    "...#ffffffffff#...",
    "...#ffkkffkkff#...",
    "...#ffffffffff#...",
    "...#fffkkkkfff#...",
    "....#ffffffff#....",
    ".....########.....",
    ".......#vv#.......",
    "..##############..",
    ".#oo##oooooo##oo#.",
    ".#oo##oooooo##oo#.",
    ".#oo##oobboo##oo#.",
    ".#oo##oobboo##oo#.",
    ".#oo##vOOOOv##oo#.",
    ".#oo##vOOOOv##oo#.",
    ".#oo##oooooo##oo#.",
    ".#oo##oobbbo##oo#.",
    ".#oo##oooooo##oo#.",
    "..##############..",
]
PF_LEGS = [
    [
        "...##oo####oo##...",
        "...##oo####oo##...",
        "...##oo####oo##...",
        "...##tt####tt##...",
        "...##tt####tt##...",
        "...####....####...",
    ],
    [
        "...##oo####oo##...",
        "..##oo#....#oo##..",
        "..##oo#....#oo##..",
        "..###tt#..#tt###..",
        "..##tt#....#tt##..",
        "..####......####..",
    ],
]

# ============================================================ 玩家 · 背面
PB = [
    "......######......",
    "....##hhhhhh##....",
    "...#hhhhhhhhhh#...",
    "..#hhhhhhhhhhhh#..",
    ".#hssssssssssssh#.",
    ".#hhhhhhhhhhhhhh#.",
    ".#hhhhhhhhhhhhhh#.",
    "..##############..",
    "...#hhhhhhhhhh#...",
    "...#hhhhhhhhhh#...",
    "...#hhhhhhhhhh#...",
    "...#hhhhhhhhhh#...",
    "....#hhhhhhhh#....",
    ".....########.....",
    ".......#vv#.......",
    "..##############..",
    ".#oo#vvvvvvvv#oo#.",
    ".#oo#vvvvvvvv#oo#.",
    ".#oo#vOOOOOOv#oo#.",
    ".#oo#vOooooOv#oo#.",
    ".#oo#vOooooOv#oo#.",
    ".#oo#vOOOOOOv#oo#.",
    ".#oo#vvvvvvvv#oo#.",
    ".#oo#oooooooo#oo#.",
    ".#oo#ooobbbоо#oo#.",
    "..##############..",
]
PB_LEGS = PF_LEGS

# ============================================================ 玩家 · 侧面（朝右）
PS = [
    ".....#####........",
    "....#hhhhh#.......",
    "...#hhhhhhh#......",
    "..#hhhhhhhhh#.....",
    "..#hHHHHHHHh#.....",
    "..#hhhhhhhhh#.....",
    "..#sssssssss#.....",
    "..############....",
    "...#ffffffff#.....",
    "...#ffffkk##......",
    "...#ffffff#.......",
    "...#fffkk#........",
    "....#ffff#........",
    ".....#####........",
    "......#vv#........",
    "..############....",
    ".#oo#oooooo#oo#...",
    ".#oo#oooooo#oo#...",
    ".#oo#oobbboo#oo#..",
    ".#oo#oobbboo#oo#yy",
    ".#oo#vOOOOOv#oo#yy",
    ".#oo#vOOOOOv#oo#..",
    ".#oo#ooooooo#oo#..",
    ".#oo#oobbbbo#oo#..",
    ".#oo#ooooooo#oo#..",
    "..##############..",
]
PS_LEGS = PF_LEGS

PLAYER = {
    "front": {"up": PF, "legs": PF_LEGS},
    "back":  {"up": PB, "legs": PB_LEGS},
    "side":  {"up": PS, "legs": PS_LEGS},
}


def validate(name, rows):
    w = max(len(r) for r in rows)
    bad = [i for i, r in enumerate(rows) if len(r) != w]
    if bad:
        print("  !! %s 行宽不一致 (应为 %d): 行 %s" % (name, w, bad))
        for i in bad[:4]:
            print("       %2d len=%d  %r" % (i, len(rows[i]), rows[i]))
    return w


def render_grid(rows, scale=1):
    import pygame
    w = max(len(r) for r in rows)
    h = len(rows)
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            col = PAL.get(ch)
            if col is not None:
                surf.set_at((x, y), col)
    if scale != 1:
        surf = pygame.transform.scale(surf, (w * scale, h * scale))
    return surf


def main():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    import pygame
    pygame.init()
    pygame.display.set_mode((64, 64))

    BG_GREEN, BG_DARK = (45, 140, 50), (24, 24, 30)
    font = pygame.font.Font("/System/Library/Fonts/Supplemental/Arial Unicode.ttf", 15)

    poses = [("front", "正面"), ("side", "侧面"), ("back", "背面")]
    for p, _ in poses:
        validate(p, PLAYER[p]["up"] + PLAYER[p]["legs"][0])

    # ---------- 放大对照区 ----------
    SCALE, PAD, LABEL_H = 5, 14, 26
    cw = max(max(len(r) for r in PLAYER[p]["up"]) for p, _ in poses) * SCALE + PAD * 2
    ch = max((len(PLAYER[p]["up"]) + len(PLAYER[p]["legs"][0])) for p, _ in poses) * SCALE + PAD * 2 + LABEL_H * 2

    sheet = pygame.Surface((cw * len(poses) * 2, ch), pygame.SRCALPHA)
    sheet.fill(BG_GREEN)

    for ci, (pose, cname) in enumerate(poses):
        for fi in range(2):
            ox = (ci * 2 + fi) * cw
            half = cw // 2
            pygame.draw.rect(sheet, BG_DARK, (ox, LABEL_H, half, ch - LABEL_H))
            pygame.draw.rect(sheet, BG_GREEN, (ox + half, LABEL_H, cw - half, ch - LABEL_H))
            spr = render_grid(PLAYER[pose]["up"] + PLAYER[pose]["legs"][fi], SCALE)
            sheet.blit(spr, (ox + (cw - spr.get_width()) // 2,
                             LABEL_H + (ch - LABEL_H - spr.get_height()) // 2))
            lab = font.render("%s-走路%d" % (cname, fi + 1), True, (255, 255, 255))
            sheet.blit(lab, (ox + (cw - lab.get_width()) // 2, 4))

    # ---------- 实际尺寸条（1x / 2x / 3x）----------
    sizes = [1, 2, 3]
    strip_h = 40 * 3 + 30
    strip = pygame.Surface((sheet.get_width(), strip_h), pygame.SRCALPHA)
    strip.fill(BG_GREEN)
    x = 20
    for s in sizes:
        spr = render_grid(PLAYER["front"]["up"] + PLAYER["front"]["legs"][0], s)
        strip.blit(spr, (x, 24 + (40 * 3 - spr.get_height())))
        lab = font.render("%dx  %dpx高" % (s, spr.get_height()), True, (255, 255, 255))
        strip.blit(lab, (x, 4))
        x += spr.get_width() + 40
    # 参考图原图放一边做对比
    ref_path = "/Users/Admin/Desktop/游戏heliops/游戏素材（好像废了）/人物（主角，敌人）/me-2.png"
    if os.path.exists(ref_path):
        ref = pygame.image.load(ref_path).convert_alpha()
        strip.blit(pygame.transform.scale(ref, (ref.get_width() * 2, ref.get_height() * 2)), (x, 24))
        lab = font.render("参考图", True, (255, 255, 255))
        strip.blit(lab, (x, 4))

    final = pygame.Surface((sheet.get_width(), sheet.get_height() + strip_h), pygame.SRCALPHA)
    final.blit(sheet, (0, 0))
    final.blit(strip, (0, sheet.get_height()))

    out = os.path.join(OUT, "精灵实验室_玩家.png")
    pygame.image.save(final, out)
    print("saved:", out, final.get_size())
    pygame.quit()


if __name__ == "__main__":
    main()
