(() => {
  "use strict";

  const STORAGE_KEY = "hr-women-daily-calendar-v1";
  const EVENING_TIME = "20:30";
  const eveningNeeds = ["هدوء", "ماء", "طعام مناسب", "تمدد لطيف", "تواصل آمن"];
  const eveningBoostBank = [
    "لا تحتاجين إلى إنهاء كل شيء قبل أن ترتاحي؛ يكفي أن تغلقي اليوم بوضوح ولطف.",
    "اختاري ما يخفف عن جسدك الليلة، لا ما يضيف اختبارًا جديدًا إلى يومك.",
    "ضعي ما لم يكتمل في قائمة الغد بدل حمله إلى السرير.",
    "الراحة ليست انسحابًا من الحياة؛ هي جزء من القدرة على الاستمرار.",
    "قد يكون أفضل قرار الليلة كوب ماء، ضوء أخف، وهاتف أبعد.",
    "اسألي نفسك: ما الذي أستطيع تركه الآن من دون ضرر؟",
    "ليس كل تعب يحتاج حلًا فوريًا؛ بعضه يحتاج نومًا وأمانًا ومساحة.",
    "اختمي اليوم باعتراف واحد بما فعلته، ولو كان صغيرًا وغير مرئي.",
    "اسمحي لجسدك أن يهبط تدريجيًا من سرعة اليوم إلى هدوء الليل.",
    "اختاري جملة أخيرة لليوم: فعلت ما استطعت ضمن طاقتي وظروفي.",
    "إن كان يومك ثقيلًا، فليكن الإغلاق بسيطًا: تنفس، ماء، وقرار واحد للغد.",
    "توقفي عن تقييم قيمتك من خلال قائمة المهام؛ أنتِ أكثر من إنتاج اليوم.",
    "إطفاء تنبيه واحد غير ضروري قد يكون بداية نوم أكثر هدوءًا.",
    "راجعي جسدك بلطف: الفك، الكتفين، البطن، والقدمين؛ ثم خففي الشد قدر الإمكان.",
    "ليس مطلوبًا حل المشاعر كلها قبل النوم؛ يكفي تسميتها وعدم محاربتها.",
    "اجعلي آخر عشر دقائق أقل ضوءًا وأقل قرارات وأكثر أمانًا.",
    "يمكنك تأجيل النقاش الذي لا يحتمل طاقتك إلى وقت أوضح وأكثر أمانًا.",
    "اختاري احتياجًا واحدًا حقيقيًا بدل خمسة أهداف مثالية.",
    "اكتبي ما يوقظ ذهنك في سطر، ثم اتركي الورقة تحمل العبء بدل رأسك.",
    "إذا كان الألم أو النزف مختلفًا بوضوح عن المعتاد، سجليه واطلبي التقييم المناسب.",
    "التقدم الهادئ يشمل معرفة متى تتوقفين، لا معرفة متى تدفعين نفسك فقط.",
    "قابلي ليلتك كما تقابلين شخصًا تحبينه: بهدوء، احترام، ومن دون توبيخ.",
    "ما لم يحدث اليوم يمكن أن يعود إلى خطة الغد؛ لا يحتاج أن يتحول إلى لوم.",
    "اختمي اليوم بحد بسيط يحمي نومك: لا رسائل عمل ولا قرارات ثقيلة الآن."
  ];

  const $ = (id) => document.getElementById(id);
  const pad = (value) => String(value).padStart(2, "0");
  const dateKey = (date = new Date()) => `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
  const addDays = (date, amount) => new Date(date.getFullYear(), date.getMonth(), date.getDate() + amount, 12);

  function readState() {
    try {
      const value = JSON.parse(localStorage.getItem(STORAGE_KEY) || "null");
      return value && typeof value === "object" ? value : { settings: {}, logs: {}, completions: {} };
    } catch (_error) {
      return { settings: {}, logs: {}, completions: {} };
    }
  }

  function writeState(state) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  }

  function ensureStyle() {
    if (document.querySelector('link[data-calendar-enhancements]')) return;
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = "calendar-enhancements.css?v=2.0.0";
    link.dataset.calendarEnhancements = "true";
    document.head.append(link);
  }

  function applyRawafidBrand() {
    document.title = document.title.replace("Health Renewal", "منصة روافد");
    document.querySelectorAll(".brand").forEach((node) => { node.textContent = "منصة روافد"; });
    document.querySelectorAll(".site-footer strong").forEach((node) => { node.textContent = "منصة روافد"; });
    const siteName = document.querySelector('meta[property="og:site_name"]');
    if (siteName) siteName.content = "منصة روافد";
  }

  function dailyEveningBoost(date = new Date()) {
    const start = new Date(date.getFullYear(), 0, 0);
    const ordinal = Math.floor((date - start) / 86400000);
    return eveningBoostBank[(ordinal * 11 + date.getMonth() * 7) % eveningBoostBank.length];
  }

  function renderEvening() {
    const card = $("eveningCheckIn");
    if (!card) return;
    const state = readState();
    const key = dateKey();
    const log = state.logs?.[key] || {};
    card.querySelectorAll("button[data-evening-need]").forEach((button) => {
      button.setAttribute("aria-pressed", String(button.dataset.eveningNeed === log.eveningNeed));
    });
    $("eveningBoost").textContent = dailyEveningBoost();
    $("eveningStatus").textContent = log.eveningNeed ? `احتياج المساء المسجل: ${log.eveningNeed}` : "";
  }

  function saveEvening(need) {
    const state = readState();
    const key = dateKey();
    state.logs ||= {};
    state.logs[key] = {
      ...(state.logs[key] || {}),
      eveningNeed: need,
      eveningCheckedAt: new Date().toISOString(),
    };
    writeState(state);
    renderEvening();
    renderWeeklyInsight();
  }

  function average(values) {
    if (!values.length) return null;
    return values.reduce((sum, value) => sum + value, 0) / values.length;
  }

  function describeAverage(value, labels) {
    if (value === null) return "لا توجد بيانات كافية";
    const index = Math.max(0, Math.min(labels.length - 1, Math.round(value) - 1));
    return `${labels[index]} · ${value.toFixed(1)}/5`;
  }

  function renderWeeklyInsight() {
    const box = $("weeklyInsightBody");
    if (!box) return;
    const state = readState();
    const logs = state.logs || {};
    const keys = Array.from({ length: 7 }, (_, index) => dateKey(addDays(new Date(), -index)));
    const entries = keys.map((key) => logs[key]).filter(Boolean);
    const mood = entries.map((entry) => Number(entry.mood)).filter((value) => value >= 1 && value <= 5);
    const energy = entries.map((entry) => Number(entry.energy)).filter((value) => value >= 1 && value <= 5);
    const pain = entries.map((entry) => Number(entry.pain)).filter((value) => value >= 0 && value <= 5);
    const eveningCount = entries.filter((entry) => entry.eveningNeed).length;
    const noonCount = entries.filter((entry) => entry.noonFeeling).length;
    const maximumPain = pain.length ? Math.max(...pain) : null;
    box.innerHTML = `
      <div><strong>${entries.length}/7</strong><span>أيام مسجلة</span></div>
      <div><strong>${describeAverage(average(mood), ["منخفض جدًا", "منخفض", "متوسط", "جيد", "جيد جدًا"])}</strong><span>متوسط المزاج الوصفي</span></div>
      <div><strong>${describeAverage(average(energy), ["منخفضة جدًا", "منخفضة", "متوسطة", "جيدة", "عالية"])}</strong><span>متوسط الطاقة الوصفي</span></div>
      <div><strong>${maximumPain === null ? "غير مسجل" : `${maximumPain}/5`}</strong><span>أعلى ألم مسجل</span></div>
      <div><strong>${noonCount}</strong><span>وقفات ظهر</span></div>
      <div><strong>${eveningCount}</strong><span>إغلاقات مسائية</span></div>`;
    $("weeklyInsightNote").textContent = entries.length < 3
      ? "سجلي ثلاثة أيام أو أكثر لرؤية نمط وصفي أوضح. لا يستخدم هذا الملخص للتشخيص."
      : "هذا ملخص وصفي لبياناتك المحلية، وليس تفسيرًا طبيًا أو تشخيصًا. قارني التغير بنمطك المعتاد واطلبي الرعاية عند الأعراض المقلقة.";
  }

  function escapeIcs(value) {
    return String(value).replaceAll("\\", "\\\\").replaceAll("\n", "\\n").replaceAll(",", "\\,").replaceAll(";", "\\;");
  }

  function downloadEveningIcs() {
    const state = readState();
    const time = state.settings?.eveningTime || EVENING_TIME;
    const timezone = state.settings?.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone || "Asia/Amman";
    const now = new Date();
    const stamp = `${now.getUTCFullYear()}${pad(now.getUTCMonth() + 1)}${pad(now.getUTCDate())}T${pad(now.getUTCHours())}${pad(now.getUTCMinutes())}${pad(now.getUTCSeconds())}Z`;
    const lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Rawafid//Women Evening Check-in AR//EN", "CALSCALE:GREGORIAN", `X-WR-CALNAME:${escapeIcs("إغلاق مسائي شخصي")}`, `X-WR-TIMEZONE:${escapeIcs(timezone)}`];
    for (let index = 0; index < 30; index += 1) {
      const date = addDays(new Date(), index);
      const compact = `${date.getFullYear()}${pad(date.getMonth() + 1)}${pad(date.getDate())}`;
      const start = `${compact}T${time.replace(":", "")}00`;
      const [hour, minute] = time.split(":").map(Number);
      const endDate = new Date(date.getFullYear(), date.getMonth(), date.getDate(), hour, minute + 5);
      const end = `${endDate.getFullYear()}${pad(endDate.getMonth() + 1)}${pad(endDate.getDate())}T${pad(endDate.getHours())}${pad(endDate.getMinutes())}00`;
      lines.push(
        "BEGIN:VEVENT",
        `UID:evening-${dateKey(date)}@healthrenewal.org`,
        `DTSTAMP:${stamp}`,
        `DTSTART;TZID=${timezone}:${start}`,
        `DTEND;TZID=${timezone}:${end}`,
        `SUMMARY:${escapeIcs("وقفة شخصية")}`,
        `DESCRIPTION:${escapeIcs(`ما الذي يحتاجه جسدك قبل النوم؟\n${dailyEveningBoost(date)}\nhttps://healthrenewal.org/sectors/women/daily-calendar/`)}`,
        "BEGIN:VALARM", "ACTION:DISPLAY", "DESCRIPTION:وقفة شخصية", "TRIGGER:-PT30M", "END:VALARM", "END:VEVENT"
      );
    }
    lines.push("END:VCALENDAR");
    const blob = new Blob([lines.join("\r\n")], { type: "text/calendar;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = Object.assign(document.createElement("a"), { href: url, download: "rawafid-women-evening-30-days.ics" });
    document.body.append(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    $("eveningStatus").textContent = "تم إنشاء 30 تذكيرًا مسائيًا بعناوين محايدة.";
  }

  function preserveWellbeingFields() {
    const form = $("logForm");
    if (!form) return;
    form.addEventListener("submit", () => {
      const before = readState().logs || {};
      window.setTimeout(() => {
        const state = readState();
        state.logs ||= {};
        Object.entries(before).forEach(([key, entry]) => {
          const preserved = {};
          for (const field of ["noonFeeling", "noonCheckedAt", "eveningNeed", "eveningCheckedAt"]) {
            if (entry?.[field] !== undefined) preserved[field] = entry[field];
          }
          if (Object.keys(preserved).length) state.logs[key] = { ...(state.logs[key] || {}), ...preserved };
        });
        writeState(state);
        renderWeeklyInsight();
      }, 0);
    }, true);
  }

  function buildEnhancements() {
    ensureStyle();
    applyRawafidBrand();
    const grid = document.querySelector(".daily-grid");
    if (grid && !$("eveningCheckIn")) {
      const card = document.createElement("section");
      card.id = "eveningCheckIn";
      card.className = "daily-item evening-checkin";
      card.innerHTML = `
        <span>إغلاق المساء · ${EVENING_TIME}</span>
        <h3>ما الذي يحتاجه جسدك قبل النوم؟</h3>
        <div class="evening-needs" role="group" aria-label="اختاري احتياج المساء">
          ${eveningNeeds.map((need) => `<button type="button" data-evening-need="${need}" aria-pressed="false">${need}</button>`).join("")}
        </div>
        <p id="eveningBoost" class="evening-boost"></p>
        <div class="evening-actions"><button id="downloadEveningIcs" type="button" class="button compact">تذكير مسائي لـ30 يومًا</button></div>
        <p id="eveningStatus" class="noon-status" aria-live="polite"></p>`;
      grid.append(card);
      card.addEventListener("click", (event) => {
        const button = event.target.closest("button[data-evening-need]");
        if (button) saveEvening(button.dataset.eveningNeed);
      });
      $("downloadEveningIcs").addEventListener("click", downloadEveningIcs);
    }

    const todaySection = $("today");
    if (todaySection && !$("weeklyInsight")) {
      const section = document.createElement("section");
      section.id = "weeklyInsight";
      section.className = "section weekly-insight";
      section.innerHTML = `
        <div class="section-heading"><div><p class="eyebrow dark">مرآة سبعة أيام</p><h2>ملخص محلي يساعدك على ملاحظة النمط</h2></div></div>
        <div class="panel"><div id="weeklyInsightBody" class="weekly-insight-grid"></div><p id="weeklyInsightNote" class="small-note"></p></div>`;
      todaySection.insertAdjacentElement("afterend", section);
    }
    preserveWellbeingFields();
    renderEvening();
    renderWeeklyInsight();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", buildEnhancements, { once: true });
  else buildEnhancements();
  window.addEventListener("storage", () => { renderEvening(); renderWeeklyInsight(); });
})();
