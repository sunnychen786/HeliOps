// indienova 表单驱动脚本（通过 CDP 附着到长期运行的 Edge，不关闭浏览器）
//
// 前置：/tmp/indienova_server.js（或 tools/indienova_server.js）以
//   --remote-debugging-port=9222 + 持久化档案启动，窗口保持打开。
//
// 用法:
//   node tools/indienova_drive.js links [url] [正则]   列出页面链接
//   node tools/indienova_drive.js text  [url]          输出正文 + 所有表单字段
//   node tools/indienova_drive.js shot  [url] [输出png] 截图
//   node tools/indienova_drive.js fill  <json文件>      按 JSON 填写字段
//   node tools/indienova_drive.js upload <选择器> <文件1,文件2,...>
//
// 填写 JSON 格式: [{"by": "id|name|label|placeholder|selector", "key": "...", "value": "..."}]
//
const { chromium } = require("playwright-core");
const fs = require("fs");

const [action, ...rest] = process.argv.slice(2);
const NODE = "/Users/Admin/.workbuddy/binaries/node/versions/22.22.2/bin/node";

async function locate(page, rule) {
  // 返回 ElementHandle 或 null
  const { by, key } = rule;
  switch (by) {
    case "id":
      return page.$(`#${CSS.escape(key)}`);
    case "name":
      return page.$(`[name="${key}"]`);
    case "selector":
      return page.$(key);
    case "placeholder":
      return page.$(`[placeholder="${key}"]`);
    case "label":
      // 找到含目标文字的 label/th/td/span，再取同一行或紧邻的 input/textarea/select
      return page.evaluateHandle((k) => {
        const norm = (s) => (s || "").replace(/\s+/g, "").trim();
        const target = norm(k);
        const nodes = [...document.querySelectorAll("label,th,td,span,div,p,li")];
        for (const n of nodes) {
          if (norm(n.textContent) === target || norm(n.textContent).startsWith(target)) {
            const field =
              n.querySelector("input,textarea,select") ||
              n.parentElement?.querySelector("input,textarea,select") ||
              n.nextElementSibling?.querySelector?.("input,textarea,select") ||
              n.parentElement?.nextElementSibling?.querySelector?.("input,textarea,select");
            if (field) return field;
          }
        }
        return null;
      }, key);
    default:
      return null;
  }
}

(async () => {
  const browser = await chromium.connectOverCDP("http://127.0.0.1:9222");
  const ctx = browser.contexts()[0];
  let page = ctx.pages().find((p) => /indienova\.com/.test(p.url())) || ctx.pages()[0];
  if (!page) page = await ctx.newPage();

  const goto = async (url) => {
    if (url) {
      await page.goto(url, { waitUntil: "domcontentloaded", timeout: 60000 });
      await page.waitForTimeout(3000);
    }
  };

  if (action === "links") {
    await goto(rest[0]);
    const pat = rest[1] || "";
    const links = await page.$$eval("a", (els) =>
      els.map((e) => ((e.innerText || "").trim().replace(/\s+/g, " ") + " => " + e.href))
    );
    const filtered = [...new Set(links)].filter((s) => s.split(" =>")[0]);
    console.log("URL:", page.url());
    console.log("TITLE:", await page.title());
    console.log(JSON.stringify((pat ? filtered.filter((s) => new RegExp(pat).test(s)) : filtered).slice(0, 40), null, 1));
  }

  if (action === "text") {
    await goto(rest[0]);
    console.log("URL:", page.url());
    console.log("TITLE:", await page.title());
    const t = await page.evaluate(() => (document.body.innerText || "").slice(0, 4000));
    console.log("TEXT:\n" + t);
    const fields = await page.$$eval("input,textarea,select", (els) =>
      els.map((e) => {
        const near = (e.closest("label")?.innerText || e.parentElement?.innerText || "")
          .replace(/\s+/g, " ")
          .trim()
          .slice(0, 40);
        return `${e.tagName}|type=${e.type || ""}|id=${e.id || ""}|name=${e.name || ""}|ph=${e.getAttribute("placeholder") || ""}|near=${near}|visible=${!!e.offsetParent}`;
      })
    );
    console.log("FIELDS:\n" + fields.join("\n"));
  }

  if (action === "shot") {
    await goto(rest[0]);
    await page.screenshot({ path: rest[1] || "/tmp/step.png", fullPage: false });
    console.log("SHOT:", rest[1] || "/tmp/step.png", "|", page.url());
  }

  if (action === "fill") {
    const rules = JSON.parse(fs.readFileSync(rest[0], "utf8"));
    for (const r of rules) {
      const h = await locate(page, r);
      const el = h.asElement ? h.asElement() : h;
      if (!el) {
        console.log("MISS:", r.by, r.key);
        continue;
      }
      const tag = await el.evaluate((e) => e.tagName);
      if (tag === "SELECT") {
        const ok = await el.selectOption(r.value).then(() => true).catch(() => false);
        if (!ok) {
          await el.selectOption({ label: r.value }).catch(() => {});
        }
        console.log("FILLED(select):", r.by, r.key, "=>", r.value);
      } else if (tag === "TEXTAREA" || (r.by === "label" && tag === "DIV")) {
        await el.evaluate((e, v) => {
          e.focus();
          e.innerText = v;
          e.dispatchEvent(new Event("input", { bubbles: true }));
        }, r.value);
        console.log("FILLED(contenteditable):", r.by, r.key);
      } else {
        await el.fill(r.value).catch(async () => {
          await el.evaluate((e, v) => {
            e.value = v;
            e.dispatchEvent(new Event("input", { bubbles: true }));
          }, r.value);
        });
        console.log("FILLED:", r.by, r.key, "=>", String(r.value).slice(0, 30));
      }
    }
    await page.screenshot({ path: "/tmp/fill_result.png" });
    console.log("DONE, shot -> /tmp/fill_result.png");
  }

  if (action === "upload") {
    const [sel, files] = [rest[0], rest[1].split(",")];
    const input = await page.$(sel);
    if (!input) console.log("NO_INPUT:", sel);
    else {
      await input.setInputFiles(files);
      console.log("UPLOADED:", files.join(", "));
      await page.waitForTimeout(2500);
    }
  }

  await page.bringToFront().catch(() => {});
  await browser.close();
})().catch((e) => {
  console.error("ERR:", e.message);
  process.exit(1);
});
