"use strict";

(() => {
  const applyProgressSemantics = () => {
    document.querySelectorAll(".progress-track").forEach((track) => {
      const bar = track.querySelector(".progress-bar");
      const raw = bar?.style.width || "0";
      const value = Math.max(0, Math.min(100, Number.parseInt(raw, 10) || 0));
      track.setAttribute("role", "progressbar");
      track.setAttribute("aria-label", "نسبة تقدم المساق");
      track.setAttribute("aria-valuemin", "0");
      track.setAttribute("aria-valuemax", "100");
      track.setAttribute("aria-valuenow", String(value));
      track.setAttribute("aria-valuetext", `${value}% من متطلبات المساق`);
    });
  };

  const root = document.getElementById("training-modules");
  applyProgressSemantics();
  if (root) new MutationObserver(applyProgressSemantics).observe(root, { childList: true, subtree: true });
})();
