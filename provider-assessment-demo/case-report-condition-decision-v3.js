"use strict";

(() => {
  const VERSION = "2026.07.25-condition-report-bridge.3";
  const AUDIT_KEY = "pa-condition-report-template-audit-v3";
  const esc = (value) => String(value ?? "")
    .replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;").replaceAll("'", "&#039;");

  const caseById = (caseId) => {
    if (typeof store === "undefined" || !Array.isArray(store.cases)) return null;
    return store.cases.find((item) => item.caseId === caseId) || null;
  };

  const selectedCondition = (caseRecord) => {
    const registry = window.PA_CONDITION_PATHWAYS;
    const saved = caseRecord?.conditionPathway;
    if (saved?.slug) return registry?.conditions?.find((item) => item.slug === saved.slug) || saved;
    try {
      const local = JSON.parse(localStorage.getItem("pa-selected-condition-v1") || "null");
      return registry?.conditions?.find((item) => item.slug === local?.slug) || local;
    } catch (_) {
      return null;
    }
  };

  const unique = (items) => [...new Set(items.map((item) => String(item || "").trim()).filter(Boolean))];
  const lines = (title, items) => `${title}:\n${unique(items).map((item) => `- ${item}`).join("\n")}`;

  const buildTemplate = (condition, caseRecord) => {
    if (!condition) return null;
    const focus = unique(condition.focus || []).slice(0, 6);
    const primary = unique(condition.primary || []);
    const supporting = unique(condition.supporting || []);
    const external = unique(condition.external || []);
    const alerts = unique(condition.alerts || []).slice(0, 4);
    const deliverables = unique(condition.deliverables || []).slice(0, 5);
    const referral = String(caseRecord?.question || "").trim() ||
      `ما نمط نقاط القوة والاحتياجات والدعم المطلوب في ${focus.slice(0, 4).join("، ") || condition.title}، وكيف يظهر ذلك في أكثر من بيئة؟`;
    const family = [
      `أمثلة حديثة من الحياة اليومية مرتبطة بـ${focus.slice(0, 3).join("، ") || "المجالات المستهدفة"}.`,
      "ما الذي ينجزه الشخص باستقلال، وما مقدار التلميح أو المساعدة المطلوبة؟",
      "الاختلاف بين البيت والمدرسة أو العمل والمجتمع، والتكييفات التي تحسن الأداء.",
      ...alerts.map((item) => `تنبيه يجب مناقشته: ${item}`)
    ];
    const provider = [
      `عينات أداء وملاحظات مؤرخة مرتبطة بـ${focus.slice(0, 4).join("، ") || condition.title}.`,
      "ما نُفذ فعليًا من خدمات أو تدخلات، ومدته وشروطه ونتيجته، لا التوصيات العامة فقط.",
      primary.length ? `المصادر الأساسية المقترحة: ${primary.join("، ")}.` : "",
      supporting.length ? `المصادر المساندة المقترحة: ${supporting.join("، ")}.` : "",
      external.length ? `الخدمات أو التقارير الخارجية: ${external.join("، ")}.` : ""
    ];
    const closure = [
      "أُجيب سؤال الإحالة بأدلة متعددة المصادر.",
      "فُصلت نتيجة الأداة عن التفسير المهني ووُثقت صلاحيتها وحدودها.",
      "اتُفق مع الشخص أو الأسرة على خطوة تالية ومسؤول وموعد ومؤشر متابعة.",
      ...deliverables.map((item) => `مخرج مطلوب: ${item}`)
    ];
    return {
      version: VERSION,
      slug: condition.slug,
      title: condition.title,
      referral,
      focus,
      family,
      provider,
      closure,
      guideUrl: `conditions/${encodeURIComponent(condition.slug)}/`
    };
  };

  const readAudit = () => {
    try {
      const value = JSON.parse(localStorage.getItem(AUDIT_KEY) || "[]");
      return Array.isArray(value) ? value : [];
    } catch (_) {
      return [];
    }
  };

  const writeAudit = (entry) => {
    try {
      const next = [entry, ...readAudit()].slice(0, 100);
      localStorage.setItem(AUDIT_KEY, JSON.stringify(next));
    } catch (_) {}
  };

  const setIfEmpty = (field, value, changed) => {
    if (!field || String(field.value || "").trim() || !String(value || "").trim()) return;
    field.value = value;
    changed.push(field.name || field.id || "field");
    field.dispatchEvent(new Event("input", { bubbles: true }));
  };

  const applyTemplate = () => {
    const form = document.getElementById("case-report-form");
    if (!form) return;
    const caseRecord = caseById(form.elements.caseId?.value);
    const condition = selectedCondition(caseRecord);
    const template = buildTemplate(condition, caseRecord);
    if (!template) {
      if (typeof toast === "function") toast("اربط الحالة بأحد المسارات العشرين قبل تطبيق قالب القرار.");
      return;
    }
    const changed = [];
    setIfEmpty(form.elements.purpose, template.referral, changed);
    setIfEmpty(form.elements.evidenceSources, [
      `قالب مسار الحالة: ${template.title} (${template.version}).`,
      lines("أدلة الأسرة أو الشخص", template.family),
      lines("أدلة مقدم الخدمة", template.provider)
    ].join("\n\n"), changed);
    setIfEmpty(form.elements.functionalContexts,
      `المجالات والبيئات التي يلزم توثيقها: ${template.focus.join("، ")}. حدّد المهمة والبيئة ومستوى المساعدة والعوائق والميسرات في كل مصدر.`, changed);
    setIfEmpty(form.elements.followUpIndicators,
      `اختر مؤشرًا واحدًا قابلًا للملاحظة من: ${template.focus.join("، ")}. ثبّت طريقة القياس والبيئة ومستوى المساعدة قبل المقارنة.`, changed);
    setIfEmpty(form.elements.decision, lines("معيار إغلاق المسار", template.closure), changed);

    writeAudit({
      eventId: `CDT-${Date.now()}`,
      version: VERSION,
      at: new Date().toISOString(),
      uid: typeof identity !== "undefined" ? identity.uid : null,
      role: typeof identity !== "undefined" ? identity.role : null,
      caseId: caseRecord?.caseId || null,
      condition: template.slug,
      fieldsFilled: changed
    });

    const status = document.querySelector("[data-condition-template-status]");
    if (status) status.textContent = changed.length
      ? `طُبقت المسودة في الحقول الفارغة فقط: ${changed.join("، ")}. راجعها وعدّلها قبل الحفظ.`
      : "لم يُستبدل أي حقل لأن الحقول المقترحة تحتوي بيانات مسبقًا.";
    if (typeof toast === "function") toast(changed.length ? "طُبقت مسودة مسار الحالة دون استبدال البيانات الحالية." : "لم تتغير الحقول الحالية.");
  };

  const render = () => {
    const form = document.getElementById("case-report-form");
    const anchor = document.getElementById("report-condition-context");
    if (!form || !anchor) return;
    let panel = document.getElementById("condition-report-template-v3");
    if (!panel) {
      panel = document.createElement("section");
      panel.id = "condition-report-template-v3";
      panel.className = "condition-report-context";
      panel.dataset.conditionReportTemplate = VERSION;
      anchor.insertAdjacentElement("afterend", panel);
    }
    const caseRecord = caseById(form.elements.caseId?.value);
    const condition = selectedCondition(caseRecord);
    const template = buildTemplate(condition, caseRecord);
    if (!template) {
      panel.innerHTML = "<strong>قالب قرار الحالة:</strong> غير متاح قبل ربط الحالة بأحد المسارات العشرين.";
      return;
    }
    panel.innerHTML = `
      <strong>قالب قرار الحالة: ${esc(template.title)}</strong>
      <p>${esc(template.referral)}</p>
      <ul>${template.focus.map((item) => `<li>${esc(item)}</li>`).join("")}</ul>
      <div class="actions">
        <button class="button secondary" type="button" data-apply-condition-template>تطبيق المسودة في الحقول الفارغة</button>
        <a class="button ghost" href="${esc(template.guideUrl)}">فتح دليل الحالة</a>
      </div>
      <p class="muted" data-condition-template-status aria-live="polite">لا يختار القالب نوع التقييم، ولا يملأ صلاحية النتيجة أو خط الأساس أو الهدف؛ هذه تتطلب بيانات فعلية وقرارًا مهنيًا.</p>`;
  };

  const install = () => {
    render();
    document.addEventListener("click", (event) => {
      if (event.target.closest("[data-apply-condition-template]")) applyTemplate();
      const button = event.target.closest("button");
      if (button?.dataset.openReport || button?.dataset.newVersion || button?.dataset.caseReport || button?.id === "new-case-report") {
        setTimeout(render, 0);
      }
    });
    const dialog = document.getElementById("case-report-dialog");
    if (dialog) new MutationObserver(() => { if (dialog.hasAttribute("open")) setTimeout(render, 0); })
      .observe(dialog, { attributes: true, attributeFilter: ["open"] });
    formObserver();
  };

  const formObserver = () => {
    const form = document.getElementById("case-report-form");
    if (!form) return;
    form.addEventListener("change", (event) => {
      if (event.target?.name === "caseId") render();
    });
  };

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", install, { once: true });
  else install();

  window.PA_CONDITION_REPORT_BRIDGE = Object.freeze({ version: VERSION, applyTemplate, buildTemplate });
})();
