import fs from "node:fs";
import { chromium } from "playwright";

const url = process.argv[2] || "http://127.0.0.1:8765/provider-assessment-demo/";
const output = process.argv[3] || "/tmp/provider-layout-probe-v225.json";
const executablePath = process.env.CHROME_PATH || chromium.executablePath();
const browser = await chromium.launch({
  executablePath,
  headless: true,
  args: ["--no-sandbox", "--disable-dev-shm-usage"],
});
const context = await browser.newContext({ viewport: { width: 1350, height: 940 } });
const page = await context.newPage();

await page.addInitScript(() => {
  const rect = (element) => {
    if (!element) return null;
    const box = element.getBoundingClientRect();
    return {
      top: box.top,
      bottom: box.bottom,
      left: box.left,
      right: box.right,
      width: box.width,
      height: box.height,
    };
  };
  const text = (element) => (element?.textContent || "").replace(/\s+/g, " ").trim().slice(0, 500);
  window.__providerLayoutV225 = { shifts: [], samples: [], mutations: [], errors: [] };
  const snapshot = (reason) => ({
    reason,
    at: performance.now(),
    readyState: document.readyState,
    header: rect(document.querySelector(".site-header")),
    headerText: text(document.querySelector(".site-header")),
    notice: rect(document.querySelector(".notice-bar")),
    noticeText: text(document.querySelector(".notice-bar")),
    main: rect(document.querySelector("main#main")),
    tabs: rect(document.querySelector(".tabs")),
    hero: rect(document.querySelector(".hero")),
    heroCard: rect(document.querySelector(".hero-card")),
    bodyChildren: [...document.body?.children || []].map((node) => ({
      tag: node.tagName,
      id: node.id,
      className: typeof node.className === "string" ? node.className : "",
      rect: rect(node),
    })),
  });
  const describeNode = (node) => {
    if (!node) return null;
    return {
      tag: node.tagName,
      id: node.id || "",
      className: typeof node.className === "string" ? node.className : "",
      text: text(node).slice(0, 180),
    };
  };
  new PerformanceObserver((list) => {
    for (const entry of list.getEntries()) {
      if (entry.hadRecentInput) continue;
      window.__providerLayoutV225.shifts.push({
        at: entry.startTime,
        value: entry.value,
        sources: (entry.sources || []).map((source) => ({
          node: describeNode(source.node),
          previousRect: source.previousRect,
          currentRect: source.currentRect,
        })),
        snapshot: snapshot("layout-shift"),
      });
    }
  }).observe({ type: "layout-shift", buffered: true });
  addEventListener("error", (event) => {
    window.__providerLayoutV225.errors.push({ at: performance.now(), message: event.message });
  });
  addEventListener("unhandledrejection", (event) => {
    window.__providerLayoutV225.errors.push({ at: performance.now(), message: String(event.reason) });
  });
  addEventListener("DOMContentLoaded", () => {
    window.__providerLayoutV225.samples.push(snapshot("DOMContentLoaded"));
    const observer = new MutationObserver((records) => {
      const relevant = records.some((record) => {
        const target = record.target?.nodeType === Node.TEXT_NODE ? record.target.parentElement : record.target;
        return target?.closest?.(".site-header,.notice-bar,.hero,.hero-card,.tabs") ||
          [...record.addedNodes].some((node) => node.nodeType === Node.ELEMENT_NODE && node.matches?.(".site-header,.notice-bar,.hero,.hero-card,.tabs"));
      });
      if (relevant) window.__providerLayoutV225.mutations.push(snapshot("relevant-mutation"));
    });
    observer.observe(document.body, { childList: true, subtree: true, characterData: true, attributes: true });
  }, { once: true });
  addEventListener("load", () => window.__providerLayoutV225.samples.push(snapshot("load")), { once: true });
  let frames = 0;
  let previous = "";
  const sampleFrame = () => {
    const current = snapshot(`frame-${frames}`);
    const signature = JSON.stringify({ header: current.header, notice: current.notice, main: current.main, tabs: current.tabs, hero: current.hero, heroCard: current.heroCard });
    if (signature !== previous) {
      window.__providerLayoutV225.samples.push(current);
      previous = signature;
    }
    frames += 1;
    if (performance.now() < 5000) requestAnimationFrame(sampleFrame);
  };
  requestAnimationFrame(sampleFrame);
});

await page.goto(url, { waitUntil: "networkidle", timeout: 60000 });
await page.waitForTimeout(5500);
const report = await page.evaluate(() => ({
  ...window.__providerLayoutV225,
  finalUrl: location.href,
  finalTitle: document.title,
  cls: window.__providerLayoutV225.shifts.reduce((total, item) => total + item.value, 0),
}));
fs.writeFileSync(output, `${JSON.stringify(report, null, 2)}\n`, "utf8");
console.log(JSON.stringify({
  cls: report.cls,
  shifts: report.shifts.length,
  samples: report.samples.length,
  mutations: report.mutations.length,
  errors: report.errors,
}, null, 2));
await browser.close();
