#!/usr/bin/env node
"use strict";

/**
 * Pre-render every provider-assessment condition from the governed registry.
 * Browser JavaScript remains available for interaction, while crawlers and
 * no-script users receive the complete semantic content in initial HTML.
 */
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const ROOT = path.resolve(__dirname, "..");
const CONDITIONS = path.join(ROOT, "provider-assessment-demo", "conditions");
const ORIGIN = "https://healthrenewal.org";
const START = "<!-- provider-prerender:v1:start -->";
const END = "<!-- provider-prerender:v1:end -->";

const escapeHtml = (value) => String(value ?? "")
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;")
  .replaceAll("'", "&#039;");

const list = (items, className = "list") => `<ul class="${className}">${(items || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`;

function loadRegistry() {
  const source = fs.readFileSync(path.join(CONDITIONS, "conditions-data-v1.js"), "utf8");
  const sandbox = { window: {} };
  vm.createContext(sandbox);
  vm.runInContext(source, sandbox, { filename: "conditions-data-v1.js" });
  const registry = sandbox.window.PA_CONDITION_PATHWAYS;
  if (!registry || !Array.isArray(registry.conditions) || !Array.isArray(registry.workflowStages)) {
    throw new Error("Provider assessment registry is missing or malformed");
  }
  return registry;
}

function faqItems(condition) {
  const firstAlert = (condition.alerts || [])[0] || "لا يعتمد القرار المهني على مقياس واحد أو نتيجة منفردة.";
  return [
    [
      `ما الذي يشمله تقييم ${condition.title}؟`,
      condition.summary,
    ],
    [
      "هل يكفي مقياس واحد لاتخاذ القرار؟",
      `${firstAlert} تجمع الخطة بين التاريخ والملاحظة والمصادر المتعددة والوظيفة والمشاركة، مع توثيق حدود كل أداة.`,
    ],
    [
      "متى نحتاج تقييمًا مكمّلًا؟",
      "يطلب تقييم مكمّل عندما تتعارض النتائج بين المصادر أو البيئات، أو تبقى فجوة مهمة في الصحة أو اللغة أو المعرفة أو التكيف أو الحس أو الحركة أو السلامة.",
    ],
    [
      "ما الذي يجب أن يتضمنه التقرير النهائي؟",
      (condition.deliverables || []).join(" "),
    ],
  ];
}

function schema(condition, url) {
  const faq = faqItems(condition);
  return {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "MedicalWebPage",
        "@id": `${url}#webpage`,
        name: `مسار تقييم ${condition.title}`,
        headline: `تقييم ${condition.title}`,
        description: condition.summary,
        url,
        inLanguage: "ar",
        about: { "@type": "MedicalCondition", name: condition.title },
        breadcrumb: { "@id": `${url}#breadcrumb` },
        mainEntity: { "@id": `${url}#faq` },
        isPartOf: {
          "@type": "CollectionPage",
          name: "مسارات التقييم المهني",
          url: `${ORIGIN}/provider-assessment-demo/conditions/`,
        },
      },
      {
        "@type": "BreadcrumbList",
        "@id": `${url}#breadcrumb`,
        itemListElement: [
          { "@type": "ListItem", position: 1, name: "الرئيسية", item: `${ORIGIN}/` },
          { "@type": "ListItem", position: 2, name: "منصة التقييم", item: `${ORIGIN}/provider-assessment-demo/` },
          { "@type": "ListItem", position: 3, name: "مسارات الحالات", item: `${ORIGIN}/provider-assessment-demo/conditions/` },
          { "@type": "ListItem", position: 4, name: condition.title, item: url },
        ],
      },
      {
        "@type": "FAQPage",
        "@id": `${url}#faq`,
        mainEntity: faq.map(([question, answer]) => ({
          "@type": "Question",
          name: question,
          acceptedAnswer: { "@type": "Answer", text: answer },
        })),
      },
    ],
  };
}

function toolGroup(title, items) {
  return `<section class="tool-group"><h3>${escapeHtml(title)}</h3>${list(items)}</section>`;
}

function render(condition, registry) {
  const faq = faqItems(condition);
  return `${START}
<div id="condition-root" aria-busy="false" data-provider-prerender="v1">
  <nav class="breadcrumb" aria-label="مسار التنقل"><a href="../../../">الرئيسية</a> / <a href="../../">منصة التقييم</a> / <a href="../">مسارات الحالات</a> / <span aria-current="page">${escapeHtml(condition.title)}</span></nav>
  <section class="hero">
    <p class="eyebrow">مسار تقييم مؤسسي متعدد التخصصات</p>
    <h1>تقييم ${escapeHtml(condition.title)}</h1>
    <p class="lead">${escapeHtml(condition.summary)}</p>
    <div class="actions"><button class="button" type="button" data-start-condition="${escapeHtml(condition.slug)}">بدء مسار هذه الحالة</button><a class="button secondary" href="../../">فتح منصة التقييم والسجل المهني</a><button class="button secondary" type="button" onclick="window.print()">طباعة الدليل</button></div>
    <p class="notice">هذا المسار ينظم جمع المعلومات والتوثيق ولا يحول نتيجة منفردة إلى تشخيص. التطبيق الرسمي لأي مقياس معياري يتم بالنسخة الأصلية وبواسطة شخص مؤهل، وتفسر النتائج داخل السياق الصحي واللغوي والتعليمي والبيئي للشخص.</p>
  </section>
  <div class="layout">
    <article class="stack">
      <section class="panel"><h2>ما الذي يشمله تقييم ${escapeHtml(condition.title)}؟</h2><p>${escapeHtml(condition.summary)}</p><h3>مجالات التركيز الوظيفي</h3>${list(condition.focus)}</section>
      <section class="panel"><h2>فريق التقييم المقترح</h2><p>يتغير الفريق بحسب سؤال الإحالة والعمر واللغة والحالة الصحية والبيئات التي تظهر فيها الحاجة. الأدوار التالية نقطة تنظيم وليست قائمة إلزامية لكل شخص.</p>${list(condition.team)}</section>
      <section class="panel"><h2>حزمة المقاييس والفحوص</h2><div class="tool-groups">${toolGroup("المقاييس الأساسية", condition.primary)}${toolGroup("المقاييس المساندة", condition.supporting)}${toolGroup("الفحوص والخدمات الخارجية", condition.external)}</div><p class="notice">اختيار الأداة يعتمد على الغرض والعمر واللغة والقدرة والنسخة المرخصة وكفاءة المنفذ. لا تجمع الأدوات لمجرد زيادة العدد، ولا تفسر الدرجة بمعزل عن الملاحظة والسياق.</p></section>
      <section class="panel"><h2>كيف تسير عملية التقييم؟</h2><ol class="stages">${registry.workflowStages.map((stage) => `<li>${escapeHtml(stage)}</li>`).join("")}</ol></section>
      <section class="panel"><h2>مخرجات التقرير المطلوبة</h2>${list(condition.deliverables)}<h3>قواعد القرار والمتابعة</h3><ul class="list"><li>يستمر المسار عندما توجد فجوة مهمة لم يُجب عنها سؤال الإحالة.</li><li>يطلب تقييم مكمّل عند تعارض النتائج بين المصادر أو البيئات.</li><li>يغلق المسار عندما توثق النتائج والقيود وخطة الدعم ومؤشرات المتابعة.</li><li>تعطى الأولوية للصحة أو السلامة عند وجود خطر مباشر أو تدهور أو فقدان مهارة.</li></ul></section>
      <section class="panel intent-faq" data-search-intent-faq="provider-v1"><h2>أسئلة شائعة عن مسار التقييم</h2>${faq.map(([question, answer]) => `<article class="faq-item"><h3>${escapeHtml(question)}</h3><p>${escapeHtml(answer)}</p></article>`).join("")}</section>
    </article>
    <aside class="stack aside-card">
      <section class="panel"><h2>تنبيهات مهنية</h2>${list(condition.alerts)}</section>
      <section class="panel"><h2>قبل بدء السجل</h2><p>حدد سؤال الإحالة والقرار المطلوب، ثم اختر المصادر والبيئات والفريق. لا تدخل معلومات تعريفية حساسة في جهاز مشترك، ووثق النسخة واللغة والتكييفات وحدود التطبيق.</p></section>
      <section class="panel"><h2>مسارات مشتركة</h2>${registry.commonDomains.slice(0, 6).map((domain) => `<p><strong>${escapeHtml(domain.name)}:</strong> ${escapeHtml(domain.tools.join("، "))}</p>`).join("")}</section>
    </aside>
  </div>
</div>
${END}`;
}

function removeMetaKeywords(source) {
  return source.replace(/\s*<meta\s+name=["']keywords["'][^>]*>\s*/gi, "\n");
}

function ensureHreflang(source, canonical) {
  const tag = `<link rel="canonical" href="${canonical}">`;
  if (!source.includes(tag)) throw new Error(`Canonical not found: ${canonical}`);
  const additions = [];
  if (!source.includes('hreflang="ar"')) additions.push(`<link rel="alternate" hreflang="ar" href="${canonical}">`);
  if (!source.includes('hreflang="x-default"')) additions.push(`<link rel="alternate" hreflang="x-default" href="${canonical}">`);
  return additions.length ? source.replace(tag, tag + additions.join("")) : source;
}

function replaceJsonLd(source, payload) {
  const script = `<script type="application/ld+json">${JSON.stringify(payload)}</script>`;
  const pattern = /<script\s+type=["']application\/ld\+json["'][^>]*>[\s\S]*?<\/script>/i;
  if (!pattern.test(source)) throw new Error("Primary JSON-LD block missing");
  return source.replace(pattern, script);
}

function replaceRoot(source, rendered) {
  if (source.includes(START) && source.includes(END)) {
    const start = source.indexOf(START);
    const end = source.indexOf(END, start) + END.length;
    return source.slice(0, start) + rendered + source.slice(end);
  }
  const start = source.indexOf('<div id="condition-root"');
  if (start < 0) throw new Error("Condition root missing");
  const noScriptEnd = source.indexOf("</noscript>", start);
  if (noScriptEnd < 0) throw new Error("No-script boundary missing");
  return source.slice(0, start) + rendered + source.slice(noScriptEnd + "</noscript>".length);
}

function updatePage(condition, registry) {
  const file = path.join(CONDITIONS, condition.slug, "index.html");
  if (!fs.existsSync(file)) throw new Error(`Condition page missing: ${condition.slug}`);
  const canonical = `${ORIGIN}/provider-assessment-demo/conditions/${condition.slug}/`;
  let source = fs.readFileSync(file, "utf8");
  source = removeMetaKeywords(source);
  source = ensureHreflang(source, canonical);
  source = replaceJsonLd(source, schema(condition, canonical));
  source = replaceRoot(source, render(condition, registry));
  return { file, source };
}

function main() {
  const mode = process.argv.includes("--check") ? "check" : process.argv.includes("--write") ? "write" : "";
  if (!mode) throw new Error("Use --write or --check");
  const registry = loadRegistry();
  const changes = [];
  for (const condition of registry.conditions) {
    const { file, source } = updatePage(condition, registry);
    const current = fs.readFileSync(file, "utf8");
    if (source !== current) changes.push({ file, source });
  }
  if (mode === "check") {
    for (const change of changes) console.log(path.relative(ROOT, change.file));
    process.exitCode = changes.length ? 1 : 0;
    return;
  }
  for (const change of changes) fs.writeFileSync(change.file, change.source, "utf8");
  console.log(`Updated ${changes.length} provider-assessment condition pages`);
}

main();
