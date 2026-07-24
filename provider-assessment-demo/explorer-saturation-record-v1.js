"use strict";

(() => {
  const RELEASE = "2026.07.25-explorer-record.1";
  const STORE_VERSION = "3";
  const SCHEMA = "pa-explorer-saturation-record-v1";
  const PROFILE_SCHEMA = "pa-explorer-saturation-v1";
  const idsKey = `pa-demo-identities-v${STORE_VERSION}`;
  const activeKey = `pa-demo-active-v${STORE_VERSION}`;
  let pending = null;
  let activeGuideId = null;

  const esc = (value) => String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");

  const read = (key, fallback = null) => {
    try {
      const raw = localStorage.getItem(key);
      return raw === null ? fallback : JSON.parse(raw);
    } catch (_) {
      return fallback;
    }
  };

  const activeIdentity = () => {
    const identities = read(idsKey, {});
    const active = read(activeKey, null);
    if (active?.role === "provider" && identities?.[active.username]) return identities[active.username];
    return identities?.__visitor__ || null;
  };

  const storeKey = (uid) => `pa-demo-store-v${STORE_VERSION}:${uid}`;
  const tools = () => window.PA_DEMO_DATA?.explorers || [];
  const findTool = (id) => tools().find((tool) => tool.id === id) || null;

  const toolForForm = (form) => tools().find(
    (tool) => tool.institutionalProfile?.schema === PROFILE_SCHEMA
      && tool.questions.some((question) => form.elements.namedItem(question.id)),
  ) || null;

  const answer = (data, name) => {
    const values = data.getAll(name).map((value) => String(value).trim()).filter(Boolean);
    if (!values.length) return "";
    return values.length === 1 ? values[0] : values;
  };

  const snapshotProfile = (tool) => {
    const profile = tool.institutionalProfile;
    return {
      schema: profile.schema,
      release: profile.release,
      toolId: tool.id,
      title: tool.title,
      category: tool.category,
      ages: [...tool.ages],
      domains: [...profile.domains],
      respondents: [...profile.respondents],
      environments: [...profile.environments],
      confounders: [...profile.confounders],
      supports: [...profile.supports],
      reportOutputs: [...profile.reportOutputs],
      followUpRules: [...profile.followUpRules],
      frameworkIds: profile.frameworks.map((item) => item.id),
      interpretationBoundary: profile.interpretationBoundary,
      professionalRecordLinkage: profile.professionalRecordLinkage,
      longitudinalComparabilityRequired: profile.longitudinalComparabilityRequired,
    };
  };

  const buildPending = (form, tool) => {
    const data = new FormData(form);
    const prefix = tool.id;
    const safetyQuestion = tool.questions.find((question) => question.safety === true);
    const safetyAnswer = safetyQuestion ? answer(data, safetyQuestion.id) : "";
    const dataQuality = {
      respondent: answer(data, `${prefix}-ctx-source`),
      observationWindow: answer(data, `${prefix}-ctx-window`),
      primarySetting: answer(data, `${prefix}-ctx-setting`),
      accommodations: answer(data, `${prefix}-ctx-access`),
      strengths: answer(data, `${prefix}-ctx-strength`),
      confidence: answer(data, `${prefix}-ctx-confidence`),
    };
    const documentedFields = Object.values(dataQuality).filter((value) => Array.isArray(value) ? value.length : String(value || "").trim()).length;
    return {
      assessmentId: tool.id,
      capturedAt: new Date().toISOString(),
      profile: snapshotProfile(tool),
      dataQuality: {
        ...dataQuality,
        documentedFields,
        requiredFields: 6,
        completeness: documentedFields === 6 ? "complete" : "incomplete",
      },
      safetyReview: {
        questionId: safetyQuestion?.id || null,
        answer: safetyAnswer,
        urgent: safetyAnswer === "immediate",
        concern: safetyAnswer === "concern",
        humanActionRequired: safetyAnswer === "immediate" || safetyAnswer === "concern",
      },
    };
  };

  const capture = (event) => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement) || form.id !== "assessment-form") return;
    const tool = toolForForm(form);
    if (!tool) return;
    pending = buildPending(form, tool);
    queueMicrotask(attachToLatestSession);
    setTimeout(attachToLatestSession, 50);
  };

  const attachToLatestSession = () => {
    if (!pending) return null;
    const identity = activeIdentity();
    if (!identity?.uid) return null;
    const key = storeKey(identity.uid);
    const store = read(key, null);
    if (!store?.cases) return null;
    const candidates = store.cases.flatMap((caseRecord) =>
      (caseRecord.sessions || []).map((session) => ({ caseRecord, session })),
    ).filter(({ session }) =>
      session.assessmentId === pending.assessmentId
      && !session.explorerSaturationRecord,
    ).sort((a, b) => new Date(b.session.completedAt) - new Date(a.session.completedAt));
    const candidate = candidates[0];
    if (!candidate || Date.now() - new Date(candidate.session.completedAt).getTime() > 15000) return null;

    const now = new Date().toISOString();
    candidate.session.explorerSaturationRecord = {
      schema: SCHEMA,
      release: RELEASE,
      recordedAt: now,
      recordedByUid: identity.uid,
      recordedByRole: identity.role,
      profile: pending.profile,
      dataQuality: pending.dataQuality,
      safetyReview: pending.safetyReview,
      professionalRecordBridge: {
        status: "ready_for_human_review",
        outputFields: [...pending.profile.reportOutputs],
        followUpRules: [...pending.profile.followUpRules],
        confoundersToReview: [...pending.profile.confounders],
        supportsToTrial: [...pending.profile.supports],
        interpretationBoundary: "exploratory-non-diagnostic-human-review-required",
        automatedDiagnosis: false,
        automatedEligibilityDecision: false,
        protectedInstrumentContent: false,
      },
    };
    candidate.caseRecord.updatedAt = now;
    store.updatedAt = now;
    localStorage.setItem(key, JSON.stringify(store));
    const detail = {
      caseId: candidate.caseRecord.caseId,
      sessionId: candidate.session.sessionId,
      assessmentId: candidate.session.assessmentId,
      record: candidate.session.explorerSaturationRecord,
    };
    pending = null;
    window.dispatchEvent(new CustomEvent("pa-explorer-saturation-record-saved", { detail }));
    return detail;
  };

  const list = (items) => `<ul>${items.map((item) => `<li>${esc(item)}</li>`).join("")}</ul>`;

  const guidePanel = (tool) => {
    const profile = tool.institutionalProfile;
    return `<section class="panel explorer-institutional-profile" data-explorer-profile="${esc(tool.id)}">
      <div class="section-heading compact"><div><h3>ملف التطبيق المؤسسي</h3><p class="muted">إطار متعدد المصادر والسياقات؛ لا يحول النتيجة إلى تشخيص أو درجة معيارية.</p></div><span class="badge neutral">${tool.questions.length} عنصرًا</span></div>
      <div class="two-column">
        <div><h4>المجالات</h4>${list(profile.domains)}</div>
        <div><h4>المجيبون والبيئات</h4>${list([...profile.respondents, ...profile.environments])}</div>
        <div><h4>عوامل يجب مراجعتها</h4>${list(profile.confounders)}</div>
        <div><h4>التكييفات والدعم</h4>${list(profile.supports)}</div>
        <div><h4>مخرجات السجل والتقرير</h4>${list(profile.reportOutputs)}</div>
        <div><h4>قواعد المتابعة</h4>${list(profile.followUpRules)}</div>
      </div>
      <h4>أطر المنهجية</h4><ul>${profile.frameworks.map((item) => `<li><a href="${esc(item.url)}" target="_blank" rel="noopener noreferrer">${esc(item.label)}</a></li>`).join("")}</ul>
      <div class="callout info"><strong>حد التفسير:</strong> مراجعة بشرية متعددة المصادر مطلوبة. لا تشخيص آلي، لا قرار أهلية آلي، ولا نسخ لأداة محمية.</div>
    </section>`;
  };

  const injectGuideProfile = () => {
    if (!activeGuideId) return;
    const tool = findTool(activeGuideId);
    const content = document.getElementById("result-content");
    if (!tool || !content || content.querySelector(`[data-explorer-profile="${CSS.escape(tool.id)}"]`)) return;
    const actions = content.querySelector(".dialog-actions");
    const holder = document.createElement("div");
    holder.innerHTML = guidePanel(tool);
    content.insertBefore(holder.firstElementChild, actions || null);
  };

  const resultPanel = (detail) => {
    const record = detail.record;
    const quality = record.dataQuality;
    const bridge = record.professionalRecordBridge;
    return `<section class="panel explorer-record-bridge" data-explorer-record-bridge="${esc(detail.sessionId)}">
      <div class="section-heading compact"><div><h3>جسر السجل المهني</h3><p class="muted">حُفظ ملف الأداة والسياق ومخرجات التقرير مع الجلسة نفسها.</p></div><span class="badge ${quality.completeness === "complete" ? "success" : "warning"}">${quality.documentedFields}/${quality.requiredFields} حقول سياقية</span></div>
      <dl class="summary-grid">
        <div><dt>مصدر المعلومات</dt><dd>${esc(quality.respondent || "غير موثق")}</dd></div>
        <div><dt>الفترة</dt><dd>${esc(quality.observationWindow || "غير موثقة")}</dd></div>
        <div><dt>البيئة</dt><dd>${esc(quality.primarySetting || "غير موثقة")}</dd></div>
        <div><dt>جودة البيانات</dt><dd>${esc(quality.confidence || "غير موثقة")}</dd></div>
      </dl>
      <p><strong>نقاط القوة:</strong> ${esc(quality.strengths || "غير موثقة")}</p>
      <p><strong>التكييفات:</strong> ${esc(quality.accommodations || "غير موثقة")}</p>
      <div class="two-column"><div><h4>مخرجات التقرير المقترحة</h4>${list(bridge.outputFields)}</div><div><h4>عوامل الالتباس الواجب مراجعتها</h4>${list(bridge.confoundersToReview)}</div></div>
      <div class="callout info">هذا الجسر ينظم التوثيق والمتابعة فقط. يبقى القرار والتفسير مسؤولية بشرية مؤهلة وبعد دمج المصادر والسياقات.</div>
    </section>`;
  };

  const injectResultBridge = (detail) => {
    const content = document.getElementById("result-content");
    if (!content || content.querySelector(`[data-explorer-record-bridge="${CSS.escape(detail.sessionId)}"]`)) return;
    const actions = content.querySelector(".dialog-actions");
    const holder = document.createElement("div");
    holder.innerHTML = resultPanel(detail);
    content.insertBefore(holder.firstElementChild, actions || null);
  };

  document.addEventListener("submit", capture, true);
  document.addEventListener("click", (event) => {
    const guideButton = event.target.closest("[data-guide]");
    if (guideButton) {
      activeGuideId = guideButton.dataset.guide;
      setTimeout(injectGuideProfile, 0);
    }
  }, true);
  window.addEventListener("pa-original-session-context-saved", attachToLatestSession);
  window.addEventListener("pa-explorer-saturation-record-saved", (event) => injectResultBridge(event.detail));

  window.PA_EXPLORER_SATURATION_RECORD = Object.freeze({
    schema: SCHEMA,
    release: RELEASE,
    attachToLatestSession,
    snapshotProfile,
  });
  document.documentElement.dataset.explorerSaturationRecord = RELEASE;
})();
