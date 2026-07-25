"use strict";

(() => {
  const data = window.PA_DEMO_DATA;
  if (!data || !Array.isArray(data.professional)) return;

  const VERSION = "220.1";
  const EXTERNAL_MODES = new Set(["external_import", "record_review"]);
  const externalPattern = /external|device|audiometry|oae|abr|bera|tympan|vision|hearing|سمع|بصر|جهاز/i;
  const normalizeText = (value) => String(value || "").trim();
  const unique = (values) => [...new Set((values || []).map(normalizeText).filter(Boolean))];

  const contractFor = (tool, forceExternal = null) => {
    const descriptor = `${tool.name || ""} ${tool.category || ""} ${tool.kind || ""} ${tool.inputMode || ""} ${tool.activationStatus || ""} ${tool.status || ""}`;
    const external = forceExternal ?? (tool.status === "external" || externalPattern.test(descriptor));
    return {
      version: VERSION,
      recordType: external ? "external_official_result_record" : "licensed_professional_administration_record",
      rightsState: external ? "external_report_only" : "rights_verification_required",
      officialAdministrationInsidePlatform: false,
      resultRecordingAllowed: true,
      protectedContentStorageAllowed: false,
      itemResponsesStorageAllowed: false,
      scoringKeyStorageAllowed: false,
      normTableStorageAllowed: false,
      sourceDocumentRequiredForCompletedRecord: true,
      publisherVersionLanguageRequired: true,
      qualificationRequired: true,
      recommendedRoles: unique(tool.recommendedRoles?.length ? tool.recommendedRoles : ["مختص مؤهل بحسب الأداة والجهة المنظمة"]),
      permittedRightsBases: external
        ? ["external_report_only", "licensed_original_copy", "official_public_permission"]
        : ["licensed_original_copy", "official_public_permission"],
      permittedScoreSources: ["official_report", "authorized_scoring_platform", "qualified_professional_record", "publisher_output"],
      selectionQuestions: [
        "ما سؤال الإحالة الذي يبرر اختيار هذه الأداة؟",
        "هل العمر واللغة والسياق وخصائص الوصول متوافقة مع النسخة؟",
        "ما الأدوات أو المصادر المكملة المطلوبة لتجنب الاعتماد على نتيجة واحدة؟",
      ],
      interpretationLimits: [
        "لا تفسر النتيجة منفردة بوصفها تشخيصًا أو قرار أهلية أو علاجًا.",
        "يجب الرجوع إلى دليل النسخة الأصلية وشروط الناشر والمؤهل المهني والنظام المحلي.",
        "تسجل المنصة الخلاصة والمرجع فقط ولا تخزن البنود أو مفاتيح التصحيح أو الجداول المعيارية.",
        "يجب توثيق التكييفات وجودة التطبيق والقيود قبل دمج النتيجة في التقرير.",
      ],
      requiredCompletedFields: [
        "publisher", "instrumentVersion", "administrationLanguage", "administratorQualification",
        "rightsBasis", "rightsReference", "scoreSource", "officialSourceReference",
        "selectionRationale", "administrationQuality", "interpretationLimitations",
        "integrationSummary", "recommendations", "followUpDate",
      ],
    };
  };

  const ids = new Set();
  for (const [index, tool] of data.professional.entries()) {
    tool.id ||= `professional-${index + 1}`;
    if (ids.has(tool.id)) throw new Error(`Duplicate professional registry id: ${tool.id}`);
    ids.add(tool.id);
    tool.professionalContract = contractFor(tool);
    tool.professionalContractVersion = VERSION;
    tool.digitalAdministrationStatus = "not_available_in_platform";
    tool.resultRecordingStatus = "available_without_protected_materials";
  }

  const customContractForMode = (administrationMode = "") => contractFor({
    id: "custom-professional-record",
    name: "تطبيق مهني مخصص أو تقرير خارجي",
    category: "مسار مهني",
    recommendedRoles: ["مختص مؤهل يطبق النسخة المرخصة أو يراجع التقرير الرسمي"],
  }, EXTERNAL_MODES.has(String(administrationMode || "")));

  window.PA_PROFESSIONAL_REGISTRY_V220 = Object.freeze({
    version: VERSION,
    count: data.professional.length,
    allDigitalAdministrationLocked: data.professional.every((tool) => tool.professionalContract.officialAdministrationInsidePlatform === false),
    protectedContentStorageAllowed: false,
    customRecordContract: customContractForMode("external_import"),
    customContractForMode,
    tools: data.professional.map((tool) => ({
      id: tool.id,
      name: tool.name,
      category: tool.category,
      recordType: tool.professionalContract.recordType,
      rightsState: tool.professionalContract.rightsState,
      requiredCompletedFields: [...tool.professionalContract.requiredCompletedFields],
    })),
  });
})();
