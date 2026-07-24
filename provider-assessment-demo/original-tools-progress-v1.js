"use strict";

(() => {
  const RELEASE = "2026.07.24-progress.1";
  const STORE_VERSION = "3";
  const idsKey = `pa-demo-identities-v${STORE_VERSION}`;
  const activeKey = `pa-demo-active-v${STORE_VERSION}`;

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

  const activeStore = () => {
    const identity = activeIdentity();
    if (!identity?.uid) return null;
    const store = read(`pa-demo-store-v${STORE_VERSION}:${identity.uid}`, null);
    return store?.uid === identity.uid ? store : null;
  };

  const assessmentTitle = (id) => window.PA_DEMO_DATA?.explorers?.find((item) => item.id === id)?.title || id;
  const formatDate = (value) => {
    try { return new Intl.DateTimeFormat("ar-JO", { dateStyle: "medium" }).format(new Date(value)); }
    catch (_) { return value || "—"; }
  };
  const number = (value) => Number.isFinite(Number(value)) ? Number(value) : null;

  const buildSeries = (caseRecord) => {
    const grouped = new Map();
    for (const session of caseRecord.sessions || []) {
      const signal = number(session.averageSignal);
      if (!session.assessmentId || signal === null) continue;
      if (!grouped.has(session.assessmentId)) grouped.set(session.assessmentId, []);
      grouped.get(session.assessmentId).push(session);
    }
    return [...grouped.entries()].map(([assessmentId, sessions]) => {
      sessions.sort((a, b) => new Date(a.completedAt) - new Date(b.completedAt));
      const baseline = sessions[0];
      const latest = sessions[sessions.length - 1];
      const baselineValue = number(baseline.averageSignal) ?? 0;
      const latestValue = number(latest.averageSignal) ?? 0;
      const delta = +(latestValue - baselineValue).toFixed(2);
      return {
        assessmentId,
        title: assessmentTitle(assessmentId),
        sessions,
        baseline,
        latest,
        baselineValue,
        latestValue,
        delta
      };
    }).sort((a, b) => new Date(b.latest.completedAt) - new Date(a.latest.completedAt));
  };

  const directionText = (series) => {
    if (series.sessions.length < 2) return "خط أساس واحد";
    if (series.delta === 0) return "ثبات وصفي";
    return series.delta > 0 ? `زيادة وصفية +${series.delta}` : `انخفاض وصفي ${series.delta}`;
  };

  const render = (caseRecord) => {
    const series = buildSeries(caseRecord);
    const repeated = series.filter((item) => item.sessions.length > 1).length;
    const rows = series.length ? series.map((item) => `
      <tr>
        <th scope="row">${esc(item.title)}</th>
        <td>${item.sessions.length}</td>
        <td>${item.baselineValue.toFixed(2)}<small>${esc(formatDate(item.baseline.completedAt))}</small></td>
        <td>${item.latestValue.toFixed(2)}<small>${esc(formatDate(item.latest.completedAt))}</small></td>
        <td><span class="progress-trend ${item.delta > 0 ? "up" : item.delta < 0 ? "down" : "flat"}">${esc(directionText(item))}</span></td>
      </tr>`).join("") : `<tr><td colspan="5">لا توجد جلسات أصلية ذات إشارة وصفية قابلة للمقارنة بعد.</td></tr>`;

    return `<section class="panel original-progress-panel" data-original-progress="${esc(caseRecord.caseId)}" aria-labelledby="original-progress-title">
      <div class="section-heading compact"><div><h3 id="original-progress-title">متابعة التقدم بالأدوات الأصلية</h3><p class="muted">مقارنة وصفية للجلسات المتكررة داخل الأداة نفسها؛ ليست درجة معيارية ولا دليلًا تشخيصيًا.</p></div><button class="button ghost small-button" type="button" data-export-original-progress="${esc(caseRecord.caseId)}">تصدير المتابعة</button></div>
      <div class="progress-summary"><span><strong>${series.length}</strong> أدوات لها خط أساس</span><span><strong>${repeated}</strong> أدوات أُعيد تطبيقها</span><span><strong>${(caseRecord.sessions || []).length}</strong> جلسة مسجلة</span></div>
      <div class="table-wrap"><table class="progress-table"><thead><tr><th>الأداة الأصلية</th><th>الجلسات</th><th>خط الأساس</th><th>الأحدث</th><th>الاتجاه</th></tr></thead><tbody>${rows}</tbody></table></div>
      <div class="callout info"><strong>قاعدة التفسير:</strong> التغير يعني اختلاف نمط الإجابات في ظروف الجلسات المسجلة فقط. راجع اختلاف المجيب والبيئة والدعم والزمن قبل استنتاج أي تحسن أو تراجع.</div>
    </section>`;
  };

  const currentCaseId = () => document.querySelector("#case-detail-content .dialog-heading .eyebrow")?.textContent?.trim() || "";

  const inject = () => {
    const content = document.getElementById("case-detail-content");
    if (!content || !content.children.length) return;
    const caseId = currentCaseId();
    if (!caseId || content.querySelector(`[data-original-progress="${CSS.escape(caseId)}"]`)) return;
    const store = activeStore();
    const caseRecord = store?.cases?.find((item) => item.caseId === caseId);
    if (!caseRecord) return;
    const actions = content.querySelector(".dialog-actions");
    const holder = document.createElement("div");
    holder.innerHTML = render(caseRecord);
    content.insertBefore(holder.firstElementChild, actions || null);
  };

  const exportProgress = (caseId) => {
    const store = activeStore();
    const identity = activeIdentity();
    const caseRecord = store?.cases?.find((item) => item.caseId === caseId);
    if (!caseRecord || !identity) return;
    const payload = {
      schema: "pa-original-tools-progress-v1",
      release: RELEASE,
      ownerUid: identity.uid,
      caseId: caseRecord.caseId,
      generatedAt: new Date().toISOString(),
      interpretationBoundary: "descriptive-longitudinal-comparison-not-diagnostic-not-norm-referenced",
      series: buildSeries(caseRecord).map((item) => ({
        assessmentId: item.assessmentId,
        title: item.title,
        sessionCount: item.sessions.length,
        baseline: { sessionId: item.baseline.sessionId, completedAt: item.baseline.completedAt, averageSignal: item.baselineValue, domainSignals: item.baseline.domainSignals || {} },
        latest: { sessionId: item.latest.sessionId, completedAt: item.latest.completedAt, averageSignal: item.latestValue, domainSignals: item.latest.domainSignals || {} },
        descriptiveDelta: item.delta
      }))
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${caseRecord.caseId}-original-tools-progress.json`;
    anchor.click();
    setTimeout(() => URL.revokeObjectURL(url), 500);
  };

  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-export-original-progress]");
    if (button) exportProgress(button.dataset.exportOriginalProgress);
  });

  const content = document.getElementById("case-detail-content");
  if (content) new MutationObserver(inject).observe(content, { childList: true, subtree: false });
  window.addEventListener("storage", inject);

  const style = document.createElement("style");
  style.textContent = `.original-progress-panel{margin-top:18px}.progress-summary{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin:12px 0}.progress-summary span{background:var(--soft,#eef8f7);border:1px solid var(--line,#c5e4e0);border-radius:12px;padding:10px}.progress-summary strong{display:block;font-size:1.25rem}.table-wrap{overflow:auto}.progress-table{width:100%;border-collapse:collapse;min-width:680px}.progress-table th,.progress-table td{padding:10px;border-bottom:1px solid var(--line,#c5e4e0);text-align:right;vertical-align:top}.progress-table td small{display:block;color:var(--muted,#567579)}.progress-trend{font-weight:800}.progress-trend.up{color:#8a3d1d}.progress-trend.down{color:#0b6b66}.progress-trend.flat{color:var(--muted,#567579)}@media(max-width:650px){.progress-summary{grid-template-columns:1fr}}`;
  document.head.appendChild(style);
  document.documentElement.dataset.originalProgressRelease = RELEASE;
})();
