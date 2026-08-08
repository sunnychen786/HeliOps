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

GAME_NAME = "HeliOps"
GAME_SCRIPT = "game.py"
WORK_DIR     = os.path.dirname(os.path.abspath(__file__))

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
    "--clean",
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

if is_mac:
    cmd.extend(["--hidden-import", "pygame._macosx"])

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
    print("\n❌ 打包失败！")
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
has_exe = os.path.exists(exe_path)

if has_app:
    size_mb = sum(
        os.path.getsize(os.path.join(root, f))
        for root, _, files in os.walk(app_path)
        for f in files
    ) / (1024 * 1024)
    print(f"\n✅ Build successful!")
    print(f"   .app: {app_path}")
    print(f"   Size: {size_mb:.1f} MB")
elif has_exe:
    size_mb = os.path.getsize(exe_path) / (1024 * 1024)
    print(f"\n✅ 打包成功！")
    print(f"   可执行文件: {exe_path}")
    print(f"   Size: {size_mb:.1f} MB")

# Create ZIP release package
zip_path = os.path.join(dist_dir, f"{GAME_NAME}.zip")
with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
    if has_app:
        for root, _, files in os.walk(app_path):
            for f in files:
                fp = os.path.join(root, f)
                an = os.path.relpath(fp, dist_dir)
                zf.write(fp, an)
    if has_exe:
        an = os.path.relpath(exe_path, dist_dir)
        zf.write(exe_path, an)

zip_mb = os.path.getsize(zip_path) / (1024 * 1024)
print(f"   ZIP: {zip_path} ({zip_mb:.1f} MB)")

# ---- 复制到发布路径 (本地 macOS 开发环境才做) ----
RELEASE_ZIP_PATH = os.path.join(os.path.expanduser("~"), "Desktop", "游戏文件", "HeliOps.zip（v1.1).zip")
in_ci = os.environ.get("CI") == "true"
if not in_ci:
    try:
        os.makedirs(os.path.dirname(RELEASE_ZIP_PATH), exist_ok=True)
        shutil.copy2(zip_path, RELEASE_ZIP_PATH)
        release_mb = os.path.getsize(RELEASE_ZIP_PATH) / (1024 * 1024)
        print(f"   Release: {RELEASE_ZIP_PATH} ({release_mb:.1f} MB)")
    except Exception as e:
        print(f"   ⚠️  Copy to release path failed: {e}")
else:
    print(f"   (CI environment - skip Desktop copy)")

# Create README
readme_path = os.path.join(dist_dir, "README.txt")
with open(readme_path, 'w') as f:
    f.write("""HeliOps - Helicopter Extraction Shooter
========================================

How to launch:
  Windows: Double-click "HeliOps.exe"
  macOS:   Double-click "HeliOps.app"

Controls:
  WASD/Arrow Keys - Move
  Mouse            - Aim
  Left Click       - Shoot
  R                - Reload
  E                - Interact / Search
  Shift            - Call Extraction
  ESC              - Pause
  1-4              - Switch Weapons

Save file location:
  Windows: %USERPROFILE%/Documents/HeliOps/
  macOS:   ~/Documents/HeliOps/

Need help? Visit: https://sunnychen786.itch.io/heliops
""")

print(f"\n📦 Release package ready!")
print(f"   dist/ contents:")
print(f"   - {GAME_NAME}.app      (macOS app)")
print(f"   - {GAME_NAME}.zip      (release package)")
print(f"   - README.txt           (readme)")
print(f"\n💡 Tip: Upload {GAME_NAME}.zip to itch.io to publish!")
