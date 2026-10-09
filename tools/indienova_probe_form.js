const { chromium } = require("playwright-core");

(async () => {
  const browser = await chromium.connectOverCDP("http://127.0.0.1:9222");
  const ctx = browser.contexts()[0];
  const page = ctx.pages().find((p) => /indienova\.com/.test(p.url())) || ctx.pages()[0];
  await page.goto("https://indienova.com/home/addNewGame", { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForTimeout(3000);

  const info = await page.evaluate(() => {
    const s = document.getElementById("gameType");
    const wrap = s ? s.parentElement : null;
    return {
      selectClass: s?.className,
      wrapClass: wrap?.className,
      wrapHTML: wrap?.outerHTML.slice(0, 400),
      formId: document.querySelector("form")?.id,
      formAction: document.querySelector("form")?.action,
      formMethod: document.querySelector("form")?.method,
      // 是否有富文本编辑器（简介会用）
      editors: [...document.querySelectorAll("[class*=editor],[class*=Editor],[id*=editor]")]
        .map((e) => e.id || e.className)
        .slice(0, 10),
      allSelects: [...document.querySelectorAll("select")].map((s) => s.id + " | cls=" + s.className),
      hiddenInputs: [...document.querySelectorAll('input[type="hidden"]')].map((i) => i.name + "=" + String(i.value).slice(0, 20)),
    };
  });
  console.log(JSON.stringify(info, null, 1));

  // 试着用原生 selectOption 选中「大型射击」并回读
  const ok = await page.selectOption("#gameType", "15").then(() => true).catch((e) => e.message);
  const back = await page.$eval("#gameType", (s) => s.value).catch(() => null);
  console.log("selectOption result:", ok, "| readback:", back);
  const label = await page.$eval("#gameType", (s) => s.options[s.selectedIndex]?.textContent).catch(() => null);
  console.log("selected label:", label);
  await browser.close();
})().catch((e) => { console.error("ERR:", e.message); process.exit(1); });
