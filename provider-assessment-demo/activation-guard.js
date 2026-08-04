"use strict";

(() => {
  const data = window.PA_DEMO_DATA;
  const hasNewerInstitutionalContract = () =>
    document.documentElement.dataset.institutionalContract === "2026.07.25-v220" ||
    Boolean(document.querySelector('script[data-institutional-contract-v220]'));
  const slug = (value) => String(value || "")
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");

  if (Array.isArray(data?.professional)) {
    data.professional.forEach((item, index) => {
      if (!item.id) item.id = `professional-${index + 1}-${slug(item.name) || "record"}`;
      const externalResultOnly = item.status === "external"
        || String(item.activationStatus || "").startsWith("external")
        || String(item.inputMode || "").includes("external");
      item.status = externalResultOnly ? "external" : "locked";
      item.rightsStatus = externalResultOnly ? "locked_or_link_only" : "locked_pending_rights";
      item.access = externalResultOnly
        ? "نتيجة خارجية أو رابط رسمي فقط؛ لا تُعرض البنود ولا يُنفذ الفحص داخل المنصة"
        : "مقفل حتى اكتمال الترخيص وحق الرقمنة والتحقق من النسخة واللغة والمؤهل";
      item.note = externalResultOnly
        ? "يمكن توثيق وجود تقرير صادر عن جهة مختصة دون نسخ مواده أو مفاتيح تصحيحه."
        : "لا يُفتح التطبيق المهني قبل موافقة حقوقية وعلمية وأمنية ومؤسسية موثقة.";
    });
  }

  const emotionalTool = data?.explorers?.find((item) => item.id === "emotional-regulation");
  if (emotionalTool && Array.isArray(emotionalTool.questions) && !emotionalTool.questions.some((question) => question.type === "checkbox")) {
    const question = {
      id: "emo-context-factors",
      domain: "context",
      type: "checkbox",
      text: "ما العوامل التي ترتبط عادةً بزيادة الانفعال أو صعوبة التعافي؟",
      options: [
        ["communication", "تعذر التعبير أو الفهم", 1],
        ["sensory", "ازدحام أو مثير حسي", 1],
        ["change", "تغيير أو انتقال مفاجئ", 1],
        ["demand", "مطلب صعب أو طويل", 1],
        ["pain_sleep", "ألم أو تعب أو قلة نوم", 1],
        ["none", "لا يوجد عامل ثابت معروف", 0],
      ],
    };
    const safetyIndex = emotionalTool.questions.findIndex((item) => item.safety === true);
    emotionalTool.questions.splice(safetyIndex >= 0 ? safetyIndex : Math.max(emotionalTool.questions.length - 1, 0), 0, question);
  }

  const patchCopy = () => {
    if (hasNewerInstitutionalContract()) return;
    document.title = "منصة التقييم وإدارة السجلات | منصة روافد";
    const description = document.querySelector('meta[name="description"]');
    if (description) description.content = "منصة عربية لإدارة الحالات والجلسات الاستكشافية وسجلات الخدمات المهنية محليًا ضمن UID مستقل، مع إبقاء المقاييس المهنية المحمية مقفلة حتى اكتمال الترخيص والمراجعة المؤسسية.";
    const notice = document.querySelector(".notice-bar");
    if (notice) notice.textContent = "الأدوات الاستكشافية الأصلية متاحة للاستخدام التعليمي غير التشخيصي. المقاييس المهنية المحمية تبقى مقفلة حتى اكتمال الترخيص وحق الرقمنة والمراجعة العلمية والأمنية والمؤسسية.";
    const heroEyebrow = document.querySelector(".hero .eyebrow");
    if (heroEyebrow) heroEyebrow.textContent = "نسخة تشغيل محلية لإدارة الحالات والسجلات";
    const heroTitle = document.getElementById("hero-title");
    if (heroTitle) heroTitle.textContent = "أنشئ حالة، نفّذ جلسات استكشافية، وسجّل الخدمات المهنية في مسار واحد.";
    const lead = document.querySelector(".hero .lead");
    if (lead) lead.textContent = "إدارة حالات متعددة، جلسات استكشافية متكررة، سجل زمني، مقارنة وصفية، وسجل خدمات مهنية. تحفظ هذه النسخة البيانات محليًا داخل المتصفح بواسطة UID مستقل، ولا تفتح مواد المقاييس المحمية.";
    const heroItems = document.querySelectorAll(".hero-card li");
    if (heroItems.length) heroItems[heroItems.length - 1].textContent = "دليل حقوقي للمقاييس المهنية مع إبقاء المواد المحمية مقفلة.";
    const professionalEyebrow = document.querySelector("#view-professional .section-heading .eyebrow");
    if (professionalEyebrow) professionalEyebrow.textContent = "دليل وصول مصنف — دون بنود أو مفاتيح محمية";
    const professionalHeading = document.querySelector("#view-professional .section-heading h2");
    if (professionalHeading) professionalHeading.textContent = "المقاييس المهنية وحالة التفعيل الحقوقي";
    const professionalCallout = document.querySelector("#view-professional .callout");
    if (professionalCallout) {
      professionalCallout.className = "callout warning";
      professionalCallout.textContent = "تظهر المقاييس المهنية كدليل وصول فقط. لا يُفتح أي تطبيق محمي قبل توثيق الترخيص وحق الرقمنة والمؤهل والنسخة اللغوية والمراجعة المؤسسية.";
    }
    const recordButton = document.getElementById("professional-record-new");
    if (recordButton) recordButton.textContent = "إضافة سجل خدمة مهنية";
    const recordCallout = document.querySelector("#view-professional-records .callout");
    if (recordCallout) recordCallout.textContent = "هذا السجل يوثق الخدمات والمواعيد والتقارير الخارجية دون تضمين بنود المقاييس أو مفاتيح التصحيح أو الادعاء بتفعيل أداة محمية.";
    const scoreField = document.querySelector('#professional-record-form [name="scoreReference"]')?.closest(".field");
    if (scoreField) {
      const label = scoreField.querySelector("span");
      const input = scoreField.querySelector("input");
      if (label) label.textContent = "مرجع تقرير خارجي أو وثيقة";
      if (input) input.placeholder = "رقم أو اسم التقرير الخارجي فقط؛ لا تدخل مفاتيح تصحيح";
    }
    const footer = document.querySelector(".site-footer p");
    if (footer) footer.textContent = "© منصة منصة روافد — تشغيل محلي لإدارة الاستكشاف والسجلات، مع دليل وصول حقوقي للمقاييس المهنية. لا تستخدم للطوارئ أو التشخيص الآلي أو تقرير الأهلية.";
  };

  const applyRightsUi = () => {
    const professionalList = document.getElementById("professional-list");
    if (!professionalList) return;
    const barStrong = professionalList.querySelector(".professional-operational-bar strong");
    const barText = professionalList.querySelector(".professional-operational-bar p");
    if (barStrong) barStrong.textContent = `${data.professional.length} مقياسًا وفحصًا في دليل الوصول المهني`;
    if (barText) barText.textContent = "إدارة السجلات متاحة، أما الأدوات المحمية فتبقى مقفلة حتى اكتمال المتطلبات الحقوقية والمؤسسية.";

    professionalList.querySelectorAll("[data-professional-tool]").forEach((button) => {
      const item = data.professional.find((entry) => entry.id === button.dataset.professionalTool);
      if (!item) return;
      const row = button.closest(".catalog-row");
      if (!row) return;
      const badge = row.querySelector(".badge");
      const columns = row.querySelectorAll(":scope > div");
      const accessText = columns[1]?.querySelector("p");
      const noteText = columns[2]?.querySelector("p");
      if (badge) {
        badge.className = `badge ${item.rightsStatus === "locked_or_link_only" ? "warning" : "danger"}`;
        badge.textContent = item.rightsStatus === "locked_or_link_only" ? "تقرير خارجي فقط" : "مقفل حتى الترخيص";
      }
      if (accessText) accessText.textContent = item.access;
      if (noteText) noteText.textContent = item.note;
      button.remove();
    });
    patchCopy();
  };

  const previousRender = typeof render === "function" ? render : null;
  if (previousRender) {
    render = function rightsGatedRender() {
      previousRender();
      applyRightsUi();
    };
    render();
  } else {
    applyRightsUi();
  }

  document.getElementById("professional-search")?.addEventListener("input", applyRightsUi);
  document.getElementById("professional-category-filter")?.addEventListener("change", applyRightsUi);

  document.addEventListener("click", (event) => {
    const protectedTool = event.target.closest("[data-professional-tool]");
    if (protectedTool) {
      event.preventDefault();
      event.stopImmediatePropagation();
      if (typeof toast === "function") toast("هذا المقياس مقفل حتى اكتمال الترخيص والمراجعة المؤسسية.");
      return;
    }

    const cancelButton = event.target.closest(
      "#account-form button[value='cancel'], #professional-record-form button[value='cancel'], #professional-lifecycle-form button[value='cancel'], #professional-record-edit-form button[value='cancel'], #backup-export-form button[value='cancel'], #backup-import-preview-form button[value='cancel'], #backup-unlock-form button[value='cancel']"
    );
    if (!cancelButton) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    const dialog = cancelButton.closest("dialog");
    if (!dialog) return;
    if (typeof dialog.close === "function") dialog.close();
    else dialog.removeAttribute("open");
  }, true);

  const loadModule = (src, moduleName) => new Promise((resolve, reject) => {
    if (document.querySelector(`[data-module="${moduleName}"]`)) {
      resolve();
      return;
    }
    const script = document.createElement("script");
    script.src = src;
    script.async = false;
    script.dataset.module = moduleName;
    script.addEventListener("load", resolve, { once: true });
    script.addEventListener("error", reject, { once: true });
    document.head.appendChild(script);
  });

  loadModule("professional-record-lifecycle.js?v=20260724-integrity1", "professional-record-lifecycle")
    .then(() => loadModule("professional-record-integrity.js?v=20260724-integrity1", "professional-record-integrity"))
    .then(() => loadModule("backup-integrity.js?v=20260724-backup1", "backup-integrity"))
    .then(() => loadModule("backup-large-file-patch.js?v=20260724-backup2", "backup-large-file-patch"))
    .catch((error) => console.error("Provider assessment module failed to load", error));
})();
