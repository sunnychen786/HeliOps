# -*- coding: utf-8 -*-
"""Create the GitHub release for a HeliOps version and attach the zips.

Why not `gh release create`: the local git checkout is far behind the remote
(commits were pushed through the Contents API because git push is blocked by
the proxy), so gh would try to push commits first and fail.

Asset names MUST be pure ASCII. GitHub rewrites any non-ASCII byte in an
asset name to '.', which silently breaks browser_download_url (404 for
anonymous visitors). The Chinese-named zips live on the desktop; the ASCII
copies next to them are what gets uploaded.

Usage: python tools/publish_release.py <version> [--trailer <mp4>]
"""
import json
import os
import sys
import urllib.request

TOK = open("/tmp/.ghtok").read().strip()
REPO = "sunnychen786/HeliOps"
DESKTOP = os.path.expanduser("~/Desktop/游戏heliops/游戏文件/HeliOps")

ASSETS = [
    ("发行版_Windows/HeliOps_Windows_Chinese_v%s.zip", "Windows 版（双击 HeliOps.exe 直接玩）"),
    ("发行版_Mac/HeliOps_Mac_Chinese_v%s.zip", "macOS 版（双击 HeliOps.app 直接玩）"),
]

BODY = """## HeliOps v%s

单人俯视角「搜打撤」射击游戏：进入战区搜刮物资，活着走到撤离点，直升机会降落接应。

### v1.4 新增

| | |
| --- | --- |
| **自带中文字体** | 游戏里内置了一份 100 KB 的中文字体（Noto Sans SC 子集，SIL OFL 许可）。所有机器渲染完全一致，不会再因为系统缺字体而整屏方框 |
| **字体诊断日志** | 启动后在 `Documents/HeliOps/font.log` 写下这次用的哪份字体、路径、中文是否可用，报问题时把它发出来即可 |
| **自适应文字渲染** | 启动时自动检测本机显示会不会把字形糊成实心色块，一旦发现就自动换成不受影响的画法（关抗锯齿 / 预乘底色） |
| **v1.4.4 根修** | 菜单背景不再覆盖显示表面的 alpha 通道 —— 这是「整个界面变成实心色块」的真正原因（字体、字号、颜色一直都是对的，只有 alpha 被毁了）。**v1.4.4 之前的所有版本在部分 macOS 上都有这个问题，请只用 v1.4.4** |

### v1.3 新增

| | |
| --- | --- |
| **生涯战绩** | 主菜单按 `T` 查看累计击杀、撤离次数、撤离率、历史最高分 |
| **榴弹炮** | 第 5 把武器，4000 分解锁，一发 5 点伤害，弹匣 4 发 |
| **夜间作战** | 入夜后战场变暗，手电是跟随朝向的 90° 光锥，灯外一片漆黑 |

### v1.3.2 / v1.3.3 修订

- 撤离时增加直升机降落 / 升空动画，替代原来直接切菜单的硬切
- 全部菜单界面换成宣传片同款深色网格背景，标题下加统一分隔线
- 修正设置页里的失效键位说明（`5 存档` / `9 读档` 已移除）
- 修正撤离后可能卡死在关卡里的时序 bug
- v1.3.3 修过一次 Windows 中文方框（靠系统字体回退，仍不可靠）；**v1.4 改成自带字体，才算彻底解决**

### 下载

| 平台 | 说明 |
| --- | --- |
| Windows | 解压后双击 `HeliOps.exe`（10/11 64 位） |
| macOS | 解压后双击 `HeliOps.app`（12+，Intel / Apple 芯片均可） |

进度自动保存在 `Documents/HeliOps/`。有问题请到
[itch.io 页面](https://sunnychen786.itch.io/heliops) 反馈。
"""


def call(method, url, payload=None, raw=None, ctype=None):
    headers = {
        "Authorization": "token " + TOK,
        "Accept": "application/vnd.github+json",
    }
    data = payload
    if raw is not None:
        data = raw
        headers["Content-Type"] = ctype
    elif payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=300) as r:
        body = r.read()
        return json.loads(body.decode()) if body else {}


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    ver = sys.argv[1]
    trailer = None
    if "--trailer" in sys.argv:
        trailer = sys.argv[sys.argv.index("--trailer") + 1]

    tag = "v%s" % ver
    api = "https://api.github.com/repos/%s" % REPO

    # ---- release (create if missing) ----
    try:
        rel = call("GET", "%s/releases/tags/%s" % (api, tag))
        print("release exists:", rel["html_url"])
    except urllib.error.HTTPError:
        rel = call("POST", "%s/releases" % api, {
            "tag_name": tag,
            "name": "HeliOps %s" % tag,
            "body": BODY % ver,
            "draft": False,
            "prerelease": False,
        })
        print("created release:", rel["html_url"])

    upload_url = rel["upload_url"].split("{")[0]

    # ---- upload assets ----
    items = [(os.path.join(DESKTOP, p % ver), d) for p, d in ASSETS]
    if trailer:
        items.append((trailer, "宣传片（73 秒）"))

    for path, desc in items:
        if not os.path.exists(path):
            print("SKIP (missing):", path)
            continue
        name = os.path.basename(path)
        # GitHub silently rewrites non-ASCII asset names to '.', and a raw
        # non-ASCII name in the query string makes urllib raise
        # UnicodeEncodeError before the request even goes out.
        safe = "".join(c if (c.isascii() and (c.isalnum() or c in "._-")) else "_"
                       for c in name)
        if safe != name:
            print("renamed asset for ASCII safety: %s -> %s" % (name, safe))
            name = safe
        size = os.path.getsize(path)
        # skip if an asset with this name is already attached
        existing = {a["name"] for a in call("GET", "%s/releases/%d/assets" % (api, rel["id"]))}
        if name in existing:
            print("already attached:", name)
            continue
        with open(path, "rb") as fh:
            call("POST", "%s?name=%s" % (upload_url, name), raw=fh.read(),
                 ctype="application/zip" if name.endswith(".zip") else "video/mp4")
        print("uploaded %s (%.1f MB)" % (name, size / 1048576.0))

    final = call("GET", "%s/releases/tags/%s" % (api, tag))
    print("\n%s" % final["html_url"])
    for a in final["assets"]:
        print("  %-42s %6.1f MB  %s" % (a["name"], a["size"] / 1048576.0,
                                        a["browser_download_url"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
