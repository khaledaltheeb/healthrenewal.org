"use strict";

(() => {
  const RELEASE = "220.3";
  const escapeHtml = (value) => String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");

  const tools = () => window.PA_DEMO_DATA?.explorers || [];
  const findToolByTitle = (title) => tools().find((tool) => title.includes(tool.title));
  const list = (items) => `<ul class="clean-list">${(items || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`;

  const protocolHtml = (tool, compact = false) => {
    const protocol = tool?.protocol;
    if (!protocol) return "";
    return `<section class="panel" data-v220-protocol="${escapeHtml(tool.id)}">
      <div class="section-heading compact"><div><p class="eyebrow">بروتوكول الاستكشاف v${escapeHtml(protocol.version)}</p><h3>حدود التطبيق وجودة المعلومات</h3></div><span class="badge neutral">${escapeHtml(tool.questions.length)} بندًا · ${escapeHtml(protocol.domains.length)} مجالًا</span></div>
      <dl class="summary-grid">
        <div><dt>سؤال الإحالة</dt><dd>${escapeHtml(protocol.referralQuestion)}</dd></div>
        <div><dt>فترة الملاحظة</dt><dd>${escapeHtml(protocol.observationWindow)}</dd></div>
        <div><dt>موعد المتابعة</dt><dd>${escapeHtml(protocol.followUp)}</dd></div>
        <div><dt>حالة الحقوق</dt><dd>محتوى استكشافي أصلي للمنصة</dd></div>
      </dl>
      ${compact ? "" : `<div class="two-column"><div><h4>مصادر المعلومات المقترحة</h4>${list(protocol.respondents)}</div><div><h4>السياقات</h4>${list(protocol.contexts)}</div></div>
      <div class="two-column"><div><h4>يستخدم عندما</h4>${list(protocol.useWhen)}</div><div><h4>لا يستخدم عندما</h4>${list(protocol.doNotUseWhen)}</div></div>`}
      <div class="callout warning"><strong>حدود التفسير:</strong> ${escapeHtml(protocol.interpretationLimits.join(" "))}</div>
    </section>`;
  };

  const enhanceExplorerCards = () => {
    document.querySelectorAll("#explorer-list .assessment-card").forEach((card) => {
      const title = card.querySelector("h3")?.textContent || "";
      const tool = findToolByTitle(title);
      if (!tool?.protocol || card.querySelector("[data-v220-card]")) return;
      const meta = document.createElement("div");
      meta.className = "callout info";
      meta.dataset.v220Card = tool.id;
      meta.innerHTML = `<strong>مسار موسع:</strong> ${escapeHtml(tool.protocol.domains.length)} مجالًا، فترة الملاحظة: ${escapeHtml(tool.protocol.observationWindow)}. النتيجة وصفية غير تشخيصية.`;
      const actions = card.querySelector(".card-actions");
      card.insertBefore(meta, actions || null);
    });
  };

  const enhanceAssessmentDialog = () => {
    const content = document.getElementById("assessment-content");
    if (!content || content.querySelector("[data-v220-protocol]")) return;
    const title = content.querySelector("h2")?.textContent || "";
    const tool = findToolByTitle(title);
    if (!tool?.protocol) return;
    const wrapper = document.createElement("div");
    wrapper.innerHTML = protocolHtml(tool, true);
    const intro = content.querySelector(".assessment-intro");
    intro?.insertAdjacentElement("afterend", wrapper.firstElementChild);
  };

  const findStoredSession = (sessionId) => {
    if (!sessionId) return null;
    for (let index = 0; index < localStorage.length; index += 1) {
      const key = localStorage.key(index);
      if (!key?.startsWith("pa-demo-store-v3:")) continue;
      try {
        const localStore = JSON.parse(localStorage.getItem(key));
        for (const caseRecord of localStore?.cases || []) {
          const session = (caseRecord.sessions || []).find((item) => item.sessionId === sessionId);
          if (session) return { caseRecord, session };
        }
      } catch {
        // Ignore malformed unrelated local data; the core app already guards its own store.
      }
    }
    return null;
  };

  const qualityFor = (tool, session) => {
    const answers = session?.answers || {};
    const scored = tool.questions.filter((question) => question.type !== "textarea");
    const narrative = tool.questions.filter((question) => question.type === "textarea");
    let answered = 0;
    let unknown = 0;
    let narrativeEvidence = 0;
    for (const question of scored) {
      const answer = answers[question.id];
      const values = Array.isArray(answer) ? answer : [answer];
      if (values.some((value) => value !== "" && value !== null && value !== undefined)) answered += 1;
      if (values.includes("unknown")) unknown += 1;
    }
    for (const question of narrative) {
      if (String(answers[question.id] || "").trim().length >= 20) narrativeEvidence += 1;
    }
    const completion = scored.length ? Math.round((answered / scored.length) * 100) : 0;
    const unknownRate = scored.length ? Math.round((unknown / scored.length) * 100) : 0;
    const label = unknownRate <= 10 && narrativeEvidence > 0
      ? "جيدة مبدئيًا"
      : unknownRate <= 25
        ? "متوسطة وتحتاج مراجعة السياق"
        : "محدودة وتحتاج معلومات إضافية";
    return { completion, unknownRate, narrativeEvidence, label };
  };

  const enhanceResultDialog = () => {
    const content = document.getElementById("result-content");
    if (!content || content.querySelector("[data-v220-quality]")) return;
    const heading = content.querySelector("h2")?.textContent || "";
    const tool = findToolByTitle(heading);
    if (!tool?.protocol) return;

    content.querySelectorAll(".signal-card span").forEach((label) => {
      const key = label.textContent?.trim();
      if (key && window.PA_DOMAIN_LABELS?.[key]) label.textContent = window.PA_DOMAIN_LABELS[key];
    });

    const sessionId = content.querySelector(".eyebrow")?.textContent?.match(/SES-[A-Z0-9]+/)?.[0];
    const stored = findStoredSession(sessionId);
    const quality = qualityFor(tool, stored?.session);
    const panel = document.createElement("section");
    panel.className = "panel";
    panel.dataset.v220Quality = tool.id;
    panel.innerHTML = `<div class="section-heading compact"><div><p class="eyebrow">جودة المعلومات</p><h3>${escapeHtml(quality.label)}</h3></div><span class="badge neutral">بروتوكول v${RELEASE}</span></div>
      <dl class="summary-grid"><div><dt>اكتمال البنود القابلة للتلخيص</dt><dd>${quality.completion}%</dd></div><div><dt>الإجابات غير المعروفة</dt><dd>${quality.unknownRate}%</dd></div><div><dt>ملاحظات سياقية كافية</dt><dd>${quality.narrativeEvidence}</dd></div><div><dt>صلاحية المقارنة</dt><dd>تحتاج ثبات سؤال الإحالة والسياق والمستجيب</dd></div></dl>
      <div class="callout info"><strong>التفسير:</strong> ${escapeHtml(tool.protocol.interpretationLimits.join(" "))}</div>`;
    const recommendation = content.querySelector(".recommendation-box");
    recommendation?.insertAdjacentElement("beforebegin", panel);
  };

  const enhanceGuideDialog = () => {
    const content = document.getElementById("result-content");
    if (!content || content.querySelector("[data-v220-protocol]")) return;
    const title = content.querySelector("h2")?.textContent || "";
    if (title.startsWith("نتيجة ")) return;
    const tool = findToolByTitle(title);
    if (!tool?.protocol) return;
    const wrapper = document.createElement("div");
    wrapper.innerHTML = protocolHtml(tool, false);
    content.querySelector(".dialog-actions")?.insertAdjacentElement("beforebegin", wrapper.firstElementChild);
  };

  const ensureScriptReady = ({ selector, src, datasetKey, ready, onReady, onFailure, attempts = 120 }) => {
    if (ready()) {
      onReady();
      return;
    }
    let script = document.querySelector(selector);
    if (!script) {
      script = document.createElement("script");
      script.src = `${src}?release=${encodeURIComponent(RELEASE)}`;
      script.defer = true;
      script.dataset[datasetKey] = RELEASE;
      document.head.appendChild(script);
    }
    let settled = false;
    const fail = (reason) => {
      if (settled) return;
      settled = true;
      console.error(reason);
      onFailure?.();
    };
    script.addEventListener("error", () => fail(`Failed to load ${src}`), { once: true });
    const poll = (remaining) => {
      if (settled) return;
      if (ready()) {
        settled = true;
        onReady();
        return;
      }
      if (remaining <= 0) {
        fail(`${src} loaded without exposing its v220 readiness contract`);
        return;
      }
      setTimeout(() => poll(remaining - 1), 50);
    };
    poll(attempts);
  };

  const loadReportIntegration = (attempt = 0) => {
    if (!document.getElementById("case-report-form")) {
      if (attempt < 120) setTimeout(() => loadReportIntegration(attempt + 1), 50);
      else console.error("Case report form did not become available for professional v220 integration");
      return;
    }
    ensureScriptReady({
      selector: 'script[data-professional-report-v220]',
      src: "professional-registry-report-integration-v220.js",
      datasetKey: "professionalReportV220",
      ready: () => Boolean(window.PA_PROFESSIONAL_REPORT_V220),
      onReady: () => undefined,
      onFailure: () => console.error("Professional report integration remains unavailable"),
    });
  };

  const loadEditIntegration = () => ensureScriptReady({
    selector: 'script[data-professional-edit-v220]',
    src: "professional-registry-edit-v220.js",
    datasetKey: "professionalEditV220",
    ready: () => Boolean(window.PA_PROFESSIONAL_EDIT_V220),
    onReady: loadReportIntegration,
    onFailure: () => {
      console.error("Professional legacy-record upgrade UI remains unavailable");
      loadReportIntegration();
    },
  });

  const loadPlanningCompatibility = () => ensureScriptReady({
    selector: 'script[data-professional-planning-compat-v220]',
    src: "professional-registry-planning-compat-v220.js",
    datasetKey: "professionalPlanningCompatV220",
    ready: () => Boolean(window.PA_PROFESSIONAL_PLANNING_COMPAT_V220),
    onReady: loadEditIntegration,
    onFailure: () => {
      console.error("Professional planning compatibility failed; draft records remain in stricter fallback mode");
      loadEditIntegration();
    },
  });

  const loadProfessionalUi = () => ensureScriptReady({
    selector: 'script[data-professional-registry-ui-v220]',
    src: "professional-registry-maturity-ui-v220.js",
    datasetKey: "professionalRegistryUiV220",
    ready: () => Boolean(window.PA_PROFESSIONAL_RECORD_V220),
    onReady: loadPlanningCompatibility,
    onFailure: () => console.error("Professional registry maturity UI remains unavailable"),
  });

  const loadProfessionalRegistry = () => ensureScriptReady({
    selector: 'script[data-professional-registry-contract-v220]',
    src: "professional-registry-contract-v220.js",
    datasetKey: "professionalRegistryContractV220",
    ready: () => Boolean(window.PA_PROFESSIONAL_REGISTRY_V220),
    onReady: loadProfessionalUi,
    onFailure: () => console.error("Professional registry rights contract remains unavailable"),
  });

  const refresh = () => {
    enhanceExplorerCards();
    enhanceAssessmentDialog();
    enhanceGuideDialog();
    enhanceResultDialog();
  };

  const boot = () => {
    refresh();
    loadProfessionalRegistry();
    new MutationObserver(refresh).observe(document.body, { childList: true, subtree: true });
  };
  window.PA_EXPLORATORY_V220_REFRESH = refresh;
  if (document.readyState === "loading") {
    window.addEventListener("DOMContentLoaded", boot, { once: true });
  } else {
    boot();
  }
})();
