# -*- coding: utf-8 -*-
"""生成一张「链接卡」图，用于 B 站动态第 5 张配图。
B 站动态的外链不会生成卡片（只有站内 BV 号/专栏/直播间才会），
所以把网址画进图里最稳。

坑：macOS 上 /System/Library/Fonts/PingFang.ttc 并不总是存在，
Pillow 静默回退到 load_default() 后中文会变成豆腐块。
这里对每个候选字体做一次「中文能否渲染」自检，不过就换下一个。
"""
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "screenshots", "indienova_00_封面_1280x720.png")
OUT = os.path.join(ROOT, "screenshots", "bili_链接卡_1280x720.png")
W, H = 1280, 720

FONT_CANDIDATES = [
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/Library/Fonts/Arial Unicode.ttf",
    "/System/Library/Fonts/STHeiti Light.ttc",
]

_PROBE = "游戏页面下载"   # 只用这几个字做自检


def _can_render(path):
    """用「墨水量」判断：能画出中文，且不是 .notdef 方框。"""
    try:
        f = ImageFont.truetype(path, 40)
    except Exception:
        return False
    def ink(ch):
        im = Image.new("L", (90, 90), 0)
        ImageDraw.Draw(im).text((10, 10), ch, font=f, fill=255)
        return sum(im.getdata())
    cjk = ink(_PROBE[0])
    if cjk <= 0:
        return False
    # .notdef 通常画成空心方框，墨水量显著低于正常汉字
    return cjk > ink("￿") * 0.5


def _pick_font():
    for p in FONT_CANDIDATES:
        if os.path.exists(p) and _can_render(p):
            print("font ->", p)
            return p
    raise SystemExit("!! 找不到能渲染中文的字体，图片会变豆腐块，已中止")


FONT_PATH = None


def font(size):
    return ImageFont.truetype(FONT_PATH, size)


def main():
    global FONT_PATH
    FONT_PATH = _pick_font()

    if os.path.exists(SRC):
        im = Image.open(SRC).convert("RGB").resize((W, H))
        im = ImageEnhance.Brightness(im).enhance(0.42)   # 压暗，保证文字可读
    else:
        im = Image.new("RGB", (W, H), (26, 26, 30))

    band = Image.new("RGBA", (W, 430), (12, 12, 16, 165))
    im = im.convert("RGBA")
    im.alpha_composite(band, (0, (H - 430) // 2))
    im = im.convert("RGB")

    d = ImageDraw.Draw(im)
    f_sm, f_big, f_md, f_tip = font(30), font(58), font(38), font(30)

    white = (255, 255, 255)
    dim = (176, 182, 194)
    accent = (255, 208, 92)
    cx = W // 2

    def center(text, y, f, fill):
        w = d.textlength(text, font=f)
        if w > W - 80:
            raise SystemExit(f"!! 文字超宽 {int(w)}px: {text}")
        d.text(((W - w) / 2, y), text, font=f, fill=fill)

    center("游戏页面", 176, f_sm, dim)
    center("indienova.com/g/heliops", 222, f_big, white)

    d.line([(cx - 300, 320), (cx + 300, 320)], fill=(90, 94, 104), width=2)

    center("免费下载", 352, f_sm, dim)
    center("pan.baidu.com/s/1wloMd9vSuZ9nq1ezJguhzA", 396, f_md, white)
    center("提取码 bkvy", 452, f_sm, accent)

    center("Windows 10/11 64 位  ·  macOS 12+（Intel / Apple 芯片）", 546, f_tip, dim)
    center("不联网 · 不付费 · 解压即玩", 592, f_tip, dim)

    im.save(OUT, "PNG", optimize=True)
    print("saved:", OUT, os.path.getsize(OUT), "bytes")


if __name__ == "__main__":
    main()
