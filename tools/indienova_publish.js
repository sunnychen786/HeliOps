// 探测 / 触发 indienova 条目「公开」按钮
// 用法: node tools/indienova_publish.js dump      <- 列出所有疑似发布按钮 + 弹层
//       node tools/indienova_publish.js dry        <- 点击并观察变化（不提交）
//       node tools/indienova_publish.js go         <- 真的点并按弹层确认
const { chromium } = require("playwright-core");

const SLUG = "heliops";
const EDIT = `https://indienova.com/home/editgame/${SLUG}`;
const mode = process.argv[2] || "dump";

(async () => {
  const browser = await chromium.connectOverCDP("http://127.0.0.1:9222");
  const ctx = browser.contexts()[0];
  let page = ctx.pages().find((p) => p.url().includes("/home/editgame/"));
  if (!page) {
    page = await ctx.newPage();
    await page.goto(EDIT, { waitUntil: "domcontentloaded" });
  }
  await page.bringToFront();

  const dump = () => page.evaluate(() => {
    const out = { buttons: [], modals: [], forms: [] };
    const kw = ["公开", "发布", "提交审核", "上线", "publish", "release"];
    for (const el of document.querySelectorAll("a,button,input[type=submit],input[type=button],span.btn,div.btn")) {
      const t = (el.innerText || el.value || el.textContent || "").trim().replace(/\s+/g, " ");
      if (!t || t.length > 40) continue;
      if (!kw.some((k) => t.includes(k))) continue;
      const r = el.getBoundingClientRect();
      out.buttons.push({
        tag: el.tagName, type: el.type || "", text: t,
        id: el.id, cls: el.className,
        href: el.getAttribute("href"),
        onclick: el.getAttribute("onclick"),
        data: JSON.stringify(Object.fromEntries([...el.attributes].filter(a => a.name.startsWith("data-")).map(a => [a.name, a.value]))),
        visible: !!(el.offsetParent || r.width),
        rect: `${Math.round(r.x)},${Math.round(r.y)} ${Math.round(r.width)}x${Math.round(r.height)}`,
        disabled: el.disabled === true,
      });
    }
    for (const m of document.querySelectorAll(".mfp-wrap,.modal,.bootbox,.swal2-container,[role=dialog]")) {
      const st = getComputedStyle(m);
      out.modals.push({
        cls: m.className, display: st.display, visibility: st.visibility,
        text: (m.innerText || "").trim().slice(0, 500),
      });
    }
    for (const f of document.querySelectorAll("form")) {
      out.forms.push({ action: f.getAttribute("action"), method: f.method, id: f.id });
    }
    return out;
  });

  const info = await dump();
  console.log("=== 按钮 ===");
  console.log(JSON.stringify(info.buttons, null, 2));
  console.log("=== 弹层 ===");
  console.log(JSON.stringify(info.modals, null, 2));

  if (mode === "dump") { await browser.close(); return; }

  // 找主发布按钮
  const target = info.buttons.find((b) => b.visible && (b.text.includes("公开") || b.text.includes("发布")));
  if (!target) { console.log("!! 没找到可见的公开按钮"); await browser.close(); return; }
  console.log(">>> 目标:", target.tag, target.cls, target.text);

  const sel = target.id ? `#${target.id}`
    : target.href ? `a[href="${target.href}"]`
    : `.${target.cls.split(" ").filter(Boolean).join(".")}`;
  console.log(">>> 选择器:", sel);

  if (mode === "dry") {
    // 只监听：点一下，看 console / 弹层 / 网络
    page.on("console", (m) => console.log("[console]", m.type(), m.text().slice(0, 300)));
    page.on("dialog", async (d) => { console.log("[dialog]", d.type(), d.message()); await d.dismiss(); });
    page.on("request", (r) => {
      if (r.method() === "POST") console.log("[POST]", r.url());
    });
    await page.click(sel).catch((e) => console.log("click err:", e.message));
    await page.waitForTimeout(2500);
    const after = await dump();
    console.log("=== 点击后弹层 ===");
    console.log(JSON.stringify(after.modals, null, 2));
    await page.screenshot({ path: "/tmp/pub_after.png", fullPage: false });
    console.log("shot: /tmp/pub_after.png");
  }

  await browser.close();
})().catch((e) => { console.error("FATAL", e); process.exit(1); });
