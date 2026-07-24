"use strict";

(() => {
  const registry = window.PA_CONDITION_PATHWAYS;
  const root = document.getElementById("condition-root");
  const slug = document.body.dataset.condition;
  const condition = registry?.conditions?.find((item) => item.slug === slug);
  if (!root || !condition || root.querySelector("[data-decision-handoff]")) return;

  const esc = (value) => String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");

  const assessmentMatrix = [
    {
      id: "screening",
      title: "المسح أو الفرز",
      useWhen: "عندما يكون السؤال: هل توجد إشارة تستدعي جمع معلومات إضافية أو إحالة؟",
      minimumEvidence: "أداة مسح ملائمة للعمر واللغة، مصدر معلومات موثق، ومراجعة القلق المستمر أو فقدان المهارة أو الخطر.",
      decision: "لا إشارة حالية، إعادة مسح في موعد محدد، أو إحالة إلى تقييم متعمق.",
      boundary: "لا يثبت التشخيص أو الأهلية، ولا يُستخدم وحده لاختيار برنامج علاجي أو تعليمي نهائي."
    },
    {
      id: "diagnostic",
      title: "التقييم التشخيصي",
      useWhen: "عندما يكون السؤال محددًا حول وجود حالة وتشخيصات بديلة أو مصاحبة.",
      minimumEvidence: "تاريخ نمائي وصحي، مقابلة، ملاحظة، مصادر متعددة، أدوات ملائمة، وفحص السمع والبصر أو العوامل الطبية عند الحاجة.",
      decision: "صياغة مهنية تبين الأدلة المؤيدة والمخالفة والحدود ومن يملك صلاحية اتخاذ القرار.",
      boundary: "لا تُحوّل درجة منفردة أو نتيجة خارجية غير موثقة إلى تشخيص آلي."
    },
    {
      id: "functional",
      title: "التقييم الوظيفي",
      useWhen: "عندما يكون السؤال: ما الذي يساعد الشخص أو يعيقه في النشاط والمشاركة والاستقلال؟",
      minimumEvidence: "ملاحظة في بيئات طبيعية، رأي الشخص والأسرة، مستوى المساعدة، التكييفات، والعوامل البيئية.",
      decision: "أولويات دعم وتكييفات وأهداف مرتبطة بمواقف الحياة اليومية.",
      boundary: "لا يُختزل الأداء الوظيفي في درجة قدرة أو تشخيص طبي فقط."
    },
    {
      id: "progress",
      title: "متابعة التقدم",
      useWhen: "عندما يكون السؤال: هل أحدثت الخطة تغيرًا قابلًا للملاحظة في هدف محدد؟",
      minimumEvidence: "خط أساس، تعريف مؤشر، وحدة قياس، تواتر جمع، ظروف ثابتة قدر الإمكان، وموعد مراجعة.",
      decision: "استمرار الخطة أو تعديلها أو إيقافها مع توثيق سبب القرار.",
      boundary: "التغير الوصفي داخل الخطة ليس تغيرًا معياريًا ولا يثبت تحسنًا سريريًا عامًا."
    }
  ];

  const familyPack = [
    `حضّر مثالين حديثين على القوة أو النجاح في ${condition.focus.slice(0, 2).join(" و")}.`,
    `حضّر مثالين على الصعوبة مع ذكر المكان والوقت ومن كان حاضرًا وما نوع المساعدة المقدمة.`,
    "اكتب ما الذي جُرّب بالفعل، وما الذي ساعد، وما الذي زاد العبء أو الضيق.",
    "اجلب تقارير خارجية أو أسماءها وتواريخها فقط؛ لا ترفع ملفات حساسة أو مواد اختبارات محمية إلى النسخة العامة.",
    "حدد أولوية واحدة قابلة للملاحظة للأسابيع القادمة بدل قائمة طويلة من الأهداف العامة."
  ];

  const providerHandoff = [
    `سؤال الإحالة محدد ويرتبط بمسار ${condition.title}.`,
    `مصادر الأدلة تشمل أكثر من بيئة أو مفسرًا واضحًا لغيابها.`,
    `تم توثيق مجالات التركيز: ${condition.focus.slice(0, 3).join("، ")}.`,
    "تمت مراجعة صلاحية النتيجة في ضوء اللغة والتواصل والسمع والبصر والحركة والتعب والألم والتكييفات.",
    "تم الفصل بين نتيجة الأداة والاستنتاج المهني، وبين المسح والتشخيص والتقييم الوظيفي والمتابعة.",
    "التقرير يذكر نقاط القوة والاحتياجات والعوامل البيئية والخطوة التالية والمسؤول والموعد.",
    "أي أداة محمية سُجلت كنتيجة خارجية أو رابط رسمي، دون نسخ البنود أو مفاتيح التصحيح أو المعايير."
  ];

  const meetingQuestions = [
    "ما نوع التقييم المطلوب الآن، ولماذا هذا النوع وليس نوعًا آخر؟",
    "ما القرار الذي يمكن لهذه البيانات دعمه، وما القرار الذي لا تستطيع دعمه؟",
    "ما الأدلة الناقصة أو المتعارضة، وكيف ستُجمع؟",
    "ما التكييفات التي استُخدمت، وهل تغيرت صلاحية المقارنة بسببها؟",
    "ما الهدف القابل للقياس، ومن سيجمع البيانات، ومتى ستتم المراجعة؟",
    "ما النسخة المبسطة التي ستُسلّم للأسرة أو للشخص؟"
  ];

  const list = (items) => `<ul class="list">${items.map((item) => `<li>${esc(item)}</li>`).join("")}</ul>`;
  const storageKey = `pa-condition-handoff-v1:${condition.slug}`;

  const section = document.createElement("section");
  section.dataset.decisionHandoff = "true";
  section.className = "stack";
  section.setAttribute("aria-label", "مسار القرار والتسليم المهني والأسري");
  section.innerHTML = `
    <section class="panel">
      <p class="eyebrow">من السؤال إلى القرار</p>
      <h2>مصفوفة اختيار نوع التقييم</h2>
      <p>اختر النوع وفق سؤال الإحالة والمخرج المطلوب، لا وفق اسم الأداة المتاحة فقط.</p>
      <div class="course decision-matrix">
        ${assessmentMatrix.map((item) => `<article class="metric" data-assessment-type="${esc(item.id)}"><strong>${esc(item.title)}</strong><span><b>يستخدم عندما:</b> ${esc(item.useWhen)}</span><span><b>الحد الأدنى من الأدلة:</b> ${esc(item.minimumEvidence)}</span><span><b>القرار الممكن:</b> ${esc(item.decision)}</span><span><b>الحد المهني:</b> ${esc(item.boundary)}</span></article>`).join("")}
      </div>
    </section>

    <section class="panel">
      <h2>حزمة الأسرة قبل الموعد لمسار ${esc(condition.title)}</h2>
      <p>الهدف هو جمع أمثلة وظيفية قابلة للفهم، لا تدريب الأسرة على إجابات اختبار.</p>
      ${list(familyPack)}
    </section>

    <section class="panel" data-handoff-checklist>
      <h2>قائمة التسليم بين المختصين</h2>
      <p>علّم البنود بعد مراجعتها. تحفظ العلامات محليًا لهذا المسار فقط.</p>
      <div class="course">
        ${providerHandoff.map((item, index) => `<button class="metric handoff-check" type="button" data-handoff-item="${index}" aria-pressed="false"><strong>${index + 1}</strong><span>${esc(item)}</span></button>`).join("")}
      </div>
      <p class="notice" data-handoff-status>لم تكتمل بنود التسليم بعد.</p>
    </section>

    <section class="panel">
      <h2>أسئلة اجتماع القرار</h2>
      ${list(meetingQuestions)}
      <div class="notice">عند وجود خطر مباشر أو فقدان مهارة أو تدهور صحي، لا تؤخر الإحالة الطبية أو مسار السلامة بانتظار اكتمال جميع المقاييس.</div>
    </section>

    <section class="panel">
      <h2>الأساس المؤسسي لهذا المسار</h2>
      <ul class="list">
        <li><a href="https://www.who.int/standards/classifications/international-classification-of-functioning-disability-and-health" rel="noopener noreferrer">WHO ICF: النشاط والمشاركة والعوامل البيئية ضمن وصف الوظيفة.</a></li>
        <li><a href="https://www.aap.org/en/patient-care/developmental-surveillance-and-screening-patient-care/" rel="noopener noreferrer">AAP: المراقبة والمسح والإحالة للتقييم عند الحاجة.</a></li>
        <li><a href="https://www.cdc.gov/act-early/about/developmental-monitoring-and-screening.html" rel="noopener noreferrer">CDC: المسح يحدد الحاجة إلى تقييم إضافي ولا يمثل تشخيصًا بذاته.</a></li>
      </ul>
      <p class="muted">لا تتضمن هذه الصفحة بنود أدوات تجارية أو مفاتيح تصحيح أو معايير. عند استخدام أداة محمية، يُرجع إلى الناشر والنسخة المرخصة والمؤهل المطلوب.</p>
    </section>`;

  const mainStack = root.querySelector(".layout main.stack");
  if (mainStack) mainStack.append(...section.children);
  else root.appendChild(section);

  const readState = () => {
    try { return JSON.parse(localStorage.getItem(storageKey) || "{}"); } catch (_) { return {}; }
  };
  const writeState = (value) => {
    try { localStorage.setItem(storageKey, JSON.stringify(value)); } catch (_) {}
  };
  const renderState = () => {
    const state = readState();
    const buttons = [...root.querySelectorAll("[data-handoff-item]")];
    buttons.forEach((button) => {
      const done = Boolean(state[button.dataset.handoffItem]);
      button.setAttribute("aria-pressed", String(done));
      button.classList.toggle("completed", done);
    });
    const count = buttons.filter((button) => button.getAttribute("aria-pressed") === "true").length;
    const status = root.querySelector("[data-handoff-status]");
    if (status) status.textContent = count === buttons.length
      ? "اكتملت قائمة التسليم. راجع مسؤول القرار والموعد ومؤشر المتابعة قبل الإغلاق."
      : `اكتملت ${count} من ${buttons.length} بنود.`;
  };

  root.addEventListener("click", (event) => {
    const button = event.target.closest("[data-handoff-item]");
    if (!button) return;
    const state = readState();
    state[button.dataset.handoffItem] = !state[button.dataset.handoffItem];
    state.updatedAt = new Date().toISOString();
    writeState(state);
    renderState();
  });

  renderState();
})();
