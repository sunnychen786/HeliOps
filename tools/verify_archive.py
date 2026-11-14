# -*- coding: utf-8 -*-
"""Verify a built PyInstaller binary actually contains the expected build.

Pulls the embedded `game` module out of the CArchive, marshal-loads it and
walks every string/name constant (co_consts AND co_names - names live in
co_names, and CPython stores literal tables as tuple-of-tuples) looking for
the markers of the current version.

Usage: python tools/verify_archive.py [path-to-HeliOps-binary]
Default: dist/HeliOps.app/Contents/MacOS/HeliOps

Original docstring:

Walks the CArchive -> PYZ -> marshal code object and searches every string
constant (including nested tuples, because CPython stores literal tables as
tuple-of-tuples) for the markers we expect in the shipped build.
"""
import io
import marshal
import os
import re
import sys

from PyInstaller.archive.readers import CArchiveReader
from PyInstaller.loader.pyimod01_archive import ZlibArchiveReader

EXE = sys.argv[1] if len(sys.argv) > 1 else "dist/HeliOps.app/Contents/MacOS/HeliOps"


def current_version():
    """Read GAME_VERSION out of game.py instead of hard-coding it here.

    The hard-coded marker silently passed stale builds: every bump meant
    editing this file too, and forgetting it made the check meaningless.
    """
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(here, "game.py"), encoding="utf-8") as fh:
        m = re.search(r'^GAME_VERSION\s*=\s*["\']([\d.]+)["\']', fh.read(), re.M)
    return m.group(1) if m else "0.0.0"


VERSION = current_version()

MUST_HAVE = [VERSION, "榴弹炮", "生涯战绩", "夜晚", "黄昏", "roll_time_of_day",
             "tally_run", "player_invuln", "GUN_ORDER", "_torch_masks",
             "NIGHT_DARK_ALPHA", "NIGHT_LIT_ALPHA", "BLEND_RGBA_SUB",
             "BLEND_RGBA_MAX", "进度自动保存",
             # v1.3.2: helicopter cinematic + the trailer's dark grid menus
             "draw_extract_lift", "extract_lift_pos", "MENU_ACCENT",
             "draw_menu_backdrop",
             # v1.3.3: the Windows font fix. Without these markers the build
             # still renders every Chinese label as a tofu box.
             "_font_has_cjk", "FONT_OK", "msyh.ttc", "FONT_FILE_CANDIDATES",
             # v1.4: the game ships its own CJK font
             "BUNDLED_FONT", "HeliOps_CJK.ttf", "_bundled_font_path",
             "FONT_SOURCE"]
# `_NIGHT_LAYER` was the v1.3.0 "pour white light onto black" implementation;
# v1.3.1 punches a hole in the darkness sheet instead.
# `render("Test")` was the broken font check that shipped v1.3.2's Windows
# build -- it accepts pygame's default font, which has no CJK glyphs.
MUST_NOT_HAVE = ["1.2.3", "1.3.1", "1.3.2", "_NIGHT_LAYER",
                 'render("Test")']


def walk_strings(code, out):
    out.update(code.co_names)
    for c in code.co_consts:
        if isinstance(c, str):
            out.add(c)
        elif isinstance(c, tuple):
            for sub in c:
                if isinstance(sub, str):
                    out.add(sub)
                elif hasattr(sub, "co_consts"):
                    walk_strings(sub, out)
        elif hasattr(c, "co_consts"):
            walk_strings(c, out)


arch = CArchiveReader(EXE)
print("archive entries:", [e[0] for e in arch.toc])

raw = arch.extract("game")      # already marshalled bytes for the main script
code = marshal.loads(raw)

strings = set()
walk_strings(code, strings)

def has(needle):
    """Substring match: names appear as `_night_vision`, f-strings keep their
    literal text whole, so an exact set membership test is too strict."""
    return any(needle in x for x in strings)


print("\n-- must be present --")
ok = True
for s in MUST_HAVE:
    hit = has(s)
    ok &= hit
    print("  %-18s %s" % (s, "OK" if hit else "MISSING"))
print("-- must be absent --")
for s in MUST_NOT_HAVE:
    hit = has(s)
    ok &= (not hit)
    print("  %-18s %s" % (s, "present (BAD)" if hit else "absent OK"))

# ---- the CJK font must actually travel with the build ----
# Without assets/HeliOps_CJK.ttf the game falls back to whatever font the
# player's machine has, and on Windows that is a font with no Chinese glyphs
# -> every label renders as a tofu box.
#
# NB: `arch.toc` is a dict -- iterating it yields the KEYS, so `[e[0] for e in
# toc]` silently gives the first character of every name. Use the keys.
entries = list(arch.toc.keys())
in_archive = any(n.replace("\\", "/").endswith("HeliOps_CJK.ttf") for n in entries)

in_bundle = False
exe_path = os.path.abspath(EXE)
if os.sep + "Contents" + os.sep + "MacOS" + os.sep in exe_path:
    # a macOS .app: the payload lives in Contents/Frameworks and the data
    # files in Contents/Resources -- both above the executable
    app_root = exe_path.split(os.sep + "Contents" + os.sep)[0]
    for root, _dirs, files in os.walk(app_root):
        if "HeliOps_CJK.ttf" in files:
            in_bundle = True
            break

font_ok = in_archive or in_bundle
ok &= font_ok
print("-- packaging --")
print("  %-18s %s" % ("CJK font",
                      "OK (in archive)" if in_archive else
                      ("OK (in bundle)" if in_bundle else "MISSING!")))
print("     (a build without the bundled font shows Chinese as boxes on Windows)")

print("\nRESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
