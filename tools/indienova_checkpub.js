// 交叉验证发布状态：编辑页发布区 + 我的游戏列表 + 会员游戏库匿名可见性
const { chromium } = require("playwright-core");
const SLUG = "heliops";

(async () => {
  const browser = await chromium.connectOverCDP("http://127.0.0.1:9222");
  const ctx = browser.contexts()[0];
  const page = await ctx.newPage();

  console.log("=== 编辑页发布区 ===");
  await page.goto(`https://indienova.com/home/editgame/${SLUG}`, { waitUntil: "networkidle" });
  await page.waitForTimeout(2000);
  const pub = await page.evaluate(() => {
    const links = [...document.querySelectorAll("a,button")]
      .filter(e => {
        const h = e.getAttribute("href") || "";
        const t = (e.innerText || e.value || "").trim();
        return /publicGame|unPublic|hideGame|delGame|公开|隐藏|下线|取消公开/i.test(h + " " + t);
      })
      .map(e => ({
        tag: e.tagName, id: e.id, href: e.getAttribute("href"),
        text: (e.innerText || e.value || "").trim().replace(/\s+/g, " ").slice(0, 60),
        visible: !!e.offsetParent,
        rect: (() => { const r = e.getBoundingClientRect(); return `${Math.round(r.x)},${Math.round(r.y)} ${Math.round(r.width)}x${Math.round(r.height)}`; })(),
      }));
    return { links, statusText: (document.body.innerText.match(/[^\n]*公开[^\n]*/g) || []).slice(0, 10) };
  });
  console.log(JSON.stringify(pub, null, 2));

  console.log("\n=== 我的游戏列表 ===");
  await page.goto("https://indienova.com/home/mygame", { waitUntil: "networkidle" }).catch(() => {});
  await page.waitForTimeout(1200);
  const mine = await page.evaluate(() => {
    const t = (document.body.innerText || "").replace(/\n{2,}/g, "\n").trim();
    return { url: location.href, text: t.slice(0, 900) };
  });
  console.log(JSON.stringify(mine, null, 2));

  await page.close();
  await browser.close();
})().catch((e) => { console.error("FATAL", e); process.exit(1); });
