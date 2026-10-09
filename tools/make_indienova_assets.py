"""生成 indienova 要求的 16:9 封面图与预览图（1280x720，<1MB）。"""
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOTS = os.path.join(ROOT, "screenshots")

W, H = 1280, 720

FONT_EN_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
FONT_EN = "/System/Library/Fonts/Supplemental/Arial.ttf"
FONT_CN_CANDIDATES = [
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
]


def cn_font(size, index=0):
    for p in FONT_CN_CANDIDATES:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size, index=index)
            except Exception:
                try:
                    return ImageFont.truetype(p, size)
                except Exception:
                    continue
    return ImageFont.load_default()


def cover_crop(src_path, w, h, zoom=1.0, x_bias=0.5, y_bias=0.5):
    """把源图裁剪成 w:h 比例。zoom>1 放大；x_bias/y_bias 控制取景中心(0~1)。"""
    im = Image.open(src_path).convert("RGB")
    target = w / h
    sw, sh = im.size
    cur = sw / sh
    if cur > target:          # 太宽 -> 裁两侧
        nw = int(sh * target / zoom)
        nh = int(sh / zoom)
    else:                     # 太高 -> 裁上下
        nw = int(sw / zoom)
        nh = int(sw / target / zoom)
    left = int((sw - nw) * x_bias)
    top = int((sh - nh) * y_bias)
    left = max(0, min(sw - nw, left))
    top = max(0, min(sh - nh, top))
    im = im.crop((left, top, left + nw, top + nh))
    return im.resize((w, h), Image.LANCZOS)


def darken(im, alpha, blur=0):
    if blur:
        im = im.filter(ImageFilter.GaussianBlur(blur))
    ov = Image.new("RGB", im.size, (0, 0, 0))
    return Image.blend(im, ov, alpha)


def vertical_gradient(size, top_a, bot_a, color=(0, 0, 0)):
    """返回一张 RGBA 竖向渐变遮罩。"""
    w, h = size
    grad = Image.new("L", (1, h))
    for y in range(h):
        grad.putpixel((0, y), int(top_a + (bot_a - top_a) * y / max(h - 1, 1)))
    grad = grad.resize((w, h))
    layer = Image.new("RGBA", (w, h), color + (0,))
    layer.putalpha(grad)
    return layer


def make_cover():
    # 用常规战斗图做底：画面里有直升机、子弹、掩体，比 Boss 图更"有内容"；
    # 取景中心右移，把左侧留给文字。
    bg = cover_crop(
        os.path.join(SHOTS, "03_游戏内战斗_a.png"), W, H, zoom=1.35, x_bias=0.58, y_bias=0.42
    )
    bg = darken(bg, 0.34)
    img = bg.convert("RGBA")

    # 左侧压暗，让文字浮出来
    left = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ld = ImageDraw.Draw(left)
    for x in range(W):
        a = int(200 * max(0.0, 1 - x / (W * 0.72)))
        ld.line([(x, 0), (x, H)], fill=(6, 10, 24, a))
    img = Image.alpha_composite(img, left)

    img = Image.alpha_composite(img, vertical_gradient((W, H), 0, 190))

    d = ImageDraw.Draw(img)

    # 主标题
    title = "HeliOps"
    ft = ImageFont.truetype(FONT_EN_BOLD, 112)
    d.text((76, 208), title, font=ft, fill=(255, 255, 255))

    # 中文副标题
    fs = cn_font(44)
    d.text((80, 344), "直升机撤离射击", font=fs, fill=(255, 214, 92))

    # 底部特性行
    ff = cn_font(27)
    feats = "撤离射击 · 四把武器 · 三个难度 · 零内购"
    d.text((80, 428), feats, font=ff, fill=(226, 232, 245))

    # 平台
    fp = ImageFont.truetype(FONT_EN, 24)
    d.text((80, 486), "WINDOWS  ·  macOS", font=fp, fill=(150, 200, 255))

    # 右下角小标签
    tag = "免费 · 单机"
    ftg = cn_font(26)
    tw = d.textlength(tag, font=ftg)
    d.rounded_rectangle(
        [W - tw - 92, H - 92, W - 40, H - 40], radius=12, fill=(255, 214, 92, 235)
    )
    d.text((W - tw - 66, H - 82), tag, font=ftg, fill=(26, 22, 10))

    out = os.path.join(SHOTS, "indienova_00_封面_1280x720.png")
    img.convert("RGB").save(out, "PNG", optimize=True)
    return out


def make_preview():
    p = os.path.join(SHOTS, "03_游戏内战斗_d.png")
    im = cover_crop(p, W, H, zoom=1.0)
    out = os.path.join(SHOTS, "indienova_01_预览_1280x720.png")
    im.save(out, "PNG", optimize=True)
    return out


if __name__ == "__main__":
    a = make_cover()
    b = make_preview()
    for f in (a, b):
        im = Image.open(f)
        print(f, im.size, f"{os.path.getsize(f)/1024:.0f} KB")
