"use strict";

(() => {
  const academy = window.PA_TRAINING_ACADEMY;
  if (!academy || !Array.isArray(academy.modules)) return;

  const esc = value => String(value ?? "").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#039;");
  const get = (key, fallback) => { try { const raw = localStorage.getItem(key); return raw === null ? fallback : JSON.parse(raw); } catch (_) { return fallback; } };
  const set = (key, value) => { try { localStorage.setItem(key, JSON.stringify(value)); return true; } catch (_) { return false; } };
  const activeIdentity = () => {
    const identities = get("pa-demo-identities-v3", {});
    const active = get("pa-demo-active-v3", null);
    if (active?.role === "provider" && identities?.[active.username]) return identities[active.username];
    if (identities?.__visitor__) return identities.__visitor__;
    const guestKey = "pa-training-guest-uid-v1";
    let uid = get(guestKey, null);
    if (!uid) { uid = `UID-TRAIN-${Date.now().toString(36).toUpperCase()}`; set(guestKey, uid); }
    return { uid, username: "training-guest", role: "visitor" };
  };
  const identity = activeIdentity();
  const progressKey = `pa-training-progress-v1:${identity.uid}`;
  let progress = get(progressKey, { ownerUid: identity.uid, academyVersion: academy.version, modules: {}, createdAt: new Date().toISOString() });
  if (!progress || progress.ownerUid !== identity.uid) progress = { ownerUid: identity.uid, academyVersion: academy.version, modules: {}, createdAt: new Date().toISOString() };
  const save = () => { progress.updatedAt = new Date().toISOString(); set(progressKey, progress); };

  const els = {
    uid: document.getElementById("training-uid"), completed: document.getElementById("completed-count"), average: document.getElementById("average-score"), hours: document.getElementById("estimated-hours"), modules: document.getElementById("training-modules"), search: document.getElementById("training-search"), level: document.getElementById("training-level"), dialog: document.getElementById("module-dialog"), dialogBody: document.getElementById("module-dialog-body"), certificate: document.getElementById("academy-certificate"), certificateUid: document.getElementById("certificate-uid"), certificateDate: document.getElementById("certificate-date"), live: document.getElementById("training-live")
  };
  let currentModuleId = "";

  const moduleProgress = id => progress.modules[id] || { checked: [], answers: {}, score: null, completed: false };
  const completionPercent = id => {
    const module = academy.modules.find(item => item.id === id);
    const state = moduleProgress(id);
    if (!module) return 0;
    const checklistPart = module.checklist.length ? state.checked.length / module.checklist.length : 0;
    const quizPart = state.score === null ? 0 : Math.min(state.score / 100, 1);
    return Math.round(((checklistPart + quizPart) / 2) * 100);
  };
  const completedModules = () => academy.modules.filter(item => moduleProgress(item.id).completed);
  const announce = text => { if (!els.live) return; els.live.textContent = ""; requestAnimationFrame(() => { els.live.textContent = text; }); };

  const renderStats = () => {
    const completed = completedModules();
    const scored = academy.modules.map(item => moduleProgress(item.id).score).filter(value => typeof value === "number");
    els.uid.textContent = identity.uid;
    els.completed.textContent = `${completed.length}/${academy.modules.length}`;
    els.average.textContent = scored.length ? `${Math.round(scored.reduce((a,b) => a+b,0) / scored.length)}%` : "—";
    els.hours.textContent = "8–10";
    const allDone = completed.length === academy.modules.length;
    els.certificate.classList.toggle("visible", allDone);
    if (allDone) {
      els.certificateUid.textContent = identity.uid;
      els.certificateDate.textContent = new Intl.DateTimeFormat("ar-JO", { dateStyle: "long" }).format(new Date());
    }
  };

  const renderModules = () => {
    const query = els.search.value.trim().toLowerCase();
    const level = els.level.value;
    const modules = academy.modules.filter(item => (!level || item.level === level) && (!query || `${item.title} ${item.objectives.join(" ")} ${item.audience.join(" ")}`.toLowerCase().includes(query)));
    els.modules.innerHTML = modules.length ? modules.map(item => {
      const state = moduleProgress(item.id);
      const percent = completionPercent(item.id);
      return `<article class="module-card"><div class="meta"><span class="tag${state.completed ? " complete" : ""}">${state.completed ? "مكتمل" : item.level}</span><span class="tag">${esc(item.duration)}</span></div><h2>${esc(item.title)}</h2><p>${esc(item.objectives[0])}</p><p><strong>الفئة:</strong> ${esc(item.audience.join("، "))}</p><div class="progress-track" role="progressbar" aria-label="نسبة تقدم المساق" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${percent}"><div class="progress-bar" style="width:${percent}%"></div></div><p>${percent}% من متطلبات المساق</p><div class="module-actions"><button class="button" type="button" data-open-module="${esc(item.id)}">${state.completed ? "مراجعة المساق" : percent ? "متابعة المساق" : "بدء المساق"}</button></div></article>`;
    }).join("") : '<div class="panel">لا توجد مساقات مطابقة.</div>';
    renderStats();
  };

  const renderModuleDialog = id => {
    const module = academy.modules.find(item => item.id === id);
    if (!module) return;
    currentModuleId = id;
    const state = moduleProgress(id);
    els.dialogBody.innerHTML = `<div class="dialog-head"><div><p class="eyebrow">${esc(module.level)} — ${esc(module.duration)}</p><h2>${esc(module.title)}</h2><p>${esc(module.audience.join("، "))}</p></div><button class="close" type="button" data-close-module aria-label="إغلاق">×</button></div><section class="objectives"><h3>أهداف التعلم</h3><ul>${module.objectives.map(item => `<li>${esc(item)}</li>`).join("")}</ul></section>${module.lessons.map((lesson,index) => `<section class="lesson"><p class="eyebrow">الدرس ${index+1}</p><h3>${esc(lesson.title)}</h3><p>${esc(lesson.text)}</p><ul>${lesson.bullets.map(item => `<li>${esc(item)}</li>`).join("")}</ul></section>`).join("")}<section class="checklist"><h3>قائمة التحقق العملية</h3><div class="checks">${module.checklist.map((item,index) => `<label class="check"><input type="checkbox" data-check-index="${index}" ${state.checked.includes(index) ? "checked" : ""}><span>${esc(item)}</span></label>`).join("")}</div></section><form id="module-quiz" class="quiz"><h3>اختبار المساق</h3>${module.quiz.map((item,qIndex) => `<fieldset class="quiz-item"><legend><strong>${qIndex+1}. ${esc(item.question)}</strong></legend><div class="options">${item.options.map((option,oIndex) => `<label class="option"><input type="radio" name="q${qIndex}" value="${oIndex}" ${String(state.answers?.[qIndex]) === String(oIndex) ? "checked" : ""} required><span>${esc(option)}</span></label>`).join("")}</div></fieldset>`).join("")}<button class="button" type="submit">تصحيح الاختبار وحفظ التقدم</button></form><section id="module-result" class="result ${state.completed ? "pass" : state.score === null ? "" : "retry"}" ${state.score === null ? "hidden" : ""}><h3>${state.completed ? "اكتمل المساق" : "تحتاج مراجعة"}</h3><p>النتيجة: <strong>${state.score ?? 0}%</strong>. حد الاجتياز ${academy.passingScore}% مع إكمال قائمة التحقق.</p></section>`;
    els.dialog.showModal ? els.dialog.showModal() : els.dialog.setAttribute("open", "");
  };

  const saveChecklist = () => {
    if (!currentModuleId) return;
    const state = moduleProgress(currentModuleId);
    state.checked = [...els.dialogBody.querySelectorAll('[data-check-index]:checked')].map(input => Number(input.dataset.checkIndex));
    progress.modules[currentModuleId] = state;
    save(); renderModules();
  };

  const gradeQuiz = event => {
    event.preventDefault();
    const module = academy.modules.find(item => item.id === currentModuleId);
    if (!module || !event.currentTarget.reportValidity()) return;
    const fd = new FormData(event.currentTarget);
    const answers = {};
    let correct = 0;
    module.quiz.forEach((item,index) => { const answer = Number(fd.get(`q${index}`)); answers[index] = answer; if (answer === item.correct) correct += 1; });
    const score = Math.round((correct / module.quiz.length) * 100);
    const state = moduleProgress(module.id);
    state.answers = answers;
    state.score = score;
    state.checked = [...els.dialogBody.querySelectorAll('[data-check-index]:checked')].map(input => Number(input.dataset.checkIndex));
    state.completed = score >= academy.passingScore && state.checked.length === module.checklist.length;
    state.completedAt = state.completed ? new Date().toISOString() : null;
    progress.modules[module.id] = state;
    save(); renderModules(); renderModuleDialog(module.id);
    announce(state.completed ? "تم إكمال المساق وحفظ النتيجة." : "تم حفظ النتيجة. أكمل قائمة التحقق وراجع الإجابات.");
  };

  const exportProgress = () => {
    const blob = new Blob([JSON.stringify({ schema: "pa-training-progress-v1", ownerUid: identity.uid, academyVersion: academy.version, progress }, null, 2)], { type: "application/json;charset=utf-8" });
    const url = URL.createObjectURL(blob); const a = document.createElement("a"); a.href = url; a.download = `training-progress-${identity.uid}.json`; a.click(); setTimeout(() => URL.revokeObjectURL(url), 500);
  };

  document.addEventListener("click", event => {
    const openButton = event.target.closest("[data-open-module]");
    if (openButton) renderModuleDialog(openButton.dataset.openModule);
    if (event.target.closest("[data-close-module]")) els.dialog.close ? els.dialog.close() : els.dialog.removeAttribute("open");
    if (event.target.closest("#export-training-progress")) exportProgress();
    if (event.target.closest("#print-certificate")) window.print();
  });
  els.dialogBody.addEventListener("change", event => { if (event.target.matches('[data-check-index]')) saveChecklist(); });
  els.dialogBody.addEventListener("submit", event => { if (event.target.id === "module-quiz") gradeQuiz(event); });
  els.search.addEventListener("input", renderModules);
  els.level.addEventListener("change", renderModules);
  renderModules();
})();
