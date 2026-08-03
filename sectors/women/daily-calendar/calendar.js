(() => {
  "use strict";

  const STORAGE_KEY = "hr-women-daily-calendar-v1";
  const MS_DAY = 86400000;
  const $ = (id) => document.getElementById(id);

  const monthPrograms = [
    ["تأسيس هادئ للصحة والعادات", "ابدئي من خط أساس واقعي للنوم والطاقة والمزاج والألم والحركة والرعاية الوقائية."],
    ["القلب والعلاقات والحدود", "صحة القلب لا تنفصل عن الضغط النفسي وجودة العلاقات والقدرة على قول لا بأمان."],
    ["الحركة والقوة والصحة الوظيفية", "الهدف حركة قابلة للاستمرار وقوة تدعم حياتك، لا عقاب للجسد ولا مقارنة."],
    ["النوم والتعافي وتنظيم الضغط", "التعافي مهارة صحية؛ الانتظام والضوء والراحة أنفع من مطاردة نوم مثالي."],
    ["الصحة أثناء الحيض وفهم النمط", "التتبع يصف النمط ويساعد على طلب الرعاية، لكنه لا يثبت سببًا أو تشخيصًا."],
    ["التغذية والطاقة والصحة الأيضية", "وجبات مرنة ومتوازنة وماء مناسب أفضل من القيود القاسية ودورات الحرمان."],
    ["الماء والجلد والحرارة والسلامة", "الاحتياجات تتغير مع الطقس والعمل والحمل والرضاعة والأدوية والحالة الصحية."],
    ["الأمان والعلاقات والدعم الاجتماعي", "العلاقة الصحية تحترم الموافقة والخصوصية والحدود ولا تستخدم الخوف أو السيطرة."],
    ["العمل والتعلم والصحة الوظيفية", "البيئة والتكييفات وتوزيع العبء جزء من الحل، وليست كل الصعوبة عيبًا فرديًا."],
    ["الوعي بالجسد والرعاية الوقائية", "اعرفي المعتاد لديك وناقشي الفحوص المناسبة لعمرك وتاريخك ومكانك مع مختصة."],
    ["التعايش مع الحالات المزمنة", "الخطة الجيدة تجمع المتابعة الطبية والروتين الواقعي والدعم ولا تختزل الحياة في المرض."],
    ["المراجعة والامتنان والتواصل", "راجعي ما نفعك فعلًا واحتفظي بالعادات الصغيرة التي يمكن حملها إلى عام جديد."]
  ];

  const morningBank = [
    "صباحك مساحة جديدة؛ خطوة صغيرة واضحة اليوم تكفي.",
    "ابدئي بلطف: قيمتك لا تُقاس بسرعة إنجازك.",
    "جسدك ليس مشروعًا للإصلاح؛ هو شريك يحتاج الإصغاء والرعاية.",
    "اختاري اليوم فعلًا واحدًا تحت سيطرتك واتركي الباقي للترتيب لاحقًا.",
    "الاستمرار الهادئ أقوى من البداية القاسية.",
    "من حقك أن تبدئي يومك دون مقارنة بجسد أو حياة شخص آخر.",
    "قولي لنفسك صباحًا: سأتعامل مع احتياجي بجدية ومن دون لوم.",
    "ليس مطلوبًا يوم مثالي؛ المطلوب قرار صحي واحد قابل للتنفيذ.",
    "مساحتك ووقتك وراحتك احتياجات مشروعة وليست مكافآت.",
    "كل ملاحظة صادقة عن جسمك أو مزاجك تساعدك على فهم أفضل.",
    "الصباح فرصة لضبط الاتجاه، وليس للحكم على اليوم كله.",
    "لديك الحق في السؤال والفهم والمشاركة في قرارات رعايتك.",
    "التعثر معلومة عن الخطة، وليس دليلًا على فشلك.",
    "القوة تشمل الراحة وطلب الدعم وتغيير الخطة عندما لا تناسبك.",
    "قابلي صباحك بجملة واقعية: أستطيع القيام بالخطوة التالية.",
    "احتياجاتك لا تقل أهمية لأنها غير مرئية للآخرين.",
    "خصصي لنفسك عشر دقائق قبل أن يمتلئ اليوم بطلبات الآخرين.",
    "وجود يوم ثقيل لا يلغي ما بنيته في الأيام السابقة.",
    "عاملي نفسك بالطريقة التي تتمنين أن تُعامل بها امرأة تحبينها.",
    "ابدئي من الواقع كما هو، لا من الصورة التي يفترضها الآخرون."
  ];

  const noonBoostBank = [
    "منتصف اليوم ليس اختبارًا لقدرتك؛ خذي نفسًا واختاري ما تحتاجينه الآن.",
    "أنوثتك ليست قالبًا واحدًا؛ هي طريقتك الخاصة في الحضور والاختيار والاعتناء بنفسك.",
    "ربما لا تحتاجين إلى مزيد من القوة الآن؛ ربما تحتاجين إلى دقيقة أمان وهدوء.",
    "ارفعي كتفيك ثم اتركيهما يهبطان؛ ليس عليك حمل اليوم كله دفعة واحدة.",
    "ضعي لمستك الجميلة في بقية اليوم: كلمة رقيقة لنفسك وحد واضح مع الآخرين.",
    "أنتِ أكثر من قائمة مهام؛ اختاري لحظة صغيرة تعيدك إلى نفسك.",
    "لا تهملي إشارات جسدك كي تكملي الصورة المثالية؛ الإصغاء شكل من أشكال القوة.",
    "رتبي ما بقي من اليوم حول طاقتك الحقيقية، لا حول توقعات غير واقعية.",
    "لمسة عطر تحبينها أو كوب دافئ أو ضوء لطيف قد تكون إشارة عودة لا رفاهية زائدة.",
    "قولي لنفسك: أستطيع تعديل الخطة من دون أن أعتذر عن احتياجي.",
    "اختاري الآن شيئًا واحدًا يخفف عنك بدل إضافة مهمة جديدة.",
    "الجمال في هذا الظهر أن تمنحي نفسك حضورًا كاملًا ولو لدقيقة.",
    "إن كان الصباح ثقيلًا، فالظهر بداية ثانية لا تحتاج إلى إذن.",
    "كوني حنونة وحازمة معًا: رقيقة مع نفسك وواضحة مع ما يستنزفك.",
    "لا تقارني إيقاعك بإيقاع امرأة أخرى؛ لكل جسد وحياة موسم مختلف.",
    "اسألي جسدك الآن: ماء أم حركة أم طعام أم هدوء أم دعم؟ ثم اختاري الأقرب.",
    "يمكنك أن تكوني طموحة وأن تستريحي؛ الأمران لا يتعارضان.",
    "اجعلي بقية اليوم أخف بدرجة واحدة فقط؛ هذا تعديل كافٍ ومؤثر.",
    "قوتك اليوم قد تظهر في طلب المساعدة أو تأجيل ما لا يحتمل طاقتك.",
    "احتفظي بمساحة وردية صغيرة في يومك: شيء تختارينه أنتِ لنفسك فقط.",
    "لا يلزم أن تكوني بخير تمامًا كي تكملي بلطف ووعي.",
    "انظري لما أنجزته منذ الصباح، ثم اختاري الخطوة التالية بلا جلد للذات.",
    "الهدوء ليس غياب الإنجاز؛ أحيانًا هو الطريقة الأذكى لحماية طاقتك.",
    "امنحي نفسك جملة صادقة: أنا أستحق أن أُعامل باحترام، مني ومن الآخرين."
  ];

  const factBank = [
    "تسجيل بداية النزف والألم والمزاج والنوم عبر عدة دورات يعطي وصفًا أفضل من الاعتماد على الذاكرة وحدها.",
    "الصحة النفسية والجسدية تتأثران بالنوم والضغط والعلاقات والموارد، وليس بعامل واحد فقط.",
    "تغيّر الأعراض عن المعتاد لديك أهم من مقارنة نفسك بمتوسط عام وحده.",
    "الرعاية الذاتية تكمل الرعاية المهنية ولا تستبدل التقييم عند وجود أعراض مقلقة أو مستمرة.",
    "الحركة الخفيفة المنتظمة قد تكون أكثر قابلية للاستمرار من جلسات شديدة متباعدة.",
    "الراحة المخططة تقلل تراكم الإرهاق؛ الانتظار حتى الانهيار يجعل الاستعادة أصعب.",
    "النزف أو الألم الذي يعطل العمل أو الدراسة يستحق مناقشة طبية.",
    "الضغط المزمن قد يظهر كتشتت أو شد عضلي أو صداع أو اضطراب نوم، وليس كقلق واضح فقط.",
    "الحدود الصحية تحمي الوقت والسلامة ولا تهدف إلى التحكم بالآخرين.",
    "الوجبة المتوازنة يمكن بناؤها من أطعمة محلية ومتاحة ومناسبة لحالتك.",
    "التعرض لضوء الصباح يساعد الساعة البيولوجية، بينما قد يؤخر الضوء الساطع ليلًا الاستعداد للنوم.",
    "تدوين الأسئلة قبل الموعد الصحي يزيد احتمال مناقشة ما يهمك بدل نسيانه تحت الضغط.",
    "الألم تجربة حقيقية حتى عندما لا يظهر سببه في فحص أولي؛ وقد يحتاج إلى متابعة مناسبة.",
    "الدواء قد يؤثر في النزف أو النوم أو الشهية أو المزاج؛ لا توقفيه فجأة دون مراجعة الواصف.",
    "توزيع أعمال الرعاية المنزلية يؤثر في الصحة والراحة والقدرة على الالتزام بالعلاج.",
    "الموافقة يمكن سحبها في أي وقت، والصمت أو الخوف لا يعني موافقة حرة.",
    "عدم انتظام الدورة قد يحدث لأسباب متعددة؛ التطبيق لا يستطيع تحديد السبب بمفرده.",
    "النزف بعد انقطاع الطمث ليس دورة عائدة ويحتاج تقييمًا طبيًا.",
    "التغير المفاجئ في الوعي أو التنفس أو القوة أو الكلام حالة طارئة.",
    "الهدف من التتبع اكتشاف النمط وتحسين الحوار مع المختصة، لا تحويل كل إحساس إلى مرض."
  ];

  const tipBank = [
    "ضعي الماء أو الدواء الموصوف أو دفتر المتابعة في مكان مرتبط بروتين ثابت بدل الاعتماد على الذاكرة.",
    "اكتبي ثلاث أولويات فقط لليوم واجعلي واحدة منها مرتبطة بصحتك أو راحتك.",
    "عند وصف عرض صحي اذكري البداية والشدة وما يزيده أو يخففه وتأثيره في حياتك.",
    "اجعلي هدف الحركة محددًا وقابلًا للتعديل: مدة قصيرة أو مسافة قريبة أو عدد مرات واقعي.",
    "خففي الضوء والشاشات قبل النوم تدريجيًا بدل الانتقال المفاجئ من نشاط عالٍ إلى النوم.",
    "احتفظي بقائمة حديثة للأدوية والمكملات والحساسيات واعرضيها في كل موعد جديد.",
    "راقبي النزف والألم بوصف وظيفي: هل يوقظك أو يمنع الخروج أو يسبب دوخة؟",
    "خططي لاستراحة قبل نقطة الإنهاك، لا بعدها فقط.",
    "استخدمي جملة حد واضحة: لا أستطيع الالتزام بهذا الآن ويمكنني مراجعته في وقت محدد.",
    "أضيفي مصدر بروتين وألياف إلى وجبة معتادة بدل إعادة بناء نظامك الغذائي في يوم واحد.",
    "حضري بيئة النوم: حرارة مريحة وضوء أقل ومنبه بعيد ومهمة الغد مكتوبة خارج الرأس.",
    "قبل الموعد اختاري سؤالًا رئيسيًا وطلبًا واضحًا ونتيجة تريدين فهمها.",
    "لا تغيري جرعة دواء موصوف بسبب تطبيق أو نصيحة عامة؛ سجلي المشكلة واتصلي بمقدم الرعاية.",
    "إذا شعرتِ بعدم الأمان استخدمي جهازًا أو قناة لا يراقبها الشخص المسيطر واطلبي دعمًا محليًا.",
    "لا تستخدمي توقع الدورة لتأكيد أو نفي الحمل؛ استخدمي اختبارًا مناسبًا واستشارة عند الحاجة.",
    "ثبتي وقت الاستيقاظ قدر الإمكان قبل محاولة فرض وقت نوم مبكر بالقوة.",
    "راجعي توقيت الكافيين وكميته عندما يظهر أرق أو خفقان وخففيه تدريجيًا إن لزم.",
    "أي نزف بعد انقطاع الطمث يستحق موعدًا طبيًا حتى لو كان قليلًا أو حدث مرة واحدة.",
    "احفظي أرقام الطوارئ وشخصًا موثوقًا في الهاتف باسم واضح وسهل الوصول.",
    "اختاري مؤشرًا واحدًا للمتابعة أسبوعيًا كي لا يتحول التتبع إلى عبء أو قلق مستمر."
  ];

  const ideaBank = [
    "أنشئي محطة صباحية صغيرة تضم ماءً ودفترًا وشيئًا يذكرك بالأولوية الصحية لليوم.",
    "استخدمي لوحة أسبوعية تقسم المهام إلى: ضروري وقابل للتأجيل ويمكن تفويضه.",
    "صممي وصفًا من سطرين لأعراضك يمكنك نسخه في موعد أو رسالة صحية.",
    "اختاري مسار حركة داخليًا وخارجيًا ليبقى لديك بديل عند تغير الطقس أو الطاقة.",
    "اجعلي آخر عشر دقائق من المساء منطقة انتقال هادئة بلا قرارات كبيرة.",
    "صوري قائمة الأدوية المحدثة واحفظي نسخة ورقية في الحقيبة.",
    "استخدمي رمزًا بسيطًا في التقويم لتمييز الألم والنزف والطاقة دون تفاصيل حساسة.",
    "ضعي إشارة مبكرة للراحة مثل شد الكتفين أو بطء التركيز قبل بلوغ الإنهاك.",
    "اكتبي ثلاث جمل حدود جاهزة للمواقف المتكررة حتى لا تبحثي عن الكلمات تحت الضغط.",
    "ابني قائمة وجبات إنقاذ سريعة من مكونات متاحة بدل الاعتماد على قوة الإرادة عند التعب.",
    "استخدمي ورقة تفريغ قبل النوم: ما يشغلني وما يمكن فعله غدًا وما ليس بيدي الآن.",
    "خصصي ملاحظة في الهاتف بعنوان أسئلتي الصحية القادمة وأضيفي إليها فور ظهور السؤال.",
    "أنشئي مقياسًا شخصيًا للألم من 0 إلى 5 مع وصف ما تستطيعين فعله في كل مستوى.",
    "اربطي كل دواء موصوف بعادة ثابتة وتنبيه محايد يحمي الخصوصية.",
    "جربي اجتماعًا منزليًا لعشر دقائق لتوزيع عبء الأسبوع بدل النقاش وقت الأزمة.",
    "اختاري كلمة سر مع شخص موثوق تعني أنك تحتاجين اتصالًا أو مساعدة دون شرح طويل.",
    "استخدمي لونًا لتوقع الدورة ولونًا مختلفًا للتاريخ الفعلي كي تلاحظي دقة التوقع.",
    "ضعي خطة بديلة منخفضة الطاقة لكل عادة: دقيقتان بدل عشر أو نسخة جالسة بدل الوقوف.",
    "صممي طلب تكييف من ثلاثة أجزاء: العائق والأثر والتعديل المقترح.",
    "اختاري يومًا أسبوعيًا لمراجعة السجل بدل مراقبته طوال الوقت."
  ];

  const suggestionBank = [
    "ابدئي اليوم قبل الرسائل بدقيقتين من الهدوء وتحديد النية.",
    "شاركي قائمة الأولويات مع من يعيش معك لتقليل الطلبات المتقاطعة.",
    "خذي معك ملخص الأعراض مطبوعًا أو على الهاتف في الموعد القادم.",
    "اختاري هذا الأسبوع نوع حركة تستمتعين به بدل ما يبدو مثاليًا على الإنترنت.",
    "جربي موعد إغلاق رقمي مسائيًا قبل النوم بثلاثين دقيقة.",
    "اطلبي من الصيدلي أو الطبيبة مراجعة التداخلات عند إضافة مكمل أو دواء دون وصفة.",
    "قارني هذا الشهر بالنمط المعتاد لديك لا بتجربة شخص آخر.",
    "ضعي استراحة قصيرة في التقويم كموعد لا يقل أهمية عن بقية المواعيد.",
    "ناقشي حدًا واحدًا متكررًا مع الشخص المعني في وقت هادئ لا أثناء النزاع.",
    "أضيفي صنفًا غنيًا بالألياف تدريجيًا مع ماء مناسب بدل الزيادة المفاجئة.",
    "جربي تثبيت موعد الاستيقاظ خمسة أيام ثم راقبي أثره قبل تغيير أشياء متعددة.",
    "اطلبي في الموعد شرح الخيارات والفوائد والمخاطر وما يحدث إذا انتظرتِ.",
    "اقترحي تقسيم المهام حسب الوقت والقدرة لا حسب أدوار اجتماعية مفترضة.",
    "راجعي إعدادات الخصوصية والموقع في الهاتف خصوصًا عند وجود مراقبة أو سيطرة.",
    "أرسلي رسالة قصيرة لشخص آمن: أحتاج عشر دقائق للحديث هذا الأسبوع.",
    "سجلي تاريخ بدء الدورة الفعلي عند حدوثه كي تتحسن حسابات المتوسط لديك.",
    "اختاري نسخة أخف من جدولك في الأيام ذات الطاقة المنخفضة بدل إلغاء كل شيء.",
    "اجعلي غرفة النوم للنوم قدر الإمكان وانقلي العمل والنقاشات الثقيلة إلى مكان آخر.",
    "راجعي خطة الطوارئ مع الأسرة أو شخص موثوق بدل انتظار وقوع الأزمة.",
    "في نهاية الأسبوع اختاري عادة واحدة للاستمرار وواحدة للتعديل وواحدة للتوقف."
  ];

  const tenMinuteBank = [
    "اكتبي نية اليوم وحاجة جسدية واحدة وحدًا واحدًا يحمي وقتك.",
    "رتبي أولوياتك في ثلاث خانات: الآن ولاحقًا ولشخص آخر.",
    "سجلي عرضًا واحدًا بصيغة البداية والشدة والمحفزات والأثر الوظيفي.",
    "تحركي حركة مريحة تناسب قدرتك اليوم: مشي أو تمدد أو تمارين جلوس.",
    "جهزي روتين ما قبل النوم وأطفئي مصدر ضوء أو تنبيه غير ضروري.",
    "حدّثي قائمة الأدوية والمكملات والحساسيات وسبب استخدام كل عنصر.",
    "راجعي آخر أربعة أسابيع وحددي أيام النزف والألم والطاقة دون استنتاج تشخيص.",
    "اجلسي بلا مهمة وأرخي الفك والكتفين واسمحي باستراحة مقصودة.",
    "تدربي بصوت مسموع على جملة حد واضحة ومحترمة لموقف متكرر.",
    "جهزي مكونين لوجبة أو وجبة خفيفة متوازنة للغد.",
    "اكتبي ما يشغل ذهنك ثم ضعي بجانب كل بند: إجراء أو انتظار أو ليس بيدي.",
    "اكتبي خمسة أسئلة صحية ثم رتبي أهم سؤالين للموعد القادم.",
    "اعملي مسحًا جسديًا لطيفًا وحددي موضع الألم وطبيعته وما يخففه.",
    "اضبطي تنبيهات الدواء الموصوف بعناوين محايدة تحمي خصوصيتك.",
    "اكتبي كل مهام الرعاية المنزلية لهذا الأسبوع وحددي ما يمكن توزيعه.",
    "راجعي خطة الأمان الرقمية: كلمات المرور ومشاركة الموقع والأجهزة المتصلة.",
    "حدّثي تاريخ بدء الدورة الفعلي ودوّني فرق التوقع دون لوم أو قلق.",
    "صممي نسخة منخفضة الطاقة من عادة مهمة يمكنك تنفيذها في الأيام الصعبة.",
    "عدلي مساحة العمل: ارتفاع الشاشة ودعم الظهر ووضع القدمين والإضاءة.",
    "راجعي إنجازات الأسبوع واختاري تعديلًا واحدًا فقط للأسبوع التالي."
  ];

  const defaults = {
    settings: {
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "Asia/Amman",
      weekStart: 6,
      calendarSystem: "gregory",
      dailyTime: "08:00",
      noonTime: "12:30",
      cycleEnabled: false,
      lastPeriodStart: "",
      cycleLength: 28,
      bleedLength: 5,
      variability: 2,
      privacyMode: "neutral",
      reminderMinutes: 30,
      includeCycleInExport: false
    },
    logs: {},
    completions: {}
  };

  let state = loadState();
  let selectedDate = zonedToday(state.settings.timezone);
  let displayMonth = new Date(selectedDate.getFullYear(), selectedDate.getMonth(), 1, 12);
  let timerSeconds = 600;
  let timerId = null;

  function copy(value) { return JSON.parse(JSON.stringify(value)); }
  function loadState() {
    try {
      const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) || "null");
      if (!parsed) return copy(defaults);
      return {
        settings: { ...defaults.settings, ...(parsed.settings || {}) },
        logs: parsed.logs && typeof parsed.logs === "object" ? parsed.logs : {},
        completions: parsed.completions && typeof parsed.completions === "object" ? parsed.completions : {}
      };
    } catch (_error) { return copy(defaults); }
  }
  function saveState() { localStorage.setItem(STORAGE_KEY, JSON.stringify(state)); }
  function clamp(value, min, max, fallback) {
    const number = Number(value);
    return Number.isFinite(number) ? Math.min(max, Math.max(min, Math.round(number))) : fallback;
  }
  function dateOnly(date) { return new Date(date.getFullYear(), date.getMonth(), date.getDate(), 12); }
  function addDays(date, amount) { const next = dateOnly(date); next.setDate(next.getDate() + amount); return next; }
  function daysBetween(a, b) {
    return Math.round((Date.UTC(b.getFullYear(), b.getMonth(), b.getDate()) - Date.UTC(a.getFullYear(), a.getMonth(), a.getDate())) / MS_DAY);
  }
  function isoDate(date) {
    return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
  }
  function parseIso(value) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(value || "")) return null;
    const [y, m, d] = value.split("-").map(Number);
    const date = new Date(y, m - 1, d, 12);
    return Number.isNaN(date.getTime()) ? null : date;
  }
  function zonedToday(timeZone) {
    try {
      const parts = new Intl.DateTimeFormat("en-CA", { timeZone, year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(new Date());
      const map = Object.fromEntries(parts.map((part) => [part.type, part.value]));
      return new Date(Number(map.year), Number(map.month) - 1, Number(map.day), 12);
    } catch (_error) {
      const now = new Date();
      return new Date(now.getFullYear(), now.getMonth(), now.getDate(), 12);
    }
  }
  function formatDate(date, options = {}) {
    let output = new Intl.DateTimeFormat("ar-JO-u-nu-latn", { weekday: "long", year: "numeric", month: "long", day: "numeric", ...options }).format(date);
    if (state.settings.calendarSystem === "dual") {
      try {
        output += ` · ${new Intl.DateTimeFormat("ar-SA-u-ca-islamic-umalqura-nu-latn", { day: "numeric", month: "long", year: "numeric" }).format(date)}`;
      } catch (_error) { /* Gregorian remains available. */ }
    }
    return output;
  }
  function dayOfYear(date) { return daysBetween(new Date(date.getFullYear(), 0, 0, 12), date); }
  function pick(list, seed) { return list[((seed % list.length) + list.length) % list.length]; }
  function dailyContent(date) {
    const ordinal = dayOfYear(date);
    const month = date.getMonth();
    const day = date.getDate();
    return {
      morning: pick(morningBank, ordinal + month * 3),
      noon: pick(noonBoostBank, ordinal * 13 + month * 19),
      fact: pick(factBank, day + month * 5),
      tip: pick(tipBank, day * 3 + month * 7),
      idea: pick(ideaBank, day * 5 + month * 11),
      suggestion: pick(suggestionBank, day * 7 + month * 13),
      ten: pick(tenMinuteBank, day * 11 + month * 17),
      theme: monthPrograms[month][0],
      focus: monthPrograms[month][1]
    };
  }

  function cycleInfo(forDate = selectedDate) {
    const s = state.settings;
    const last = parseIso(s.lastPeriodStart);
    if (!s.cycleEnabled || !last) return null;
    const length = clamp(s.cycleLength, 15, 90, 28);
    const bleed = clamp(s.bleedLength, 1, 14, 5);
    const variability = clamp(s.variability, 0, 14, 2);
    const delta = daysBetween(last, forDate);
    let index = Math.floor(delta / length);
    if (delta < 0) index = Math.ceil(delta / length) - 1;
    const cycleStart = addDays(last, index * length);
    const nextStart = forDate <= cycleStart ? cycleStart : addDays(cycleStart, length);
    const currentStart = forDate >= cycleStart ? cycleStart : addDays(cycleStart, -length);
    return {
      length,
      bleed,
      variability,
      cycleDay: daysBetween(currentStart, forDate) + 1,
      nextStart,
      windowStart: addDays(nextStart, -variability),
      windowEnd: addDays(nextStart, variability + bleed - 1)
    };
  }

  function ensureMorningCard() {
    let target = $("dailyMorning");
    if (target) return target;
    const section = document.createElement("section");
    section.className = "daily-item ten morning";
    const label = document.createElement("span");
    label.textContent = "صباح إيجابي";
    target = document.createElement("p");
    target.id = "dailyMorning";
    section.append(label, target);
    const grid = document.querySelector(".daily-grid");
    grid.insertBefore(section, grid.firstChild);
    return target;
  }


  function ensureNoonCard() {
    let card = $("noonCheckIn");
    if (card) return card;
    card = document.createElement("section");
    card.id = "noonCheckIn";
    card.className = "daily-item noon-checkin";
    card.innerHTML = `
      <span>وقفة الظهر · 12:30</span>
      <h3>كيف تشعرين الآن؟</h3>
      <div class="noon-feelings" role="group" aria-label="اختاري شعورك الآن">
        <button type="button" class="noon-feeling" data-feeling="هادئة" aria-pressed="false">هادئة</button>
        <button type="button" class="noon-feeling" data-feeling="بخير" aria-pressed="false">بخير</button>
        <button type="button" class="noon-feeling" data-feeling="متعبة" aria-pressed="false">متعبة</button>
        <button type="button" class="noon-feeling" data-feeling="قلقة" aria-pressed="false">قلقة</button>
        <button type="button" class="noon-feeling" data-feeling="أحتاج استراحة" aria-pressed="false">أحتاج استراحة</button>
      </div>
      <p id="dailyNoonBoost" class="noon-boost"></p>
      <p id="noonStatus" class="noon-status" aria-live="polite"></p>`;
    card.addEventListener("click", (event) => {
      const button = event.target.closest("button[data-feeling]");
      if (!button) return;
      const key = isoDate(selectedDate);
      state.logs[key] = {
        ...(state.logs[key] || {}),
        noonFeeling: button.dataset.feeling,
        noonCheckedAt: new Date().toISOString()
      };
      saveState();
      card.querySelectorAll("button[data-feeling]").forEach((item) => {
        item.setAttribute("aria-pressed", String(item === button));
      });
      $("noonStatus").textContent = `سُجل شعورك: ${button.dataset.feeling}. خذي من الدفعة ما يناسبك واتركي الباقي.`;
    });
    const grid = document.querySelector(".daily-grid");
    const morning = ensureMorningCard().closest("section");
    grid.insertBefore(card, morning.nextSibling);
    return card;
  }

  function renderToday() {
    const content = dailyContent(selectedDate);
    $("selectedDate").textContent = formatDate(selectedDate);
    $("monthTheme").textContent = `${content.theme} — ${content.focus}`;
    ensureMorningCard().textContent = content.morning;
    const noonCard = ensureNoonCard();
    noonCard.querySelector("#dailyNoonBoost").textContent = content.noon;
    $("dailyFact").textContent = content.fact;
    $("dailyTip").textContent = content.tip;
    $("dailyIdea").textContent = content.idea;
    $("dailySuggestion").textContent = content.suggestion;
    $("dailyTen").textContent = content.ten;
    const key = isoDate(selectedDate);
    $("completeDay").checked = Boolean(state.completions[key]);
    const entry = state.logs[key] || {};
    noonCard.querySelectorAll("button[data-feeling]").forEach((button) => {
      button.setAttribute("aria-pressed", String(button.dataset.feeling === entry.noonFeeling));
    });
    $("noonStatus").textContent = entry.noonFeeling ? `شعور الظهر المسجل: ${entry.noonFeeling}` : "";
    $("mood").value = entry.mood ?? "";
    $("energy").value = entry.energy ?? "";
    $("pain").value = entry.pain ?? "";
    $("flow").value = entry.flow ?? "";
    $("privateNote").value = entry.note ?? "";
    const info = cycleInfo(selectedDate);
    $("cycleChip").hidden = !info;
    if (info) $("cycleChip").textContent = `اليوم التقديري ${Math.max(1, info.cycleDay)} من الدورة`;
    renderCycleSummary();
    renderStreak();
  }

  function renderCycleSummary() {
    const today = zonedToday(state.settings.timezone);
    const info = cycleInfo(today);
    $("cycleEmpty").hidden = Boolean(info);
    $("cycleSummary").hidden = !info;
    if (!info) return;
    const until = daysBetween(today, info.nextStart);
    $("nextPeriodDate").textContent = formatDate(info.nextStart, { weekday: undefined });
    $("daysUntilPeriod").textContent = until === 0 ? "اليوم تقريبًا" : until > 0 ? `${until} يوم` : "مرّ الموعد المتوقع";
    $("predictionRange").textContent = `${formatDate(info.windowStart, { weekday: undefined, year: undefined, month: "short" })} – ${formatDate(info.windowEnd, { weekday: undefined, year: undefined, month: "short" })}`;
    $("cycleDayValue").textContent = String(Math.max(1, info.cycleDay));
  }

  function renderStreak() {
    let streak = 0;
    let cursor = zonedToday(state.settings.timezone);
    while (state.completions[isoDate(cursor)]) { streak += 1; cursor = addDays(cursor, -1); }
    $("streakText").textContent = streak ? `سلسلة الاستمرار: ${streak} يوم` : "ابدئي سلسلة هادئة من اليوم";
  }

  function isInPredictedPeriod(date) {
    const info = cycleInfo(date);
    if (!info) return false;
    return [addDays(info.nextStart, -info.length), info.nextStart, addDays(info.nextStart, info.length)].some((start) => {
      return date >= addDays(start, -info.variability) && date <= addDays(start, info.variability + info.bleed - 1);
    });
  }

  function renderCalendar() {
    $("calendarMonthTitle").textContent = new Intl.DateTimeFormat("ar-JO-u-nu-latn", { month: "long", year: "numeric" }).format(displayMonth);
    const weekdays = ["الأحد", "الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت"];
    const start = Number(state.settings.weekStart);
    const ordered = [...weekdays.slice(start), ...weekdays.slice(0, start)];
    $("weekdayHeader").replaceChildren(...ordered.map((name) => Object.assign(document.createElement("span"), { textContent: name })));
    const first = new Date(displayMonth.getFullYear(), displayMonth.getMonth(), 1, 12);
    const offset = (first.getDay() - start + 7) % 7;
    const gridStart = addDays(first, -offset);
    const today = zonedToday(state.settings.timezone);
    const buttons = [];
    for (let index = 0; index < 42; index += 1) {
      const date = addDays(gridStart, index);
      const key = isoDate(date);
      const button = document.createElement("button");
      button.type = "button";
      button.className = "day-button";
      button.textContent = String(date.getDate());
      button.setAttribute("role", "gridcell");
      button.setAttribute("aria-label", formatDate(date));
      if (date.getMonth() !== displayMonth.getMonth()) button.classList.add("outside");
      if (key === isoDate(today)) button.classList.add("today");
      if (key === isoDate(selectedDate)) button.classList.add("selected");
      if (state.completions[key]) button.classList.add("completed");
      if (isInPredictedPeriod(date)) button.classList.add("period");
      button.addEventListener("click", () => {
        selectedDate = date;
        displayMonth = new Date(date.getFullYear(), date.getMonth(), 1, 12);
        renderAll();
        $("today").scrollIntoView({ behavior: "smooth", block: "start" });
      });
      buttons.push(button);
    }
    $("monthGrid").replaceChildren(...buttons);
  }

  function populateTimezones() {
    let zones = ["Asia/Amman", "Asia/Riyadh", "Asia/Dubai", "Asia/Kuwait", "Asia/Qatar", "Asia/Baghdad", "Asia/Beirut", "Africa/Cairo", "Africa/Casablanca", "Africa/Algiers", "Africa/Tunis", "Europe/London", "Europe/Paris", "America/New_York"];
    if (typeof Intl.supportedValuesOf === "function") {
      try { zones = Intl.supportedValuesOf("timeZone"); } catch (_error) { /* fallback */ }
    }
    if (!zones.includes(state.settings.timezone)) zones.unshift(state.settings.timezone);
    $("timezone").replaceChildren(...zones.map((zone) => {
      const option = document.createElement("option");
      option.value = zone;
      option.textContent = zone.replaceAll("_", " ");
      return option;
    }));
  }

  function populateSettings() {
    const s = state.settings;
    $("timezone").value = s.timezone;
    $("weekStart").value = String(s.weekStart);
    $("calendarSystem").value = s.calendarSystem;
    $("dailyTime").value = s.dailyTime;
    $("noonTime").value = s.noonTime;
    $("lastPeriodStart").value = s.lastPeriodStart;
    $("cycleLength").value = s.cycleLength;
    $("bleedLength").value = s.bleedLength;
    $("variability").value = String(s.variability);
    $("cycleEnabled").checked = s.cycleEnabled;
    $("privacyMode").value = s.privacyMode;
    $("reminderMinutes").value = String(s.reminderMinutes);
    $("includeCycleInExport").checked = s.includeCycleInExport;
  }

  function readSettings() {
    return {
      timezone: $("timezone").value || defaults.settings.timezone,
      weekStart: clamp($("weekStart").value, 0, 6, 6),
      calendarSystem: $("calendarSystem").value === "dual" ? "dual" : "gregory",
      dailyTime: /^\d{2}:\d{2}$/.test($("dailyTime").value) ? $("dailyTime").value : "08:00",
      noonTime: /^\d{2}:\d{2}$/.test($("noonTime").value) ? $("noonTime").value : "12:30",
      lastPeriodStart: $("lastPeriodStart").value,
      cycleLength: clamp($("cycleLength").value, 15, 90, 28),
      bleedLength: clamp($("bleedLength").value, 1, 14, 5),
      variability: clamp($("variability").value, 0, 14, 2),
      cycleEnabled: $("cycleEnabled").checked,
      privacyMode: ["neutral", "wellness", "explicit"].includes($("privacyMode").value) ? $("privacyMode").value : "neutral",
      reminderMinutes: clamp($("reminderMinutes").value, 0, 10080, 30),
      includeCycleInExport: $("includeCycleInExport").checked
    };
  }

  function renderAll() { renderToday(); renderCalendar(); }
  function updateTimer() {
    $("timerValue").textContent = `${String(Math.floor(timerSeconds / 60)).padStart(2, "0")}:${String(timerSeconds % 60).padStart(2, "0")}`;
  }
  function startTimer() {
    $("timerBox").hidden = false;
    if (timerId) return;
    timerId = window.setInterval(() => {
      timerSeconds -= 1;
      updateTimer();
      if (timerSeconds <= 0) {
        window.clearInterval(timerId);
        timerId = null;
        state.completions[isoDate(selectedDate)] = true;
        saveState();
        $("completeDay").checked = true;
        $("timerValue").textContent = "اكتملت عشر دقائق";
        renderCalendar();
        renderStreak();
      }
    }, 1000);
  }
  function pauseTimer() { if (timerId) window.clearInterval(timerId); timerId = null; }
  function resetTimer() { pauseTimer(); timerSeconds = 600; updateTimer(); }

  function icsEscape(text) { return String(text).replaceAll("\\", "\\\\").replaceAll("\n", "\\n").replaceAll(",", "\\,").replaceAll(";", "\\;"); }
  function icsStamp(date) {
    return `${date.getUTCFullYear()}${String(date.getUTCMonth() + 1).padStart(2, "0")}${String(date.getUTCDate()).padStart(2, "0")}T${String(date.getUTCHours()).padStart(2, "0")}${String(date.getUTCMinutes()).padStart(2, "0")}${String(date.getUTCSeconds()).padStart(2, "0")}Z`;
  }
  function icsLocal(date, time) {
    return `${date.getFullYear()}${String(date.getMonth() + 1).padStart(2, "0")}${String(date.getDate()).padStart(2, "0")}T${time.replace(":", "")}00`;
  }
  function eventTitle(kind = "daily") {
    if (kind === "period") return state.settings.privacyMode === "explicit" ? "نافذة الدورة المتوقعة" : "متابعة شخصية";
    if (kind === "noon") return state.settings.privacyMode === "neutral" ? "وقفة شخصية" : "كيف أشعر الآن؟";
    return state.settings.privacyMode === "neutral" ? "موعد شخصي" : "10 دقائق لصحتي";
  }
  function alarmTrigger(minutes) {
    if (minutes === 0) return "TRIGGER:PT0M";
    return minutes % 1440 === 0 ? `TRIGGER:-P${minutes / 1440}D` : `TRIGGER:-PT${minutes}M`;
  }
  function buildIcs(days) {
    const now = new Date();
    const today = zonedToday(state.settings.timezone);
    const lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Health Renewal//Women Daily Calendar AR//EN", "CALSCALE:GREGORIAN", "METHOD:PUBLISH", `X-WR-CALNAME:${icsEscape("تقويم صحتي اليومي")}`, `X-WR-TIMEZONE:${icsEscape(state.settings.timezone)}`];
    for (let index = 0; index < days; index += 1) {
      const date = addDays(today, index);
      const content = dailyContent(date);
      const start = icsLocal(date, state.settings.dailyTime);
      const [hour, minute] = state.settings.dailyTime.split(":").map(Number);
      const endDate = new Date(date.getFullYear(), date.getMonth(), date.getDate(), hour, minute + 10);
      const end = icsLocal(endDate, `${String(endDate.getHours()).padStart(2, "0")}:${String(endDate.getMinutes()).padStart(2, "0")}`);
      lines.push("BEGIN:VEVENT", `UID:daily-${isoDate(date)}@healthrenewal.org`, `DTSTAMP:${icsStamp(now)}`, `DTSTART;TZID=${state.settings.timezone}:${start}`, `DTEND;TZID=${state.settings.timezone}:${end}`, `SUMMARY:${icsEscape(eventTitle())}`, `DESCRIPTION:${icsEscape(`رسالة الصباح: ${content.morning}\nتطبيق 10 دقائق: ${content.ten}\nhttps://healthrenewal.org/sectors/women/daily-calendar/`)}`, "BEGIN:VALARM", "ACTION:DISPLAY", `DESCRIPTION:${icsEscape(eventTitle())}`, alarmTrigger(state.settings.reminderMinutes), "END:VALARM", "END:VEVENT");
      const [noonHour, noonMinute] = state.settings.noonTime.split(":").map(Number);
      const noonStartDate = new Date(date.getFullYear(), date.getMonth(), date.getDate(), noonHour, noonMinute);
      const noonEndDate = new Date(noonStartDate.getTime() + 5 * 60000);
      const noonStart = icsLocal(noonStartDate, state.settings.noonTime);
      const noonEnd = icsLocal(noonEndDate, `${String(noonEndDate.getHours()).padStart(2, "0")}:${String(noonEndDate.getMinutes()).padStart(2, "0")}`);
      lines.push("BEGIN:VEVENT", `UID:noon-${isoDate(date)}@healthrenewal.org`, `DTSTAMP:${icsStamp(now)}`, `DTSTART;TZID=${state.settings.timezone}:${noonStart}`, `DTEND;TZID=${state.settings.timezone}:${noonEnd}`, `SUMMARY:${icsEscape(eventTitle("noon"))}`, `DESCRIPTION:${icsEscape(`كيف تشعرين الآن؟\nدفعة الظهر: ${content.noon}\nhttps://healthrenewal.org/sectors/women/daily-calendar/`)}`, "BEGIN:VALARM", "ACTION:DISPLAY", `DESCRIPTION:${icsEscape(eventTitle("noon"))}`, alarmTrigger(state.settings.reminderMinutes), "END:VALARM", "END:VEVENT");
    }
    const info = state.settings.includeCycleInExport ? cycleInfo(today) : null;
    if (info) {
      let start = info.nextStart;
      const exportEnd = addDays(today, days - 1);
      while (start <= exportEnd) {
        if (start >= today) {
          const eventStart = addDays(start, -info.variability);
          const eventEnd = addDays(start, info.bleed + info.variability + 1);
          lines.push("BEGIN:VEVENT", `UID:cycle-${isoDate(start)}@healthrenewal.org`, `DTSTAMP:${icsStamp(now)}`, `DTSTART;VALUE=DATE:${isoDate(eventStart).replaceAll("-", "")}`, `DTEND;VALUE=DATE:${isoDate(eventEnd).replaceAll("-", "")}`, `SUMMARY:${icsEscape(eventTitle("period"))}`, `DESCRIPTION:${icsEscape("توقع تقريبي قابل للتغير. لا يستخدم لمنع الحمل أو التشخيص.")}`, "TRANSP:TRANSPARENT", "END:VEVENT");
        }
        start = addDays(start, info.length);
      }
    }
    lines.push("END:VCALENDAR");
    return lines.join("\r\n");
  }

  function downloadIcs() {
    const days = clamp($("exportRange").value, 1, 365, 365);
    const blob = new Blob([buildIcs(days)], { type: "text/calendar;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = Object.assign(document.createElement("a"), { href: url, download: `health-renewal-women-calendar-${days}-days.ics` });
    document.body.append(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    $("calendarStatus").textContent = `تم إنشاء ملف يضم ${days} يومًا. راجعي أسماء الأحداث قبل استيراده إلى تقويم مشترك.`;
  }

  function openGoogleCalendar() {
    const content = dailyContent(selectedDate);
    const [hour, minute] = state.settings.dailyTime.split(":").map(Number);
    const start = new Date(selectedDate.getFullYear(), selectedDate.getMonth(), selectedDate.getDate(), hour, minute);
    const end = new Date(start.getTime() + 10 * 60000);
    const compact = (date) => `${date.getFullYear()}${String(date.getMonth() + 1).padStart(2, "0")}${String(date.getDate()).padStart(2, "0")}T${String(date.getHours()).padStart(2, "0")}${String(date.getMinutes()).padStart(2, "0")}00`;
    const params = new URLSearchParams({ action: "TEMPLATE", text: eventTitle(), dates: `${compact(start)}/${compact(end)}`, details: `رسالة الصباح: ${content.morning}\n\nوقفة الظهر: كيف تشعرين الآن؟ — ${content.noon}\n\nتطبيق 10 دقائق: ${content.ten}\n\nhttps://healthrenewal.org/sectors/women/daily-calendar/`, ctz: state.settings.timezone });
    window.open(`https://calendar.google.com/calendar/render?${params}`, "_blank", "noopener,noreferrer");
  }

  async function enableNotifications() {
    if (!("Notification" in window)) { $("calendarStatus").textContent = "هذا المتصفح لا يدعم إشعارات الويب."; return; }
    const permission = await Notification.requestPermission();
    if (permission !== "granted") { $("calendarStatus").textContent = "لم يُمنح إذن الإشعارات؛ استخدمي تقويم الهاتف بدلًا منه."; return; }
    new Notification("رسالة صباحية من تقويم صحتك", { body: dailyContent(selectedDate).morning });
    $("calendarStatus").textContent = "تم اختبار الإشعار. للتذكير المستقبلي الموثوق استخدمي تقويم الهاتف.";
  }

  function bindEvents() {
    $("previousDay").addEventListener("click", () => { selectedDate = addDays(selectedDate, -1); displayMonth = new Date(selectedDate.getFullYear(), selectedDate.getMonth(), 1, 12); renderAll(); });
    $("nextDay").addEventListener("click", () => { selectedDate = addDays(selectedDate, 1); displayMonth = new Date(selectedDate.getFullYear(), selectedDate.getMonth(), 1, 12); renderAll(); });
    $("todayButton").addEventListener("click", () => { selectedDate = zonedToday(state.settings.timezone); displayMonth = new Date(selectedDate.getFullYear(), selectedDate.getMonth(), 1, 12); renderAll(); });
    $("previousMonth").addEventListener("click", () => { displayMonth = new Date(displayMonth.getFullYear(), displayMonth.getMonth() - 1, 1, 12); renderCalendar(); });
    $("nextMonth").addEventListener("click", () => { displayMonth = new Date(displayMonth.getFullYear(), displayMonth.getMonth() + 1, 1, 12); renderCalendar(); });
    $("currentMonth").addEventListener("click", () => { const today = zonedToday(state.settings.timezone); displayMonth = new Date(today.getFullYear(), today.getMonth(), 1, 12); renderCalendar(); });
    $("startTimer").addEventListener("click", startTimer);
    $("pauseTimer").addEventListener("click", pauseTimer);
    $("resetTimer").addEventListener("click", resetTimer);
    $("completeDay").addEventListener("change", (event) => {
      const key = isoDate(selectedDate);
      if (event.target.checked) state.completions[key] = true; else delete state.completions[key];
      saveState(); renderCalendar(); renderStreak();
    });
    $("settingsForm").addEventListener("submit", (event) => {
      event.preventDefault();
      const next = readSettings();
      if (next.cycleEnabled && !parseIso(next.lastPeriodStart)) { $("settingsStatus").textContent = "أضيفي أول يوم لآخر دورة أو ألغِ تفعيل التوقع."; $("lastPeriodStart").focus(); return; }
      state.settings = next;
      saveState();
      selectedDate = zonedToday(state.settings.timezone);
      displayMonth = new Date(selectedDate.getFullYear(), selectedDate.getMonth(), 1, 12);
      $("settingsStatus").textContent = "حُفظت الإعدادات محليًا في هذا الجهاز.";
      renderAll();
    });
    $("clearPrivateData").addEventListener("click", () => {
      if (!window.confirm("سيُحذف سجل الدورة والملاحظات والإنجازات والإعدادات من هذا المتصفح فقط. هل تتابعين؟")) return;
      localStorage.removeItem(STORAGE_KEY);
      state = copy(defaults);
      selectedDate = zonedToday(state.settings.timezone);
      displayMonth = new Date(selectedDate.getFullYear(), selectedDate.getMonth(), 1, 12);
      populateTimezones(); populateSettings(); renderAll();
      $("settingsStatus").textContent = "حُذفت البيانات المحلية.";
    });
    $("logForm").addEventListener("submit", (event) => {
      event.preventDefault();
      const key = isoDate(selectedDate);
      state.logs[key] = { mood: $("mood").value, energy: $("energy").value, pain: $("pain").value, flow: $("flow").value, note: $("privateNote").value.trim().slice(0, 300), updatedAt: new Date().toISOString() };
      saveState();
      $("logStatus").textContent = `حُفظ سجل ${formatDate(selectedDate, { weekday: undefined })} محليًا.`;
    });
    $("markPeriodStart").addEventListener("click", () => {
      state.settings.lastPeriodStart = isoDate(selectedDate);
      state.settings.cycleEnabled = true;
      state.logs[isoDate(selectedDate)] = { ...(state.logs[isoDate(selectedDate)] || {}), flow: $("flow").value || "medium", periodStart: true, updatedAt: new Date().toISOString() };
      saveState(); populateSettings(); renderAll();
      $("logStatus").textContent = "سُجلت بداية الدورة لهذا اليوم وأُعيد حساب التوقع محليًا.";
    });
    $("downloadIcs").addEventListener("click", downloadIcs);
    $("openGoogleCalendar").addEventListener("click", openGoogleCalendar);
    $("enableNotifications").addEventListener("click", enableNotifications);
  }

  function registerServiceWorker() {
    if ("serviceWorker" in navigator && location.protocol === "https:") navigator.serviceWorker.register("service-worker.js").catch(() => {});
  }

  populateTimezones();
  populateSettings();
  bindEvents();
  renderAll();
  updateTimer();
  registerServiceWorker();
})();
