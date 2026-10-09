// 全量校验 indienova 游戏条目已保存的内容
const { chromium } = require("playwright-core");

(async () => {
  const b = await chromium.connectOverCDP("http://127.0.0.1:9222");
  const ctx = b.contexts()[0];
  const page = ctx.pages().find((p) => /indienova/.test(p.url())) || ctx.pages()[0];

  await page.goto("https://indienova.com/home/editgame/heliops", {
    waitUntil: "domcontentloaded",
    timeout: 60000,
  });
  await page.waitForTimeout(4000);

  const r = await page.evaluate(() => {
    const out = {};
    const val = (id) => document.getElementById(id)?.value ?? null;

    out.basic = { name: val("gameName"), en: val("gameEName") };
    out.support = {
      version: val("gameVersion"),
      price: val("gamePrice"),
      percent: val("gamePercent"),
      type: val("gameType"),
      type2: val("gameType2"),
      theme: val("gameTheme"),
      engine: val("gameEngine"),
    };
    out.intro = {
      briefLen: (val("briefIntro") || "").length,
      bigLen: (val("bigIntro") || "").length,
      bigHasH3: /<h3>/.test(val("bigIntro") || ""),
    };

    const f = (a) => document.querySelector(`form[action$="/action/${a}"]`);
    const cnt = (a, sel) => {
      const fm = f(a);
      return fm ? fm.querySelectorAll(sel).length : -1;
    };

    out.features = [...(f("feature")?.querySelectorAll('input[name="feature[]"]') || [])].map(
      (i) => i.value.slice(0, 24)
    );
    out.featureIcons = [...(f("feature")?.querySelectorAll('select[name="feature_icon[]"]') || [])].map(
      (s) => s.value
    );
    out.demos = [...(f("demo")?.querySelectorAll('input[name="demo[]"]') || [])].map((i) => i.value.slice(0, 40));
    out.demoLinks = [...(f("demo")?.querySelectorAll('input[name="demo_link[]"]') || [])].map((i) =>
      i.value.slice(0, 46)
    );
    out.links = [...(f("links")?.querySelectorAll('input[name="link_title[]"]') || [])].map((i) => i.value);
    out.linkUrls = [...(f("links")?.querySelectorAll('input[name="link_link[]"]') || [])].map((i) =>
      i.value.slice(0, 46)
    );
    out.platforms = [
      ...(f("platform")?.querySelectorAll('input[name="gamePlatforms[]"]') || []),
    ]
      .filter((c) => c.checked)
      .map((c) => c.value);

    // 画廊缩略图（渲染在 form 之外，按 hive 缩略图统计）
    out.galleryThumbs = [
      ...document.querySelectorAll("img, [style*=background-image]"),
    ]
      .map((e) => e.src || getComputedStyle(e).backgroundImage)
      .filter((s) => /img-\d+-[A-Za-z0-9]+\.png_t\d/.test(s || "")).length;
    out.logo = [...document.querySelectorAll("img,[style*=background-image]")]
      .map((e) => e.src || getComputedStyle(e).backgroundImage)
      .some((s) => /\/farm\/gameimg\/.*l-\d+/.test(s || ""));
    out.preview = [...document.querySelectorAll("img,[style*=background-image]")]
      .map((e) => e.src || getComputedStyle(e).backgroundImage)
      .some((s) => /\/farm\/gameimg\/.*p-\d+/.test(s || ""));

    // 右侧发布状态
    const body = document.body.innerText;
    out.status = /尚未公开/.test(body) ? "尚未公开" : /已公开/.test(body) ? "已公开" : "未知";
    return out;
  });

  console.log(JSON.stringify(r, null, 1));
  await page.screenshot({ path: "/tmp/verify_edit.png", fullPage: true });
  console.log("SHOT /tmp/verify_edit.png");

  // 预览页面
  await page.goto("https://indienova.com/g/heliops", { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForTimeout(3000);
  console.log("PREVIEW URL:", page.url(), "| TITLE:", await page.title());
  const t = await page.evaluate(() => (document.body.innerText || "").replace(/\s+/g, " ").slice(0, 700));
  console.log("PREVIEW TEXT:", t);
  await page.screenshot({ path: "/tmp/verify_preview.png", fullPage: true });
  console.log("SHOT /tmp/verify_preview.png");

  await b.close();
})().catch((e) => {
  console.error("ERR:", e.message);
  process.exit(1);
});
