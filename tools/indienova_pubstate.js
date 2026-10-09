// 1) 跟踪 publicGame 的完整重定向链与 Location
// 2) 检查 /g/heliops 的公开状态
// node tools/indienova_pubstate.js
const { chromium } = require("playwright-core");
const SLUG = "heliops";

(async () => {
  const browser = await chromium.connectOverCDP("http://127.0.0.1:9222");
  const ctx = browser.contexts()[0];
  const page = await ctx.newPage();

  page.on("response", async (r) => {
    const u = r.url();
    if (!u.includes("indienova.com")) return;
    if (r.status() >= 300 && r.status() < 400) {
      const h = r.headers();
      console.log(`  [${r.status()}] ${u}\n      -> location: ${h.location || h.Location || "(none)"}  set-cookie: ${h["set-cookie"] ? "yes" : "no"}`);
    }
  });

  console.log("=== 访问 /g/heliops (公开页) ===");
  const p = await page.goto(`https://indienova.com/g/${SLUG}`, { waitUntil: "domcontentloaded" });
  console.log("[final]", p.status(), page.url());
  const g = await page.evaluate(() => {
    const t = (document.body.innerText || "").replace(/\n{2,}/g, "\n").trim();
    const notPub = /尚未公开|暂未公开|未公开|该游戏尚未/.test(t);
    return { title: document.title, notPublicHint: notPub, head: t.slice(0, 600) };
  });
  console.log(JSON.stringify(g, null, 2));

  console.log("\n=== 访问 /home/publicGame/heliops ===");
  await page.goto(`https://indienova.com/home/publicGame/${SLUG}`, { waitUntil: "domcontentloaded" });
  console.log("[after publicGame]", page.url());

  console.log("\n=== 再看 /g/heliops ===");
  await page.goto(`https://indienova.com/g/${SLUG}`, { waitUntil: "domcontentloaded" });
  const g2 = await page.evaluate(() => {
    const t = (document.body.innerText || "").replace(/\n{2,}/g, "\n").trim();
    return { title: document.title, notPublicHint: /尚未公开|暂未公开|未公开/.test(t), head: t.slice(0, 600) };
  });
  console.log(JSON.stringify(g2, null, 2));
  await page.screenshot({ path: "/tmp/g_after.png" });

  console.log("\n=== 编辑页按钮现状 ===");
  await page.goto(`https://indienova.com/home/editgame/${SLUG}`, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(1500);
  const btn = await page.evaluate(() => {
    const b = document.querySelector("#iPublicGame");
    const r = b && b.getBoundingClientRect();
    return {
      exists: !!b,
      text: b ? (b.innerText || "").trim() : null,
      href: b ? b.getAttribute("href") : null,
      rect: r ? `${Math.round(r.x)},${Math.round(r.y)} ${Math.round(r.width)}x${Math.round(r.height)}` : null,
    };
  });
  console.log(JSON.stringify(btn, null, 2));

  await page.close();
  await browser.close();
})().catch((e) => { console.error("FATAL", e); process.exit(1); });
