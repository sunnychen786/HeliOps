const { chromium } = require("playwright-core");
(async () => {
  const browser = await chromium.connectOverCDP("http://127.0.0.1:9222");
  const ctx = browser.contexts()[0];
  const page = ctx.pages().find((p) => /indienova\.com/.test(p.url())) || ctx.pages()[0];

  const dump = await page.evaluate(() =>
    [...document.querySelectorAll('input[name="gamePlatforms[]"]')].map((c) => {
      const lab = c.closest("label");
      const cs = getComputedStyle(c);
      return {
        value: c.value,
        checked: c.checked,
        offsetParent: !!c.offsetParent,
        display: cs.display,
        visibility: cs.visibility,
        w: c.offsetWidth,
        h: c.offsetHeight,
        labelText: (lab?.innerText || "").trim().slice(0, 20),
        wrapperCls: (lab?.className || c.parentElement?.className || "").slice(0, 60),
        outerHTML: c.outerHTML.slice(0, 160),
      };
    })
  );
  console.log(JSON.stringify(dump.filter((d) => ["windows", "mac", "linux"].includes(d.value)), null, 1));

  // 尝试用 Playwright 原生 check
  try {
    await page.check('input[name="gamePlatforms[]"][value="windows"]', { force: true, timeout: 5000 });
    console.log("native check(windows) OK");
  } catch (e) {
    console.log("native check failed:", e.message.slice(0, 120));
  }
  const after = await page.evaluate(() =>
    [...document.querySelectorAll('input[name="gamePlatforms[]"]')].filter((c) => c.checked).map((c) => c.value)
  );
  console.log("after native check:", JSON.stringify(after));

  await page.screenshot({ path: "/tmp/probe_platform.png", fullPage: true });
  await browser.close();
})().catch((e) => { console.error("ERR:", e.message); process.exit(1); });
