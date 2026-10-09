// 诊断 publicGame 被 302 的原因
const { chromium } = require("playwright-core");
const SLUG = "heliops";

(async () => {
  const browser = await chromium.connectOverCDP("http://127.0.0.1:9222");
  const ctx = browser.contexts()[0];
  const page = ctx.pages().find((p) => p.url().includes("indienova.com")) || await ctx.newPage();
  await page.bringToFront();

  // 1) 用页面内 fetch，redirect:manual 拿到 302 的 Location
  const r1 = await page.evaluate(async (slug) => {
    const res = await fetch(`/home/publicGame/${slug}`, { redirect: "manual", credentials: "include" });
    const h = {};
    res.headers.forEach((v, k) => (h[k] = v));
    let body = "";
    try { body = await res.text(); } catch (e) {}
    return { type: res.type, status: res.status, url: res.url, headers: h, body: body.slice(0, 800) };
  }, SLUG);
  console.log("=== fetch manual ===");
  console.log(JSON.stringify(r1, null, 2));

  // 2) 也试 POST
  const r2 = await page.evaluate(async (slug) => {
    const res = await fetch(`/home/publicGame/${slug}`, { method: "POST", redirect: "manual", credentials: "include" });
    const h = {};
    res.headers.forEach((v, k) => (h[k] = v));
    let body = "";
    try { body = await res.text(); } catch (e) {}
    return { status: res.status, headers: h, body: body.slice(0, 800) };
  }, SLUG);
  console.log("=== POST manual ===");
  console.log(JSON.stringify(r2, null, 2));

  // 3) 检查条目当前状态 / 必填项
  const state = await page.evaluate(async () => {
    const res = await fetch("/home/editgame/heliops", { credentials: "include" });
    const html = await res.text();
    const doc = new DOMParser().parseFromString(html, "text/html");
    const grab = (s) => { const e = doc.querySelector(s); return e ? (e.value || e.innerText || "").trim().slice(0, 200) : null; };
    return {
      hasPublicBtn: !!doc.querySelector("#iPublicGame"),
      publicBtnHref: (doc.querySelector("#iPublicGame") || {}).getAttribute ? doc.querySelector("#iPublicGame").getAttribute("href") : null,
      brief: grab("#briefIntro"),
      big: (grab("#bigIntro") || "").slice(0, 120),
      logo: (doc.querySelector("#logoImage") || {}).value || grab("[name=logoImage]"),
      version: grab("[name=version]"),
      price: grab("[name=price]"),
      progress: grab("[name=progress]"),
      releasedate: grab("[name=releaseDate]"),
      allInputs: [...doc.querySelectorAll("input,select,textarea")].map(e => `${e.tagName}#${e.id}.${e.name}=${(e.value||"").slice(0,40)}`).slice(0, 80),
    };
  });
  console.log("=== 条目状态 ===");
  console.log(JSON.stringify(state, null, 2));

  await browser.close();
})().catch((e) => { console.error("FATAL", e); process.exit(1); });
