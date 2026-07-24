"use strict";

(() => {
  const registry = window.PA_CONDITION_PATHWAYS;
  const root = document.getElementById("condition-root");
  const slug = document.body.dataset.condition;
  const condition = registry?.conditions?.find((item) => item.slug === slug);
  if (!root || !condition || root.querySelector("[data-assessment-education]")) return;

  const esc = (value) => String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");

  const types = [
    {
      id: "screening",
      title: "1. المسح أو الفرز",
      purpose: "يحدد احتمال وجود حاجة تستحق التقييم المتعمق، ولا يثبت التشخيص ولا يحدد الأهلية بمفرده.",
      output: "نتيجة مثل: لا توجد إشارة حالية، إعادة مسح، أو إحالة لتقييم أشمل.",
      record: "اسم الأداة والإصدار واللغة والمجيب والتاريخ وسبب المسح والنتيجة وخطوة المتابعة."
    },
    {
      id: "diagnostic",
      title: "2. التقييم التشخيصي",
      purpose: "يجيب سؤالًا تشخيصيًا محددًا عبر تاريخ ومقابلة وملاحظة وأدوات ملائمة وفحص البدائل التفسيرية.",
      output: "صياغة سريرية مبررة توضح الأدلة المؤيدة والمخالفة والحدود والحالات المصاحبة أو البديلة.",
      record: "السؤال التشخيصي، مصادر المعلومات، المعايير المستخدمة، التكييفات، صلاحية النتائج، ومن اتخذ القرار."
    },
    {
      id: "functional",
      title: "3. التقييم الوظيفي",
      purpose: "يصف ما يستطيع الشخص فعله في النشاط والمشاركة، والعوائق والميسرات في البيت والمدرسة والعمل والمجتمع.",
      output: "ملف نقاط قوة واحتياجات وتكييفات وأولويات دعم مرتبطة بمواقف الحياة الفعلية.",
      record: "المهمة والبيئة ومستوى المساعدة والجودة والاستقلال والعوامل البيئية ورأي الشخص والأسرة."
    },
    {
      id: "progress",
      title: "4. متابعة التقدم",
      purpose: "تستخدم مؤشرات متكررة حساسة للتغير للإجابة: هل تحسن الأداء المستهدف، وبأي مقدار، وفي أي سياق؟",
      output: "خط أساس وهدف وفترات قياس واتجاه وصفي وقرار استمرار أو تعديل أو إنهاء الخطة.",
      record: "تعريف المؤشر ووحدة القياس وتواتر الجمع وهوية المقيم وثبات الظروف وأي تغيير في التدخل."
    }
  ];

  const progressByCondition = {
    "autism": ["عدد المبادرات التواصلية الوظيفية في موقف طبيعي", "الاستقلال في الانتقال بين نشاطين", "المشاركة المشتركة مع شريك مألوف"],
    "intellectual-disability": ["نسبة إتمام روتين يومي بأقل مساعدة", "استخدام مهارة سلامة في البيئة الطبيعية", "تعميم المهارة بين البيت والمجتمع"],
    "down-syndrome": ["وضوح طلب وظيفي أو استجابة تواصلية", "إتمام مهارة عناية ذاتية", "التحمل والمشاركة في نشاط حركي مناسب"],
    "adhd": ["بدء المهمة خلال زمن محدد", "نسبة إكمال واجبات قصيرة", "عدد مرات استخدام استراتيجية تنظيم دون تذكير"],
    "specific-learning-disabilities": ["دقة وطلاقة مهارة أكاديمية محددة", "نسبة الاستقلال في استخدام استراتيجية تعلم", "الاحتفاظ بالمهارة عبر أسابيع"],
    "language-speech-disorders": ["عدد الوظائف التواصلية في عينة طبيعية", "نسبة الفهم أو الإنتاج لهدف لغوي محدد", "قابلية فهم الكلام لدى شركاء مختلفين"],
    "hearing-loss-deafness": ["الاستجابة للمعلومات السمعية في بيئة حقيقية", "فهم الكلام وفق ظروف ضوضاء موثقة", "الاستخدام اليومي الفعلي للجهاز وفق سجل مختص"],
    "visual-impairment": ["الوصول المستقل إلى مادة تعليمية", "زمن العثور على هدف بصري أو لمسي", "الاستقلال والأمان في مسار تنقل محدد"],
    "cerebral-palsy": ["إنجاز مهمة حركة أو يدين ذات معنى", "مستوى المساعدة في الأكل أو التواصل", "المشاركة في نشاط مختار"],
    "developmental-coordination-disorder": ["جودة إتمام مهمة مدرسية أو عناية ذاتية", "السرعة مع الحفاظ على الدقة", "المشاركة في اللعب أو النشاط الحركي"],
    "physical-motor-disabilities": ["مسافة أو زمن تنقل ضمن شروط ثابتة", "الاستقلال في الانتقال أو استخدام الجهاز", "المشاركة في دور منزلي أو مدرسي أو مجتمعي"],
    "sensory-processing": ["مدة المشاركة قبل الحاجة إلى استراحة", "العودة للنشاط بعد تكييف بيئي", "عدد المواقف المنجزة دون ضيق شديد"],
    "behavioral-emotional-disorders": ["الحضور والمشاركة في نشاط متوقع", "استخدام مهارة تنظيم أو طلب مساعدة", "شدة أو مدة عرض محدد وفق تعريف واضح"],
    "severe-behavior-self-injury": ["التكرار والمدة والشدة وفق تعريف تشغيلي", "عدد فرص استخدام تواصل بديل", "معدل التعافي والعودة الآمنة للنشاط"],
    "multiple-disabilities-deafblindness": ["المبادرات والاستجابات عبر قناة تواصل متاحة", "الاختيار المستقل بين بديلين", "المشاركة في روتين طبيعي متعدد الحواس"],
    "global-developmental-delay": ["اكتساب مهارة نمائية وظيفية محددة", "مستوى المساعدة في روتين يومي", "ظهور المهارة مع أكثر من شخص وبيئة"],
    "brain-injury-memory-executive": ["إتمام تسلسل يومي باستخدام دعم خارجي", "تذكر معلومة وظيفية بعد مدة محددة", "الاستقلال في التخطيط والمراجعة الذاتية"],
    "aac": ["عدد المبادرات التواصلية المستقلة", "تنوع الوظائف والكلمات أو الرموز المستخدمة", "نجاح الوصول للنظام عبر بيئات وشركاء مختلفين"],
    "genetic-syndromes": ["مؤشر وظيفي فردي مرتبط بالتواصل أو الحركة أو الاستقلال", "المشاركة مع مراعاة التعب والحالة الطبية", "جودة الحياة واختيار الشخص أو الأسرة"],
    "transition-adulthood": ["إتمام مهمة مهنية أو مجتمعية بمعيار واضح", "الاستقلال في التنقل أو إدارة موعد أو مال", "عدد الأدوار والخيارات التي يمارسها الشخص فعليًا"]
  };

  const genericFamilyQuestions = [
    "ما التغير الذي سيحدث فرقًا حقيقيًا في الحياة اليومية خلال الأشهر المقبلة؟",
    "أين تظهر القوة أو الصعوبة أكثر: البيت، المدرسة، العمل، المجتمع أم مع أشخاص محددين؟",
    "ما التكييفات أو طرق التواصل التي تجعل الشخص ينجح؟",
    "ما النتائج التي لا تتفق مع ملاحظات الشخص أو الأسرة، وما سبب الاختلاف المحتمل؟",
    "ما المؤشر البسيط الذي سنراجعه لاحقًا لمعرفة أن الخطة نافعة؟"
  ];

  const interpretationRules = [
    "ابدأ بسؤال الإحالة، لا بالدرجة: اذكر ما الذي كان مطلوبًا فهمه أو اتخاذ قرار بشأنه.",
    "افصل بين نتيجة الأداة وبين الاستنتاج المهني؛ الدرجة دليل واحد ضمن مصادر متعددة.",
    "صِف صلاحية النتيجة: اللغة، السمع، البصر، الحركة، التعب، الألم، الأدوية، وطريقة التواصل قد تغير الأداء.",
    "فسر التباين بين البيئات بدل دمج الإجابات قسرًا؛ الاختلاف قد يكشف أثر السياق أو مستوى الدعم.",
    "اختم بخطوة قابلة للتنفيذ ومؤشر متابعة، لا بعبارة عامة مثل المتابعة عند الحاجة."
  ];

  const documentationChecklist = [
    "هوية الحالة باسم مستعار وUID، وسؤال الإحالة، والموافقات وحدود السرية.",
    "مصادر المعلومات وتواريخها والبيئات التي تمت ملاحظتها.",
    "اسم الأداة الرسمي والإصدار واللغة والمالك أو الناشر والمؤهل المطلوب للتطبيق.",
    "من طبق أو سجل النتيجة، وطريقة التطبيق، وأي تكييفات أو خروج عن الإجراءات الأصلية.",
    "النتيجة كما وردت من المصدر المصرح، دون نسخ البنود أو مفاتيح التصحيح أو الجداول المعيارية.",
    "نقاط القوة والاحتياجات والعوامل البيئية والمخاطر وخطة الإحالة أو الدعم.",
    "مؤشر خط الأساس والهدف والموعد والمسؤول عن إعادة القياس."
  ];

  const sourceLinks = [
    { label: "منظمة الصحة العالمية: إطار ICF للوظيفة والنشاط والمشاركة والعوامل البيئية", href: "https://www.who.int/standards/classifications/international-classification-of-functioning-disability-and-health" },
    { label: "الأكاديمية الأمريكية لطب الأطفال: المراقبة والمسح النمائي", href: "https://www.aap.org/en/patient-care/developmental-surveillance-and-screening-patient-care/" },
    { label: "CDC: الفرق بين المراقبة والمسح والتقييم النمائي", href: "https://www.cdc.gov/act-early/about/developmental-monitoring-and-screening.html" }
  ];

  const list = (items) => `<ul class="list">${items.map((item) => `<li>${esc(item)}</li>`).join("")}</ul>`;
  const education = document.createElement("section");
  education.dataset.assessmentEducation = "true";
  education.className = "stack";
  education.setAttribute("aria-label", "التفسير والتوثيق والتعليم الأسري");
  education.innerHTML = `
    <section class="panel">
      <p class="eyebrow">إطار القرار السريري والتربوي</p>
      <h2>أربعة أنواع مختلفة من التقييم</h2>
      <p>لا يجوز التعامل مع المسح، والتقييم التشخيصي، والتقييم الوظيفي، ومتابعة التقدم كأنها عملية واحدة. لكل نوع سؤال ونتيجة وطريقة توثيق مختلفة.</p>
      <div class="course assessment-type-course">
        ${types.map((item) => `<article class="metric"><strong>${esc(item.title)}</strong><span><b>الغرض:</b> ${esc(item.purpose)}</span><span><b>المخرج:</b> ${esc(item.output)}</span><span><b>التوثيق:</b> ${esc(item.record)}</span></article>`).join("")}
      </div>
    </section>

    <section class="panel">
      <h2>كيف تُفسر النتائج دون مبالغة تشخيصية؟</h2>
      ${list(interpretationRules)}
      <div class="notice">النتيجة المرتفعة في أداة مسح تعني أن التقييم الإضافي مبرر، ولا تعني ثبوت الحالة. النتيجة المنخفضة لا تلغي قلقًا مستمرًا أو فقدان مهارة أو خطرًا مباشرًا.</div>
    </section>

    <section class="panel">
      <h2>مؤشرات متابعة مناسبة لمسار ${esc(condition.title)}</h2>
      <p>تُختار المؤشرات بالتعاون مع الشخص والأسرة، وتُقاس في ظروف موثقة وبأقل عبء ممكن.</p>
      ${list(progressByCondition[condition.slug] || condition.focus.slice(0, 3))}
      <p><strong>صيغة الهدف:</strong> في [الموقف] سيؤدي الشخص [السلوك القابل للملاحظة] بمستوى مساعدة [محدد] في [عدد أو نسبة] من الفرص خلال [مدة].</p>
    </section>

    <section class="panel">
      <h2>قائمة توثيق الحالة المهنية</h2>
      ${list(documentationChecklist)}
    </section>

    <section class="panel">
      <h2>دليل الأسرة ومقدم الخدمة قبل الاجتماع</h2>
      <p>دوّن أمثلة حديثة ومحددة بدل الاكتفاء بوصف عام، واطلب نسخة مفهومة من الخلاصة والخطوات التالية.</p>
      ${list(genericFamilyQuestions)}
    </section>

    <section class="panel" data-course-progress>
      <h2>كورس قصير: مراجعة جودة خطة التقييم</h2>
      <p>أكمل الوحدات الأربع واحفظ تقدمك محليًا داخل المتصفح.</p>
      <div class="course">
        ${types.map((item) => `<button class="metric course-check" type="button" data-course-unit="${esc(item.id)}" aria-pressed="false"><strong>${esc(item.title)}</strong><span>اضغط بعد مراجعة الغرض والمخرج والتوثيق.</span></button>`).join("")}
      </div>
      <p class="notice" data-course-status>لم تكتمل أي وحدة بعد.</p>
    </section>

    <section class="panel">
      <h2>المراجع المؤسسية المستخدمة</h2>
      <ul class="list">${sourceLinks.map((source) => `<li><a href="${esc(source.href)}" rel="noopener noreferrer">${esc(source.label)}</a></li>`).join("")}</ul>
      <p class="muted">تعرض الروابط الأطر العامة فقط. اختيار أداة بعينها وتفسيرها يخضعان لإصدارها الرسمي وحقوقها وتعليماتها ومؤهل المستخدم.</p>
    </section>`;

  const mainStack = root.querySelector(".layout main.stack");
  if (mainStack) mainStack.append(...education.children);
  else root.appendChild(education);

  const storageKey = `pa-condition-course-v1:${condition.slug}`;
  const readProgress = () => {
    try { return JSON.parse(localStorage.getItem(storageKey) || "{}"); } catch (_) { return {}; }
  };
  const writeProgress = (value) => {
    try { localStorage.setItem(storageKey, JSON.stringify(value)); } catch (_) {}
  };
  const renderProgress = () => {
    const progress = readProgress();
    const buttons = [...root.querySelectorAll("[data-course-unit]")];
    buttons.forEach((button) => {
      const done = Boolean(progress[button.dataset.courseUnit]);
      button.setAttribute("aria-pressed", String(done));
      button.classList.toggle("completed", done);
    });
    const count = buttons.filter((button) => button.getAttribute("aria-pressed") === "true").length;
    const status = root.querySelector("[data-course-status]");
    if (status) status.textContent = count === buttons.length ? "اكتملت الوحدات الأربع. راجع الخطة مع الفريق وحدد مؤشر المتابعة." : `اكتملت ${count} من ${buttons.length} وحدات.`;
  };

  root.addEventListener("click", (event) => {
    const button = event.target.closest("[data-course-unit]");
    if (!button) return;
    const progress = readProgress();
    progress[button.dataset.courseUnit] = !progress[button.dataset.courseUnit];
    progress.updatedAt = new Date().toISOString();
    writeProgress(progress);
    renderProgress();
  });

  renderProgress();
})();
