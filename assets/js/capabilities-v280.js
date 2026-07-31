(() => {
  "use strict";

  const normalize = (value) =>
    String(value || "")
      .toLocaleLowerCase("ar")
      .normalize("NFKD")
      .replace(/[\u064B-\u065F\u0670]/g, "")
      .replace(/[أإآ]/g, "ا")
      .replace(/ى/g, "ي")
      .replace(/ؤ/g, "و")
      .replace(/ئ/g, "ي")
      .trim();

  const initializeRegistry = () => {
    const form = document.querySelector("[data-cap-filters]");
    const registry = document.querySelector("[data-cap-registry]");
    if (!form || !registry) return;

    const search = form.querySelector("[data-cap-search]");
    const category = form.querySelector("[data-cap-category]");
    const route = form.querySelector("[data-cap-route]");
    const evidence = form.querySelector("[data-cap-evidence]");
    const count = document.querySelector("[data-cap-count]");
    const empty = document.querySelector("[data-cap-empty]");
    const cards = Array.from(registry.querySelectorAll("[data-cap-condition]"));

    if (!search || !category || !route || !evidence || !count || !empty) return;

    const apply = () => {
      const query = normalize(search.value);
      const selectedCategory = category.value;
      const selectedRoute = route.value;
      const selectedEvidence = evidence.value;
      let visible = 0;

      cards.forEach((card) => {
        const matchesText =
          !query || normalize(card.dataset.search).includes(query);
        const matchesCategory =
          !selectedCategory || card.dataset.category === selectedCategory;
        const matchesRoute =
          !selectedRoute || card.dataset.route === selectedRoute;
        const matchesEvidence =
          !selectedEvidence || card.dataset.evidence === selectedEvidence;
        const show =
          matchesText && matchesCategory && matchesRoute && matchesEvidence;
        card.hidden = !show;
        if (show) visible += 1;
      });

      count.textContent = String(visible);
      empty.hidden = visible !== 0;
    };

    search.addEventListener("input", apply);
    category.addEventListener("change", apply);
    route.addEventListener("change", apply);
    evidence.addEventListener("change", apply);
    form.addEventListener("reset", () => window.setTimeout(apply, 0));
    apply();
  };

  const initializePrint = () => {
    const printButtons = document.querySelectorAll("[data-cap-print]");
    printButtons.forEach((button) => {
      button.addEventListener("click", () => window.print());
    });
  };

  const initialize = () => {
    initializeRegistry();
    initializePrint();
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initialize, { once: true });
  } else {
    initialize();
  }
})();
