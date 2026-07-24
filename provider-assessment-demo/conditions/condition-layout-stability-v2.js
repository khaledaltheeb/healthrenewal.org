"use strict";

(() => {
  const root = document.getElementById("condition-root");
  if (!root || document.body.dataset.depth !== "detail" || document.body.dataset.layoutStable !== "true") return;

  let revealed = false;
  const ready = () => Boolean(root.querySelector(".layout") && root.querySelector("[data-assessment-education]"));
  const reveal = (reason) => {
    if (revealed) return;
    revealed = true;
    root.classList.add("condition-ready");
    root.removeAttribute("aria-busy");
    root.dataset.layoutReadyReason = reason;
  };
  const revealWhenReady = () => {
    if (!ready()) return false;
    requestAnimationFrame(() => requestAnimationFrame(() => reveal("content-complete")));
    return true;
  };

  root.setAttribute("aria-busy", "true");
  if (!revealWhenReady()) {
    const observer = new MutationObserver(() => {
      if (!revealWhenReady()) return;
      observer.disconnect();
    });
    observer.observe(root, { childList: true, subtree: true });
    window.addEventListener("load", () => {
      if (ready()) revealWhenReady();
    }, { once: true });
    window.setTimeout(() => {
      observer.disconnect();
      reveal("safe-timeout");
    }, 5000);
  }
})();
