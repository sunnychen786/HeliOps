// 填写「游戏介绍」分区（Froala 富文本，无全局 API → 直接操作编辑器 DOM）
// 用法: node tools/indienova_fill_intro.js [submit]
const { chromium } = require("playwright-core");

const DO_SUBMIT = process.argv[2] === "submit";

const BRIEF =
  "<p>单机俯视角直升机撤离射击：驾驶直升机进入战区，搜集物资、装备武器，在敌人与 Boss 的围追堵截中坚持到撤离点，" +
  "把战利品安全带出战区并强化装备。战场布局与音效全部程序生成，支持 Windows 与 macOS，免费无内购。</p>";

const BIG = [
  "<h3>关于这款游戏</h3>",
  "<p>《HeliOps》是一款俯视角的直升机撤离射击游戏，一个人玩也很紧张。你驾驶直升机进入战区，在有限的时间里搜索补给箱、捡到武器、清掉挡路的敌人，然后赶到撤离点把东西带出去。带出去的战利品会变成分数，用来换取更强的装备——但一旦在战区里被击落，这一趟就白跑了。</p>",
  "<h3>玩法</h3>",
  "<ul>",
  "<li><b>移动</b>：WASD 或方向键飞行，直升机有惯性，转向和刹车都要留提前量。</li>",
  "<li><b>射击</b>：按住空格自动瞄准最近的敌人开火，专心走位即可。</li>",
  "<li><b>搜索</b>：靠近补给箱按 J 搜索，能拿到弹药、护盾和武器。</li>",
  "<li><b>撤离</b>：在黄色撤离点停留 3 秒完成撤离，成功撤离后结算并自动存档。</li>",
  "<li><b>其它</b>：数字键 1-4 或 Tab／滚轮切换武器，8 打开补给站商店，P 查看任务面板，ESC 暂停。</li>",
  "</ul>",
  "<h3>游戏特色</h3>",
  "<ul>",
  "<li><b>四种武器各有取舍</b>：手枪均衡、步枪射速快但后坐明显、霰弹近距爆发、狙击单发高伤但节奏慢。</li>",
  "<li><b>三个难度</b>：普通、困难、极难；困难以上需用 Boss 掉落的令牌解锁，越难奖励越高。</li>",
  "<li><b>程序生成的战场</b>：每次进入战区，掩体布局与物资位置都不相同。</li>",
  "<li><b>持续成长</b>：撤离带出的分数可以买装备，角色一点点变强，再去挑战更难的局。</li>",
  "<li><b>零内购、纯单机</b>：不需要联网，不额外收费。</li>",
  "</ul>",
  "<h3>运行与下载</h3>",
  "<p>游戏解压即玩：Windows 版运行 <b>HeliOps.exe</b>，macOS 版运行 <b>HeliOps.app</b>。下载地址见页面下方的「Demo 下载」区块。</p>",
].join("");

(async () => {
  const b = await chromium.connectOverCDP("http://127.0.0.1:9222");
  const ctx = b.contexts()[0];
  const page = ctx.pages().find((p) => /indienova/.test(p.url())) || ctx.pages()[0];
  await page.goto("https://indienova.com/home/editgame/heliops", {
    waitUntil: "domcontentloaded",
    timeout: 60000,
  });
  await page.waitForTimeout(3500);

  await page.evaluate(() => {
    const n = [...document.querySelectorAll("a,div,span,h3,h4,button")]
      .filter((e) => (e.innerText || "").replace(/\s+/g, " ").trim().startsWith("游戏介绍"))
      .sort((a, b) => a.innerText.length - b.innerText.length)[0];
    if (n) n.click();
  });
  await page.waitForTimeout(2500);

  const editors = page.locator(".froala-element[contenteditable='true']");
  const n = await editors.count();
  console.log("editors:", n);

  const writeInto = async (idx, html, textareaId) => {
    const ed = editors.nth(idx);
    await ed.scrollIntoViewIfNeeded().catch(() => {});
    await ed.click({ force: true }).catch(() => {});
    await page.keyboard.press("Meta+A").catch(() => {});
    await page.keyboard.press("Delete").catch(() => {});
    await ed.evaluate((e, h) => {
      e.innerHTML = h;
      e.dispatchEvent(new Event("input", { bubbles: true }));
      e.dispatchEvent(new Event("keyup", { bubbles: true }));
      e.dispatchEvent(new Event("blur", { bubbles: true }));
    }, html);
    // 同步底层 textarea（表单提交读的是它）
    await page.evaluate(
      ({ h, id }) => {
        const t = document.getElementById(id);
        if (t) {
          t.value = h;
          t.dispatchEvent(new Event("input", { bubbles: true }));
          t.dispatchEvent(new Event("change", { bubbles: true }));
        }
      },
      { h: html, id: textareaId }
    );
    console.log(`${textareaId} <- ${html.length} chars`);
  };

  await writeInto(0, BRIEF, "briefIntro");
  await writeInto(1, BIG, "bigIntro");

  // 点空白处让编辑器失焦，再看内容有没有被 Froala 覆盖
  await page.click("h3", { force: true }).catch(() => {});
  await page.waitForTimeout(1500);

  const check = await page.evaluate(() => {
    const eds = [...document.querySelectorAll(".froala-element[contenteditable='true']")];
    return {
      editorPlain: eds.map((e) => (e.innerText || "").replace(/\s+/g, " ").slice(0, 60)),
      briefVal: (document.getElementById("briefIntro")?.value || "").length,
      bigVal: (document.getElementById("bigIntro")?.value || "").length,
      briefHasHtml: /<p>/.test(document.getElementById("briefIntro")?.value || ""),
      bigHasH3: /<h3>/.test(document.getElementById("bigIntro")?.value || ""),
    };
  });
  console.log("CHECK:", JSON.stringify(check));

  await page.screenshot({ path: "/tmp/intro_filled.png", fullPage: true });
  console.log("SHOT /tmp/intro_filled.png");

  if (DO_SUBMIT) {
    const r = await page.evaluate(() => {
      const target = document.getElementById("bigIntro");
      const btns = [...document.querySelectorAll('button,input[type="submit"]')].filter((x) =>
        /提交更改/.test((x.value || x.innerText || "").trim())
      );
      if (!btns.length) return "no-button";
      const tt = target?.getBoundingClientRect().top || 0;
      let best = btns[0],
        bestD = 1e9;
      for (const x of btns) {
        const d = Math.abs(x.getBoundingClientRect().top - tt);
        if (d < bestD) (bestD = d), (best = x);
      }
      best.click();
      return "clicked (of " + btns.length + ")";
    });
    console.log("SUBMIT:", r);
    await page.waitForTimeout(6000);
    console.log("URL:", page.url());
    const after = await page.evaluate(() => ({
      brief: (document.getElementById("briefIntro")?.value || "").length,
      big: (document.getElementById("bigIntro")?.value || "").length,
    }));
    console.log("AFTER_SAVE_LENGTHS:", JSON.stringify(after));
    await page.screenshot({ path: "/tmp/intro_submitted.png", fullPage: true });
    console.log("SHOT /tmp/intro_submitted.png");
  }

  await b.close();
})().catch((e) => {
  console.error("ERR:", e.message);
  process.exit(1);
});
