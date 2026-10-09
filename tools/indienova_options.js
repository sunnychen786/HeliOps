const { chromium } = require("playwright-core");
(async () => {
  const browser = await chromium.connectOverCDP("http://127.0.0.1:9222");
  const ctx = browser.contexts()[0];
  const page = ctx.pages().find((p) => /indienova\.com/.test(p.url())) || ctx.pages()[0];

  const info = await page.evaluate(() => {
    const out = {};
    for (const id of ["gameType", "gameType2", "gameTheme", "gameEngine"]) {
      const s = document.getElementById(id);
      out[id] = s ? [...s.options].map((o) => o.value + " | " + o.textContent.trim()) : null;
    }
    out.radios = [...document.querySelectorAll('input[name="gamePubOption"]')].map((r) => ({
      id: r.id,
      value: r.value,
      label: (r.closest("label")?.innerText || r.parentElement?.innerText || "").replace(/\s+/g, " ").trim(),
      checked: r.checked,
    }));
    out.platformLabels = [...document.querySelectorAll('input[name="gamePlatforms[]"]')].map((c) => ({
      value: c.value,
      label: (c.closest("label")?.innerText || c.parentElement?.innerText || "").replace(/\s+/g, " ").trim(),
      checked: c.checked,
    }));
    out.required = [...document.querySelectorAll("[required]")].map((e) => e.name || e.id);
    out.fileHints = [...document.querySelectorAll('input[type="file"]')].map((f) => ({
      id: f.id,
      near: (f.closest("label")?.innerText || f.parentElement?.innerText || "").replace(/\s+/g, " ").trim().slice(0, 160),
    }));
    out.buttons = [...document.querySelectorAll('button,input[type="submit"],a.btn')].map((b) =>
      (b.value || b.innerText || "").replace(/\s+/g, " ").trim().slice(0, 30)
    ).filter(Boolean);
    return out;
  });
  console.log(JSON.stringify(info, null, 1));
  await browser.close();
})().catch((e) => { console.error("ERR:", e.message); process.exit(1); });
