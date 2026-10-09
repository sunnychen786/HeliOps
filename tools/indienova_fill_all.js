// indienova 游戏条目批量填写（按分区表单 action 精确定位）
// 用法: node tools/indienova_fill_all.js <stage>
//   stage: intro | platform | gallery | demo | feature | links | support | all
const { chromium } = require("playwright-core");
const path = require("path");

const ROOT = path.dirname(__dirname);
const SHOTS = path.join(ROOT, "screenshots");

const BAIDU_URL = "https://pan.baidu.com/s/1wloMd9vSuZ9nq1ezJguhzA";
const BAIDU_CODE = "bkvy";

const GALLERY = [
  "03_游戏内战斗_d.png",
  "03_游戏内战斗_a.png",
  "07_补给站商店.png",
  "05_任务面板.png",
  "02_新手教程.png",
];

const BRIEF =
  "<p>单机俯视角直升机撤离射击：驾驶直升机进入战区，搜集物资、装备武器，在敌人与 Boss 的围追堵截中坚持到撤离点，" +
  "把战利品安全带出战区并强化装备。战场布局与音效全部程序生成，支持 Windows 与 macOS，免费无内购。</p>";

const BIG = [
  "<h3>关于这款游戏</h3>",
  "<p>《HeliOps》是一款俯视角的直升机撤离射击游戏，一个人玩也很紧张。你驾驶直升机进入战区，在有限的时间里搜索补给箱、捡到武器、清掉挡路的敌人，然后赶到撤离点把东西带出去。带出去的战利品会变成分数，用来换取更强的装备——但一旦在战区里被击落，这一趟就白跑了。</p>",
  "<h3>玩法</h3>",
  "<ul>",
  "<li><b>移动</b>：WASD 或方向键飞行，直升机有惯性，转向和刹车都要留提前量。</li>",
  "<li><b>射击</b>：按住空格自动瞄准最近的敌人开火，专心走位即可。</li>",
  "<li><b>搜索</b>：靠近补给箱按 J 搜索，能拿到弹药、护盾和武器。</li>",
  "<li><b>撤离</b>：在黄色撤离点停留 3 秒完成撤离，成功撤离后结算并自动存档。</li>",
  "<li><b>其它</b>：数字键 1-4 或 Tab／滚轮切换武器，8 打开补给站商店，P 查看任务面板，ESC 暂停。</li>",
  "</ul>",
  "<h3>游戏特色</h3>",
  "<ul>",
  "<li><b>四种武器各有取舍</b>：手枪均衡、步枪射速快但后坐明显、霰弹近距爆发、狙击单发高伤但节奏慢。</li>",
  "<li><b>三个难度</b>：普通、困难、极难；困难以上需用 Boss 掉落的令牌解锁，越难奖励越高。</li>",
  "<li><b>程序生成的战场</b>：每次进入战区，掩体布局与物资位置都不相同。</li>",
  "<li><b>持续成长</b>：撤离带出的分数可以买装备，角色一点点变强，再去挑战更难的局。</li>",
  "<li><b>零内购、纯单机</b>：不需要联网，不额外收费。</li>",
  "</ul>",
  "<h3>运行与下载</h3>",
  "<p>游戏解压即玩：Windows 版运行 <b>HeliOps.exe</b>，macOS 版运行 <b>HeliOps.app</b>。下载地址见页面下方的「Demo 下载」区块。</p>",
].join("");

const FEATURES = [
  { icon: "star2", text: "撤离射击玩法：搜集物资、装备武器，活着走到撤离点才算数" },
  { icon: "heart2", text: "四种武器各有取舍：手枪 / 步枪 / 霰弹 / 狙击，手感完全不同" },
  { icon: "cloud2", text: "程序生成的战场：每次进入，掩体布局与物资位置都不一样" },
  { icon: "diamond2", text: "零内购、纯单机：不联网、不付费，解压即玩" },
];

const LINKS = [
  { title: "百度网盘下载（提取码 bkvy）", url: BAIDU_URL },
  { title: "源代码仓库（GitHub）", url: "https://github.com/sunnychen786/HeliOps" },
];

const DEMOS = [
  {
    version: "v1.1 中文版 · Windows 10/11（64 位）",
    link: `${BAIDU_URL} 提取码：${BAIDU_CODE}`,
  },
  {
    version: "v1.1 中文版 · macOS 12+（Intel / Apple 芯片）",
    link: `${BAIDU_URL} 提取码：${BAIDU_CODE}`,
  },
];

const STAGE = process.argv[2] || "all";

// ---------- 工具 ----------
async function openEdit(page) {
  await page.goto("https://indienova.com/home/editgame/heliops", {
    waitUntil: "domcontentloaded",
    timeout: 60000,
  });
  await page.waitForTimeout(3000);
}

async function expand(page, title) {
  // 编辑页每个分区是 <div class="acctitle">标题</div> + <div class="acc_content">内容</div>。
  // 注意：分区内部也可能存在同名 <h3>（隐藏），所以必须只认 .acctitle，
  // 并且仅在内容收起时才点击（重复点击会把它关掉）。
  const r = await page.evaluate((t) => {
    const titles = [...document.querySelectorAll(".acctitle")].filter((e) =>
      (e.innerText || "").replace(/\s+/g, " ").trim().startsWith(t)
    );
    const el = titles[0];
    if (!el) return "no-title";
    const content = el.nextElementSibling?.classList?.contains("acc_content")
      ? el.nextElementSibling
      : el.parentElement?.querySelector(".acc_content");
    const open = content ? !!content.offsetParent : false;
    if (!open) el.click();
    return (open ? "already-open" : "clicked") + "|" + (content ? content.className : "no-content");
  }, title);
  await page.waitForTimeout(2000);
  return r;
}

const form = (page, suffix) => page.locator(`form[action$="/action/${suffix}"]`);

async function clickBtn(page, suffix, re) {
  const f = form(page, suffix);
  const btns = f.locator('button, input[type="submit"]');
  const n = await btns.count();
  for (let i = 0; i < n; i++) {
    const t = ((await btns.nth(i).inputValue().catch(() => "")) || (await btns.nth(i).innerText().catch(() => ""))).trim();
    if (re.test(t)) {
      await btns.nth(i).click({ force: true });
      return t;
    }
  }
  return null;
}

// ---------- 各阶段 ----------
async function stageIntro(page) {
  await expand(page, "游戏介绍");
  const editors = page.locator(".froala-element[contenteditable='true']");
  console.log("  editors:", await editors.count());

  const put = async (idx, html, id) => {
    const ed = editors.nth(idx);
    await ed.scrollIntoViewIfNeeded().catch(() => {});
    await ed.click({ force: true }).catch(() => {});
    await page.keyboard.press("Meta+A").catch(() => {});
    await page.keyboard.press("Delete").catch(() => {});
    await ed.evaluate((e, h) => {
      e.innerHTML = h;
      e.dispatchEvent(new Event("input", { bubbles: true }));
      e.dispatchEvent(new Event("keyup", { bubbles: true }));
    }, html);
    await page.evaluate(
      ({ h, i }) => {
        const t = document.getElementById(i);
        if (t) {
          t.value = h;
          t.dispatchEvent(new Event("input", { bubbles: true }));
        }
      },
      { h: html, i: id }
    );
  };
  await put(0, BRIEF, "briefIntro");
  await put(1, BIG, "bigIntro");
  const btn = await clickBtn(page, "detail", /提交游戏介绍|提交更改/);
  console.log("  submit:", btn);
  await page.waitForTimeout(6000);
}

async function stagePlatform(page) {
  await expand(page, "运行平台");
  const vals = await page.evaluate(() => {
    const f = document.querySelector('form[action$="/action/platform"]');
    return [...f.querySelectorAll('input[name="gamePlatforms[]"]')].map((c) => ({
      v: c.value,
      label: (c.closest("label")?.innerText || "").trim(),
      checked: c.checked,
    }));
  });
  console.log("  platforms:", JSON.stringify(vals.filter((x) => /win|mac|linux/i.test(x.label))));
  // 确保只勾 Windows / Mac
  await page.evaluate(() => {
    const f = document.querySelector('form[action$="/action/platform"]');
    for (const c of f.querySelectorAll('input[name="gamePlatforms[]"]')) {
      const lab = (c.closest("label")?.innerText || "").trim();
      const want = /^(Windows|Mac)$/i.test(lab);
      c.checked = want;
      const l = c.closest("label");
      if (l) l.classList.toggle("active", want);
    }
  });
  const btn = await clickBtn(page, "platform", /更改支持的平台|提交/);
  console.log("  submit:", btn);
  await page.waitForTimeout(5000);
}

async function stageSupport(page) {
  await expand(page, "辅助信息");
  await page.evaluate(() => {
    const set = (id, v) => {
      const e = document.getElementById(id);
      if (e) {
        e.value = v;
        e.dispatchEvent(new Event("input", { bubbles: true }));
      }
    };
    set("gameVersion", "v1.1");
    set("gamePrice", "免费");
    set("gamePercent", "100");
  });
  const btn = await clickBtn(page, "support", /提交更改|提交/);
  console.log("  submit:", btn);
  await page.waitForTimeout(5000);
}

async function stageGallery(page) {
  await expand(page, "游戏截图画面");
  for (const file of GALLERY) {
    const p = path.join(SHOTS, file);
    // 点「添加一个」新增一行上传框
    const added = await clickBtn(page, "image", /添加一个|添加图片/);
    await page.waitForTimeout(1200);
    const files = form(page, "image").locator('input[type="file"]');
    const cnt = await files.count();
    await files.nth(cnt - 1).setInputFiles(p);
    await page.waitForTimeout(2000);
    const up = await clickBtn(page, "image", /提交图片|提交/);
    console.log(`  ${file}  add=${added} inputs=${cnt} upload=${up}`);
    await page.waitForTimeout(4500);
  }
}

async function stageDemo(page) {
  await expand(page, "Demo 下载");
  for (const d of DEMOS) {
    const added = await clickBtn(page, "demo", /添加 Demo 信息|添加/);
    await page.waitForTimeout(1200);
    const res = await page.evaluate((row) => {
      const f = document.querySelector('form[action$="/action/demo"]');
      const vs = f.querySelectorAll('input[name="demo[]"]');
      const ls = f.querySelectorAll('input[name="demo_link[]"]');
      const v = vs[vs.length - 1];
      const l = ls[ls.length - 1];
      if (!v || !l) return "no-fields";
      v.value = row.version;
      v.dispatchEvent(new Event("input", { bubbles: true }));
      l.value = row.link;
      l.dispatchEvent(new Event("input", { bubbles: true }));
      return "filled";
    }, d);
    const up = await clickBtn(page, "demo", /提交 Demo 信息|提交/);
    console.log(`  ${d.version.slice(0, 24)}  add=${added} ${res} upload=${up}`);
    await page.waitForTimeout(4500);
  }
}

async function stageFeature(page) {
  await expand(page, "游戏特色");
  for (const f of FEATURES) {
    const added = await clickBtn(page, "feature", /添加一个|添加/);
    await page.waitForTimeout(1000);
    const res = await page.evaluate((row) => {
      const fm = document.querySelector('form[action$="/action/feature"]');
      const icons = fm.querySelectorAll('select[name="feature_icon[]"]');
      const texts = fm.querySelectorAll('input[name="feature[]"]');
      const ic = icons[icons.length - 1];
      const tx = texts[texts.length - 1];
      if (!ic || !tx) return "no-fields";
      ic.value = row.icon;
      ic.dispatchEvent(new Event("change", { bubbles: true }));
      const jq = window.jQuery;
      if (jq && jq(ic).selectpicker) jq(ic).selectpicker("refresh");
      tx.value = row.text;
      tx.dispatchEvent(new Event("input", { bubbles: true }));
      return ic.value + "|" + tx.value.slice(0, 12);
    }, f);
    console.log(`  ${f.text.slice(0, 16)}  add=${added} ${res}`);
    await page.waitForTimeout(600);
  }
  const btn = await clickBtn(page, "feature", /提交游戏特色|提交/);
  console.log("  submit:", btn);
  await page.waitForTimeout(5000);
}

async function stageLinks(page) {
  await expand(page, "相关链接");
  for (const l of LINKS) {
    const added = await clickBtn(page, "links", /添加新链接|添加/);
    await page.waitForTimeout(1000);
    const res = await page.evaluate((row) => {
      const fm = document.querySelector('form[action$="/action/links"]');
      const ts = fm.querySelectorAll('input[name="link_title[]"]');
      const ls = fm.querySelectorAll('input[name="link_link[]"]');
      const t = ts[ts.length - 1];
      const u = ls[ls.length - 1];
      if (!t || !u) return "no-fields";
      t.value = row.title;
      t.dispatchEvent(new Event("input", { bubbles: true }));
      u.value = row.url;
      u.dispatchEvent(new Event("input", { bubbles: true }));
      return "ok";
    }, l);
    console.log(`  ${l.title.slice(0, 16)}  add=${added} ${res}`);
    await page.waitForTimeout(600);
  }
  const btn = await clickBtn(page, "links", /提交相关链接|提交/);
  console.log("  submit:", btn);
  await page.waitForTimeout(5000);
}

// ---------- 主流程 ----------
(async () => {
  const b = await chromium.connectOverCDP("http://127.0.0.1:9222");
  const ctx = b.contexts()[0];
  const page = ctx.pages().find((p) => /indienova/.test(p.url())) || ctx.pages()[0];
  await openEdit(page);

  const stages = {
    intro: stageIntro,
    platform: stagePlatform,
    support: stageSupport,
    gallery: stageGallery,
    demo: stageDemo,
    feature: stageFeature,
    links: stageLinks,
  };

  const run = STAGE === "all" ? Object.values(stages) : [stages[STAGE]].filter(Boolean);
  for (const fn of run) {
    console.log("=== " + fn.name + " ===");
    try {
      await fn(page);
    } catch (e) {
      console.log("  STAGE ERROR:", e.message.slice(0, 160));
      await openEdit(page);
    }
  }

  await page.screenshot({ path: `/tmp/fill_${STAGE}.png`, fullPage: true });
  console.log("SHOT /tmp/fill_" + STAGE + ".png | URL:", page.url());
  await b.close();
})().catch((e) => {
  console.error("ERR:", e.message);
  process.exit(1);
});
