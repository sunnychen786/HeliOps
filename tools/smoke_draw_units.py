# -*- coding: utf-8 -*-
"""冒烟测试：强制调用全部角色绘制函数，确认 v1.2 精灵改造后没有 NameError。
game.py 没有 main guard，所以钩住第一帧 display.flip 来跑我们的代码。
"""
import os
import sys
import shutil

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
FRESH = "/tmp/heliops_draw_test_home"
shutil.rmtree(FRESH, ignore_errors=True)
os.makedirs(FRESH, exist_ok=True)
os.environ["HOME"] = FRESH

GAME_DIR = "/Users/Admin/WorkBuddy/2026-05-31-19-56-04"
sys.path.insert(0, GAME_DIR)

import pygame  # noqa: E402

done = [False]
report = []


def hook():
    if done[0]:
        return
    done[0] = True
    try:
        G = sys.modules["game"]
        # 每个单位都用全部朝向 + 两帧画一遍
        for unit in ("player", "enemy", "chaser", "super", "boss"):
            for pose in ("front", "side", "back"):
                for fr in (0, 1):
                    G.get_sprite(unit, pose, fr)
        # 直接调用绘制函数（会走到像素精灵 + 叠加层）
        G.draw_player(400.0, 400.0)
        G.draw_enemy(300.0, 300.0, "patrol")
        G.draw_enemy(320.0, 300.0, "alert")
        G.draw_enemy(340.0, 300.0, "chase")
        G.draw_enemy(360.0, 300.0, "tired")
        G.draw_boss([500.0, 380.0, 18, None, None, 24])
        G.draw_chaser([520.0, 420.0, 7, True])
        G.draw_chaser([540.0, 420.0, 7, False])
        G.draw_super_chaser([560.0, 460.0, True])
        G.draw_super_chaser([580.0, 460.0, False])
        report.append("OK: 全部绘制函数调用成功")
    except Exception as e:
        import traceback
        report.append("FAIL: " + repr(e))
        report.append(traceback.format_exc())
    finally:
        pygame.quit()


pygame.display.flip = hook

try:
    import game  # noqa: F401  运行即进入主循环，第一帧被 hook 拦下
except SystemExit:
    pass
except Exception as e:
    report.append("外层异常: %r" % (e,))

print("\n".join(report) if report else "!! hook 未被触发")
