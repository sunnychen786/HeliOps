# -*- coding: utf-8 -*-
"""Build the indienova cover (600x900) for HeliOps from a captured gameplay shot."""
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

SHOTS = "/Users/Admin/WorkBuddy/2026-05-31-19-56-04/screenshots"
SRC = os.path.join(SHOTS, "03_游戏内战斗_a.png")
OUT = os.path.join(SHOTS, "00_封面_indienova_600x900.png")

W, H = 600, 900
FONT_CJK = "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"

# --- background: widen the gameplay shot to the cover aspect, then darken it ---
bg = Image.open(SRC).convert("RGB")
# trim the in-game HUD (top) and the mission bar (bottom) before scaling up
bg = bg.crop((0, 106, bg.width, bg.height - 58))
scale = max(W / bg.width, H / bg.height)
bg = bg.resize((int(bg.width * scale + 0.5), int(bg.height * scale + 0.5)), Image.LANCZOS)
left = (bg.width - W) // 2
top = int((bg.height - H) * 0.55)          # keep the action slightly above centre
bg = bg.crop((left, top, left + W, top + H))
bg = bg.filter(ImageFilter.GaussianBlur(1.2))

overlay = Image.new("RGB", (W, H), (6, 18, 10))
bg = Image.blend(bg, overlay, 0.42)

# vertical gradient so the title and the footer stay readable
grad = Image.new("L", (1, H))
for y in range(H):
    v = 150 if y < H * 0.45 else 150 - int((y - H * 0.45) / (H * 0.55) * 120)
    grad.putpixel((0, y), max(30, v))
bg = Image.composite(bg, Image.new("RGB", (W, H), (3, 10, 6)), grad.resize((W, H)))

d = ImageDraw.Draw(bg, "RGBA")

f_title = ImageFont.truetype(FONT_CJK, 104)
f_sub = ImageFont.truetype(FONT_CJK, 34)
f_txt = ImageFont.truetype(FONT_CJK, 25)
f_small = ImageFont.truetype(FONT_CJK, 21)

def center(text, font, y, fill, shadow=(0, 0, 0, 200)):
    box = d.textbbox((0, 0), text, font=font)
    x = (W - (box[2] - box[0])) / 2 - box[0]
    d.text((x + 2, y + 3), text, font=font, fill=shadow)
    d.text((x, y), text, font=font, fill=fill)
    return box[3] - box[1]

# title
y = 96
h = center("HeliOps", f_title, y, (255, 214, 40))
y += h + 18
h = center("直升机撤离射击", f_sub, y, (245, 248, 255))
y += h + 26

# divider
d.line((W * 0.25, y, W * 0.75, y), fill=(255, 214, 40, 170), width=2)
y += 30

for line in ("搜索物资 · 击退敌军 · 活着撤离", "程序生成的像素战场 · 无内购 · 免费游玩"):
    h = center(line, f_txt, y, (222, 232, 240))
    y += h + 10

# footer band
band_top = H - 128
d.rectangle((0, band_top, W, H), fill=(0, 0, 0, 165))
y = band_top + 22
h = center("Windows / macOS · 单机 · 中文", f_txt, y, (255, 224, 90))
y += h + 12
center("独立开发者 sunnychen786", f_small, y, (200, 210, 220))

bg.save(OUT)
print("saved", OUT, bg.size)
