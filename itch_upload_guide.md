# HeliOps - itch.io 发布页内容

> 复制下面各部分对应到网页表单即可。

---

## 🔴 第一步（必做）：验证邮箱

页面顶部有两个红色错误："完成您的上传时出现问题。在上传文件之前，请验证您的电子邮件地址"

操作：
1. 打开注册时用的邮箱，找到 itch.io 发的验证邮件（标题大概是 "Verify your email address"）
2. 点邮件里的验证链接
3. 验证完刷新本页面 → 红色错误消失 → 才能上传文件

---

## 📝 各字段填写内容

### 1. 标题
✅ 已填：`HeliOps - Helicopter Extraction Shooter`
（不需要改）

### 2. 项目网址（URL slug）
❌ 当前是中文：`直升机--直升机-提取-射手`
✅ **改为英文**：`heliops`

**说明**：URL slug 是项目页 URL 的一部分（最终地址会是 `https://sunnychen786.itch.io/heliops`）。
中文 slug 对国际用户来说很难记，也会让搜索分享困难。直接改成 `heliops` 最干净。

### 3. 简短的描述或标语
```
A top-down helicopter shooter with supply runs, hard/extreme modes, and a snappy extraction loop.
```

### 4. 分类
✅ 已选 `游戏 -- 一个你可以玩的软件`
（不需要改）

### 5. 项目种类
✅ 已选 `可下载 -- 您只有文件需要下载`
（不需要改）

### 6. 发布状态
建议先选 **`草稿 -- 项目仅自己可见`**（默认），填完所有内容、确认没问题后再改回 `已发布`。

### 7. 定价
✅ 已勾选 `0美元或捐赠`，默认 $2.00
（不需要改）

### 8. 上传（先验证邮箱！）

文件：`~/Desktop/HeliOps.zip`（33MB）

### 9. 详情 / 描述（粘贴下面整段到富文本框）

```markdown
## HeliOps - Helicopter Extraction Shooter

A fast-paced top-down helicopter action game: land, scavenge supplies, fight enemies, and extract before time runs out.

### How to Play
- **WASD / Arrow keys** to move your helicopter
- **Mouse** to aim and shoot
- **E** to search supply piles and extract from the zone
- **1-4** to switch weapons (Pistol / Rifle / Shotgun / Sniper)
- **B** to open shop, **ESC** to pause
- **P** to open task panel

### Features
- 4 weapons, each with distinct damage and range
- 3 difficulty modes (Normal / Hard / Extreme)
- Persistent character growth (tokens, unlocks, score)
- Boss fights with chasers and super chasers
- Procedurally placed supply piles and extraction zones
- Auto-save after every successful extraction

### Difficulty
- **Normal**: Standard challenge, learn the ropes
- **Hard**: 1.5x HP / 1.3x rewards / 1.5x spawn, unlocked by collecting Boss tokens
- **Extreme**: Stack of Hard + extra 1.4x HP, unlocked by completing all 3 hard-mode tasks

### System Requirements
- **OS**: macOS 10.13+ (Windows build coming soon)
- **Disk**: 100MB free
- **No additional dependencies** - just unzip and run

### Tips
- The extraction zone appears on your minimap - plan your route
- Boss drops sometimes contain hard-mode tokens (20% chance)
- Don't forget to extract! Death = lose everything in your backpack
- The shop (key 8) only opens between runs - sell loot there

Have fun, pilot!
```

### 10. 类型（Genre）
选 **`Action`**（动作）

### 11. 标签（最多 10 个）
```
action, shooter, top-down, helicopter, indie, singleplayer, arcade, survival, extraction, shooter
```

### 12. 人工智能生成披露
- 游戏代码：自己写的
- 美术：自己做的方块图形
- 文案：自己写的
- **答案**：选 **`否 -- 这个项目不包含生成性人工智能的输出`**

### 13. 应用商店链接
全部不选（暂时只发布在 itch.io）

### 14. 自定义名词（Custom noun）
留空（默认 "游戏" 就行）
> 如果你想改成 "Pilot" 或 "Sortie" 之类的特色词，可以填一个

### 15. 下载和安装说明（粘贴下面整段）

```markdown
### macOS
1. Download `HeliOps.zip` and unzip
2. Open `HeliOps.app` from the unzipped folder
3. If macOS blocks the app: System Settings → Privacy & Security → "Open Anyway"
4. Save files are stored in `~/Documents/HeliOps/`

### Windows
Coming soon. Currently macOS only.

### Controls reference
See the in-game tutorial (auto-shown on first launch).
```

### 16. 社区
- 暂时选 **`评论 -- 在项目页面的底部添加嵌套评论线程`**（最轻量）
- 后期流量大了再加讨论板

### 17. 可见性和访问性
最后一步填完所有内容后，**改回 `公开 -- 任何人都可以查看该页面`**，再点 "保存和查看页面"

> 第一次填表建议先 `草稿` 模式保存，确认所有内容看起来都对了再 `公开`

---

## ✅ 上传后必做

1. **保存并查看页面** → 检查游戏页面渲染是否正常
2. **试玩一次** → 用网页下载链接，验证游戏能正常打开
3. **设置封面图**（630×500 推荐）→ 做一个 16:10 截屏或宣传图
4. **加截图**（强烈推荐 3-5 张）→ 游戏内不同场景的截图，能大幅提升转化率
5. **分享到社交平台** → Twitter / Reddit r/indiegaming / 小红书

## 📊 后续跟踪

- 第一周：观察下载量、评论反馈
- 一个月后：根据玩家反馈做 v1.1 补丁
- 出 Windows 版：用 GitHub Actions 自动构建（之前的发布指南里有详细步骤）
