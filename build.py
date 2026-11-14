#!/usr/bin/env python3
"""PyInstaller build script - HeliOps
Usage:
    python3 build.py          # Build for current platform
    python3 build.py --clean  # Clean and rebuild

Output:
    dist/HeliOps.app     (macOS app bundle)
    dist/HeliOps          (macOS executable)
    dist/HeliOps.zip      (auto-generated release package)
"""

import os
import sys
import shutil
import subprocess
import zipfile
import glob
import re

GAME_NAME = "HeliOps"
GAME_SCRIPT = "game.py"
WORK_DIR     = os.path.dirname(os.path.abspath(__file__))


def _game_version():
    """Read GAME_VERSION from game.py so the README can never lag the build."""
    with open(os.path.join(WORK_DIR, GAME_SCRIPT), encoding="utf-8") as fh:
        m = re.search(r'^GAME_VERSION\s*=\s*["\']([\d.]+)["\']', fh.read(), re.M)
    return m.group(1) if m else "0.0.0"


GAME_VERSION = _game_version()

# ---- 清理 ----
if "--clean" in sys.argv:
    for d in ["build_work", "build_cache", "dist", "__pycache__", f"{GAME_NAME}.spec"]:
        path = os.path.join(WORK_DIR, d)
        if os.path.exists(path):
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
            print(f"  Cleaned: {d}")
    print("Clean complete.\n")

# ---- 构建 ----
is_mac = sys.platform == "darwin"
is_win = sys.platform == "win32"

# Use `python -m PyInstaller` for cross-platform compatibility
# (avoids pyinstaller binary path issues on Windows where it lands in Scripts/)
cmd = [
    sys.executable, "-m", "PyInstaller",
    "--onedir" if is_mac else "--onefile",   # macOS 用 onedir（app bundle），Windows 用 onefile
    "--windowed",
    "--name", GAME_NAME,
    "--noconfirm",
    "--workpath", os.path.join(WORK_DIR, "build_work"),
    "--specpath", WORK_DIR,
    "--distpath", os.path.join(WORK_DIR, "dist"),
    "--hidden-import", "pygame",
    "--hidden-import", "pygame.pkgdata",
    "--exclude-module", "numpy",
    "--exclude-module", "PIL",
    "--exclude-module", "tkinter",
    "--exclude-module", "pandas",
    GAME_SCRIPT,
]
# --clean makes PyInstaller rmtree its bincache (~100 files), which trips the
# sandbox's bulk-delete guard and aborts the build. The cache is content-hashed
# anyway, so skipping it is safe; set HELIOPS_CLEAN=1 to force the wipe.
if os.environ.get("HELIOPS_CLEAN") == "1":
    cmd.insert(6, "--clean")

if is_mac:
    cmd.extend(["--hidden-import", "pygame._macosx"])

# ---- 把内嵌中文字体打进包里 ----
# v1.4 起游戏自带 assets/HeliOps_CJK.ttf。没有它，Windows 上所有中文会变成
# 方框（系统里不一定有能用的中文字体）。必须用 --add-data 一起打进去，
# 运行时 game.py 会从 sys._MEIPASS 找它。
# NOTE: use ABSOLUTE source paths -- PyInstaller resolves a relative
# --add-data against --specpath, not against the working directory.
FONT_ASSET = os.path.join(WORK_DIR, "assets", "HeliOps_CJK.ttf")
if os.path.exists(FONT_ASSET):
    cmd.extend(["--add-data", "%s%sassets" % (FONT_ASSET, os.pathsep)])
    print("Bundling font: %s" % FONT_ASSET)
else:
    print("[WARN] %s not found -- the build will rely on system fonts!" % FONT_ASSET)

# The font is a subset of Noto Sans SC under the SIL OFL: ship the licence
# text with it.
OFL_ASSET = os.path.join(WORK_DIR, "assets", "OFL.txt")
if os.path.exists(OFL_ASSET):
    cmd.extend(["--add-data", "%s%sassets" % (OFL_ASSET, os.pathsep)])

if is_mac:
    cmd.extend(["--osx-bundle-identifier", "com.heliops.game"])
    env = os.environ.copy()
    env["PYINSTALLER_CONFIG_DIR"] = os.path.join(WORK_DIR, "build_cache")
else:
    env = None

print(f"Building {GAME_NAME}...")
print(f"Platform: macOS" if is_mac else f"Platform: {sys.platform}")

result = subprocess.run(cmd, cwd=WORK_DIR, env=env)

if result.returncode != 0:
    print("\n[FAIL] Build failed!")
    sys.exit(1)

# ---- 打包成 ZIP ----
dist_dir = os.path.join(WORK_DIR, "dist")
if is_mac:
    app_path = os.path.join(dist_dir, f"{GAME_NAME}.app")
    exe_path = os.path.join(dist_dir, GAME_NAME)
else:
    app_path = None
    exe_path = os.path.join(dist_dir, f"{GAME_NAME}.exe")

# 判断实际存在的产物
has_app = app_path and os.path.exists(app_path)
# On macOS PyInstaller emits BOTH dist/HeliOps.app and the raw dist/HeliOps/
# onedir it was wrapped from. Zipping both shipped every dylib twice and the
# release ballooned from 16 MB to 34 MB, so the loose folder is skipped: the
# .app bundle already contains it.
has_exe = (not is_mac) and os.path.exists(exe_path)

if has_app:
    size_mb = sum(
        os.path.getsize(os.path.join(root, f))
        for root, _, files in os.walk(app_path)
        for f in files
    ) / (1024 * 1024)
    print(f"\n[OK] Build successful!")
    print(f"   .app: {app_path}")
    print(f"   Size: {size_mb:.1f} MB")
elif has_exe:
    size_mb = os.path.getsize(exe_path) / (1024 * 1024)
    print(f"\n[OK] Build successful! (exe)")
    print(f"   Executable: {exe_path}")
    print(f"   Size: {size_mb:.1f} MB")

# Create ZIP release package
#
# macOS is handled by tools/package_mac.py, not here. Two reasons:
#   * A .app is full of symlinks (85 in this build: Resources/libpython3.13.dylib
#     -> ../Frameworks/..., Frameworks/libSDL2 -> pygame/.dylibs/...). zipfile
#     *follows* them and stores the target's bytes under every link name, so
#     libpython was packed twice and the archive came out 34 MB instead of 16 MB.
#   * ditto preserves both the links and the mode bits a bundle needs to launch.
# Windows has a single exe, so zipfile is fine there.
zip_path = os.path.join(dist_dir, f"{GAME_NAME}.zip")
if has_app:
    print(f"   (macOS: skipping zipfile — run tools/package_mac.py for the release zip)")
else:
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        if has_exe:
            an = os.path.relpath(exe_path, dist_dir)
            zf.write(exe_path, an)

    zip_mb = os.path.getsize(zip_path) / (1024 * 1024)
    print(f"   ZIP: {zip_path} ({zip_mb:.1f} MB)")
    # No copy to ~/Desktop/游戏文件/ any more: that folder predates the
    # 发行版_Mac / 发行版_Windows convention and only collected stale builds.

# Create README
readme_path = os.path.join(dist_dir, "README.txt")
# The old text here was three versions stale: it called the player a
# helicopter, told you to "fly" to the pad, and listed 5 = 存档 / 9 = 读档,
# which now collide with the grenade cannon slot and do nothing at all.
README_TEXT = """HeliOps - 直升机撤离射击（中文版）v%s
========================================

如何启动：
  Windows: 双击 "HeliOps.exe"
  macOS:   双击 "HeliOps.app"

操作说明（战斗中）：
  WASD / 方向键    - 移动角色
  空格             - 射击（自动瞄准最近敌人）
  J                - 搜索物资（靠近物资按住约 1.5 秒）
  1-5              - 切换武器（手枪 / 步枪 / 霰弹枪 / 狙击枪 / 榴弹炮）
  R                - 换弹（换弹过程中无法射击）
  P 或 ESC         - 暂停

主菜单：
  Enter            - 出发
  T                - 生涯战绩
  S                - 设置
  8                - 补给站（买枪 / 回血 / 补弹）
  D                - 切换难度（普通 → 困难 → 极难）
  P                - 任务栏
  ESC              - 返回 / Q - 退出

游戏目标：
  你是地面士兵。在战区搜索物资，走到黄色撤离点停留 3 秒，
  直升机会降落接应。撤离后物资按倍率结算得分，
  可在补给站购买装备。被击倒则本局物资全部丢失。

存档位置：
  Windows: %%USERPROFILE%%/Documents/HeliOps/
  macOS:   ~/Documents/HeliOps/

需要帮助？访问：https://sunnychen786.itch.io/heliops
"""

with open(readme_path, 'w', encoding='utf-8-sig', newline='\r\n') as f:
    f.write(README_TEXT % GAME_VERSION)

print(f"\n[DONE] Release package ready!")
print(f"   dist/ contents:")
print(f"   - {GAME_NAME}.app      (macOS app)")
print(f"   - {GAME_NAME}.zip      (release package)")
print(f"   - README.txt           (readme)")
print(f"\nTip: Upload {GAME_NAME}.zip to itch.io to publish!")
