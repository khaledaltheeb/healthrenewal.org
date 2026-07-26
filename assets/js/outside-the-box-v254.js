(function () {
  "use strict";

  const STORAGE_KEY = "pterminology-btr-icf-v254";

  function normalize(value) {
    return String(value || "")
      .normalize("NFKD")
      .replace(/[\u064B-\u065F\u0670]/g, "")
      .replace(/[أإآ]/g, "ا")
      .replace(/ى/g, "ي")
      .replace(/ة/g, "ه")
      .toLocaleLowerCase("ar");
  }

  function setupConditionFilters() {
    const form = document.querySelector("[data-condition-filters]");
    if (!form) return;
    const search = form.querySelector("[data-condition-search]");
    const cluster = form.querySelector("[data-condition-cluster]");
    const tier = form.querySelector("[data-condition-tier]");
    const cards = Array.from(document.querySelectorAll("[data-condition-card]"));
    const results = document.querySelector("[data-condition-results]");
    const empty = document.querySelector("[data-condition-empty]");

    function update() {
      const query = normalize(search.value);
      let visible = 0;
      cards.forEach(function (card) {
        const searchMatch = !query || normalize(card.dataset.search).includes(query);
        const clusterMatch = !cluster.value || card.dataset.cluster === cluster.value;
        const tierMatch = !tier.value || card.dataset.tier === tier.value;
        const show = searchMatch && clusterMatch && tierMatch;
        card.hidden = !show;
        if (show) visible += 1;
      });
      results.textContent = visible + (visible === 1 ? " حالة ظاهرة" : " حالة ظاهرة");
      empty.hidden = visible !== 0;
    }

    form.addEventListener("input", update);
    form.addEventListener("reset", function () {
      window.setTimeout(update, 0);
    });
    update();
  }

  function blankState() {
    return { version: 254, plan: null, records: [] };
  }

  function readState() {
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (!raw) return blankState();
      const state = JSON.parse(raw);
      if (
        !state ||
        state.version !== 254 ||
        !Array.isArray(state.records)
      ) {
        return blankState();
      }
      return state;
    } catch (_error) {
      return blankState();
    }
  }

  function writeState(state) {
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
      return true;
    } catch (_error) {
      return false;
    }
  }

  function isoWithAddedWeeks(isoDate, weeks) {
    if (!isoDate) return "";
    const parts = isoDate.split("-").map(Number);
    if (parts.length !== 3 || parts.some(Number.isNaN)) return "";
    const date = new Date(parts[0], parts[1] - 1, parts[2], 12, 0, 0);
    date.setDate(date.getDate() + weeks * 7);
    return [
      date.getFullYear(),
      String(date.getMonth() + 1).padStart(2, "0"),
      String(date.getDate()).padStart(2, "0"),
    ].join("-");
  }

  function displayDate(isoDate) {
    if (!isoDate) return "—";
    const parts = isoDate.split("-").map(Number);
    const date = new Date(parts[0], parts[1] - 1, parts[2], 12, 0, 0);
    return new Intl.DateTimeFormat("ar", {
      year: "numeric",
      month: "long",
      day: "numeric",
    }).format(date);
  }

  function updatePlanDates(startDate) {
    document.querySelectorAll("[data-plan-date]").forEach(function (cell) {
      const week = Number(cell.dataset.planDate);
      cell.textContent = displayDate(isoWithAddedWeeks(startDate, week));
    });
  }

  function setWarning(node, message) {
    if (!node) return;
    node.textContent = message;
    node.hidden = !message;
  }

  function setupMonitoringMatrix() {
    const planForm = document.querySelector("[data-plan-form]");
    const recordForm = document.querySelector("[data-record-form]");
    if (!planForm || !recordForm) return;

    const conditionSelect = planForm.querySelector("[data-plan-condition]");
    const recordsBody = document.querySelector("[data-records-body]");
    const status = document.querySelector("[data-storage-status]");
    const warning = document.querySelector("[data-record-warning]");
    let state = readState();

    const requestedCondition = new URLSearchParams(window.location.search).get("condition");
    if (requestedCondition) {
      const option = Array.from(conditionSelect.options).find(function (item) {
        return item.value === requestedCondition;
      });
      if (option) conditionSelect.value = requestedCondition;
    }

    function restorePlan() {
      if (!state.plan) return;
      ["case_code", "condition", "start_date", "target"].forEach(function (name) {
        const field = planForm.elements.namedItem(name);
        if (field && state.plan[name]) field.value = state.plan[name];
      });
      updatePlanDates(state.plan.start_date);
    }

    function phaseLabel(value) {
      return {
        baseline: "خط الأساس",
        intervention: "تطبيق",
        generalization: "تعميم",
        maintenance: "صيانة",
      }[value] || value;
    }

    function assentLabel(value) {
      return {
        accepted: "موافق/متقبل",
        unclear: "غير واضح",
        declined: "رفض/توقف",
      }[value] || value;
    }

    function independenceRate(record) {
      const opportunities = Number(record.opportunities);
      const independent = Number(record.independent);
      if (!opportunities) return "—";
      return ((independent / opportunities) * 100).toLocaleString("ar", {
        maximumFractionDigits: 1,
      }) + "٪";
    }

    function renderRecords() {
      recordsBody.textContent = "";
      if (!state.records.length) {
        const row = document.createElement("tr");
        row.dataset.emptyRow = "";
        const cell = document.createElement("td");
        cell.colSpan = 11;
        cell.textContent = "لا توجد سجلات محفوظة.";
        row.appendChild(cell);
        recordsBody.appendChild(row);
      } else {
        state.records
          .slice()
          .sort(function (a, b) {
            return String(a.date).localeCompare(String(b.date));
          })
          .forEach(function (record) {
            const row = document.createElement("tr");
            const values = [
              displayDate(record.date),
              phaseLabel(record.phase),
              record.context,
              record.opportunities,
              record.independent,
              record.prompted,
              independenceRate(record),
              record.fidelity + "٪",
              record.burden,
              assentLabel(record.assent),
            ];
            values.forEach(function (value) {
              const cell = document.createElement("td");
              cell.textContent = String(value);
              row.appendChild(cell);
            });
            const action = document.createElement("td");
            const button = document.createElement("button");
            button.type = "button";
            button.className = "otb-button secondary";
            button.textContent = "حذف";
            button.dataset.deleteRecord = record.id;
            action.appendChild(button);
            row.appendChild(action);
            recordsBody.appendChild(row);
          });
      }
      const planName = state.plan ? " · " + state.plan.case_code : "";
      status.textContent =
        state.records.length.toLocaleString("ar") +
        " سجل محفوظ محليًا" +
        planName;
    }

    planForm.addEventListener("submit", function (event) {
      event.preventDefault();
      const fields = new FormData(planForm);
      state.plan = {
        case_code: String(fields.get("case_code") || "").trim(),
        condition: String(fields.get("condition") || ""),
        start_date: String(fields.get("start_date") || ""),
        target: String(fields.get("target") || "").trim(),
      };
      if (!writeState(state)) {
        setWarning(warning, "تعذر الحفظ المحلي في هذا المتصفح. يمكنك الطباعة دون حفظ.");
        return;
      }
      updatePlanDates(state.plan.start_date);
      setWarning(warning, "");
      renderRecords();
    });

    recordForm.addEventListener("submit", function (event) {
      event.preventDefault();
      if (!state.plan) {
        setWarning(warning, "أنشئ إطار المتابعة واحفظه أولًا.");
        planForm.scrollIntoView({ behavior: "smooth", block: "start" });
        return;
      }
      const fields = new FormData(recordForm);
      const opportunities = Number(fields.get("opportunities"));
      const independent = Number(fields.get("independent"));
      const prompted = Number(fields.get("prompted"));
      const fidelity = Number(fields.get("fidelity"));
      if (independent + prompted > opportunities) {
        setWarning(
          warning,
          "مجموع النجاح المستقل والنجاح مع تلميح لا يمكن أن يتجاوز عدد الفرص."
        );
        return;
      }
      if (fidelity < 0 || fidelity > 100) {
        setWarning(warning, "جودة التنفيذ يجب أن تكون بين 0 و100.");
        return;
      }
      const record = {
        id:
          String(Date.now()) +
          "-" +
          Math.random().toString(16).slice(2, 8),
        date: String(fields.get("date") || ""),
        phase: String(fields.get("phase") || ""),
        context: String(fields.get("context") || "").trim(),
        opportunities: opportunities,
        independent: independent,
        prompted: prompted,
        prompt_type: String(fields.get("prompt_type") || "").trim(),
        duration: String(fields.get("duration") || ""),
        frequency: String(fields.get("frequency") || ""),
        fidelity: fidelity,
        burden: String(fields.get("burden") || ""),
        assent: String(fields.get("assent") || ""),
        notes: String(fields.get("notes") || "").trim(),
      };
      state.records.push(record);
      if (!writeState(state)) {
        state.records.pop();
        setWarning(warning, "تعذر الحفظ المحلي؛ لم يضف السجل.");
        return;
      }
      setWarning(warning, "");
      recordForm.reset();
      renderRecords();
    });

    recordsBody.addEventListener("click", function (event) {
      const button = event.target.closest("[data-delete-record]");
      if (!button) return;
      if (!window.confirm("حذف هذا السجل من هذا الجهاز؟ لا يمكن استعادته بعد الحذف.")) {
        return;
      }
      state.records = state.records.filter(function (record) {
        return record.id !== button.dataset.deleteRecord;
      });
      writeState(state);
      renderRecords();
    });

    function safeCsvCell(value) {
      let text = String(value === null || value === undefined ? "" : value);
      if (/^[=+\-@]/.test(text)) text = "'" + text;
      return '"' + text.replace(/"/g, '""') + '"';
    }

    function download(content, type, filename) {
      const blob = new Blob([content], { type: type });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    }

    document
      .querySelector("[data-export-json]")
      .addEventListener("click", function () {
        download(
          JSON.stringify(state, null, 2),
          "application/json;charset=utf-8",
          "btr-icf-v254.json"
        );
      });

    document
      .querySelector("[data-export-csv]")
      .addEventListener("click", function () {
        const headers = [
          "case_code",
          "condition",
          "target",
          "date",
          "phase",
          "context",
          "opportunities",
          "independent",
          "prompted",
          "prompt_type",
          "duration",
          "frequency",
          "fidelity",
          "burden",
          "assent",
          "notes",
        ];
        const rows = [headers.map(safeCsvCell).join(",")];
        state.records.forEach(function (record) {
          const combined = Object.assign({}, state.plan || {}, record);
          rows.push(
            headers
              .map(function (key) {
                return safeCsvCell(combined[key]);
              })
              .join(",")
          );
        });
        download(
          "\ufeff" + rows.join("\n"),
          "text/csv;charset=utf-8",
          "btr-icf-v254.csv"
        );
      });

    document.querySelector("[data-print]").addEventListener("click", function () {
      window.print();
    });

    document
      .querySelector("[data-clear-records]")
      .addEventListener("click", function () {
        if (
          !window.confirm(
            "حذف الخطة وكل السجلات المحفوظة داخل هذا المتصفح؟ لا يمكن استعادتها بعد الحذف."
          )
        ) {
          return;
        }
        window.localStorage.removeItem(STORAGE_KEY);
        state = blankState();
        planForm.reset();
        recordForm.reset();
        updatePlanDates("");
        renderRecords();
        setWarning(warning, "حُذفت الخطة والسجلات المحلية نهائيًا من هذا المتصفح.");
      });

    restorePlan();
    renderRecords();
  }

  document.addEventListener("DOMContentLoaded", function () {
    setupConditionFilters();
    setupMonitoringMatrix();
  });
})();
