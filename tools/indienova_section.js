// 展开指定分区并检查其内部字段/编辑器
// 用法: node tools/indienova_section.js "游戏介绍"
const { chromium } = require("playwright-core");

const TITLE = process.argv[2];

(async () => {
  const b = await chromium.connectOverCDP("http://127.0.0.1:9222");
  const ctx = b.contexts()[0];
  const page = ctx.pages().find((p) => /indienova/.test(p.url())) || ctx.pages()[0];
  await page.goto("https://indienova.com/home/editgame/heliops", {
    waitUntil: "domcontentloaded",
    timeout: 60000,
  });
  await page.waitForTimeout(3500);

  // 找到分区标题并点击展开
  const clicked = await page.evaluate((t) => {
    const nodes = [...document.querySelectorAll("a,div,span,h3,h4,button")]
      .filter((e) => {
        const s = (e.innerText || "").replace(/\s+/g, " ").trim();
        return s.startsWith(t) && s.length < 80;
      })
      .sort((a, b) => a.innerText.length - b.innerText.length);
    if (!nodes.length) return null;
    const el = nodes[0];
    el.click();
    return el.innerText.replace(/\s+/g, " ").trim().slice(0, 60);
  }, TITLE);
  console.log("CLICKED:", clicked);
  await page.waitForTimeout(2500);

  const info = await page.evaluate(() => {
    const res = { textareas: [], froala: [], contenteditable: [], files: [], submits: [] };
    for (const t of document.querySelectorAll("textarea"))
      res.textareas.push({
        id: t.id,
        name: t.name,
        visible: !!t.offsetParent,
        len: (t.value || "").length,
        next: (t.nextElementSibling?.className || "").slice(0, 50),
      });
    for (const d of document.querySelectorAll("[class*=fr-],[class*=froala]"))
      res.froala.push((d.className || "").slice(0, 70));
    for (const c of document.querySelectorAll("[contenteditable=true]"))
      res.contenteditable.push((c.className || "").slice(0, 70) + " | visible=" + !!c.offsetParent);
    for (const f of document.querySelectorAll('input[type="file"]'))
      res.files.push({ name: f.name, id: f.id, visible: !!f.offsetParent, near: (f.closest("label")?.innerText || "").replace(/\s+/g, " ").slice(0, 40) });
    for (const btn of document.querySelectorAll('button,input[type="submit"]'))
      res.submits.push((btn.value || btn.innerText || "").replace(/\s+/g, " ").trim().slice(0, 24));
    return res;
  });
  console.log(JSON.stringify(info, null, 1));
  await page.screenshot({ path: "/tmp/section.png", fullPage: false });
  console.log("SHOT /tmp/section.png");
  await b.close();
})().catch((e) => {
  console.error("ERR:", e.message);
  process.exit(1);
});
