"use strict";

(() => {
  const registry = window.PA_CONDITION_PATHWAYS;
  if (!registry || !Array.isArray(registry.conditions)) return;

  const escapeHtml = (value) => String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");

  const conditionBySlug = (slug) => registry.conditions.find((item) => item.slug === slug);
  const basePrefix = document.body.dataset.depth === "detail" ? "../../" : "../";
  const conditionsPrefix = document.body.dataset.depth === "detail" ? "../" : "";

  const rememberPathway = (condition) => {
    try {
      localStorage.setItem("pa-selected-condition-v1", JSON.stringify({
        slug: condition.slug,
        title: condition.title,
        selectedAt: new Date().toISOString(),
        registryVersion: registry.version
      }));
      const history = JSON.parse(localStorage.getItem("pa-condition-pathway-history-v1") || "[]");
      const next = [{ slug: condition.slug, title: condition.title, selectedAt: new Date().toISOString() }, ...history.filter((item) => item.slug !== condition.slug)].slice(0, 20);
      localStorage.setItem("pa-condition-pathway-history-v1", JSON.stringify(next));
    } catch (_) {
      // The pathway still opens when local storage is unavailable.
    }
  };

  const startPathway = (condition) => {
    rememberPathway(condition);
    window.location.href = `${basePrefix}?condition=${encodeURIComponent(condition.slug)}#workspace`;
  };

  const toolGroup = (title, tools) => `
    <section class="tool-group">
      <h3>${escapeHtml(title)}</h3>
      <div class="tools">${tools.map((tool) => `<span class="tool">${escapeHtml(tool)}</span>`).join("")}</div>
    </section>`;

  const list = (items) => `<ul class="list">${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`;

  const loadEducation = () => {
    if (document.body.dataset.depth !== "detail" || document.querySelector('[data-module="condition-education-v1"]')) return;
    const script = document.createElement("script");
    script.src = "../condition-education-v1.js?v=20260724-content1";
    script.defer = true;
    script.dataset.module = "condition-education-v1";
    script.addEventListener("error", () => console.error("Condition education module failed to load"), { once: true });
    document.head.appendChild(script);
  };

  const renderIndex = () => {
    const grid = document.getElementById("conditions-grid");
    const search = document.getElementById("condition-search");
    const teamFilter = document.getElementById("team-filter");
    if (!grid || !search || !teamFilter) return;

    const teams = [...new Set(registry.conditions.flatMap((item) => item.team))].sort((a, b) => a.localeCompare(b, "ar"));
    teams.forEach((team) => teamFilter.add(new Option(team, team)));

    const render = () => {
      const query = search.value.trim().toLowerCase();
      const team = teamFilter.value;
      const filtered = registry.conditions.filter((item) => {
        const haystack = `${item.title} ${item.summary} ${item.primary.join(" ")} ${item.supporting.join(" ")} ${item.team.join(" ")}`.toLowerCase();
        return (!query || haystack.includes(query)) && (!team || item.team.includes(team));
      });

      grid.innerHTML = filtered.length ? filtered.map((item, index) => `
        <article class="card">
          <p class="eyebrow">المسار ${index + 1}</p>
          <h3>${escapeHtml(item.title)}</h3>
          <p>${escapeHtml(item.summary)}</p>
          <div class="tag-row">${item.focus.slice(0, 4).map((tag) => `<span class="tag">${escapeHtml(tag)}</span>`).join("")}</div>
          <div class="actions">
            <a class="button secondary" href="${escapeHtml(item.slug)}/">فتح الدليل</a>
            <button class="button" type="button" data-start-condition="${escapeHtml(item.slug)}">بدء المسار</button>
          </div>
        </article>`).join("") : '<div class="empty">لا توجد حالات مطابقة للبحث الحالي.</div>';
    };

    search.addEventListener("input", render);
    teamFilter.addEventListener("change", render);
    render();
  };

  const renderDetail = () => {
    const root = document.getElementById("condition-root");
    const slug = document.body.dataset.condition;
    const condition = conditionBySlug(slug);
    if (!root || !condition) return;

    root.innerHTML = `
      <div class="breadcrumb"><a href="${conditionsPrefix}">مسارات الحالات</a> / ${escapeHtml(condition.title)}</div>
      <section class="hero">
        <p class="eyebrow">مسار تقييم مؤسسي متعدد التخصصات</p>
        <h1>${escapeHtml(condition.title)}</h1>
        <p class="lead">${escapeHtml(condition.summary)}</p>
        <div class="actions">
          <button class="button" type="button" data-start-condition="${escapeHtml(condition.slug)}">بدء مسار هذه الحالة</button>
          <a class="button secondary" href="${basePrefix}">فتح منصة التقييم والسجل المهني</a>
          <button class="button secondary" type="button" onclick="window.print()">طباعة الدليل</button>
        </div>
        <div class="notice">هذا المسار ينظم التقييم والتوثيق ولا يحول نتيجة منفردة إلى تشخيص. التطبيق الرسمي لأي مقياس معياري يتم بالنسخة الأصلية وبواسطة شخص مؤهل.</div>
      </section>

      <div class="layout">
        <main class="stack">
          <section class="panel">
            <h2>فريق التقييم المقترح</h2>
            ${list(condition.team)}
          </section>

          <section class="panel">
            <h2>حزمة المقاييس والفحوص</h2>
            <div class="tool-groups">
              ${toolGroup("المقاييس الأساسية", condition.primary)}
              ${toolGroup("المقاييس المساندة", condition.supporting)}
              ${toolGroup("الفحوص والخدمات الخارجية", condition.external)}
              ${toolGroup("مجالات التركيز", condition.focus)}
            </div>
          </section>

          <section class="panel">
            <h2>مراحل العمل المؤسسي</h2>
            <div class="stages">${registry.workflowStages.map((stage) => `<article class="stage">${escapeHtml(stage)}</article>`).join("")}</div>
          </section>

          <section class="panel">
            <h2>الكورس المختصر قبل التطبيق</h2>
            <div class="course">
              <article class="metric"><strong>1. الغرض</strong><span>صياغة سؤال إحالة وظيفي واضح.</span></article>
              <article class="metric"><strong>2. المصادر</strong><span>تحديد من يجيب وما البيئات المطلوبة.</span></article>
              <article class="metric"><strong>3. الاختيار</strong><span>مطابقة العمر واللغة والقدرة والغرض.</span></article>
              <article class="metric"><strong>4. التوثيق</strong><span>تسجيل النسخة والمنفذ والتكييفات والقيود.</span></article>
              <article class="metric"><strong>5. القرار</strong><span>أداة مكملة أو خطة دعم أو إغلاق المسار.</span></article>
            </div>
          </section>

          <section class="panel">
            <h2>مخرجات التقرير المطلوبة</h2>
            ${list(condition.deliverables)}
          </section>

          <section class="panel">
            <h2>قواعد القرار والمتابعة</h2>
            <ul class="list">
              <li>يستمر المسار عندما توجد فجوة مهمة في اللغة أو المعرفة أو التكيف أو الحس أو الحركة أو السلامة.</li>
              <li>يُطلب تقييم مكمل عندما تتعارض النتائج بين المصادر أو البيئات.</li>
              <li>يُغلق المسار عندما أُجيب سؤال الإحالة، ووُثقت القيود، وحُددت خطة دعم ومؤشرات متابعة.</li>
              <li>تُعطى الأولوية للإحالة الطبية أو مسار السلامة عند وجود خطر مباشر أو تدهور صحي أو فقدان مهارة.</li>
            </ul>
          </section>
        </main>

        <aside class="stack aside-card">
          <section class="panel">
            <h2>تنبيهات مهنية</h2>
            ${list(condition.alerts)}
          </section>
          <section class="panel">
            <h2>حفظ المسار داخل UID</h2>
            <p>عند الضغط على «بدء مسار هذه الحالة» تُحفظ الحالة المختارة محليًا ثم تُفتح منصة السجل المهني. بعد إنشاء الحالة يمكن إضافة كل تطبيق وتاريخ ونتيجة وملاحظة وخطوة تالية.</p>
            <button class="button" type="button" data-start-condition="${escapeHtml(condition.slug)}">الانتقال إلى السجل</button>
          </section>
          <section class="panel">
            <h2>المسارات المشتركة</h2>
            ${registry.commonDomains.slice(0, 6).map((domain) => `<p><strong>${escapeHtml(domain.name)}:</strong> ${escapeHtml(domain.tools.join("، "))}</p>`).join("")}
          </section>
        </aside>
      </div>`;

    loadEducation();
  };

  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-start-condition]");
    if (!button) return;
    const condition = conditionBySlug(button.dataset.startCondition);
    if (condition) startPathway(condition);
  });

  renderIndex();
  renderDetail();
})();
