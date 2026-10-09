// 填写 indienova「添加我新开发的游戏」第 1 步（基本信息）
// 用法: node tools/indienova_fill_step1.js [submit]
const { chromium } = require("playwright-core");
const path = require("path");

const ROOT = path.dirname(__dirname);
const SHOTS = path.join(ROOT, "screenshots");
const COVER = path.join(SHOTS, "indienova_00_封面_1280x720.png");
const PREVIEW = path.join(SHOTS, "indienova_01_预览_1280x720.png");

const DO_SUBMIT = process.argv[2] === "submit";

// 表单内容（想改内容只改这里）
const DATA = {
  gameName: "HeliOps",
  gameSlugName: "heliops",
  gameType: "15", // 大型射击
  gameType2: "12", // 第三人称射击
  gameTheme: "22", // 战争
  gameEngine: "250", // 其它
  gameEngineAdd: "Pygame（Python + SDL）",
  year: "2026",
  month: "9",
  day: "13",
  platforms: ["windows", "mac"],
};

(async () => {
  const browser = await chromium.connectOverCDP("http://127.0.0.1:9222");
  const ctx = browser.contexts()[0];
  const page = ctx.pages().find((p) => /indienova\.com/.test(p.url())) || ctx.pages()[0];

  await page.goto("https://indienova.com/home/addNewGame", {
    waitUntil: "domcontentloaded",
    timeout: 60000,
  });
  await page.waitForTimeout(3000);

  // 若已被拦（新会员 1 小时限制）
  const body = await page.evaluate(() => document.body.innerText);
  if (/需要等待一小时/.test(body)) {
    console.log("BLOCKED: 新会员 1 小时限制仍在");
    await browser.close();
    process.exit(2);
  }

  const refreshPicker = (id) =>
    page.evaluate((sel) => {
      const el = document.getElementById(sel);
      if (!el) return;
      const jq = window.jQuery || window.$;
      if (jq && jq(el).selectpicker) jq(el).selectpicker("refresh");
    }, id);

  const setSelect = async (id, value, label) => {
    await page.selectOption(`#${id}`, value).catch(() => {});
    await refreshPicker(id);
    const got = await page.$eval(`#${id}`, (s) => s.value).catch(() => null);
    console.log(`select ${id} -> ${got} (${label})${got === value ? "" : "  ⚠️不匹配"}`);
  };

  // ---- 文本 ----
  await page.fill("#gameName", DATA.gameName);
  await page.fill("#gameSlugName", DATA.gameSlugName);
  console.log("text: gameName / gameSlugName 已填");

  // ---- 下拉 ----
  await setSelect("gameType", DATA.gameType, "主要分类");
  await setSelect("gameType2", DATA.gameType2, "次要分类");
  await setSelect("gameTheme", DATA.gameTheme, "主题");
  await setSelect("gameEngine", DATA.gameEngine, "引擎");

  // 引擎「其它」的补充输入框（默认隐藏）
  await page.evaluate((v) => {
    const el = document.getElementById("gameEngineAdd");
    if (!el) return;
    el.value = v;
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
  }, DATA.gameEngineAdd);
  console.log("text: gameEngineAdd 已填（隐藏框，用 JS 赋值）");

  // ---- 发布日期 ----
  await setSelect("gameYear", DATA.year, "年");
  await setSelect("gameMonth", DATA.month, "月");
  await setSelect("gameDay", DATA.day, "日");
  await page.evaluate(() => {
    const r = document.getElementById("gamePubOption_2");
    if (r && !r.checked) r.click();
  });
  console.log("radio: 预计发布或者已经发布");

  // ---- 平台 ----
  // 这批复选框是 bootstrap 的 btn-group(data-toggle="buttons")，直接 click 会被
  // 按钮组插件吞掉（点了但 input 仍为 unchecked）。所以直接写 checked 并同步
  // label 的 active 类——真正参与提交的是 input.checked。
  const setPlatform = (val, on) =>
    page.evaluate(
      ({ v, state }) => {
        const cb = [...document.querySelectorAll('input[name="gamePlatforms[]"]')].find(
          (c) => c.value === v
        );
        if (!cb) return null;
        cb.checked = state;
        cb.dispatchEvent(new Event("input", { bubbles: true }));
        cb.dispatchEvent(new Event("change", { bubbles: true }));
        const lab = cb.closest("label");
        if (lab) lab.classList.toggle("active", state);
        return cb.checked;
      },
      { v: val, state: on }
    );

  for (const p of DATA.platforms) console.log("platform:", p, "->", await setPlatform(p, true));
  // 未列出的平台一律取消，避免误勾
  await page.evaluate((keep) => {
    for (const cb of document.querySelectorAll('input[name="gamePlatforms[]"]')) {
      if (!keep.includes(cb.value)) {
        cb.checked = false;
        const lab = cb.closest("label");
        if (lab) lab.classList.remove("active");
      }
    }
  }, DATA.platforms);
  // 「交给 INDIENOVA 发行」保持不勾
  await page.evaluate(() => {
    const c = document.getElementById("indienovaPub");
    if (c) {
      c.checked = false;
      const lab = c.closest("label");
      if (lab) lab.classList.remove("active");
    }
  });

  // ---- 图片 ----
  await page.setInputFiles("#logoImage", COVER);
  await page.waitForTimeout(1200);
  await page.setInputFiles("#previewImage", PREVIEW);
  await page.waitForTimeout(2500);
  console.log("images:", path.basename(COVER), "+", path.basename(PREVIEW));

  await page.screenshot({ path: "/tmp/step1_filled.png", fullPage: true });
  console.log("SHOT: /tmp/step1_filled.png");

  // ---- 回读校验 ----
  const check = await page.evaluate(() => {
    const v = (id) => document.getElementById(id)?.value;
    return {
      gameName: v("gameName"),
      slug: v("gameSlugName"),
      type: v("gameType"),
      type2: v("gameType2"),
      theme: v("gameTheme"),
      engine: v("gameEngine"),
      engineAdd: v("gameEngineAdd"),
      y: v("gameYear"),
      m: v("gameMonth"),
      d: v("gameDay"),
      pub2: document.getElementById("gamePubOption_2")?.checked,
      platforms: [...document.querySelectorAll('input[name="gamePlatforms[]"]')]
        .filter((c) => c.checked)
        .map((c) => c.value),
      logo: !!document.getElementById("logoImage")?.files?.length,
      preview: !!document.getElementById("previewImage")?.files?.length,
    };
  });
  console.log("VERIFY:", JSON.stringify(check));

  if (DO_SUBMIT) {
    console.log("SUBMIT...");
    await page.evaluate(() => {
      const b = [...document.querySelectorAll('button,input[type="submit"]')].find((x) =>
        /添加新游戏/.test(x.value || x.innerText || "")
      );
      if (b) b.click();
    });
    await page.waitForTimeout(6000);
    console.log("AFTER SUBMIT URL:", page.url());
    await page.screenshot({ path: "/tmp/step1_after.png", fullPage: true });
    console.log("SHOT: /tmp/step1_after.png");
  }

  await page.bringToFront().catch(() => {});
  await browser.close();
})().catch((e) => {
  console.error("ERR:", e.message);
  process.exit(1);
});
