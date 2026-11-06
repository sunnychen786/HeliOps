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
    ns = {"pygame": pygame, "os": os}
    exec(src[start:end], ns)
    return ns


NS = load_font_section()
has_cjk = NS["_font_has_cjk"]
get_font = NS["_get_font"]

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

# 6. a simulated machine with no CJK font at all must be detected
saved_files = list(NS["FONT_FILE_CANDIDATES"])
saved_names = list(NS["FONT_NAME_CANDIDATES"])
saved_patterns = list(NS["FONT_GLOB_PATTERNS"])
saved_globdir = NS["FONT_GLOB_DIR"]
try:
    NS["FONT_FILE_CANDIDATES"] = ["/definitely/not/here.ttf"]
    NS["FONT_NAME_CANDIDATES"] = ["NoSuchFontFamilyXyz"]
    NS["FONT_GLOB_PATTERNS"] = ["no_such_font_*.ttf"]
    NS["FONT_GLOB_DIR"] = "/definitely/not/here"
    fallback = get_font(32)
    check("a machine without CJK fonts is detected (not silently boxed)",
          has_cjk(fallback) is False,
          "falls back to the default font and FONT_OK stays False")
finally:
    NS["FONT_FILE_CANDIDATES"] = saved_files
    NS["FONT_NAME_CANDIDATES"] = saved_names
    NS["FONT_GLOB_PATTERNS"] = saved_patterns
    NS["FONT_GLOB_DIR"] = saved_globdir

# 7. the Windows file branch must actually work when the file is there
if real_cjk:
    path, _ = real_cjk
    try:
        NS["FONT_FILE_CANDIDATES"] = [path]
        NS["FONT_NAME_CANDIDATES"] = ["NoSuchFontFamilyXyz"]
        NS["FONT_GLOB_PATTERNS"] = ["no_such_font_*.ttf"]
        NS["FONT_GLOB_DIR"] = "/definitely/not/here"
        via_file = get_font(32)
        check("a CJK font FILE is used even when no font name matches",
              has_cjk(via_file) is True, os.path.basename(path))
    finally:
        NS["FONT_FILE_CANDIDATES"] = saved_files
        NS["FONT_NAME_CANDIDATES"] = saved_names
        NS["FONT_GLOB_PATTERNS"] = saved_patterns
        NS["FONT_GLOB_DIR"] = saved_globdir

# 8. the game's own Chinese UI strings must not render as boxes
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
