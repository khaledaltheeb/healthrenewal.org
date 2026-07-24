"use strict";

(() => {
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
