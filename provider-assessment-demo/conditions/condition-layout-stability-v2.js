"use strict";

(() => {
  const root = document.getElementById("condition-root");
  if (!root || document.body.dataset.depth !== "detail" || document.body.dataset.layoutStable !== "true") return;

  let revealed = false;
  const requiredModules = ["[data-assessment-education]", "[data-condition-decision-guide]"];
  const complete = () => Boolean(root.querySelector(".layout") && requiredModules.every((selector) => root.querySelector(selector)));
  const failed = () => Boolean(root.querySelector("[data-module-load-error]"));
  const reveal = (reason) => {
    if (revealed) return;
    revealed = true;
    document.body.dataset.layoutReady = "true";
    root.classList.add("condition-ready");
    root.removeAttribute("aria-busy");
    root.dataset.layoutReadyReason = reason;
  };
  const revealWhenSettled = () => {
    if (!complete() && !failed()) return false;
    requestAnimationFrame(() => requestAnimationFrame(() => reveal(complete() ? "content-complete" : "module-error")));
    return true;
  };

  root.setAttribute("aria-busy", "true");
  if (!revealWhenSettled()) {
    const observer = new MutationObserver(() => {
      if (!revealWhenSettled()) return;
      observer.disconnect();
    });
    observer.observe(root, { childList: true, subtree: true });
    window.addEventListener("load", revealWhenSettled, { once: true });
    window.setTimeout(() => {
      observer.disconnect();
      reveal("safe-timeout");
    }, 12000);
  }
})();
