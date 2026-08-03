(() => {
  "use strict";

  const STORAGE_KEY = "hr-student-daily-calendar-v1";
  const DAY_MS = 86400000;
  const $ = (id) => document.getElementById(id);
  const qsa = (selector, root = document) => [...root.querySelectorAll(selector)];

  const monthThemes = [
    ["تأسيس نظام واقعي", "هذا الشهر لبناء روتين يمكن الاستمرار عليه، لا جدول مثالي ينهار بعد أيام."],
    ["الاسترجاع بدل إعادة القراءة", "اختبر ما تتذكره قبل فتح المصدر، ثم صحح الفجوات."],
    ["إدارة الوقت والطاقة", "وزع المهمات الصعبة على أوقات الطاقة الأعلى، لا على الفراغ وحده."],
    ["حل المسائل والتطبيق", "الفهم يثبت عندما تستخدم الفكرة في سؤال أو مثال أو شرح."],
    ["الاختبارات دون استنزاف", "الخطة الجيدة تبدأ مبكرًا وتزيد المحاكاة تدريجيًا وتخفف قرب الاختبار."],
    ["الكتابة والمشروعات", "قسّم العمل إلى بحث، مخطط، مسودة، مراجعة، وتسليم بدل مهمة واحدة ضخمة."],
    ["التعلم الصيفي المرن", "حافظ على الحد الأدنى المفيد واترك مساحة للراحة والاهتمامات."],
    ["العودة المنظمة", "ابدأ بخط أساس بسيط للمواد والمواعيد والنوم قبل رفع الحمل."],
    ["التركيز والبيئة", "أزل مشتتًا واحدًا واضحًا وجهز أول خطوة قبل بدء المؤقت."],
    ["المراجعة المتباعدة", "ارجع للمعلومة في أوقات متباعدة بدل حشدها في جلسة واحدة."],
    ["المشروعات الجماعية", "حدد المسؤوليات والمواعيد ومعيار الإنجاز كتابيًا منذ البداية."],
    ["الإغلاق والتقييم", "راجع ما نجح وما يحتاج تغييرًا وانقل الدروس إلى الفترة القادمة."]
  ];

  const morningBank = [
    "لا تحتاج إلى إنهاء كل شيء اليوم؛ تحتاج إلى بدء الشيء الصحيح.",
    "ابدأ بأصغر خطوة يمكن رؤيتها وقياسها.",
    "الخطة الواقعية تحترم وقتك وطاقتك ولا تعاقبك.",
    "جلسة واحدة كاملة أفضل من ساعات مشتتة.",
    "حدد ناتجًا واحدًا لليوم: ماذا ستفهم أو تحل أو تكتب؟",
    "التعثر معلومة عن الخطة، وليس حكمًا على ذكائك.",
    "ابدأ بالسؤال الأصعب بينما ذهنك أكثر صفاءً.",
    "جهز المكان والمصدر والمهمة قبل تشغيل المؤقت.",
    "لا تقارن يومك الدراسي بلقطة منتقاة من حياة طالب آخر.",
    "هدفك التقدم القابل للتكرار، لا الاندفاع المؤقت.",
    "يمكنك تعديل الخطة دون أن تلغي الهدف.",
    "اسأل نفسك: ما الخطوة التي تجعل بقية العمل أسهل؟",
    "الراحة المخططة جزء من التعلم وليست هروبًا منه.",
    "ابدأ بالاسترجاع من الذاكرة ثم افتح الكتاب.",
    "ضع الهاتف بعيدًا لدورة واحدة فقط؛ لا تحتاج إلى قرار أبدي.",
    "ركز على الدليل: سؤال حُل، فقرة كُتبت، مفهوم شُرح.",
    "المهمة غير الواضحة تبدو أكبر؛ اكتب أول فعل مطلوب.",
    "يوم دراسي جيد لا يعني يومًا بلا تعب، بل يومًا بخيارات ذكية.",
    "اطلب توضيحًا مبكرًا بدل تراكم الغموض.",
    "ابدأ من مستواك الحالي، لا من المكان الذي تتمنى أنك وصلت إليه.",
    "كل جلسة تنتهي بملاحظة للخطوة التالية توفر وقت البدء غدًا.",
    "اجعل أول خمس دقائق سهلة لتقليل مقاومة البداية.",
    "تعلمك لا يقاس بسرعة الآخرين.",
    "اختر أولوية واحدة تحميها من المقاطعات اليوم."
  ];

  const ideaBank = [
    "حوّل عنوان الدرس إلى ثلاثة أسئلة وحاول الإجابة عنها قبل القراءة.",
    "اكتب ورقة أخطاء: السؤال، سبب الخطأ، والقاعدة التي تمنع تكراره.",
    "اشرح المفهوم بصوتك كأنك تدرسه لطالب أصغر.",
    "ابدأ كل جلسة بدقيقتين لاسترجاع ما تعلمته في الجلسة السابقة.",
    "اجمع المهمات المتشابهة لتقليل وقت الانتقال بين الأنواع.",
    "استخدم اختبارًا قصيرًا في نهاية الجلسة بدل إعادة قراءة الخلاصة.",
    "حدد معيار انتهاء واضحًا: عشر مسائل أو مخطط من صفحة واحدة.",
    "ضع سؤالًا لم تفهمه في قائمة منفصلة واطلب مساعدة محددة.",
    "قسم المشروع إلى نواتج صغيرة لكل يوم بدل موعد نهائي واحد.",
    "اكتب ملخصًا من الذاكرة ثم قارنه بالمصدر بلون مختلف.",
    "ابدأ بالأمثلة المحلولة ثم أغلقها وحاول إعادة الحل.",
    "خصص جلسة أسبوعية لترتيب الملفات والمراجع والمواعيد.",
    "استخدم التناوب بين موضوعين مرتبطين بدل تكرار نمط واحد طويلًا.",
    "اكتب توقعك للإجابة قبل مشاهدة الحل.",
    "اختر مكانًا ثابتًا لبطاقات المراجعة حتى لا تضيع بين التطبيقات.",
    "حول المهمة إلى سؤال قرار: ما الذي أحتاجه كي أبدأ خلال دقيقتين؟",
    "اجعل المراجعة الأولى قصيرة جدًا خلال 24 ساعة.",
    "أنشئ مثالًا من حياتك للمفهوم المجرد.",
    "راجع أهداف الأسبوع قبل قبول مهمة إضافية.",
    "اترك آخر خمس دقائق لترتيب الخطوة التالية والمصادر المطلوبة."
  ];

  const memoryBank = [
    "الاسترجاع النشط أقوى من الشعور بالألفة الناتج عن إعادة القراءة.",
    "المعلومة التي تسترجعها بصعوبة مناسبة غالبًا تثبت أكثر من المعلومة السهلة جدًا.",
    "المراجعة المتباعدة تعني العودة قبل النسيان الكامل، لا الانتظار حتى ليلة الاختبار.",
    "ربط الفكرة بمثال وصورة وسؤال يزيد مسارات الوصول إليها.",
    "التبديل بين أنواع مسائل متقاربة يساعد على تعلم متى تستخدم كل طريقة.",
    "النوم بعد التعلم يدعم تثبيت الذاكرة؛ السهر ليس دائمًا وقتًا إضافيًا حقيقيًا.",
    "الشرح الذاتي يكشف الفجوات التي تخفيها القراءة الصامتة.",
    "تصحيح الخطأ فورًا مع تفسيره أفضل من حفظ الإجابة الصحيحة وحدها.",
    "تجزئة المعلومات إلى وحدات ذات معنى تقلل العبء على الذاكرة العاملة.",
    "الاختبار التجريبي يجب أن يشبه ظروف الاختبار الفعلي تدريجيًا.",
    "تغيير ترتيب الأسئلة يمنع حفظ التسلسل بدل فهم المحتوى.",
    "كتابة كلمات مفتاحية ثم بناء الإجابة منها تدريب جيد للاستدعاء.",
    "لا تجعل بطاقة المراجعة تحمل أكثر من سؤال رئيسي واحد.",
    "المقارنة بين مفهومين متشابهين تقلل الخلط بينهما.",
    "ابدأ المراجعة بالسؤال لا بالإجابة.",
    "تذكر مثالًا مضادًا يساعد على فهم حدود القاعدة.",
    "إغلاق المصدر أثناء الشرح يحول النشاط من قراءة إلى استرجاع.",
    "تكرار الجلسة القصيرة عبر أيام أفضل من جلسة واحدة متعبة غالبًا.",
    "استرجاع الفكرة في سياقات مختلفة يجعل استخدامها أكثر مرونة.",
    "ضع علامة على درجة الثقة ثم تحقق؛ هذا يدرب دقة تقديرك لمعرفتك."
  ];

  const wellbeingBank = [
    "اشرب ماء وخذ حركة قصيرة قبل تفسير التشتت بأنه كسل.",
    "إذا تكرر النوم القصير، خفف الحمل واطلب دعمًا بدل زيادة المنبهات فقط.",
    "شد الفك والكتفين إشارة مفيدة لأخذ تنفس بطيء وتعديل الوضعية.",
    "الوجبة أو الوجبة الخفيفة المنتظمة قد تمنع هبوط الطاقة المفاجئ.",
    "الراحة بين الجلسات ينبغي أن تغير وضع الجسم وتبعد العين عن الشاشة.",
    "الضغط العالي لعدة أيام يحتاج مراجعة الجدول والتوقعات ومصادر الدعم.",
    "لا تجعل وقت النوم مساحة لتعويض كل ما لم تنجزه.",
    "القلق قبل الاختبار لا يعني عدم الاستعداد؛ استخدمه لتحديد خطوة عملية.",
    "العزلة الطويلة أثناء الضغط قد تزيد الحمل؛ تواصل مع شخص آمن.",
    "التكييفات التعليمية حق تنظيمي عند وجود احتياج موثق، وليست امتيازًا.",
    "المشي القصير أو التمدد قد يساعد على استعادة الانتباه بعد الجلوس الطويل.",
    "الاستراحة التي تتحول إلى تصفح مفتوح قد لا تعيد الطاقة؛ ضع لها حدًا زمنيًا.",
    "اعمل في إضاءة مريحة وخفف الوهج والمسافة غير المناسبة للشاشة.",
    "إذا أصبح الضغط يمنع الأكل أو النوم أو الحضور، لا تؤجل طلب المساعدة.",
    "اسمح بيوم أخف بعد اختبار أو تسليم كبير بدل تراكم الإنهاك.",
    "التنفس البطيء لا يحل المشكلة لكنه قد يخفض الاستثارة لتستطيع اختيار الخطوة التالية.",
    "حدد وقتًا لإغلاق الدراسة حتى لا تبقى في حالة تأهب طوال المساء.",
    "الحديث القاسي مع النفس يستهلك انتباهًا؛ استخدم لغة تصف المشكلة لا هويتك.",
    "اطلب من الأسرة أو الزملاء فترة عدم مقاطعة محددة بدل توقع الهدوء تلقائيًا.",
    "التعب المستمر أو الأعراض الجسدية الجديدة تستحق تقييمًا مناسبًا."
  ];

  const challengeBank = [
    "اكتب كل ما تتذكره عن موضوع واحد خلال خمس دقائق، ثم صحح لخمس دقائق.",
    "حل سؤالين دون فتح الحل، ثم اشرح سبب كل خطوة.",
    "رتب مكتبك وجهز مصدر الجلسة القادمة وأغلق ثلاث مشتتات.",
    "اختر مهمة مؤجلة واكتب أول ثلاث خطوات صغيرة لها.",
    "اصنع خمس بطاقات سؤال وجواب من درس اليوم.",
    "راجع خطأين سابقين وحل سؤالًا مشابهًا لكل منهما.",
    "اشرح مفهومًا في تسجيل صوتي لا يتجاوز دقيقتين.",
    "اكتب سؤالًا محددًا سترسله للمعلم أو الزميل.",
    "حوّل فقرة طويلة إلى مخطط من خمس نقاط فقط.",
    "نفذ دورة تركيز عشر دقائق بلا هاتف ثم سجل ما أنجزته.",
    "اختر اختبارًا قديمًا وحدد الأنماط الثلاثة الأكثر تكرارًا.",
    "راجع مواعيد الأسبوع وحدد مهمة يجب تقديمها قبل موعدها.",
    "اكتب تعريفين متشابهين ثم سطر الفرق بينهما.",
    "ضع خطة إنقاذ من ثلاث خطوات إذا تعطل جدول اليوم.",
    "أغلق المصدر واكتب مثالًا من عندك على القاعدة.",
    "اختر صفحة واحدة وحول عناوينها إلى أسئلة.",
    "حدد مكانًا واحدًا ستبدأ منه غدًا واتركه جاهزًا.",
    "احذف مهمة منخفضة القيمة أو أجلها بقرار واضح.",
    "اكتب ما تعلمته اليوم في ثلاث جمل دون نسخ.",
    "نفذ استراحة حركة وتنفس ثم ابدأ أصعب خمس دقائق."
  ];

  const noonBoostBank = [
    "توقف دقيقة: هل تحتاج إلى استراحة، أم إلى مهمة أوضح، أم إلى تقليل المشتتات؟",
    "منتصف اليوم فرصة لإعادة ضبط الخطة، لا لإصدار حكم على اليوم كله.",
    "اختر خطوة واحدة تعيد الإحساس بالتقدم خلال عشر دقائق.",
    "إذا انخفض التركيز، قلل حجم المهمة قبل زيادة الضغط على نفسك.",
    "راجع ما أنجزته فعلًا ثم قرر ما يستحق بقية طاقتك.",
    "يمكنك تبديل المادة أو نوع النشاط دون التخلي عن اليوم.",
    "خذ ماء وحركة قصيرة ثم عد بسؤال محدد، لا بعنوان فصل كامل.",
    "إذا كنت متوترًا، اكتب المخاوف خارج رأسك وحدد ما يمكن فعله اليوم.",
    "لا تستخدم التعب دليلًا على الفشل؛ استخدمه لتعديل طول الجلسة.",
    "أغلق تبويبًا واحدًا، ضع الهاتف بعيدًا، وابدأ دورة قصيرة.",
    "الاستراحة المقصودة تحمي بقية اليوم أكثر من المقاومة المشتتة.",
    "إن ضاع الصباح، فالظهر بداية ثانية كاملة.",
    "اسأل: ما المهمة التي تخفف أكبر ضغط إذا تقدمت فيها قليلًا؟",
    "تقدمك لا يحتاج إلى شعور مثالي؛ يحتاج إلى فعل صغير واضح.",
    "اختر مستوى كافيًا من الجودة للمسودة الأولى، ثم حسّن لاحقًا.",
    "إذا كنت عالقًا، انتقل من القراءة إلى سؤال أو مثال أو شرح.",
    "لا تعاقب نفسك بجلسة طويلة؛ جرّب عشرين دقيقة قابلة للإنهاء.",
    "ضع حدًا لما لن تفعله اليوم حتى تحمي ما ستفعله.",
    "اطلب مساعدة محددة بدل عبارة: لا أفهم شيئًا.",
    "استعد تركيزك بإعادة كتابة الهدف في سطر واحد.",
    "خفف المقارنة، وارفع وضوح الخطوة التالية.",
    "توقف عن إعادة ترتيب الخطة وابدأ أول بند لدورة واحدة.",
    "راجع النوم والطعام والضغط قبل لوم قدرتك على التركيز.",
    "أنهِ جلسة واحدة بإغلاق واضح ثم قرر التالية."
  ];

  const defaultState = {
    version: 1,
    profile: {name: "", level: "school", subjects: [], weeklyGoal: 12, defaultMinutes: 120, weekStart: 6},
    settings: {morningTime: "07:00", noonTime: "12:30", eveningTime: "19:30", reminderMinutes: 10, eventPrivacy: "neutral"},
    tasks: [], reviews: [], exams: [], logs: {}, weekPlans: {}, timer: {minutes: 45, remaining: 2700, running: false, endAt: 0, subject: ""}
  };

  let state = loadState();
  let selectedDate = startOfDay(new Date());
  let timerInterval = null;
  let deferredInstallPrompt = null;
  let showTodayOnly = false;

  function clone(value) { return JSON.parse(JSON.stringify(value)); }
  function loadState() {
    try {
      const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) || "null");
      if (!parsed || typeof parsed !== "object") return clone(defaultState);
      return {
        ...clone(defaultState), ...parsed,
        profile: {...clone(defaultState.profile), ...(parsed.profile || {})},
        settings: {...clone(defaultState.settings), ...(parsed.settings || {})},
        timer: {...clone(defaultState.timer), ...(parsed.timer || {})},
        tasks: Array.isArray(parsed.tasks) ? parsed.tasks : [],
        reviews: Array.isArray(parsed.reviews) ? parsed.reviews : [],
        exams: Array.isArray(parsed.exams) ? parsed.exams : [],
        logs: parsed.logs && typeof parsed.logs === "object" ? parsed.logs : {},
        weekPlans: parsed.weekPlans && typeof parsed.weekPlans === "object" ? parsed.weekPlans : {}
      };
    } catch (_) { return clone(defaultState); }
  }
  function saveState() { localStorage.setItem(STORAGE_KEY, JSON.stringify(state)); }
  function uid(prefix) { return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`; }
  function startOfDay(date) { const d = new Date(date); d.setHours(0,0,0,0); return d; }
  function isoDate(date) { const d = new Date(date); return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}`; }
  function parseDate(value) { const [year, month, day] = String(value).split("-").map(Number); return startOfDay(new Date(year, (month || 1) - 1, day || 1)); }
  function addDays(date, days) { const d = startOfDay(date); d.setDate(d.getDate() + Number(days || 0)); return d; }
  function utcDayNumber(date) { const d = new Date(date); return Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()) / DAY_MS; }
  function daysBetween(a, b) { return Math.round(utcDayNumber(b) - utcDayNumber(a)); }
  function escapeICS(value) { return String(value || "").replace(/\\/g,"\\\\").replace(/\n/g,"\\n").replace(/,/g,"\\,").replace(/;/g,"\\;"); }
  function pad(n) { return String(n).padStart(2,"0"); }
  function icsDateTime(date, time) {
    const [h,m] = (time || "09:00").split(":").map(Number);
    const d = new Date(date); d.setHours(h || 0,m || 0,0,0);
    return `${d.getFullYear()}${pad(d.getMonth()+1)}${pad(d.getDate())}T${pad(d.getHours())}${pad(d.getMinutes())}00`;
  }
  function dateLabel(date) { return new Intl.DateTimeFormat("ar", {weekday:"long", year:"numeric", month:"long", day:"numeric"}).format(date); }
  function dayIndex(date) { return Math.floor(utcDayNumber(date)); }
  function pick(bank, date, offset = 0) { return bank[Math.abs(dayIndex(date) + offset) % bank.length]; }
  function setStatus(id, text) { const el = $(id); if (el) el.textContent = text; }
  function downloadFile(name, content, type) {
    const blob = new Blob([content], {type});
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url; a.download = name; document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  function renderToday() {
    $("todayDate").textContent = dateLabel(selectedDate);
    $("morningMessage").textContent = pick(morningBank, selectedDate);
    $("dailyIdea").textContent = pick(ideaBank, selectedDate, 3);
    $("memoryTip").textContent = pick(memoryBank, selectedDate, 7);
    $("wellbeingTip").textContent = pick(wellbeingBank, selectedDate, 11);
    $("microChallenge").textContent = pick(challengeBank, selectedDate, 17);
    const theme = monthThemes[selectedDate.getMonth()];
    $("monthTheme").textContent = `موضوع الشهر: ${theme[0]} — ${theme[1]}`;
    $("noonBoost").textContent = pick(noonBoostBank, selectedDate, 5);
    hydrateDailyLog();
  }

  function hydrateProfile() {
    $("studentName").value = state.profile.name || "";
    $("educationLevel").value = state.profile.level || "school";
    $("subjects").value = (state.profile.subjects || []).join("، ");
    $("weeklyGoal").value = state.profile.weeklyGoal || 12;
    $("defaultMinutes").value = state.profile.defaultMinutes || 120;
    $("weekStart").value = String(state.profile.weekStart ?? 6);
    $("planMinutes").value = state.profile.defaultMinutes || 120;
    renderSubjectOptions();
  }

  function renderSubjectOptions() {
    const list = $("subjectOptions"); list.textContent = "";
    (state.profile.subjects || []).forEach(subject => { const option = document.createElement("option"); option.value = subject; list.appendChild(option); });
  }

  function hydrateSettings() {
    $("morningTime").value = state.settings.morningTime;
    $("noonTime").value = state.settings.noonTime;
    $("eveningTime").value = state.settings.eveningTime;
    $("reminderMinutes").value = String(state.settings.reminderMinutes);
    $("eventPrivacy").value = state.settings.eventPrivacy;
    $("noonTimeLabel").textContent = state.settings.noonTime;
  }

  function hydrateDailyLog() {
    const key = isoDate(selectedDate);
    const log = state.logs[key] || {};
    $("stressLevel").value = log.stress ?? 3;
    $("sleepHours").value = log.sleep ?? 7;
    $("eveningReflection").value = log.reflection || "";
    qsa(".choice", $("noonChoices")).forEach(btn => btn.setAttribute("aria-pressed", String(btn.dataset.value === log.noonFocus)));
    wellbeingAdvice(Number(log.stress ?? 3), Number(log.sleep ?? 7));
  }

  function wellbeingAdvice(stress, sleep) {
    let text = "سجل بسيط يكفي؛ الهدف فهم النمط وليس مراقبة مثالية.";
    if (stress >= 5) text = "الضغط مرتفع جدًا اليوم. خفف الحمل، تواصل مع شخص موثوق أو مرشد، ولا تبق وحدك مع أفكار خطرة.";
    else if (stress >= 4 && sleep < 6) text = "اجتماع ضغط مرتفع ونوم قصير يستدعي خطة أخف ودعمًا واقعيًا، لا تمديد الدراسة حتى وقت متأخر.";
    else if (sleep < 5) text = "النوم القصير قد يضعف التركيز والذاكرة. قدم الراحة وخفف القرارات الصعبة اليوم قدر الإمكان.";
    else if (stress <= 2 && sleep >= 7) text = "الطاقة تبدو مناسبة؛ استخدمها في أولوية صعبة ثم حافظ على استراحة ونهاية يوم واضحة.";
    $("wellbeingAdvice").textContent = text;
  }

  function buildSmartPlan({subject, minutes, energy, difficulty, mode}) {
    const total = Math.max(15, Math.min(720, Number(minutes) || 60));
    let focus = 45, rest = 10;
    if (energy === "low") { focus = 20; rest = 7; }
    if (energy === "high") { focus = 60; rest = 10; }
    if (difficulty === "hard") focus = Math.min(focus, 35);
    if (mode === "project" && energy !== "low") focus = Math.max(focus, 45);
    const wrap = Math.max(5, Math.round(total * .08));
    const recall = mode === "review" ? Math.max(10, Math.round(total * .25)) : Math.max(5, Math.round(total * .12));
    let available = Math.max(5, total - wrap - recall);
    const sessions = [];
    let count = 1;
    while (available > 0 && count <= 10) {
      const duration = Math.min(focus, available);
      sessions.push({kind:"focus", duration, label: sessionLabel(mode, count, difficulty)});
      available -= duration;
      if (available > 8) {
        const breakMinutes = Math.min(rest, available);
        sessions.push({kind:"break", duration: breakMinutes, label:"استراحة حركة وماء دون تصفح مفتوح"});
        available -= breakMinutes;
      }
      count += 1;
    }
    sessions.push({kind:"recall", duration: recall, label:"استرجاع من الذاكرة أو أسئلة قصيرة وتصحيح الفجوات"});
    sessions.push({kind:"wrap", duration: wrap, label:"تلخيص النتيجة وكتابة أول خطوة للجلسة القادمة"});
    return {subject: subject || "المادة المحددة", total, focus, rest, sessions};
  }
  function sessionLabel(mode, count, difficulty) {
    const labels = {
      learn:["مسح سريع للعناوين وصياغة أسئلة","فهم مركز مع أمثلة","شرح ذاتي دون مصدر","تطبيق وتصحيح"],
      practice:["اختيار مسائل ممثلة","حل دون مشاهدة الحل","تحليل الأخطاء","إعادة حل سؤال مشابه"],
      review:["اختبار قبلي من الذاكرة","استرجاع منظم","تصحيح الفجوات","اختبار ختامي مختلط"],
      project:["تحديد الناتج والمصادر","إنتاج مسودة","مراجعة معيار الجودة","توثيق وخطوة تالية"]
    };
    const base = labels[mode] || labels.learn;
    const label = base[(count - 1) % base.length];
    return difficulty === "hard" ? `${label} مع مثال واحد فقط في البداية` : label;
  }

  function renderPlan(plan) {
    const box = $("planResult"); box.textContent = "";
    const title = document.createElement("h3"); title.textContent = `${plan.subject}: خطة ${plan.total} دقيقة`;
    const note = document.createElement("p"); note.textContent = `نمط التركيز المقترح ${plan.focus} دقيقة، مع استراحة تقارب ${plan.rest} دقائق. عدّل الخطة إذا تغيرت طاقتك.`;
    const list = document.createElement("ol");
    plan.sessions.forEach(item => { const li = document.createElement("li"); li.textContent = `${item.duration} د — ${item.label}`; list.appendChild(li); });
    const add = document.createElement("button"); add.type = "button"; add.className = "btn small secondary"; add.textContent = "تحويلها إلى مهمة اليوم";
    add.addEventListener("click", () => {
      state.tasks.push({id:uid("task"), title:`خطة ${plan.subject}`, subject:plan.subject, priority:"high", due:isoDate(selectedDate), estimate:plan.total, done:false, createdAt:new Date().toISOString()});
      saveState(); renderTasks(); setStatus("profileStatus", "أضيفت الخطة إلى مهام اليوم.");
    });
    box.append(title,note,list,add);
  }

  function renderTasks() {
    const list = $("taskList"); list.textContent = "";
    const today = isoDate(selectedDate);
    const tasks = [...state.tasks]
      .filter(task => !showTodayOnly || task.due === today)
      .sort((a,b) => Number(a.done)-Number(b.done) || priorityRank(a.priority)-priorityRank(b.priority) || String(a.due || "9999").localeCompare(String(b.due || "9999")));
    if (!tasks.length) { const li=document.createElement("li"); li.className="empty"; li.textContent="لا توجد مهام مطابقة."; list.appendChild(li); return; }
    tasks.forEach(task => {
      const li = document.createElement("li"); li.className = `list-item${task.done ? " done" : ""}`;
      const check = document.createElement("input"); check.type="checkbox"; check.checked=Boolean(task.done); check.setAttribute("aria-label",`إكمال ${task.title}`);
      check.addEventListener("change",()=>{ task.done=check.checked; task.completedAt=task.done?new Date().toISOString():null; saveState(); renderTasks(); });
      const body=document.createElement("div"); const title=document.createElement("div"); title.className="item-title"; title.textContent=task.title;
      const meta=document.createElement("div"); meta.className="meta"; meta.textContent=[task.subject, task.due?`موعد ${task.due}`:"بلا موعد", `${task.estimate||0} د`].filter(Boolean).join(" · ");
      const priority=document.createElement("span"); priority.className=`priority-${task.priority}`; priority.textContent=`أولوية ${priorityArabic(task.priority)}`; body.append(title,meta,priority);
      const actions=document.createElement("div"); actions.className="row-actions";
      const focus=document.createElement("button"); focus.type="button"; focus.className="btn small secondary"; focus.textContent="ابدأ تركيز"; focus.addEventListener("click",()=>{ $("focusSubject").value=task.subject||task.title; setTimerMinutes(Math.min(90, Math.max(15, Number(task.estimate)||25))); document.getElementById("timerHeading").scrollIntoView({behavior:"smooth"}); });
      const del=document.createElement("button"); del.type="button"; del.className="btn small danger"; del.textContent="حذف"; del.addEventListener("click",()=>{ state.tasks=state.tasks.filter(item=>item.id!==task.id); saveState(); renderTasks(); });
      actions.append(focus,del); li.append(check,body,actions); list.appendChild(li);
    });
  }
  function priorityRank(value){ return {high:0,medium:1,low:2}[value] ?? 3; }
  function priorityArabic(value){ return {high:"عالية",medium:"متوسطة",low:"منخفضة"}[value] || "متوسطة"; }

  function reviewDates(start) { return [1,3,7,14,30].map(offset => isoDate(addDays(start,offset))); }
  function renderReviews() {
    const list=$("reviewList"); list.textContent="";
    const reviews=[...state.reviews].sort((a,b)=>String(nextReviewDate(a)||"9999").localeCompare(String(nextReviewDate(b)||"9999")));
    if(!reviews.length){const li=document.createElement("li");li.className="empty";li.textContent="أضف موضوعًا لإنشاء خمس مراجعات متباعدة.";list.appendChild(li);return;}
    reviews.forEach(review=>{
      const li=document.createElement("li");li.className="list-item";
      const marker=document.createElement("span");marker.textContent="↻";marker.setAttribute("aria-hidden","true");
      const body=document.createElement("div");const title=document.createElement("div");title.className="item-title";title.textContent=`${review.subject}: ${review.topic}`;
      const meta=document.createElement("div");meta.className="meta";meta.textContent=review.dates.map((d,i)=>`${i+1}: ${d}${review.done?.[i]?" ✓":""}`).join(" · ");body.append(title,meta);
      const actions=document.createElement("div");actions.className="row-actions";
      const nextIndex=(review.done||[]).findIndex(done=>!done);const complete=document.createElement("button");complete.type="button";complete.className="btn small secondary";complete.textContent=nextIndex===-1?"اكتملت":"إكمال التالية";complete.disabled=nextIndex===-1;complete.addEventListener("click",()=>{review.done=review.done||[false,false,false,false,false];review.done[nextIndex]=true;saveState();renderReviews();});
      const del=document.createElement("button");del.type="button";del.className="btn small danger";del.textContent="حذف";del.addEventListener("click",()=>{state.reviews=state.reviews.filter(item=>item.id!==review.id);saveState();renderReviews();});actions.append(complete,del);li.append(marker,body,actions);list.appendChild(li);
    });
  }
  function nextReviewDate(review){const idx=(review.done||[]).findIndex(done=>!done);return idx===-1?null:review.dates[idx];}

  function examPlan(exam) {
    const days = daysBetween(new Date(), parseDate(exam.date));
    if (days < 0) return "انتهى الموعد؛ راجع النتيجة والدروس المستفادة.";
    if (days === 0) return "اليوم: مراجعة خفيفة، تجهيز الأدوات، واتباع تعليمات المؤسسة.";
    if (days <= 3) return "محاكاة قصيرة، مراجعة الأخطاء المتكررة، ونوم كافٍ؛ لا تبدأ مصادر ضخمة جديدة.";
    if (days <= 7) return "أسئلة مختلطة يومية، قائمة أخطاء، ومراجعات استرجاع قصيرة.";
    if (days <= 21) return "قسّم المنهج إلى وحدات، افهم ثم طبّق، وأجر اختبارًا أسبوعيًا.";
    return "ابن خط أساس، وزع الوحدات على الأسابيع، واترك آخر 20% من المدة للمحاكاة والمراجعة.";
  }
  function renderExams(){
    const list=$("examList");list.textContent="";
    const exams=[...state.exams].sort((a,b)=>a.date.localeCompare(b.date));
    if(!exams.length){const li=document.createElement("li");li.className="empty";li.textContent="لا توجد اختبارات أو مشروعات كبرى مسجلة.";list.appendChild(li);return;}
    exams.forEach(exam=>{
      const li=document.createElement("li");li.className="list-item";const marker=document.createElement("span");marker.textContent="⏳";
      const body=document.createElement("div");const title=document.createElement("div");title.className="item-title";title.textContent=`${exam.subject}: ${exam.name}`;
      const days=daysBetween(new Date(),parseDate(exam.date));const meta=document.createElement("div");meta.className="meta";meta.textContent=`${exam.date} · ${days>=0?`باقي ${days} يومًا`:`مر ${Math.abs(days)} يومًا`} · أهمية ${exam.weight}`;
      const plan=document.createElement("p");plan.textContent=examPlan(exam);body.append(title,meta,plan);
      const actions=document.createElement("div");actions.className="row-actions";const add=document.createElement("button");add.type="button";add.className="btn small secondary";add.textContent="مهمة تحضير";add.addEventListener("click",()=>{state.tasks.push({id:uid("task"),title:`تحضير ${exam.name}`,subject:exam.subject,priority:exam.weight===3?"high":"medium",due:isoDate(addDays(parseDate(exam.date),-1)),estimate:60,done:false,createdAt:new Date().toISOString()});saveState();renderTasks();});const del=document.createElement("button");del.type="button";del.className="btn small danger";del.textContent="حذف";del.addEventListener("click",()=>{state.exams=state.exams.filter(item=>item.id!==exam.id);saveState();renderExams();});actions.append(add,del);li.append(marker,body,actions);list.appendChild(li);
    });
  }

  function startOfWeek(date){const d=startOfDay(date);const start=Number(state.profile.weekStart ?? 6);const diff=(d.getDay()-start+7)%7;return addDays(d,-diff);}
  function generateWeekPlan(){
    const start=startOfWeek(selectedDate);const days=Array.from({length:7},(_,i)=>addDays(start,i));const buckets=days.map(()=>[]);
    const items=[];
    state.tasks.filter(t=>!t.done).forEach(task=>items.push({label:`${task.subject?task.subject+": ":""}${task.title}`,due:task.due||isoDate(addDays(start,6)),score:100-priorityRank(task.priority)*20,minutes:Number(task.estimate)||30}));
    state.reviews.forEach(review=>{const next=nextReviewDate(review);if(next&&next>=isoDate(start)&&next<=isoDate(addDays(start,6)))items.push({label:`مراجعة ${review.subject}: ${review.topic}`,due:next,score:90,minutes:20});});
    state.exams.forEach(exam=>{const examDate=parseDate(exam.date);const left=daysBetween(start,examDate);if(left>=0&&left<=35)items.push({label:`تحضير ${exam.subject}: ${exam.name}`,due:isoDate(examDate),score:80+Number(exam.weight)*10,minutes:left<=7?60:40});});
    items.sort((a,b)=>a.due.localeCompare(b.due)||b.score-a.score);
    const loads=Array(7).fill(0);
    items.forEach(item=>{
      const dueIndex=Math.max(0,Math.min(6,daysBetween(start,parseDate(item.due))));let candidates=Array.from({length:dueIndex+1},(_,i)=>i);
      if(!candidates.length)candidates=[0];candidates.sort((a,b)=>loads[a]-loads[b]);const idx=candidates[0];buckets[idx].push(item);loads[idx]+=item.minutes;
    });
    const lightDay=loads.indexOf(Math.min(...loads));buckets[lightDay].push({label:"مساحة خفيفة: ترتيب، تعويض صغير، أو راحة",minutes:20,score:0});
    const key=isoDate(start);state.weekPlans[key]=buckets;saveState();renderWeek();
  }
  function renderWeek(){
    const start=startOfWeek(selectedDate);const key=isoDate(start);const buckets=state.weekPlans[key]||Array.from({length:7},()=>[]);const grid=$("weekGrid");grid.textContent="";
    Array.from({length:7},(_,i)=>addDays(start,i)).forEach((date,i)=>{const card=document.createElement("article");card.className="week-day";const h=document.createElement("h3");h.textContent=new Intl.DateTimeFormat("ar",{weekday:"long",day:"numeric",month:"short"}).format(date);const ul=document.createElement("ul");(buckets[i]||[]).forEach(item=>{const li=document.createElement("li");li.textContent=`${item.label}${item.minutes?` (${item.minutes} د)`:""}`;ul.appendChild(li);});if(!ul.children.length){const li=document.createElement("li");li.className="empty";li.textContent="مرن أو راحة";ul.appendChild(li);}card.append(h,ul);grid.appendChild(card);});
  }

  function setTimerMinutes(minutes){state.timer.minutes=minutes;state.timer.remaining=Math.round(minutes*60);state.timer.running=false;state.timer.endAt=0;clearInterval(timerInterval);saveState();renderTimer();}
  function renderTimer(){let remaining=state.timer.remaining;if(state.timer.running&&state.timer.endAt){remaining=Math.max(0,Math.ceil((state.timer.endAt-Date.now())/1000));state.timer.remaining=remaining;if(remaining<=0)finishTimer();}
    const mins=Math.floor(remaining/60),secs=remaining%60;$("timerDisplay").textContent=`${pad(mins)}:${pad(secs)}`;const total=Math.max(1,state.timer.minutes*60);$("timerProgress").style.width=`${Math.min(100,Math.max(0,(1-remaining/total)*100))}%`;$("timerLabel").textContent=state.timer.running?`جلسة ${state.timer.subject||"دراسة"} قيد التشغيل.`:"جاهز لبدء جلسة تركيز.";
  }
  function startTimer(){if(state.timer.running)return;state.timer.subject=$("focusSubject").value.trim();if(state.timer.remaining<=0)state.timer.remaining=state.timer.minutes*60;state.timer.running=true;state.timer.endAt=Date.now()+state.timer.remaining*1000;saveState();timerInterval=setInterval(()=>{renderTimer();saveState();},1000);renderTimer();}
  function pauseTimer(){if(!state.timer.running)return;state.timer.remaining=Math.max(0,Math.ceil((state.timer.endAt-Date.now())/1000));state.timer.running=false;state.timer.endAt=0;clearInterval(timerInterval);saveState();renderTimer();}
  function finishTimer(){clearInterval(timerInterval);state.timer.running=false;state.timer.endAt=0;state.timer.remaining=0;saveState();renderTimer();$("timerLabel").textContent="اكتملت الجلسة. سجل النتيجة وخذ استراحة مناسبة.";if("Notification" in window&&Notification.permission==="granted")new Notification("اكتملت جلسة التركيز",{body:"خذ استراحة قصيرة ثم قرر الخطوة التالية."});}

  function buildICS(days){
    const now=new Date();const stamp=`${now.getUTCFullYear()}${pad(now.getUTCMonth()+1)}${pad(now.getUTCDate())}T${pad(now.getUTCHours())}${pad(now.getUTCMinutes())}${pad(now.getUTCSeconds())}Z`;const reminder=Number(state.settings.reminderMinutes)||0;const neutral=state.settings.eventPrivacy==="neutral";const lines=["BEGIN:VCALENDAR","VERSION:2.0","PRODID:-//Health Renewal//Student Calendar AR//EN","CALSCALE:GREGORIAN","METHOD:PUBLISH","X-WR-CALNAME:تقويم الطالب"];
    const event=(uidValue,date,time,duration,summary,description)=>{lines.push("BEGIN:VEVENT",`UID:${uidValue}@healthrenewal.org`,`DTSTAMP:${stamp}`,`DTSTART:${icsDateTime(date,time)}`,`DTEND:${icsDateTime(date,newTime(time,duration))}`,`SUMMARY:${escapeICS(summary)}`,`DESCRIPTION:${escapeICS(description)}`);if(reminder>=0)lines.push("BEGIN:VALARM","ACTION:DISPLAY",`TRIGGER:-PT${reminder}M`,`DESCRIPTION:${escapeICS(summary)}`,"END:VALARM");lines.push("END:VEVENT");};
    for(let i=0;i<days;i+=1){const date=addDays(new Date(),i);const content=[pick(morningBank,date),pick(ideaBank,date,3),pick(memoryBank,date,7)].join("\n");event(`morning-${isoDate(date)}`,date,state.settings.morningTime,20,neutral?"وقت شخصي":"بداية خطة الدراسة",content);event(`noon-${isoDate(date)}`,date,state.settings.noonTime,5,neutral?"وقفة شخصية":"كيف يسير تركيزي الآن؟",pick(noonBoostBank,date,5));event(`evening-${isoDate(date)}`,date,state.settings.eveningTime,10,neutral?"مراجعة شخصية":"مراجعة يوم الطالب","ما الذي أنجزته؟ ما الخطوة التالية؟ جهز أول مهمة للغد.");}
    state.exams.filter(exam=>daysBetween(new Date(),parseDate(exam.date))>=0&&daysBetween(new Date(),parseDate(exam.date))<days).forEach(exam=>event(`exam-${exam.id}`,parseDate(exam.date),"08:00",60,neutral?"موعد مهم":`${exam.subject}: ${exam.name}`,examPlan(exam)));
    lines.push("END:VCALENDAR");return lines.join("\r\n");
  }
  function newTime(time,minutes){const [h,m]=time.split(":").map(Number);const total=(h*60+m+minutes)%(24*60);return `${pad(Math.floor(total/60))}:${pad(total%60)}`;}
  function googleCalendarToday(){const date=selectedDate;const start=icsDateTime(date,state.settings.morningTime);const end=icsDateTime(date,newTime(state.settings.morningTime,45));const title=state.settings.eventPrivacy==="neutral"?"وقت شخصي":"خطة دراسة اليوم";const details=[pick(morningBank,date),pick(ideaBank,date,3),`وقفة الظهر ${state.settings.noonTime}: كيف يسير تركيزك الآن؟`].join("\n");const url=`https://calendar.google.com/calendar/render?action=TEMPLATE&text=${encodeURIComponent(title)}&dates=${start}/${end}&details=${encodeURIComponent(details)}`;window.open(url,"_blank","noopener");}

  function exportData(){downloadFile(`student-calendar-backup-${isoDate(new Date())}.json`,JSON.stringify(state,null,2),"application/json;charset=utf-8");setStatus("settingsStatus","تم إنشاء نسخة احتياطية محلية.");}
  async function importData(file){try{const parsed=JSON.parse(await file.text());if(!parsed||typeof parsed!=="object"||!Array.isArray(parsed.tasks)||!Array.isArray(parsed.exams))throw new Error("invalid");state={...clone(defaultState),...parsed,profile:{...clone(defaultState.profile),...(parsed.profile||{})},settings:{...clone(defaultState.settings),...(parsed.settings||{})},timer:{...clone(defaultState.timer),...(parsed.timer||{})}};saveState();hydrateAll();setStatus("settingsStatus","تم استيراد النسخة بنجاح.");}catch(_){setStatus("settingsStatus","تعذر استيراد الملف. استخدم نسخة JSON صادرة من الأداة.");}}
  function hydrateAll(){hydrateProfile();hydrateSettings();renderToday();renderTasks();renderReviews();renderExams();renderWeek();renderTimer();}

  function bindEvents(){
    $("profileForm").addEventListener("submit",e=>{e.preventDefault();state.profile={name:$("studentName").value.trim(),level:$("educationLevel").value,subjects:$("subjects").value.split(/[،,]/).map(s=>s.trim()).filter(Boolean).slice(0,30),weeklyGoal:Number($("weeklyGoal").value)||12,defaultMinutes:Number($("defaultMinutes").value)||120,weekStart:Number($("weekStart").value)};saveState();renderSubjectOptions();setStatus("profileStatus","حُفظ إعداد الطالب محليًا.");renderWeek();});
    $("smartPlanForm").addEventListener("submit",e=>{e.preventDefault();renderPlan(buildSmartPlan({subject:$("planSubject").value.trim(),minutes:$("planMinutes").value,energy:$("energyLevel").value,difficulty:$("taskDifficulty").value,mode:$("studyMode").value}));});
    $("taskForm").addEventListener("submit",e=>{e.preventDefault();state.tasks.push({id:uid("task"),title:$("taskTitle").value.trim(),subject:$("taskSubject").value.trim(),priority:$("taskPriority").value,due:$("taskDue").value,estimate:Number($("taskEstimate").value)||30,done:false,createdAt:new Date().toISOString()});saveState();e.target.reset();$("taskEstimate").value=30;renderTasks();});
    $("showOnlyToday").addEventListener("click",()=>{showTodayOnly=!showTodayOnly;$("showOnlyToday").setAttribute("aria-pressed",String(showTodayOnly));renderTasks();});
    $("focusPreset").addEventListener("change",()=>setTimerMinutes(Number($("focusPreset").value)));
    $("startTimer").addEventListener("click",startTimer);$("pauseTimer").addEventListener("click",pauseTimer);$("resetTimer").addEventListener("click",()=>setTimerMinutes(Number($("focusPreset").value)));
    qsa(".choice",$("noonChoices")).forEach(btn=>btn.addEventListener("click",()=>{const key=isoDate(selectedDate);state.logs[key]={...(state.logs[key]||{}),noonFocus:btn.dataset.value,noonCheckedAt:new Date().toISOString()};saveState();hydrateDailyLog();setStatus("noonStatus",`حُفظ: ${btn.dataset.value}. عدّل بقية اليوم بما يناسبك.`);}));
    $("wellbeingForm").addEventListener("submit",e=>{e.preventDefault();const key=isoDate(selectedDate);state.logs[key]={...(state.logs[key]||{}),stress:Number($("stressLevel").value),sleep:Number($("sleepHours").value),reflection:$("eveningReflection").value.trim(),updatedAt:new Date().toISOString()};saveState();wellbeingAdvice(state.logs[key].stress,state.logs[key].sleep);setStatus("noonStatus","حُفظ سجل اليوم محليًا.");});
    $("stressLevel").addEventListener("input",()=>wellbeingAdvice(Number($("stressLevel").value),Number($("sleepHours").value)));$("sleepHours").addEventListener("input",()=>wellbeingAdvice(Number($("stressLevel").value),Number($("sleepHours").value)));
    $("reviewForm").addEventListener("submit",e=>{e.preventDefault();const start=$("reviewStart").value?parseDate($("reviewStart").value):selectedDate;state.reviews.push({id:uid("review"),subject:$("reviewSubject").value.trim(),topic:$("reviewTopic").value.trim(),start:isoDate(start),dates:reviewDates(start),done:[false,false,false,false,false]});saveState();e.target.reset();$("reviewStart").value=isoDate(selectedDate);renderReviews();});
    $("examForm").addEventListener("submit",e=>{e.preventDefault();state.exams.push({id:uid("exam"),subject:$("examSubject").value.trim(),name:$("examName").value.trim(),date:$("examDate").value,weight:Number($("examWeight").value)});saveState();e.target.reset();renderExams();});
    $("generateWeek").addEventListener("click",generateWeekPlan);$("printWeek").addEventListener("click",()=>window.print());
    $("settingsForm").addEventListener("submit",e=>{e.preventDefault();state.settings={morningTime:$("morningTime").value||"07:00",noonTime:$("noonTime").value||"12:30",eveningTime:$("eveningTime").value||"19:30",reminderMinutes:Number($("reminderMinutes").value),eventPrivacy:$("eventPrivacy").value};saveState();hydrateSettings();setStatus("settingsStatus","حُفظت أوقات التذكير محليًا.");});
    qsa("[data-ics-days]").forEach(btn=>btn.addEventListener("click",()=>{const days=Number(btn.dataset.icsDays);downloadFile(`student-calendar-${days}-days.ics`,buildICS(days),"text/calendar;charset=utf-8");setStatus("settingsStatus",`تم إنشاء ملف تقويم لمدة ${days} يومًا.`);}));
    $("googleToday").addEventListener("click",googleCalendarToday);
    $("testNotification").addEventListener("click",async()=>{if(!("Notification" in window)){setStatus("settingsStatus","هذا المتصفح لا يدعم إشعارات الويب.");return;}const permission=await Notification.requestPermission();if(permission==="granted"){new Notification("تذكير تجريبي",{body:"تقويم الطلاب جاهز. التذكيرات المضمونة تكون عبر ملف ICS وتقويم الهاتف."});setStatus("settingsStatus","ظهر إشعار تجريبي. قد يوقف المتصفح إشعارات الصفحة عند إغلاقها؛ استخدم ICS للتذكير المستمر.");}else setStatus("settingsStatus","لم يُسمح بالإشعارات.");});
    $("exportData").addEventListener("click",exportData);$("importData").addEventListener("change",e=>{const [file]=e.target.files;if(file)importData(file);e.target.value="";});
    $("clearData").addEventListener("click",()=>{if(!confirm("سيتم حذف جميع المهام والاختبارات والسجلات المحلية من هذا المتصفح. هل أنت متأكد؟"))return;localStorage.removeItem(STORAGE_KEY);state=clone(defaultState);hydrateAll();setStatus("settingsStatus","مُسحت البيانات المحلية.");});
    $("prevDay").addEventListener("click",()=>{selectedDate=addDays(selectedDate,-1);renderToday();renderWeek();});$("nextDay").addEventListener("click",()=>{selectedDate=addDays(selectedDate,1);renderToday();renderWeek();});$("goToday").addEventListener("click",()=>{selectedDate=startOfDay(new Date());renderToday();renderWeek();});
    window.addEventListener("beforeinstallprompt",e=>{e.preventDefault();deferredInstallPrompt=e;$("installApp").hidden=false;});$("installApp").addEventListener("click",async()=>{if(!deferredInstallPrompt)return;deferredInstallPrompt.prompt();await deferredInstallPrompt.userChoice;deferredInstallPrompt=null;$("installApp").hidden=true;});
  }

  function init(){
    $("taskDue").value=isoDate(selectedDate);$("reviewStart").value=isoDate(selectedDate);
    const examDefault=addDays(selectedDate,14);$("examDate").value=isoDate(examDefault);
    hydrateAll();bindEvents();
    if(state.timer.running){timerInterval=setInterval(()=>{renderTimer();saveState();},1000);}
    if("serviceWorker" in navigator)window.addEventListener("load",()=>navigator.serviceWorker.register("service-worker.js").catch(()=>{}));
  }

  init();
})();
