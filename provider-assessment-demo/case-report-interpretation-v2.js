"use strict";

(() => {
  const form = document.getElementById("case-report-form");
  if (!form || form.dataset.interpretationV2 === "true" || typeof store === "undefined" || typeof save !== "function") return;
  form.dataset.interpretationV2 = "true";

  const VERSION = "2026.07.24-report-interpretation.2";
  const esc = (value) => String(value ?? "")
    .replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;").replaceAll("'", "&#039;");
  const assessmentLabels = {
    screening: "المسح أو الفرز",
    diagnostic: "التقييم التشخيصي",
    functional: "التقييم الوظيفي",
    progress: "متابعة التقدم"
  };
  const validityLabels = {
    adequate: "صالحة للتفسير ضمن السؤال المحدد",
    qualified: "صالحة بشروط أو قيود موثقة",
    insufficient: "غير كافية لاتخاذ قرار",
    external: "نتيجة خارجية موثقة تحتاج مراجعة المصدر"
  };

  const field = (name, html) => {
    if (form.elements[name]) return null;
    const wrapper = document.createElement("label");
    wrapper.className = "field";
    wrapper.dataset.reportV2Field = name;
    wrapper.innerHTML = html;
    return wrapper;
  };

  const grid = form.querySelector(".report-form-grid");
  if (!grid) return;
  const anchor = form.elements.purpose?.closest("label") || grid.firstElementChild;
  const fields = [
    field("assessmentType", '<span>نوع التقييم</span><select name="assessmentType" required><option value="">اختر النوع</option><option value="screening">المسح أو الفرز</option><option value="diagnostic">التقييم التشخيصي</option><option value="functional">التقييم الوظيفي</option><option value="progress">متابعة التقدم</option></select>'),
    field("resultValidity", '<span>صلاحية النتيجة</span><select name="resultValidity" required><option value="">اختر مستوى الصلاحية</option><option value="adequate">صالحة للتفسير ضمن السؤال المحدد</option><option value="qualified">صالحة بشروط أو قيود موثقة</option><option value="insufficient">غير كافية لاتخاذ قرار</option><option value="external">نتيجة خارجية موثقة تحتاج مراجعة المصدر</option></select>'),
    field("validityLimitations", '<span>حدود الصلاحية والتفسير</span><textarea name="validityLimitations" rows="3" maxlength="2200" placeholder="اللغة، السمع، البصر، الحركة، التعب، الألم، طريقة التواصل، اختلاف البيئات، التكييفات أو نقص المصادر" required></textarea>'),
    field("baseline", '<span>خط الأساس</span><textarea name="baseline" rows="3" maxlength="1800" placeholder="وصف أو قيمة أولية قابلة لإعادة القياس"></textarea>'),
    field("measurableTarget", '<span>الهدف القابل للقياس</span><textarea name="measurableTarget" rows="3" maxlength="1800" placeholder="السلوك أو المهارة، الظروف، مستوى المساعدة، المعيار والمدة"></textarea>'),
    field("measurementMethod", '<span>طريقة ووحدة القياس</span><input name="measurementMethod" maxlength="500" placeholder="تكرار، مدة، نسبة، دقة، مستوى مساعدة أو مقياس وظيفي">'),
    field("remeasureDate", '<span>موعد إعادة القياس</span><input name="remeasureDate" type="date">'),
    field("familySummary", '<span>ملخص مبسط للأسرة أو مقدم الرعاية</span><textarea name="familySummary" rows="4" maxlength="2600" placeholder="ما الذي وجدناه؟ ما الذي لا تعنيه النتيجة؟ ما الخطوة التالية؟ وكيف ستتم متابعة التقدم؟" required></textarea>'),
    field("revisionReason", '<span>سبب إصدار نسخة جديدة</span><textarea name="revisionReason" rows="2" maxlength="1000" placeholder="إضافة مصدر، تصحيح معلومة، مراجعة فريق، تحديث متابعة أو تعديل خطة"></textarea>')
  ].filter(Boolean);
  fields.forEach((node) => {
    if (["validityLimitations", "baseline", "measurableTarget", "familySummary", "revisionReason"].includes(node.dataset.reportV2Field)) node.classList.add("report-full");
    grid.insertBefore(node, anchor);
  });

  for (const [name, value] of [["parentReportId", ""], ["changedFields", ""], ["conditionPathwaySlug", ""], ["interpretationVersion", VERSION]]) {
    if (form.elements[name]) continue;
    const input = document.createElement("input");
    input.type = "hidden";
    input.name = name;
    input.value = value;
    form.appendChild(input);
  }

  const caseById = (caseId) => store.cases.find((item) => item.caseId === caseId);
  const currentPathway = () => {
    try { return JSON.parse(localStorage.getItem("pa-selected-condition-v1") || "null"); }
    catch (_) { return null; }
  };
  const comparableKeys = ["assessmentType", "resultValidity", "validityLimitations", "baseline", "measurableTarget", "measurementMethod", "remeasureDate", "familySummary", "purpose", "strengths", "needs", "integratedSummary", "recommendations", "decision", "followUpDate", "followUpIndicators", "reviewStatus"];

  form.addEventListener("submit", (event) => {
    const type = form.elements.assessmentType.value;
    const progressRequired = type === "progress";
    for (const name of ["baseline", "measurableTarget", "measurementMethod", "remeasureDate"]) form.elements[name].required = progressRequired;
    if (progressRequired && !form.reportValidity()) {
      event.preventDefault();
      event.stopImmediatePropagation();
      return;
    }

    const caseRecord = caseById(form.elements.caseId.value);
    const currentId = form.elements.reportId.value;
    const prior = currentId ? (caseRecord?.reports || []).find((item) => item.reportId === currentId) : null;
    if (prior) {
      if (!form.elements.revisionReason.value.trim()) {
        form.elements.revisionReason.setCustomValidity("اكتب سبب إصدار النسخة الجديدة حتى يبقى سجل المراجعة واضحًا.");
        if (!form.reportValidity()) {
          event.preventDefault();
          event.stopImmediatePropagation();
          form.elements.revisionReason.setCustomValidity("");
          return;
        }
      }
      form.elements.parentReportId.value = prior.reportId;
      form.elements.changedFields.value = comparableKeys.filter((key) => String(prior[key] || "") !== String(form.elements[key]?.value || "")).join(",");
      form.elements.reportId.value = "";
    }
    const pathway = caseRecord?.conditionPathway || currentPathway();
    form.elements.conditionPathwaySlug.value = pathway?.slug || "";
    form.elements.interpretationVersion.value = VERSION;
  }, true);

  form.addEventListener("input", (event) => {
    if (event.target.name === "revisionReason") event.target.setCustomValidity("");
  });

  const enhancePreview = () => {
    const preview = document.getElementById("case-report-preview");
    if (!preview || preview.querySelector("[data-report-v2-preview]")) return;
    const section = document.createElement("section");
    section.dataset.reportV2Preview = "true";
    section.innerHTML = `<h3>عقد التفسير والمتابعة</h3><dl class="summary-grid"><div><dt>نوع التقييم</dt><dd data-v2-assessment>غير محدد</dd></div><div><dt>صلاحية النتيجة</dt><dd data-v2-validity>غير محددة</dd></div><div><dt>إعادة القياس</dt><dd data-v2-remeasure>غير محدد</dd></div></dl><p><strong>حدود التفسير:</strong> <span data-v2-limitations>غير مسجلة</span></p><p><strong>خط الأساس:</strong> <span data-v2-baseline>غير مسجل</span></p><p><strong>الهدف:</strong> <span data-v2-target>غير مسجل</span></p><p><strong>ملخص الأسرة:</strong> <span data-v2-family>غير مسجل</span></p><p class="report-disclaimer">المسح لا يثبت التشخيص، والنتيجة المنفردة لا تكفي لاتخاذ قرار سريري أو تربوي. يجب توثيق المصادر والقيود والسياق والمؤهل المهني.</p>`;
    preview.appendChild(section);
  };

  const refreshV2 = () => {
    enhancePreview();
    const preview = document.getElementById("case-report-preview");
    if (!preview) return;
    const set = (selector, value) => { const node = preview.querySelector(selector); if (node) node.textContent = value || "غير مسجل"; };
    set("[data-v2-assessment]", assessmentLabels[form.elements.assessmentType.value] || "غير محدد");
    set("[data-v2-validity]", validityLabels[form.elements.resultValidity.value] || "غير محددة");
    set("[data-v2-remeasure]", form.elements.remeasureDate.value || "غير محدد");
    set("[data-v2-limitations]", form.elements.validityLimitations.value);
    set("[data-v2-baseline]", form.elements.baseline.value);
    set("[data-v2-target]", form.elements.measurableTarget.value);
    set("[data-v2-family]", form.elements.familySummary.value);
  };

  const observer = new MutationObserver(refreshV2);
  observer.observe(document.getElementById("case-report-preview"), { childList: true });
  form.addEventListener("input", refreshV2);
  form.addEventListener("change", refreshV2);
  refreshV2();

  window.PA_CASE_REPORT_INTERPRETATION_V2 = Object.freeze({
    version: VERSION,
    assessmentTypes: Object.keys(assessmentLabels),
    proprietaryContentIncluded: false
  });
})();
