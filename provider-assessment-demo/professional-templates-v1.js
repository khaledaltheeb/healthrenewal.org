"use strict";

(() => {
  const form = document.getElementById("professional-record-form");
  if (!form || typeof D === "undefined" || !Array.isArray(D.professional)) return;

  const VERSION = "2026.07.24-templates.1";
  const notesField = form.elements.notes;
  const submitActions = form.querySelector(".dialog-actions");
  const container = document.createElement("section");
  container.id = "professional-template-fields";
  container.className = "professional-template-fields";
  submitActions.before(container);

  const style = document.createElement("style");
  style.textContent = `
    .professional-template-fields{margin:18px 0;display:grid;gap:14px}
    .template-heading{border-top:1px solid var(--line);padding-top:16px}.template-heading h3{margin:.2rem 0}.template-heading p{margin:0;color:var(--muted)}
    .template-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
    .template-checks{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}
    .template-check{display:flex;gap:8px;align-items:flex-start;border:1px solid var(--line);border-radius:12px;padding:10px;background:#fbfefd}
    .template-check input{margin-top:.35rem}.template-full{grid-column:1/-1}
    @media(max-width:760px){.template-grid,.template-checks{grid-template-columns:1fr}}
  `;
  document.head.appendChild(style);

  const esc = (value) => String(value ?? "")
    .replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;").replaceAll("'", "&#039;");

  const select = (name, label, options, required = false) => `
    <label class="field"><span>${esc(label)}</span><select name="detail_${esc(name)}" ${required ? "required" : ""}>
      <option value="">اختر</option>${options.map(([value, text]) => `<option value="${esc(value)}">${esc(text)}</option>`).join("")}
    </select></label>`;

  const input = (name, label, placeholder = "", type = "text") => `
    <label class="field"><span>${esc(label)}</span><input name="detail_${esc(name)}" type="${esc(type)}" maxlength="240" placeholder="${esc(placeholder)}"></label>`;

  const textarea = (name, label, placeholder = "") => `
    <label class="field template-full"><span>${esc(label)}</span><textarea name="detail_${esc(name)}" rows="3" maxlength="1600" placeholder="${esc(placeholder)}"></textarea></label>`;

  const checks = (name, label, options) => `
    <fieldset class="field template-full"><legend>${esc(label)}</legend><div class="template-checks">${options.map(([value, text]) => `
      <label class="template-check"><input type="checkbox" name="detail_${esc(name)}" value="${esc(value)}"><span>${esc(text)}</span></label>`).join("")}</div></fieldset>`;

  const commonFields = () => `
    ${select("purpose", "غرض التطبيق", [["screening","مسح أو استكشاف"],["diagnostic_support","دعم قرار تشخيصي ضمن تقييم شامل"],["planning","تخطيط دعم أو تدخل"],["progress","متابعة التغير"],["eligibility","توثيق للأهلية وفق نظام الجهة"],["research","بحث أو جودة خدمة"]], true)}
    ${select("setting", "بيئة التطبيق", [["clinic","عيادة أو مركز"],["home","المنزل"],["school","المدرسة"],["community","المجتمع أو العمل"],["remote","عن بُعد"],["multiple","بيئات متعددة"]], true)}
    ${checks("informants", "مصادر المعلومات المستخدمة", [["self","الشخص نفسه"],["parent","الوالد أو مقدم الرعاية"],["teacher","المعلم أو المدرسة"],["provider","مقدم خدمة"],["records","السجلات والتقارير"],["direct","الملاحظة أو الأداء المباشر"]])}
    ${checks("accommodations", "التكييفات المستخدمة", [["none","دون تكييفات"],["visual","دعم بصري"],["communication","تواصل بديل أو مترجم"],["motor","تكييف حركي أو طريقة استجابة"],["breaks","فواصل أو تقسيم الجلسة"],["environment","تعديل البيئة أو المثيرات"]])}
    ${select("validity", "صلاحية التطبيق للتفسير", [["valid","صالح للتفسير"],["qualified","صالح مع تحفظات"],["incomplete","غير مكتمل"],["invalid","غير صالح"],["pending","تحتاج المراجعة"]], true)}
    ${textarea("limitations", "القيود والتحفظات", "اللغة، التعب، التعاون، التكييفات، نقص المصادر أو أي عامل يؤثر في التفسير")}`;

  const ratingTemplate = () => `
    <div class="template-heading"><h3>قالب الاستبانة أو مقياس التقدير</h3><p>يوثق المجيب والنسخة والدرجات والمقارنة بين المصادر.</p></div>
    <div class="template-grid">
      ${commonFields()}
      ${select("respondent", "المجيب الأساسي", [["self","تقرير ذاتي"],["parent","والد أو مقدم رعاية"],["teacher","معلم"],["provider","مقدم خدمة"],["interview","مقابلة مقننة"],["multiple","أكثر من نموذج"]], true)}
      ${input("raw_score", "الدرجة الخام أو ملخص المجالات", "مثال: الدرجة الخام أو أسماء المجالات المرتفعة")}
      ${input("standard_score", "الدرجة المعيارية أو T-score", "أدخلها فقط من التقرير الرسمي")}
      ${input("percentile", "المئين أو النطاق", "مثال: المئين 75 أو النطاق المرتفع")}
      ${select("cross_source", "اتساق المصادر", [["consistent","متسقة"],["partly","متسقة جزئيًا"],["different","مختلفة بوضوح"],["single","مصدر واحد فقط"]])}
      ${textarea("subscales", "المجالات أو المقاييس الفرعية", "سجل المجالات ذات الدلالة والنتائج المتباينة دون نسخ بنود الأداة")}
    </div>`;

  const performanceTemplate = () => `
    <div class="template-heading"><h3>قالب اختبار الأداء أو القدرات</h3><p>يوثق شروط الجلسة ومؤشرات الأداء والدرجات الصادرة عن النسخة الأصلية.</p></div>
    <div class="template-grid">
      ${commonFields()}
      ${select("completion", "اكتمال الاختبار", [["complete","مكتمل"],["partial","مكتمل جزئيًا"],["discontinued","أوقف وفق القواعد"],["unable","تعذر التطبيق"]], true)}
      ${select("engagement", "المشاركة وبذل الجهد", [["adequate","مناسب"],["variable","متغير"],["limited","محدود"],["uncertain","غير مؤكد"]])}
      ${input("composite", "الدرجة الكلية أو المركبة", "من التقرير الرسمي عند توفرها")}
      ${input("indices", "المؤشرات أو الدرجات الفرعية", "مثال: ذاكرة عاملة، سرعة معالجة، قراءة، حركة")}
      ${input("confidence", "فاصل الثقة أو نطاق الخطأ", "إن ورد في التقرير الرسمي")}
      ${textarea("behavioral_observation", "الملاحظة السلوكية أثناء الأداء", "فهم التعليمات، الاستراتيجية، التعب، السرعة، التصحيح الذاتي، الاستجابة للفواصل")}
    </div>`;

  const interviewTemplate = () => `
    <div class="template-heading"><h3>قالب المقابلة أو الملاحظة المنظمة</h3><p>يوثق الوحدة والسياق والمصادر والملاحظات المباشرة.</p></div>
    <div class="template-grid">
      ${commonFields()}
      ${input("module", "الوحدة أو النموذج المستخدم", "الوحدة، الفئة العمرية أو شكل المقابلة")}
      ${input("duration", "مدة التطبيق", "مثال: 60 دقيقة")}
      ${checks("contexts", "السياقات التي جُمعت منها الملاحظات", [["structured","جلسة منظمة"],["free","نشاط حر"],["home","المنزل"],["school","المدرسة"],["community","المجتمع"],["video","مادة فيديو موثقة"]])}
      ${textarea("direct_observations", "الملاحظات المباشرة", "صف السلوك والتواصل والمشاركة دون استنتاجات غير مدعومة")}
      ${textarea("history_summary", "خلاصة التاريخ والمقابلة", "بداية الصعوبات، مسار النمو، الاختلاف بين البيئات، نقاط القوة والتغيرات")}
    </div>`;

  const externalTemplate = () => `
    <div class="template-heading"><h3>قالب الفحص الخارجي أو الجهازي</h3><p>لا تحاكي المنصة الجهاز؛ تسجل نتيجة صادرة عن الجهة المختصة.</p></div>
    <div class="template-grid">
      ${commonFields()}
      ${input("facility", "الجهة المنفذة", "المستشفى أو العيادة أو المختبر")}
      ${input("device_protocol", "الجهاز أو البروتوكول", "اسم الجهاز أو نوع الفحص والإعدادات الأساسية")}
      ${input("body_side", "الجهة أو الجانب", "يمين، يسار، ثنائي، مجال بصري، وضعية...")}
      ${input("measurement", "القياس والوحدة", "عتبة، زمن، مسافة، درجة، مستوى أو وحدة التقرير")}
      ${input("report_reference", "مرجع التقرير", "رقم التقرير أو اسم الملف المحلي دون بيانات شخصية")}
      ${select("result_class", "تصنيف النتيجة", [["within","ضمن المتوقع"],["borderline","حدية أو تحتاج متابعة"],["outside","خارج المتوقع"],["inconclusive","غير حاسمة"],["repeat","يلزم إعادة الفحص"]], true)}
      ${textarea("external_conclusion", "خلاصة الجهة المختصة", "انسخ الخلاصة المهنية المسموح بها دون رفع التقرير أو بيانات الهوية")}
    </div>`;

  const classificationTemplate = () => `
    <div class="template-heading"><h3>قالب التصنيف الوظيفي أو الحركي</h3><p>يوثق المستوى في السياق المعتاد والأجهزة والمساعدة، ويفصل التصنيف عن قياس التغير.</p></div>
    <div class="template-grid">
      ${commonFields()}
      ${input("level", "المستوى أو الفئة", "مثال: المستوى III أو التصنيف الوظيفي المحدد")}
      ${select("assistance", "مقدار المساعدة المعتاد", [["independent","مستقل"],["supervision","إشراف أو تذكير"],["partial","مساعدة جزئية"],["substantial","مساعدة كبيرة"],["complete","مساعدة كاملة"]])}
      ${checks("equipment", "الأجهزة أو وسائل الوصول", [["none","دون جهاز"],["orthosis","جبيرة أو جهاز تقويمي"],["walker","مشاية أو عكاز"],["wheelchair","كرسي متحرك"],["communication","جهاز تواصل"],["positioning","مقعد أو وضعية مساندة"]])}
      ${textarea("context_variation", "اختلاف الأداء بين البيئات", "المنزل، المدرسة، المجتمع، المسافات، الأسطح، التعب والمساعدة المتاحة")}
      ${textarea("change_measure", "مقياس التغير المكمل", "حدد الأداة التي ستقيس التغير إذا كان العنصر الحالي تصنيفًا ثابتًا")}
    </div>`;

  const behaviorTemplate = () => `
    <div class="template-heading"><h3>قالب التحليل الوظيفي للسلوك</h3><p>يحوّل الوصف إلى بيانات قابلة للقياس مع أولوية السلامة.</p></div>
    <div class="template-grid">
      ${commonFields()}
      ${textarea("operational_definition", "التعريف التشغيلي للسلوك", "ما الذي يفعله الشخص تحديدًا بحيث يتفق مراقبان على حدوثه؟")}
      ${input("frequency", "التكرار", "عدد المرات خلال فترة محددة")}
      ${input("duration", "المدة", "متوسط أو نطاق المدة")}
      ${input("intensity", "الشدة", "تعريف مستويات الشدة المستخدمة")}
      ${input("latency", "زمن الكمون", "الوقت بين المطلب أو الحدث وبدء السلوك")}
      ${checks("antecedents", "السوابق المتكررة", [["demand","مطلب أو مهمة"],["denied","منع أو تأجيل"],["transition","انتقال أو تغيير"],["attention","تغير الانتباه الاجتماعي"],["sensory","مثير حسي أو بيئي"],["pain","ألم أو تعب أو عامل صحي"]])}
      ${checks("consequences", "النتائج اللاحقة", [["escape","إيقاف المطلب أو الهروب"],["access","الحصول على شيء أو نشاط"],["attention","انتباه اجتماعي"],["sensory","تغير حسي أو تنظيم ذاتي"],["medical","تدخل صحي أو رعاية"],["unclear","غير واضح"]])}
      ${select("hypothesis", "الوظيفة أو الفرضية الأولية", [["escape","الهروب أو تجنب المطلب"],["tangible","الوصول لشيء أو نشاط"],["attention","الانتباه الاجتماعي"],["automatic","تعزيز تلقائي أو حسي"],["pain","ألم أو حاجة صحية"],["multiple","وظائف متعددة"],["unknown","غير محددة بعد"]])}
      ${textarea("safety_plan", "إجراءات السلامة والدعم الوقائي", "من يتدخل، ما الذي يُبعد، كيف يتم طلب المساعدة، وما البديل التواصلي أو البيئي")}
    </div>`;

  const communicationTemplate = () => `
    <div class="template-heading"><h3>قالب اللغة أو التواصل المعزز والبديل</h3><p>يوثق الوظائف التواصلية والوسيلة وطريقة الوصول والتعميم عبر الشركاء.</p></div>
    <div class="template-grid">
      ${commonFields()}
      ${checks("modalities", "وسائل التواصل المستخدمة", [["speech","الكلام"],["gesture","الإشارة أو الإيماء"],["sign","لغة الإشارة"],["pictures","الصور والرموز"],["writing","القراءة والكتابة"],["device","جهاز تواصل"]])}
      ${checks("functions", "الوظائف التواصلية الملاحظة", [["request","الطلب"],["refuse","الرفض"],["comment","التعليق والمشاركة"],["question","السؤال"],["social","التفاعل الاجتماعي"],["repair","إصلاح سوء الفهم"]])}
      ${select("access_method", "طريقة الوصول", [["direct_touch","لمس مباشر"],["pointing","إشارة أو تأشير"],["switch","مفتاح ومسح"],["eye_gaze","تتبع العين"],["partner","مسح بمساعدة الشريك"],["multiple","أكثر من طريقة"]])}
      ${textarea("trial_results", "نتائج التجربة العملية", "ما الوسائل التي جُربت؟ ما الدقة والسرعة والاستقلال؟ وفي أي بيئات؟")}
      ${textarea("partner_support", "دعم الشركاء والتعميم", "تدريب الأسرة والمدرسة، الانتظار، النمذجة، توفير النظام وإتاحة المفردات")}
    </div>`;

  const genericTemplate = () => `
    <div class="template-heading"><h3>قالب تطبيق مهني عام</h3><p>قالب مرن للأدوات التي لا تنتمي إلى نمط واحد.</p></div>
    <div class="template-grid">
      ${commonFields()}
      ${input("result_summary", "النتيجة المنظمة", "الدرجة أو المستوى أو الفئة من التقرير الرسمي")}
      ${textarea("domain_findings", "النتائج حسب المجالات", "نقاط القوة والاحتياجات والاختلاف بين المصادر")}
      ${textarea("recommendations", "التوصيات المرتبطة بالنتيجة", "أداة مكملة، تكييف، دعم، إحالة أو متابعة")}
    </div>`;

  const chooseTemplate = (tool) => {
    const text = `${tool?.name || ""} ${tool?.category || ""} ${tool?.kind || ""} ${tool?.inputMode || ""}`.toLowerCase();
    if (tool?.status === "external" || /external|device|audiometry|oae|abr|tympan|vision/.test(text)) return externalTemplate;
    if (/fba|abc data|fast|qabf|motivation assessment|behavior problems|scatterplot|السلوك الوظيفي|إيذاء الذات/.test(text)) return behaviorTemplate;
    if (/gmfcs|macs|cfcs|edacs|classification|تصنيف/.test(text)) return classificationTemplate;
    if (/communication|aac|language|speech|لغة|تواصل|نطق/.test(text)) return communicationTemplate;
    if (/interview|observation|adi|ados|disco|مقابلة|ملاحظة/.test(text)) return interviewTemplate;
    if (/rating|questionnaire|scale|vineland|abas|conners|brief|basc|cbcl|sdq|استبانة|تقدير/.test(text)) return ratingTemplate;
    if (/performance|test|wisc|wais|wppsi|stanford|leiter|wiat|woodcock|ktea|ctopp|towre|gort|mabc|bot|pdms|اختبار|قدرات|تحصيل/.test(text)) return performanceTemplate;
    return genericTemplate;
  };

  const renderTemplate = () => {
    const toolId = form.elements.toolId.value;
    const toolName = form.elements.toolName.value;
    const tool = D.professional.find((item) => item.id === toolId || item.name === toolName) || { name: toolName };
    const template = chooseTemplate(tool);
    container.innerHTML = template();
    container.dataset.templateTool = tool.id || tool.name || "custom";
    container.dataset.templateVersion = VERSION;
  };

  document.addEventListener("click", (event) => {
    if (!event.target.closest("[data-professional-tool],#professional-record-new")) return;
    queueMicrotask(renderTemplate);
  }, true);

  form.addEventListener("submit", () => {
    const details = {};
    const fd = new FormData(form);
    for (const [key, value] of fd.entries()) {
      if (!key.startsWith("detail_") || !String(value).trim()) continue;
      const cleanKey = key.slice(7);
      if (Object.prototype.hasOwnProperty.call(details, cleanKey)) {
        details[cleanKey] = Array.isArray(details[cleanKey]) ? [...details[cleanKey], String(value)] : [details[cleanKey], String(value)];
      } else {
        details[cleanKey] = String(value);
      }
    }
    if (!Object.keys(details).length) return;
    const structured = `\n\n[بيانات القالب المهني ${VERSION}]\n${JSON.stringify(details, null, 2)}`;
    notesField.value = `${notesField.value.trim()}${structured}`.trim();
  }, true);

  renderTemplate();
})();
