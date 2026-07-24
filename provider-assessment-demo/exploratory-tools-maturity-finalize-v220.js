"use strict";
(() => {
  const root = window.PA_EXPLORATORY_V220;
  const data = window.PA_DEMO_DATA;
  if (!root || !data || !Array.isArray(data.explorers)) return;
  window.PA_DOMAIN_LABELS = Object.freeze({"developmental_trajectory":"المسار النمائي والوظيفي","generalization":"تعميم المهارات","problem_solving":"حل المشكلات","self_direction":"التوجيه الذاتي","environment":"العوامل البيئية","strengths":"نقاط القوة","safety":"السلامة","priorities":"الأولويات","repair":"إصلاح التواصل","choice_expression":"التعبير عن الاختيار والرفض","health_communication":"التواصل الصحي","aac_access":"الوصول للتواصل البديل والمعزز","partner_support":"دعم شريك التواصل","language_access":"الوصول اللغوي","communication_participation":"المشاركة التواصلية","communication_examples":"أمثلة التواصل","working_memory":"الذاكرة العاملة","inhibition":"كبح الاستجابة","planning":"التخطيط","time_management":"إدارة الوقت","cognitive_flexibility":"المرونة المعرفية","self_monitoring":"المراقبة الذاتية","executive_supports":"الدعامات التنفيذية","executive_examples":"أمثلة الأداء التنفيذي","reading_comprehension":"فهم المقروء","written_expression":"التعبير الكتابي","numeracy":"الحساب الوظيفي","demonstration_access":"إظهار المعرفة","instruction_language":"لغة التعليم","learning_opportunity":"فرصة التعلم","response_to_instruction":"الاستجابة للتعليم","learning_evidence":"أدلة التعلم","daily_routines":"الروتين اليومي","health_management":"إدارة الصحة","money_use":"استخدام المال","transport_access":"الوصول والتنقل","responsibility":"المسؤوليات","supported_decision":"القرار المدعوم","dignity_privacy":"الكرامة والخصوصية","adaptive_goal":"الهدف الوظيفي","vestibular":"الحركة والتوازن","proprioception":"الإحساس العميق","interoception":"الإحساس الداخلي","sensory_seeking":"البحث الحسي","sensory_recovery":"التعافي الحسي","sensory_environment":"البيئة الحسية","sensory_pattern":"النمط الحسي","transfers":"الانتقالات الحركية","endurance":"التحمل","upper_limb":"استخدام الطرف العلوي","environmental_mobility":"الحركة في البيئة","assistive_device":"الأجهزة المساندة","falls":"السقوط","motor_goal":"هدف المشاركة الحركية","emotional_triggers":"محفزات الانفعال","distress_communication":"التواصل أثناء الضيق","self_regulation":"التنظيم الذاتي","co_regulation":"التنظيم المشترك","cross_setting":"اختلاف البيئات","protective_factors":"العوامل الوقائية","behavior_episode":"وصف الحدث","social_preference":"التفضيلات الاجتماعية","social_context":"فهم السياق الاجتماعي","conflict_repair":"إصلاح الخلاف","boundaries":"الحدود","belonging":"الانتماء","social_access":"الوصول الاجتماعي","social_examples":"أمثلة المشاركة","play_exploration":"استكشاف اللعب","symbolic_play":"اللعب الرمزي","shared_play":"اللعب المشترك","play_creativity":"الإبداع في اللعب","play_transition":"الانتقال في اللعب","play_access":"الوصول للعب","play_strength":"قوة اللعب والاهتمام","sleep_schedule":"جدول النوم","sleep_duration":"مدة النوم","early_waking":"الاستيقاظ المبكر","daytime_impact":"الأثر النهاري","sleep_breathing":"التنفس أثناء النوم","sleep_factors":"عوامل النوم","sleep_diary":"ملخص سجل النوم","oral_motor":"المضغ والمهارات الفموية","hydration":"السوائل","meal_communication":"التواصل في الوجبة","meal_environment":"بيئة الوجبة","nutrition_risk":"المخاطر التغذوية","diet_safety":"سلامة الحمية","meal_observation":"ملاحظة الوجبة","independent_work":"العمل المستقل","group_learning":"التعلم الجماعي","assessment_access":"الوصول للتقييم","school_relationships":"العلاقات المدرسية","school_environment":"البيئة المدرسية","school_collaboration":"التعاون المدرسي","school_evidence":"دليل المشاركة المدرسية","consent":"الموافقة والرفض","accessible_information":"المعلومات الميسرة","accommodation_request":"طلب التكييف","complaint_access":"الوصول للشكوى","decision_support":"دعم القرار","health_advocacy":"المناصرة الصحية","decision_example":"مثال القرار","family_strengths":"قوة الأسرة","caregiver_capacity":"قدرة مقدم الرعاية","service_access":"الوصول للخدمات","care_coordination":"تنسيق الرعاية","person_voice":"صوت الشخص","goal_feasibility":"قابلية الهدف للتنفيذ","family_plan":"خطة الأسرة","operational_definition":"التعريف القابل للملاحظة","behavior_duration":"قياس السلوك","setting_events":"عوامل السياق","consequences":"النتائج اللاحقة","behavior_communication":"بديل التواصل","hypothesis_quality":"جودة الفرضية","abc_observation":"ملاحظة ABC","bilateral_coordination":"التناسق الثنائي","fine_precision":"الدقة الحركية","handwriting_access":"الوصول للكتابة","fine_self_care":"الأدوات في العناية الذاتية","fine_endurance":"تحمل المهام الدقيقة","postural_support":"الدعم الوضعي","fine_task_analysis":"تحليل المهمة الدقيقة","sequencing":"تسلسل الخطوات","prospective_memory":"الذاكرة المستقبلية","time_estimation":"تقدير الوقت","task_monitoring":"مراقبة المهمة","task_switching":"التنقل بين المهام","external_support":"الدعامات الخارجية","planning_example":"مثال التخطيط","autonomy":"الاستقلال والاختيار","supportive_relationships":"العلاقات الداعمة","energy":"الطاقة","participation_barriers":"عوائق المشاركة","coping_resources":"موارد التكيف","meaningful_goal":"هدف المشاركة","employment":"الاستعداد للعمل","postsecondary":"التعليم والتدريب اللاحق","transition_transport":"تنقل البالغين","financial_literacy":"المهارات المالية","adult_health":"إدارة الصحة للبالغين","adult_services":"خدمات البالغين","transition_plan":"خطة الانتقال","communication":"التواصل","learning":"التعلم","participation":"المشاركة","receptive":"فهم اللغة","expressive":"التعبير","functional":"التواصل الوظيفي","initiation":"البدء","sustained":"استمرار الانتباه","organization":"التنظيم","instruction":"فرص التعليم","reading":"القراءة","supports":"التكييفات","self_care":"العناية الذاتية","community":"المشاركة المجتمعية","sound":"الأصوات","touch":"اللمس","visual":"البيئة البصرية","mobility":"التنقل","balance":"التوازن","access":"الوصول","intensity":"شدة الانفعال","recovery":"التعافي","risk":"السلامة الحالية","context":"السياق"});
  const existing = new Set();
  for (const tool of data.explorers) for (const question of tool.questions || []) {
    if (existing.has(question.id)) throw new Error(`Duplicate exploratory question id: ${question.id}`);
    existing.add(question.id);
  }
  const make = (toolId,def) => {
    const [suffix,domain,text,mode] = def, id = `v220-${toolId}-${suffix}`;
    if (mode === "note") return {id,domain,type:"textarea",text,required:false,maxLength:1600,maturityVersion:root.version,evidenceRole:"context"};
    return {id,domain,type:"radio",text,safety:mode==="safety",options:root.scales[mode]||root.scales.capacity,maturityVersion:root.version,evidenceRole:mode==="safety"?"safety":"functional"};
  };
  const reports = [];
  for (const tool of data.explorers) {
    const spec = root.specs[tool.id];
    if (!spec) throw new Error(`Missing v220 maturity spec: ${tool.id}`);
    for (const definition of spec.questions) {
      const question = make(tool.id,definition);
      if (existing.has(question.id)) throw new Error(`Duplicate v220 question id: ${question.id}`);
      existing.add(question.id);
      tool.questions.push(question);
    }
    const domains = [...new Set(tool.questions.map(q=>q.domain).filter(Boolean))];
    tool.duration = "12–18 دقيقة";
    tool.questionSetVersion = root.version;
    tool.maturityStatus = "expanded_original_exploratory";
    tool.protocol = {
      version:root.version,instrumentType:"original_exploratory_non_diagnostic",rightsStatus:"original_platform_content",
      purpose:spec.purpose,referralQuestion:spec.referral,observationWindow:spec.window,respondents:spec.respondents,contexts:spec.contexts,
      useWhen:["تنظيم خط أساس وظيفي أو سؤال إحالة واضح.","اختيار معلومات أو تكييف أو أداة تالية بصورة غير تشخيصية.","متابعة تغير وظيفي عند ثبات السؤال والسياق بما يكفي للمقارنة."],
      doNotUseWhen:spec.avoid,interpretationLimits:root.limits,followUp:spec.follow,
      minimumEvidence:{observedContexts:Math.min(2,spec.contexts.length),informationSources:Math.min(2,spec.respondents.length),unknownResponseReviewRequired:true,urgentSafetyOverridesScoring:true},
      domains,references:root.references,
      alignmentNotice:"استرشاد مفاهيمي بالأداء والمشاركة والعوامل البيئية والإتاحة؛ لا تمثل الأداة اعتمادًا أو ترجمة أو نسخة من أدوات الجهات المرجعية."
    };
    reports.push({id:tool.id,questions:tool.questions.length,domains:domains.length,safetyItems:tool.questions.filter(q=>q.safety).length});
  }
  if (data.explorers.length !== 20) throw new Error(`Expected 20 exploratory tools, found ${data.explorers.length}`);
  for (const report of reports) if (report.questions < 12 || report.domains < 6) throw new Error(`Tool below v220 maturity threshold: ${report.id}`);
  window.PA_EXPLORATORY_MATURITY_V220 = Object.freeze({version:root.version,tools:reports,toolCount:reports.length,minimumQuestions:Math.min(...reports.map(x=>x.questions)),minimumDomains:Math.min(...reports.map(x=>x.domains)),nonDiagnostic:true,protectedItemsCopied:false});
})();
