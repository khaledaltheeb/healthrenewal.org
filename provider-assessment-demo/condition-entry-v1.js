"use strict";

(() => {
  const registry = window.PA_CONDITION_PATHWAYS;
  if (!registry || !Array.isArray(registry.conditions)) return;

  const params = new URLSearchParams(window.location.search);
  const requestedSlug = params.get("condition");
  const requestedView = params.get("open");
  let stored = null;
  try { stored = JSON.parse(localStorage.getItem("pa-selected-condition-v1") || "null"); } catch (_) {}
  const slug = requestedSlug || stored?.slug || "";
  const condition = registry.conditions.find((item) => item.slug === slug);

  const currentPathway = () => {
    let saved = null;
    try { saved = JSON.parse(localStorage.getItem("pa-selected-condition-v1") || "null"); } catch (_) {}
    const currentParams = new URLSearchParams(window.location.search);
    const activeSlug = currentParams.get("condition") || saved?.slug || "";
    const item = registry.conditions.find((candidate) => candidate.slug === activeSlug);
    return item ? {
      slug: item.slug,
      title: item.title,
      summary: item.summary,
      registryVersion: registry.version,
      selectedAt: saved?.selectedAt || new Date().toISOString()
    } : null;
  };

  const openView = (name) => {
    const tab = document.querySelector(`[data-view="${name}"]`);
    if (tab) {
      tab.click();
      document.getElementById(`view-${name}`)?.scrollIntoView({ behavior: "smooth", block: "start" });
      return true;
    }
    return false;
  };

  const addConditionsLink = () => {
    const headerActions = document.querySelector(".header-actions");
    if (headerActions && !document.getElementById("conditions-hub-link")) {
      const link = document.createElement("a");
      link.id = "conditions-hub-link";
      link.className = "button ghost";
      link.href = "conditions/";
      link.textContent = "مسارات الحالات";
      headerActions.prepend(link);
    }

    const heroActions = document.querySelector(".hero-actions");
    if (heroActions && !heroActions.querySelector('[href="conditions/"]')) {
      const link = document.createElement("a");
      link.className = "button secondary";
      link.href = "conditions/";
      link.textContent = "استعراض الحالات العشرين";
      heroActions.appendChild(link);
    }
  };

  const bindPathwayToCaseCreation = () => {
    if (typeof makeCase !== "function" || makeCase.pathwayAware === true) return;
    const originalMakeCase = makeCase;
    const pathwayAwareMakeCase = function pathwayAwareMakeCase(formData) {
      const caseRecord = originalMakeCase(formData);
      const pathway = currentPathway();
      if (caseRecord && pathway) {
        caseRecord.conditionPathway = pathway;
        caseRecord.updatedAt = new Date().toISOString();
        save();
        render();
      }
      return caseRecord;
    };
    pathwayAwareMakeCase.pathwayAware = true;
    makeCase = pathwayAwareMakeCase;
  };

  const showContext = () => {
    if (!condition || document.getElementById("condition-context-bar")) return;
    const workspace = document.getElementById("workspace");
    if (!workspace) return;

    const bar = document.createElement("section");
    bar.id = "condition-context-bar";
    bar.className = "callout info";
    bar.setAttribute("aria-label", "مسار الحالة المختارة");
    bar.innerHTML = `<strong>مسار الحالة الحالي: ${condition.title}</strong><br><span>${condition.summary}</span><div class="card-actions" style="margin-top:10px"><button class="button primary small-button" type="button" id="open-condition-professional">عرض المقاييس المرتبطة</button><a class="button ghost small-button" href="conditions/${condition.slug}/">فتح دليل الحالة</a><button class="button ghost small-button" type="button" id="clear-condition-pathway">إلغاء التحديد</button></div>`;
    workspace.prepend(bar);

    document.getElementById("open-condition-professional")?.addEventListener("click", () => {
      const search = document.getElementById("professional-search");
      if (search) {
        search.value = condition.title;
        search.dispatchEvent(new Event("input", { bubbles: true }));
      }
      openView("professional");
    });

    document.getElementById("clear-condition-pathway")?.addEventListener("click", () => {
      try { localStorage.removeItem("pa-selected-condition-v1"); } catch (_) {}
      params.delete("condition");
      const next = `${window.location.pathname}${params.toString() ? `?${params}` : ""}${window.location.hash}`;
      window.history.replaceState({}, "", next);
      bar.remove();
    });
  };

  const routeRequestedView = () => {
    const routeMap = {
      professional: "professional",
      records: "professional-records",
      reports: "reports",
      cases: "cases",
      explorers: "explorers",
      guide: "guide",
      dashboard: "dashboard"
    };
    const target = routeMap[requestedView];
    if (!target) return;
    let attempts = 0;
    const route = () => {
      attempts += 1;
      if (openView(target) || attempts >= 16) return;
      setTimeout(route, 80);
    };
    requestAnimationFrame(route);
  };

  addConditionsLink();
  bindPathwayToCaseCreation();
  showContext();
  routeRequestedView();

  if (condition && requestedSlug) {
    try {
      localStorage.setItem("pa-selected-condition-v1", JSON.stringify({
        slug: condition.slug,
        title: condition.title,
        selectedAt: new Date().toISOString(),
        registryVersion: registry.version
      }));
    } catch (_) {}
  }
})();
