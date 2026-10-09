// 直接访问公开地址 / 或点击按钮，观察真实结果
// node tools/indienova_pubgo.js goto   -> 直接 GET /home/publicGame/heliops
// node tools/indienova_pubgo.js click  -> 点 #iPublicGame 并跟随
const { chromium } = require("playwright-core");
const SLUG = "heliops";
const mode = process.argv[2] || "goto";

(async () => {
  const browser = await chromium.connectOverCDP("http://127.0.0.1:9222");
  const ctx = browser.contexts()[0];
  let page = ctx.pages().find((p) => p.url().includes("/home/editgame/"));
  if (!page) { page = await ctx.newPage(); await page.goto(`https://indienova.com/home/editgame/${SLUG}`, { waitUntil: "domcontentloaded" }); }
  await page.bringToFront();

  console.log("[before]", page.url());

  let resp = null;
  page.on("response", (r) => {
    if (r.url().includes("publicGame")) resp = r;
  });
  page.on("console", (m) => console.log("[console]", m.type(), m.text().slice(0, 200)));

  if (mode === "goto") {
    const r = await page.goto(`https://indienova.com/home/publicGame/${SLUG}`, { waitUntil: "domcontentloaded" });
    console.log("[status]", r && r.status(), r && r.headers()["location"] || "");
  } else {
    await page.click("#iPublicGame").catch((e) => console.log("click err:", e.message));
    await page.waitForTimeout(3000);
  }

  await page.waitForTimeout(1200);
  console.log("[after]", page.url());
  if (resp) console.log("[resp]", resp.status(), resp.url());

  const body = await page.evaluate(() => {
    const t = (document.body.innerText || "").replace(/\n{2,}/g, "\n").trim();
    // 找提示/警告区域
    const alerts = [...document.querySelectorAll(".alert,.flash,.mfp-content,.bootbox, .notice, .error, .warn")]
      .map(e => (e.innerText || "").trim().slice(0, 300)).filter(Boolean);
    return { url: location.href, alerts, text: t.slice(0, 1500) };
  });
  console.log("=== 页面 ===");
  console.log(JSON.stringify(body, null, 2));
  await page.screenshot({ path: "/tmp/pub_result.png" });
  console.log("shot /tmp/pub_result.png");
  await browser.close();
})().catch((e) => { console.error("FATAL", e); process.exit(1); });
