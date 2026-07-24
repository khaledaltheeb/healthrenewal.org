"use strict";

(() => {
  const data = window.PA_DEMO_DATA;
  if (!data || !Array.isArray(data.explorers)) return;

  const tool = data.explorers.find((item) => item.id === "emotional-regulation");
  if (!tool || !Array.isArray(tool.questions)) return;
  if (tool.questions.some((question) => question.type === "checkbox")) return;

  const contextQuestion = {
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

  const safetyIndex = tool.questions.findIndex((question) => question.safety === true);
  tool.questions.splice(safetyIndex >= 0 ? safetyIndex : Math.max(tool.questions.length - 1, 0), 0, contextQuestion);
})();
