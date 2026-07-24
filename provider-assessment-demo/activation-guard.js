"use strict";

(() => {
  const data = window.PA_DEMO_DATA;
  const slug = (value) => String(value || "")
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");

  if (Array.isArray(data?.professional)) {
    data.professional.forEach((item, index) => {
      if (!item.id) item.id = `professional-${index + 1}-${slug(item.name) || "record"}`;
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

  if (typeof render === "function") render();

  document.addEventListener("click", (event) => {
    const cancelButton = event.target.closest(
      "#account-form button[value='cancel'], #professional-record-form button[value='cancel']"
    );
    if (!cancelButton) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    const dialog = cancelButton.closest("dialog");
    if (!dialog) return;
    if (typeof dialog.close === "function") dialog.close();
    else dialog.removeAttribute("open");
  }, true);
})();
