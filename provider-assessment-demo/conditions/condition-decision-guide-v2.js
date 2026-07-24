"use strict";

(() => {
  const registry = window.PA_CONDITION_PATHWAYS;
  const root = document.getElementById("condition-root");
  const slug = document.body.dataset.condition;
  const condition = registry?.conditions?.find((item) => item.slug === slug);
  if (!root || !condition || root.querySelector("[data-condition-decision-guide]")) return;

  const esc = (value) => String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");

  const profiles = {
    "autism": {
      referral: "هل تفسر أنماط التواصل الاجتماعي والسلوك المتكرر والمعلومات النمائية الحاجة الحالية إلى دعم متخصص؟",
      family: ["أمثلة على المبادرة والاستجابة والتواصل الوظيفي في مواقف طبيعية.", "المواقف التي تزيد أو تخف فيها الصعوبة، وطرق التواصل أو التهيئة التي تساعد."],
      functional: "التواصل والمشاركة والانتقال بين الأنشطة والاستقلال في البيئات اليومية.",
      progress: "أعد القياس بمؤشر تواصل أو مشاركة محدد، ولا تستخدم تغير درجة مسح بوصفه دليلًا تشخيصيًا."
    },
    "intellectual-disability": {
      referral: "ما نمط القدرات والتكيف الفعلي، وما مقدار الدعم المطلوب للتعلم والاستقلال والسلامة؟",
      family: ["ما الذي ينجزه الشخص باستقلال وما الذي يحتاج فيه تلميحًا أو مساعدة؟", "أمثلة على التواصل والعناية الذاتية والسلامة واستخدام المهارات في المجتمع."],
      functional: "السلوك التكيفي في التواصل والمهارات اليومية والمشاركة، لا الدرجة المعرفية وحدها.",
      progress: "تابع مهارة يومية قابلة للملاحظة ومستوى المساعدة والتعميم بين بيئتين."
    },
    "down-syndrome": {
      referral: "ما نقاط القوة والاحتياجات الحالية في التواصل والحركة والتعلم والاستقلال، وما العوامل الصحية المؤثرة؟",
      family: ["التغيرات الحديثة في السمع أو النوم أو البلع أو الطاقة أو التواصل.", "روتين يومي يريد الشخص أو الأسرة زيادة الاستقلال فيه."],
      functional: "ملف منفصل للغة والحركة والمهارات اليومية والمشاركة مع دمج المتابعة الصحية الرسمية.",
      progress: "استخدم هدفًا وظيفيًا واحدًا في التواصل أو العناية الذاتية أو الحركة مع شروط قياس ثابتة."
    },
    "adhd": {
      referral: "هل تظهر صعوبات الانتباه أو الاندفاع أو النشاط في أكثر من سياق، وما أثرها الوظيفي والبدائل التفسيرية؟",
      family: ["مواقف محددة يبدأ فيها الشخص المهمة أو يفقدها، وما الذي يغير الأداء.", "النوم والروتين والأدوية والقلق والتعلم وأي اختلاف بين البيت والمدرسة."],
      functional: "بدء المهمة وإكمالها والتنظيم وإدارة الوقت والأثر في المنزل والمدرسة أو العمل.",
      progress: "تابع سلوكًا تشغيليًا مثل زمن بدء المهمة أو نسبة الإكمال، لا الانطباع العام فقط."
    },
    "specific-learning-disabilities": {
      referral: "ما المهارة الأكاديمية المحددة المتأثرة، وما علاقتها بالتعليم السابق واللغة والانتباه والاستجابة للتدخل؟",
      family: ["عينات حديثة من القراءة أو الكتابة أو الرياضيات مع وصف نوع الخطأ.", "تاريخ التعليم والغياب ولغة التدريس والدعم الذي جُرّب ونتيجته."],
      functional: "دقة وطلاقة وفهم المهارة المستهدفة وتأثيرها في الوصول للمنهج والواجبات والاختبارات.",
      progress: "استخدم عينات متكافئة ومتكررة لنفس المهارة، وسجل الدقة والطلاقة ونوع المساعدة."
    },
    "language-speech-disorders": {
      referral: "هل الصعوبة الأساسية في فهم اللغة أو التعبير أو أصوات الكلام أو الطلاقة أو الاستخدام الاجتماعي، وكيف تؤثر في المشاركة؟",
      family: ["أمثلة كلام أو تواصل في مواقف طبيعية ومع شركاء مختلفين.", "اللغات المستخدمة، تاريخ السمع، ومدى فهم الآخرين للكلام أو النظام البديل."],
      functional: "الوظائف التواصلية وقابلية الفهم والمشاركة، مع احترام التعدد اللغوي ووسائل التواصل البديلة.",
      progress: "تابع هدفًا لغويًا أو تواصليًا محددًا في عينة طبيعية، لا نتيجة جلسة معزولة فقط."
    },
    "hearing-loss-deafness": {
      referral: "كيف يؤثر الوصول السمعي أو البصري إلى اللغة في التواصل والتعلم والمشاركة، وما التهيئات المطلوبة؟",
      family: ["المواقف التي يصعب فيها فهم الكلام أو الوصول للمعلومات.", "استخدام الأجهزة أو لغة الإشارة أو الترجمة والتهيئات في الحياة اليومية."],
      functional: "الوصول إلى التواصل في الضوضاء والتعليم والمجتمع، وليس عتبة السمع وحدها.",
      progress: "وثق شروط البيئة وطريقة التواصل والجهاز أو التهيئة عند كل قياس للمقارنة العادلة."
    },
    "visual-impairment": {
      referral: "ما مقدار الرؤية الوظيفية أو الاعتماد على اللمس والسمع، وكيف يؤثر ذلك في الوصول والتنقل والتعلم؟",
      family: ["المهام التي تتغير فيها الكفاءة حسب الإضاءة أو التباين أو المسافة.", "وسائل الوصول المفضلة ومواقف التنقل التي تحتاج تدريبًا أو تهيئة."],
      functional: "الوصول إلى المواد والتنقل الآمن والاستقلال في المهام مع توثيق الإضاءة والتباين والمسافة.",
      progress: "كرر المهمة في شروط موثقة، وسجل الزمن والدقة ومستوى المساعدة وطريقة الوصول."
    },
    "cerebral-palsy": {
      referral: "كيف تؤثر الحركة والوضعية واليدين والكلام أو الأكل في النشاط والمشاركة، وما الدعم التقني أو البشري المطلوب؟",
      family: ["مهمة ذات معنى يريد الشخص أداءها بسهولة أو استقلال أكبر.", "الألم والتعب والوضعية والمعدات والبيئات التي تغير الأداء."],
      functional: "الإنجاز في المهام الفعلية والمشاركة وجودة الحركة ومستوى المساعدة، لا القدرة الجسدية المجردة فقط.",
      progress: "تابع مهمة وظيفية ثابتة مع توثيق المعدات والوضعية والتعب ومستوى المساعدة."
    },
    "developmental-coordination-disorder": {
      referral: "هل صعوبات اكتساب المهارات الحركية تؤثر فعليًا في الدراسة أو العناية الذاتية أو اللعب بعد استبعاد تفسيرات أخرى؟",
      family: ["المهارات الحركية التي يتجنبها الشخص أو تحتاج وقتًا ومساعدة زائدين.", "فرص التدريب السابقة والألم أو التعب أو العوامل البصرية والتعليمية."],
      functional: "جودة وسرعة المهام المدرسية واليومية والمشاركة والثقة، مع مقارنة الأداء بمتطلبات البيئة.",
      progress: "قِس مهمة حقيقية متكررة وسجل الجودة والزمن والمساعدة، لا اختبار المهارة المعزول فقط."
    },
    "physical-motor-disabilities": {
      referral: "ما العوائق الحركية والبيئية التي تحد من الاستقلال والمشاركة، وما التهيئات أو الأجهزة التي تغير الأداء؟",
      family: ["المسارات والانتقالات والمهام التي تتطلب مساعدة أو تعرض الشخص للإجهاد.", "الأجهزة الحالية ومشكلات الملاءمة والوصول في البيت والمدرسة أو المجتمع."],
      functional: "التنقل والانتقال والوصول واستخدام الأطراف والمشاركة ضمن البيئة الفعلية.",
      progress: "تابع مسافة أو زمنًا أو مستوى مساعدة في مهمة محددة مع تثبيت الجهاز والبيئة قدر الإمكان."
    },
    "sensory-processing": {
      referral: "ما الاستجابات الحسية القابلة للملاحظة، وفي أي سياق تؤثر في المشاركة أو التنظيم، وما البدائل الممكنة؟",
      family: ["سجل الموقف والمثير والاستجابة والمدة وما حدث قبلها وبعدها.", "التكييفات التي حسنت المشاركة أو زادت الضيق دون افتراض سبب تشخيصي واحد."],
      functional: "المشاركة والتنظيم والعودة للنشاط بعد تعديل البيئة، مع تجنب تفسير كل سلوك بوصفه حسيًا.",
      progress: "تابع مدة المشاركة أو العودة للنشاط في مواقف محددة، وسجل التكييف المستخدم."
    },
    "behavioral-emotional-disorders": {
      referral: "ما السلوك أو الانفعال المحدد، وما شدته ومدته وسياقه وأثره، وهل توجد عوامل صحية أو تعليمية أو بيئية؟",
      family: ["أمثلة حديثة مع الموقف والمدة والشدة وما ساعد على التعافي.", "التغيرات في النوم أو الصحة أو المدرسة أو العلاقات أو الأدوية."],
      functional: "المشاركة والتنظيم وطلب المساعدة والعلاقات والأداء اليومي، لا قائمة الأعراض وحدها.",
      progress: "عرّف السلوك أو المهارة تشغيليًا وتابع التكرار أو المدة أو الشدة مع سياق واضح."
    },
    "severe-behavior-self-injury": {
      referral: "ما الوظيفة المحتملة للسلوك وعوامل الخطر الطبية والبيئية والتواصلية، وما خطة السلامة الفورية؟",
      family: ["وصف دقيق لما يحدث قبل السلوك وأثناءه وبعده، مع الإصابات أو الحاجة إلى رعاية طبية.", "طرق التواصل المتاحة والعوامل الصحية أو الألم أو التغير المفاجئ."],
      functional: "السلامة والتواصل البديل والوصول للاحتياجات والعودة للنشاط، مع أولوية التقييم الطبي عند الاشتباه.",
      progress: "تابع التكرار والمدة والشدة وفرص استخدام بديل تواصلي، ولا تؤخر مسار الطوارئ عند خطر مباشر."
    },
    "multiple-disabilities-deafblindness": {
      referral: "كيف يتلقى الشخص المعلومات ويعبر عن الاختيار عبر قنوات حسية وتواصلية متاحة، وما الدعم المطلوب للمشاركة؟",
      family: ["الإشارات أو الحركات أو الرموز التي يستخدمها الشخص للتوقع والاختيار والرفض.", "الروتينات والأشخاص والبيئات التي تجعل التواصل أو المشاركة أوضح."],
      functional: "الوصول متعدد الحواس والتواصل والمشاركة والاستقلال، مع وقت استجابة كاف وشركاء مدربين.",
      progress: "تابع المبادرات والاستجابات والاختيارات في روتين طبيعي وبنفس قناة التواصل الموثقة."
    },
    "global-developmental-delay": {
      referral: "ما المجالات النمائية المتأثرة وما نقاط القوة، وهل النمط عام أم متفاوت، وما الخطوة التشخيصية والوظيفية التالية؟",
      family: ["مهارات ظهرت أو لم تظهر أو فُقدت، مع توقيتها وسياقها.", "أمثلة على اللعب والتواصل والحركة والعناية الذاتية في الروتين اليومي."],
      functional: "ملف منفصل لكل مجال نمائي مع أثره في الروتين والمشاركة، بدل عمر نمائي عام واحد.",
      progress: "اختر مهارة وظيفية واحدة في كل أولوية، وتابع مستوى المساعدة وظهورها مع أكثر من شخص أو بيئة."
    },
    "brain-injury-memory-executive": {
      referral: "ما التغير عن الأداء السابق في الذاكرة والانتباه والتنظيم والسلوك، وكيف يؤثر في السلامة والاستقلال؟",
      family: ["وصف الأداء قبل الإصابة وبعدها في مهام يومية محددة.", "مواقف النسيان أو الاندفاع أو التعب وفعالية المذكرات أو الدعم الخارجي."],
      functional: "إتمام التسلسل اليومي والتخطيط والمراقبة الذاتية واستخدام التعويضات في الواقع.",
      progress: "كرر مهمة وظيفية مع نفس الدعم الخارجي وسجل الاستقلال والأخطاء والزمن والتعب."
    },
    "aac": {
      referral: "هل يملك الشخص وسيلة تواصل فعالة ومتاحة دائمًا لمبادرة رسائل متنوعة مع شركاء وبيئات مختلفة؟",
      family: ["ما الرسائل التي يريد الشخص التعبير عنها ولا يستطيع حاليًا؟", "من يفهم النظام، وأين يتوفر، وما عوائق الوصول الحركي أو البصري أو اللغوي؟"],
      functional: "الوظائف التواصلية والاستقلال وسرعة الوصول وتدريب الشركاء، لا عدد الرموز المتعلمة فقط.",
      progress: "تابع المبادرات المستقلة وتنوع الوظائف ونجاح التواصل عبر شركاء وبيئات متعددة."
    },
    "genetic-syndromes": {
      referral: "ما الملف الفردي للقدرات والوظيفة والصحة بدل افتراض نمط ثابت من اسم المتلازمة؟",
      family: ["نقاط القوة والاحتياجات الحالية والتغيرات الصحية أو التعب أو الألم.", "الأهداف ذات الأولوية للشخص والأسرة في التواصل والاستقلال والمشاركة."],
      functional: "ملف فردي متعدد المجالات يدمج المعلومات الطبية الرسمية مع الأداء اليومي والاختيارات.",
      progress: "اختر مؤشرًا وظيفيًا ذا معنى للشخص، ووثق أي تغير صحي أو دوائي قد يؤثر في القياس."
    },
    "transition-adulthood": {
      referral: "ما المهارات والفرص والدعم اللازم للانتقال إلى أدوار راشدة مختارة في العمل والتعليم والسكن والمجتمع؟",
      family: ["ما الذي يريده الشخص لنفسه، وما القرارات التي يمكنه المشاركة فيها الآن؟", "خبرات العمل والتنقل وإدارة المواعيد والمال والعناية الذاتية والعلاقات."],
      functional: "الاختيار وتقرير المصير والمهارات المهنية والمجتمعية والاستقلال والدعم الطبيعي المتاح.",
      progress: "تابع أداء مهمة راشدة حقيقية وعدد الفرص والاختيارات الفعلية، لا التدريب داخل الجلسة فقط."
    }
  };

  const profile = profiles[condition.slug];
  if (!profile) return;

  const decisionTypes = [
    {
      id: "screening",
      title: "المسح أو الفرز",
      question: `هل توجد إشارة تستدعي تقييمًا أعمق لمسار ${condition.title}؟`,
      evidence: "أداة مسح ملائمة مع قلق الأسرة أو مقدم الخدمة ومعلومات أولية عن السياق.",
      next: "نتيجة مثيرة للقلق ⟵ إحالة وتقييم متعمق. نتيجة غير مثيرة مع قلق مستمر ⟵ متابعة أو تقييم إضافي، لا إغلاق آلي."
    },
    {
      id: "diagnostic",
      title: "التقييم التشخيصي",
      question: profile.referral,
      evidence: `تاريخ ومقابلة وملاحظة ومصادر متعددة يقودها أو يراجعها ${condition.team.slice(0, 2).join(" و")}.`,
      next: "صياغة توضح الأدلة المؤيدة والمخالفة والبدائل وحدود الصلاحية، دون اعتماد أداة واحدة."
    },
    {
      id: "functional",
      title: "التقييم الوظيفي",
      question: `كيف يظهر الأداء في ${profile.functional}`,
      evidence: `ملاحظة ومقابلة وعينات أداء في ${condition.focus.slice(0, 3).join("، ")} مع رأي الشخص والأسرة.`,
      next: `تحويل النتائج إلى ${condition.deliverables.slice(0, 2).join(" و")} مع تهيئات ومسؤوليات واضحة.`
    },
    {
      id: "progress",
      title: "متابعة التقدم",
      question: "هل تغير الأداء المستهدف فعلًا، وفي أي سياق وبأي مقدار؟",
      evidence: "خط أساس وتعريف تشغيلي ووحدة قياس وتواتر ثابت وهوية المقيم وأي تغير في التدخل أو البيئة.",
      next: profile.progress
    }
  ];

  const handoffFields = [
    "سؤال الإحالة والقرار المطلوب ونوع التقييم.",
    "مصادر الأدلة والبيئات والتواريخ والأشخاص المشاركين.",
    "الأدوات الرسمية وإصداراتها ولغاتها ومؤهل المنفذ أو مرجع النتيجة الخارجية.",
    "التكييفات وأي خروج عن الإجراءات، وتأثيره المحتمل في صلاحية النتيجة.",
    "نتيجة كل مصدر كما وردت، ثم التفسير المهني المنفصل عنها.",
    "نقاط القوة والاحتياجات والعوامل البيئية ورأي الشخص والأسرة.",
    "القرار والخطوة التالية والمسؤول والموعد وخط الأساس ومؤشر المتابعة.",
    "حدود التقرير: ما الذي لا يمكن استنتاجه من البيانات الحالية؟"
  ];

  const conflictRules = [
    "لا تُحسب متوسطات بين البيت والمدرسة أو المقيمين لإخفاء الاختلاف؛ افحص متطلبات كل بيئة ومستوى الدعم فيها.",
    "إذا تعارضت أداة معيارية مع الأداء الطبيعي، راجع اللغة والتواصل والحس والحركة والتعب والألم وفهم المهمة.",
    "إذا كانت جودة التطبيق أو النسخة أو هوية المجيب غير موثقة، صنّف النتيجة محدودة الصلاحية ولا تبنِ عليها قرارًا منفردًا.",
    "إذا بقي سؤال الإحالة بلا إجابة، أضف مصدرًا محددًا أو أعد صياغة السؤال بدل تكرار اختبارات غير موجهة."
  ];

  const rightsRules = [
    "الأداة الأصلية أو المفتوحة يمكن تشغيلها فقط وفق ترخيصها وتعليماتها المنشورة.",
    "الأداة التجارية المحمية تُستخدم عبر النسخة الرسمية والمستخدم المؤهل؛ المنصة تسجل الاسم والإصدار والنتيجة أو التقرير الخارجي والرابط الرسمي.",
    "لا تُنسخ البنود أو الصور أو جداول المعايير أو مفاتيح التصحيح أو صفحات الدليل إلى السجل أو المادة التعليمية.",
    "أي تكييف يغير طريقة التطبيق يجب توثيقه، ولا تُعامل الدرجة كأنها معيارية إذا لم تسمح التعليمات الرسمية بذلك."
  ];

  const quiz = [
    {
      id: "positive-screen",
      prompt: `ظهرت نتيجة مسح مثيرة للقلق في مسار ${condition.title}. ما الإجراء الصحيح؟`,
      options: [
        "تسجيل تشخيص نهائي مباشرة.",
        "إحالة لتقييم أعمق ودمج النتيجة مع التاريخ والملاحظة ومصادر أخرى.",
        "تجاهل النتيجة حتى تظهر مشكلة شديدة."
      ],
      answer: 1,
      explanation: "المسح يحدد الحاجة إلى تقييم إضافي ولا يثبت التشخيص أو الأهلية بمفرده."
    },
    {
      id: "different-settings",
      prompt: "كانت ملاحظات الأسرة والمدرسة مختلفة بوضوح. ما التفسير الأفضل؟",
      options: [
        "اختيار رأي الطرف الذي أعطى الدرجة الأعلى.",
        "حساب متوسط الدرجتين وإهمال السياق.",
        "تحليل متطلبات كل بيئة والدعم والمحفزات وأوقات ظهور السلوك."
      ],
      answer: 2,
      explanation: "الاختلاف بين البيئات قد يكون معلومة وظيفية مهمة، وليس خطأ يجب محوه."
    },
    {
      id: "protected-tool",
      prompt: "وصل تقرير من أداة تجارية محمية. ماذا يُحفظ في المنصة؟",
      options: [
        "البنود ومفتاح التصحيح كاملين لتسهيل المراجعة.",
        "اسم الأداة والإصدار والمنفذ والنتيجة الرسمية ومرجع التقرير والحدود دون المواد المحمية.",
        "صورة الدليل المطبوع والجداول المعيارية."
      ],
      answer: 1,
      explanation: "التوثيق المهني لا يتطلب نسخ المواد المحمية؛ تُسجل النتيجة الخارجية ومرجعها وسياقها."
    },
    {
      id: "progress-measure",
      prompt: "ما الذي يجعل متابعة التقدم قابلة للمقارنة؟",
      options: [
        "تغيير المهمة وطريقة القياس في كل مرة.",
        "الاعتماد على الانطباع العام فقط.",
        "تعريف المؤشر وخط الأساس ووحدة القياس والظروف والتواتر وتوثيق أي تغير."
      ],
      answer: 2,
      explanation: "المقارنة تحتاج مؤشرًا واضحًا وظروفًا موثقة حتى يُفهم التغير ولا يُنسب خطأً إلى الخطة."
    }
  ];

  const list = (items) => `<ul class="list">${items.map((item) => `<li>${esc(item)}</li>`).join("")}</ul>`;
  const guide = document.createElement("section");
  guide.dataset.conditionDecisionGuide = "v2";
  guide.className = "stack";
  guide.setAttribute("aria-label", `مسار القرار والتعلم التطبيقي لحالة ${condition.title}`);
  guide.innerHTML = `
    <section class="panel">
      <p class="eyebrow">مسار قرار خاص بالحالة</p>
      <h2>من سؤال الإحالة إلى القرار في ${esc(condition.title)}</h2>
      <p><strong>سؤال الإحالة المقترح:</strong> ${esc(profile.referral)}</p>
      <div class="course" role="list">
        ${decisionTypes.map((item) => `<article class="metric" role="listitem"><strong>${esc(item.title)}</strong><span><b>السؤال:</b> ${esc(item.question)}</span><span><b>الأدلة المطلوبة:</b> ${esc(item.evidence)}</span><span><b>الخطوة التالية:</b> ${esc(item.next)}</span></article>`).join("")}
      </div>
    </section>

    <section class="panel">
      <h2>ما الذي تحضره الأسرة ومقدم الخدمة؟</h2>
      <div class="course">
        <article class="metric"><strong>من الأسرة أو الشخص</strong>${list(profile.family)}</article>
        <article class="metric"><strong>من مقدم الخدمة</strong>${list([
          `أمثلة أو عينات أداء مرتبطة بـ${condition.focus.slice(0, 3).join("، ")}.`,
          "تواريخ الخدمات والتدخلات والتغييرات ودرجة الالتزام والسياق.",
          "تقرير يوضح ما نُفذ فعلًا وما لم يُنفذ، لا توصيات عامة فقط."
        ])}</article>
      </div>
    </section>

    <section class="panel">
      <h2>عند اختلاف النتائج أو ضعف صلاحيتها</h2>
      ${list(conflictRules)}
      <div class="notice">لا تُخفى النتيجة غير المتوافقة ولا تُحوّل تلقائيًا إلى تشخيص. تُوثق، ويُشرح سبب محدوديتها، ويُحدد مصدر إضافي يجيب سؤالًا واضحًا.</div>
    </section>

    <section class="panel">
      <h2>قالب تسليم الحالة بين أعضاء الفريق</h2>
      ${list(handoffFields)}
      <p><strong>معيار الإغلاق:</strong> أُجيب سؤال الإحالة، وفُصلت النتيجة عن التفسير، ووُثقت الحدود، واتفق الفريق مع الشخص أو الأسرة على خطوة تالية ومؤشر متابعة.</p>
    </section>

    <section class="panel">
      <h2>حقوق الأدوات والتكامل الرسمي</h2>
      ${list(rightsRules)}
    </section>

    <section class="panel" data-decision-quiz>
      <h2>تدريب تطبيقي: أربعة قرارات يجب إتقانها</h2>
      <p>اختر الإجابة المهنية الأفضل. تُحفظ النتيجة محليًا داخل هذا المتصفح فقط.</p>
      <div class="stack">
        ${quiz.map((question, qIndex) => `<fieldset class="metric" data-quiz-question="${esc(question.id)}"><legend><strong>${qIndex + 1}. ${esc(question.prompt)}</strong></legend>${question.options.map((option, optionIndex) => `<label><input type="radio" name="${esc(question.id)}" value="${optionIndex}"> ${esc(option)}</label>`).join("")}<p class="muted" data-quiz-feedback hidden></p></fieldset>`).join("")}
      </div>
      <div class="actions"><button class="button" type="button" data-check-decision-quiz>تحقق من الإجابات</button><button class="button secondary" type="button" data-reset-decision-quiz>إعادة التدريب</button></div>
      <p class="notice" data-decision-quiz-status aria-live="polite">لم يُقيّم التدريب بعد.</p>
    </section>

    <section class="panel">
      <h2>المراجع المؤسسية لهذا الإطار</h2>
      <ul class="list">
        <li><a href="https://www.who.int/standards/classifications/international-classification-of-functioning-disability-and-health" rel="noopener noreferrer">منظمة الصحة العالمية: ICF والوظيفة والنشاط والمشاركة والعوامل البيئية</a></li>
        <li><a href="https://www.aap.org/en/patient-care/developmental-surveillance-and-screening-patient-care/" rel="noopener noreferrer">الأكاديمية الأمريكية لطب الأطفال: المراقبة والمسح النمائي عمليتان متكاملتان وليستا بديلتين</a></li>
        <li><a href="https://www.cdc.gov/act-early/about/developmental-monitoring-and-screening.html" rel="noopener noreferrer">CDC، تحديث 16 فبراير 2026: المسح الرسمي يحدد الحاجة إلى تقييم إضافي</a></li>
        <li><a href="https://sites.ed.gov/idea/regs/b/d/300.304" rel="noopener noreferrer">IDEA §300.304: استخدام أدوات واستراتيجيات متعددة وعدم اعتماد مقياس واحد معيارًا وحيدًا</a></li>
      </ul>
      <p class="muted">هذه مراجع لإطار القرار العام. اختيار أداة محددة أو تشخيص أو أهلية يخضع للقانون المحلي، وتعليمات النسخة الرسمية، ومؤهل الممارس، والسياق الفردي.</p>
    </section>`;

  const mainStack = root.querySelector(".layout main.stack");
  if (mainStack) mainStack.append(...guide.children);
  else root.appendChild(guide);

  const storageKey = `pa-condition-decision-quiz-v2:${condition.slug}`;
  const readSaved = () => {
    try { return JSON.parse(localStorage.getItem(storageKey) || "{}"); } catch (_) { return {}; }
  };
  const writeSaved = (value) => {
    try { localStorage.setItem(storageKey, JSON.stringify(value)); } catch (_) {}
  };

  const restoreQuiz = () => {
    const saved = readSaved();
    for (const [questionId, answer] of Object.entries(saved.answers || {})) {
      const input = root.querySelector(`[data-quiz-question="${CSS.escape(questionId)}"] input[value="${CSS.escape(String(answer))}"]`);
      if (input) input.checked = true;
    }
    if (Number.isInteger(saved.score)) {
      const status = root.querySelector("[data-decision-quiz-status]");
      if (status) status.textContent = `النتيجة السابقة: ${saved.score} من ${quiz.length}.`;
    }
  };

  const evaluateQuiz = () => {
    const answers = {};
    let score = 0;
    quiz.forEach((question) => {
      const fieldset = root.querySelector(`[data-quiz-question="${CSS.escape(question.id)}"]`);
      const selected = fieldset?.querySelector("input:checked");
      const feedback = fieldset?.querySelector("[data-quiz-feedback]");
      const answer = selected ? Number(selected.value) : null;
      answers[question.id] = answer;
      const correct = answer === question.answer;
      if (correct) score += 1;
      if (feedback) {
        feedback.hidden = false;
        feedback.textContent = answer === null ? `لم تُجب. ${question.explanation}` : `${correct ? "إجابة صحيحة." : "تحتاج مراجعة."} ${question.explanation}`;
      }
      fieldset?.classList.toggle("completed", correct);
    });
    const status = root.querySelector("[data-decision-quiz-status]");
    if (status) status.textContent = score === quiz.length ? `أُتقنت القرارات الأربعة (${score}/${quiz.length}).` : `النتيجة ${score} من ${quiz.length}. راجع التفسير تحت كل سؤال.`;
    writeSaved({ answers, score, completedAt: new Date().toISOString(), condition: condition.slug });
  };

  const resetQuiz = () => {
    root.querySelectorAll("[data-quiz-question]").forEach((fieldset) => {
      fieldset.querySelectorAll("input").forEach((input) => { input.checked = false; });
      fieldset.classList.remove("completed");
      const feedback = fieldset.querySelector("[data-quiz-feedback]");
      if (feedback) { feedback.hidden = true; feedback.textContent = ""; }
    });
    try { localStorage.removeItem(storageKey); } catch (_) {}
    const status = root.querySelector("[data-decision-quiz-status]");
    if (status) status.textContent = "أُعيد التدريب. اختر إجابة لكل سؤال.";
  };

  root.querySelector("[data-check-decision-quiz]")?.addEventListener("click", evaluateQuiz);
  root.querySelector("[data-reset-decision-quiz]")?.addEventListener("click", resetQuiz);
  restoreQuiz();
})();
