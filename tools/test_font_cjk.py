# -*- coding: utf-8 -*-
"""Regression test: the UI font must actually be able to draw Chinese.

The v1.3.2 Windows build shipped with every Chinese label rendered as a
tofu box. Root cause: `_get_font()` validated a candidate with
`render("Test").get_width() > 20`. On Windows no file candidate exists, and
`pygame.font.SysFont("PingFang SC")` does not fail -- it silently returns the
DEFAULT font, which renders "Test" fine. So the game accepted a font with no
CJK glyphs at all and the whole UI became boxes.

This test pins the behaviour that prevents a repeat:
  * the checker must REJECT a font without CJK glyphs
  * the checker must ACCEPT a real CJK font
  * the Windows font paths must still be in game.py
  * a simulated "no CJK font on this machine" must be detected (FONT_OK False)
    rather than silently producing boxes

game.py has no __main__ guard (importing it runs the whole game), so the font
section is extracted from the source and exec'd in a throwaway namespace.
"""
import os
import re
import sys

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "game.py")

import pygame  # noqa: E402

pygame.init()
pygame.display.set_mode((320, 240))


def load_font_section():
    """exec only the font part of game.py (no game loop, no side effects)."""
    with open(SRC, encoding="utf-8") as fh:
        src = fh.read()
    start = src.index("# Font (CJK support")
    end = src.index("FONT_OK = _font_has_cjk(font_normal)")
    end = src.index("\n", end) + 1
    ns = {"pygame": pygame, "os": os, "sys": sys, "__file__": SRC}
    # the embedded-font module (base64 copy compiled into the executable)
    try:
        sys.path.insert(0, ROOT)
        import heliops_font
        ns["heliops_font"] = heliops_font
    except Exception:
        pass
    exec(src[start:end], ns)
    return ns


NS = load_font_section()
has_cjk = NS["_font_has_cjk"]
get_font = NS["_get_font"]
bundled_path = NS["_bundled_font_path"]()

# A real CJK font on this machine, whatever it is called. The list covers
# macOS, Windows and Linux so the same test runs on the CI runner.
CJK_FONT_FILES = [
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/Library/Fonts/Arial Unicode.ttf",
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/msyhbd.ttc",
    "C:/Windows/Fonts/simhei.ttf",
    "C:/Windows/Fonts/simsun.ttc",
    "C:/Windows/Fonts/msjh.ttc",
    "C:/Windows/Fonts/Deng.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
]
real_cjk = None
for p in CJK_FONT_FILES:
    if os.path.exists(p):
        try:
            f = pygame.font.Font(p, 28)
        except Exception:
            continue
        if has_cjk(f):
            real_cjk = (p, f)
            break

results = []


def check(label, ok, detail=""):
    results.append((label, ok, detail))
    print("  %-4s %s%s" % ("PASS" if ok else "FAIL", label,
                           ("  " + detail) if detail else ""))


print("CJK font regression test")
print("-" * 60)

# 0. the font we SHIP must exist, load, and cover every character in game.py
check("the bundled font file exists",
      bool(bundled_path) and os.path.exists(bundled_path or ""),
      bundled_path or "NOT FOUND")
if bundled_path and os.path.exists(bundled_path):
    bf = pygame.font.Font(bundled_path, 28)
    check("the bundled font can draw Chinese", has_cjk(bf) is True,
          os.path.basename(bundled_path))

    with open(SRC, encoding="utf-8") as fh:
        game_src = fh.read()
    used = sorted(set(c for c in game_src if ord(c) > 0x7f))
    box = pygame.image.tostring(bf.render("\ue123", True, (255, 255, 255)), "RGBA")
    missing = [c for c in used
               if pygame.image.tostring(bf.render(c, True, (255, 255, 255)), "RGBA") == box]
    check("the bundled font covers every character the game prints",
          not missing,
          ("MISSING: %s" % "".join(missing)) if missing
          else "%d 个非 ASCII 字符全覆盖" % len(used))
else:
    check("the bundled font can draw Chinese", False, "font file missing")
    check("the bundled font covers every character the game prints", False,
          "font file missing")

# 1. the checker must reject a font with no CJK glyphs
default_font = pygame.font.SysFont(None, 28)
check("checker rejects a non-CJK font",
      has_cjk(default_font) is False,
      "SysFont(None) has no Chinese glyphs")

# 2. and accept a real CJK font
if real_cjk:
    path, f = real_cjk
    check("checker accepts a real CJK font",
          has_cjk(f) is True, os.path.basename(path))
else:
    check("checker accepts a real CJK font", False,
          "no CJK font found on this machine at all")

# 3. the machine's own pick must be CJK-capable
picked = get_font(32)
check("the font the game picks can draw Chinese",
      has_cjk(picked) is True,
      "height=%d" % picked.get_height())

# 4. the Windows paths must still be in game.py (they are the whole reason
#    the v1.3.2 build was broken)
with open(SRC, encoding="utf-8") as fh:
    text = fh.read()
need_win = ["msyh.ttc", "msyhbd.ttc", "simhei.ttf", "simsun.ttc", "msjh.ttc"]
missing = [n for n in need_win if n not in text]
check("game.py still lists the Windows CJK font files",
      not missing, ("missing: %s" % missing) if missing else
      "msyh.ttc / simhei / simsun / msjh")

# 5. the old broken validation must be gone (ignore comment lines -- the
#    explanation of the bug itself mentions the pattern)
code_only = "\n".join(l for l in text.splitlines() if not l.strip().startswith("#"))
check("the broken 'Test' width check is gone",
      'render("Test"' not in code_only and "get_width() > 20" not in code_only)

# 6. a machine with NO CJK font at all -- not even the bundled one -- must be
#    detected instead of silently shipping boxes
saved_files = list(NS["FONT_FILE_CANDIDATES"])
saved_names = list(NS["FONT_NAME_CANDIDATES"])
saved_patterns = list(NS["FONT_GLOB_PATTERNS"])
saved_globdir = NS["FONT_GLOB_DIR"]
saved_bundled = NS["BUNDLED_FONT"]
saved_module = NS.get("heliops_font")
try:
    NS["BUNDLED_FONT"] = "assets/__no_such_bundled_font__.ttf"
    NS["heliops_font"] = None      # and no embedded copy either
    NS["FONT_FILE_CANDIDATES"] = ["/definitely/not/here.ttf"]
    NS["FONT_NAME_CANDIDATES"] = ["NoSuchFontFamilyXyz"]
    NS["FONT_GLOB_PATTERNS"] = ["no_such_font_*.ttf"]
    NS["FONT_GLOB_DIR"] = "/definitely/not/here"
    fallback = get_font(32)
    check("a machine without any CJK font is detected (not silently boxed)",
          has_cjk(fallback) is False,
          "falls back to the default font and FONT_OK stays False")
finally:
    NS["FONT_FILE_CANDIDATES"] = saved_files
    NS["FONT_NAME_CANDIDATES"] = saved_names
    NS["FONT_GLOB_PATTERNS"] = saved_patterns
    NS["FONT_GLOB_DIR"] = saved_globdir
    NS["BUNDLED_FONT"] = saved_bundled
    NS["heliops_font"] = saved_module

# 6b. the font bytes embedded in the code must be restorable even when the
#     data file is unusable (antivirus / folder policy / broken unpack)
embed_path = NS.get("_font_from_embedded_bytes")
if embed_path is None or NS.get("heliops_font") is None:
    check("the embedded font copy can be restored to a file", False,
          "heliops_font module missing")
else:
    try:
        blob = embed_path()
        ok_blob = bool(blob) and os.path.exists(blob)
        if ok_blob:
            bf2 = pygame.font.Font(blob, 28)
            ok_blob = has_cjk(bf2)
        check("the embedded font copy can be restored to a file", ok_blob,
              os.path.basename(blob) if blob else "no file")
    except Exception as e:
        check("the embedded font copy can be restored to a file", False, str(e))

# 7. the bundled font must win over the system fonts -- that is the whole
#    point of shipping it
NS["FONT_SOURCE"] = "unknown"
_ = get_font(32)
check("the bundled font is preferred over system fonts",
      NS["FONT_SOURCE"] == "bundled", NS["FONT_SOURCE"])

# 8. the Windows file branch must still work when the file is there
if real_cjk:
    path, _ = real_cjk
    try:
        NS["BUNDLED_FONT"] = "assets/__no_such_bundled_font__.ttf"
        NS["FONT_FILE_CANDIDATES"] = [path]
        NS["FONT_NAME_CANDIDATES"] = ["NoSuchFontFamilyXyz"]
        NS["FONT_GLOB_PATTERNS"] = ["no_such_font_*.ttf"]
        NS["FONT_GLOB_DIR"] = "/definitely/not/here"
        via_file = get_font(32)
        check("a CJK font FILE is used even when no font name matches",
              has_cjk(via_file) is True, os.path.basename(path))
    finally:
        NS["BUNDLED_FONT"] = saved_bundled
        NS["FONT_FILE_CANDIDATES"] = saved_files
        NS["FONT_NAME_CANDIDATES"] = saved_names
        NS["FONT_GLOB_PATTERNS"] = saved_patterns
        NS["FONT_GLOB_DIR"] = saved_globdir

# 7c. the text-mode probe must exist and every fallback mode must render
#      real glyphs. On some machines the display driver blends the glyph
#      alpha as if it were a colour channel, which turns the whole text into
#      a solid bar. The game probes for that at startup and falls back to a
#      rendering mode that cannot hit the bug, so all three modes have to
#      produce readable output.
if "_probe_text_mode" not in NS or "render_text" not in NS:
    check("the text-mode probe and render_text helper exist", False,
          "missing from game.py")
else:
    check("the text-mode probe and render_text helper exist", True)

    import pygame as _pg

    def _ink(surf, color):
        px = _pg.image.tostring(surf, "RGB")
        n = len(px) // 3
        if not n:
            return 0.0
        r, g, b = color
        hit = sum(1 for i in range(0, len(px), 3)
                  if abs(px[i] - r) < 40 and abs(px[i + 1] - g) < 40
                  and abs(px[i + 2] - b) < 50)
        return hit / n

    _font = NS["font_normal"]
    _color = (240, 240, 240)
    _results = []
    for _mode in ("aa", "solid", "flat"):
        NS["TEXT_MODE"] = _mode
        try:
            _surf = NS["render_text"](_font, "HeliOps 撤离", _color)
            _test = _pg.Surface(_surf.get_size())
            _test.fill((10, 16, 28))
            _test.blit(_surf, (0, 0))
            _ratio = _ink(_test, _color)
            _results.append((_mode, _ratio))
        except Exception as _exc:
            _results.append((_mode, None))
    NS["TEXT_MODE"] = "aa"

    _bad = [m for m, r in _results if r is None or r > 0.55]
    check("every text fallback mode draws real glyphs, not a solid bar",
          not _bad,
          ("flooded: %s" % _bad) if _bad
          else "  ".join("%s=%.2f" % (m, r) for m, r in _results))

# 7d. THE alpha-channel trap. The menu backdrop used to be built with
#      .convert() plus a SRCALPHA vignette; blitting it onto the display
#      surface overwrote the display's alpha channel with 0, and every glyph
#      drawn afterwards came out as a solid coloured bar. The font was fine,
#      the colours were fine -- only the alpha was broken.
#
#      This check reproduces that exact sequence and asserts the text still
#      renders. It is the regression test for "the whole UI is a row of
#      solid blocks".
import math as _math

# The backdrop builder lives outside the font section, so pull it out of
# the source directly.
_bg_src = open(SRC, encoding="utf-8").read()
if "def _menu_backdrop_surface():" not in _bg_src:
    check("the menu backdrop builder is available for the alpha test", False,
          "missing from game.py")
    NS["_menu_backdrop_surface"] = None
else:
    _b0 = _bg_src.index("def _menu_backdrop_surface():")
    _b1 = _bg_src.index("\ndef ", _b0 + 10)
    _bg_ns = {"pygame": pygame, "math": _math, "os": os,
              "WIDTH": 1200, "HEIGHT": 800,
              "MENU_BG": (10, 16, 28), "MENU_GRID": (17, 27, 43),
              "_MENU_BACKDROP": None}
    exec(compile(_bg_src[_b0:_b1], "game.py", "exec"), _bg_ns)
    NS["_menu_backdrop_surface"] = _bg_ns["_menu_backdrop_surface"]
    check("the menu backdrop builder is available for the alpha test", True)

    _bg = NS["_menu_backdrop_surface"]()
    _masks = _bg.get_masks()

    # The backdrop must NOT carry an alpha channel. Blitting a surface that
    # has one overwrites the destination's alpha, and on a real display
    # surface (32-bit WITH alpha) that destroys every glyph drawn later.
    check("the menu backdrop has no alpha channel",
          _masks[3] == 0,
          "masks=%s (4th entry must be 0)" % (_masks,))

    # The masks alone are not enough: under the dummy SDL driver a surface
    # with an alpha channel still reports 0, so the real display driver is
    # what exposes the bug. Inspect the pixels instead -- every one of them
    # must be fully opaque.
    try:
        _bp = pygame.image.tostring(_bg, "RGBA")
        _bn = len(_bp) // 4
        _b_opaque = sum(1 for _i in range(3, len(_bp), 4)
                        if _bp[_i] == 255) / _bn if _bn else 0.0
        check("every pixel of the menu backdrop is fully opaque",
              _b_opaque > 0.99,
              "opaque=%.1f%%%s" % (100 * _b_opaque,
                                  "  <<< TRANSLUCENT BACKDROP" if _b_opaque < 0.99 else ""))
    except Exception as _exc:
        check("every pixel of the menu backdrop is fully opaque", False, str(_exc))

    # The full menu sequence, on a surface that behaves like the real
    # display: 32 bits WITH an alpha channel. The dummy SDL driver hands out
    # a 32-bit surface WITHOUT one, which is why this bug hides from a
    # headless test -- so build the alpha-carrying surface by hand.
    try:
        _screen = pygame.Surface((1200, 800), 0, 32)
        # fill with an explicit alpha: a 32-bit surface starts fully
        # transparent, and the real display surface is opaque
        _screen.fill((10, 16, 28, 255))
    except Exception as _exc:
        _screen = None
        check("text survives the menu draw order (backdrop then text)", False,
              "cannot create a surface: %s" % _exc)
    if _screen is not None:
        try:
            _font = NS["font_normal"]
            _surf = NS["render_text"](_font, "HeliOps \u64a4\u79bb", (255, 220, 60))
            _screen.fill((10, 16, 28))
            _screen.blit(_bg, (0, 0))
            _screen.blit(_surf, (20, 20))
            _pg2 = pygame
            _region = _screen.subsurface((20, 20, _surf.get_width(), _surf.get_height()))
            _px = _pg2.image.tostring(_region, "RGB")
            _n = len(_px) // 3
            _hit = sum(1 for _i in range(0, len(_px), 3)
                       if abs(_px[_i] - 255) < 45 and abs(_px[_i + 1] - 220) < 45
                       and abs(_px[_i + 2] - 60) < 55)
            _ratio = _hit / _n if _n else 0.0
            check("text survives the menu draw order (backdrop then text)",
                  _ratio < 0.55,
                  "ink=%.3f%s" % (_ratio, "  <<< SOLID BAR" if _ratio > 0.55 else ""))

            # NOTE: the "destination alpha stays 255" half of this bug can
            # only be observed on a real display surface. An off-screen
            # pygame.Surface(..., 0, 32) has no usable alpha channel at all
            # (tostring("RGBA") always reports 0), so asserting on it would
            # be a fake check. The two assertions above -- the backdrop is
            # pixel-opaque, and the text still reads -- cover the same
            # defect from the side that can be verified headlessly.
        except Exception as _exc:
            check("text survives the menu draw order (backdrop then text)", False,
                  str(_exc))

# 8b. a font living under a NON-ASCII path (Chinese Windows user name) must
#     still load -- FreeType opens font files with a narrow-character API, so
#     such a path fails on Windows and the game has to copy the file
#     somewhere ASCII-safe first.
import shutil
import tempfile

nonascii_dir = os.path.join(tempfile.gettempdir(), "\u4e2d\u6587\u76ee\u5f55", "assets")
try:
    os.makedirs(nonascii_dir, exist_ok=True)
    shutil.copy2(bundled_path, os.path.join(nonascii_dir, "HeliOps_CJK.ttf"))
    saved_b2 = NS["BUNDLED_FONT"]
    saved_log = list(NS.get("_FONT_LOG_LINES", []))
    saved_lookup = NS["_bundled_font_path"]
    try:
        NS["_bundled_font_path"] = lambda: os.path.join(nonascii_dir, "HeliOps_CJK.ttf")
        NS["_FONT_LOG_LINES"] = []
        f_non = get_font(32)
        check("a font under a non-ASCII path still loads",
              has_cjk(f_non) is True,
              "copied to an ASCII path" if any("ASCII path" in x for x in NS["_FONT_LOG_LINES"])
              else "loaded in place")
    finally:
        NS["BUNDLED_FONT"] = saved_b2
        NS["_FONT_LOG_LINES"] = saved_log
        NS["_bundled_font_path"] = saved_lookup
except Exception as e:
    check("a font under a non-ASCII path still loads", False, str(e))

# 9. the game's own Chinese UI strings must not render as boxes
if real_cjk:
    _, f = real_cjk
    strings = ["生涯战绩", "榴弹炮", "撤离成功", "补给站", "被击倒", "直升机撤离射击"]
    bad = []
    for s in strings:
        box = pygame.image.tostring(f.render("\ue123", True, (255, 255, 255)), "RGBA")
        for ch in s:
            if pygame.image.tostring(f.render(ch, True, (255, 255, 255)), "RGBA") == box:
                bad.append(ch)
                break
    check("every UI string renders real glyphs", not bad,
          ("missing: %s" % bad) if bad else " / ".join(strings[:3]) + " ...")

print("-" * 60)
passed = sum(1 for _, ok, _ in results if ok)
print("=== %d/%d checks passed ===" % (passed, len(results)))
sys.exit(0 if passed == len(results) else 1)
