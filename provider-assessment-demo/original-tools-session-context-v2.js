"use strict";

(() => {
  const RELEASE = "2026.07.25-context.2";
  const STORE_VERSION = "3";
  const idsKey = `pa-demo-identities-v${STORE_VERSION}`;
  const activeKey = `pa-demo-active-v${STORE_VERSION}`;
  let pendingContext = null;

  const read = (key, fallback = null) => {
    try {
      const raw = localStorage.getItem(key);
      return raw === null ? fallback : JSON.parse(raw);
    } catch (_) {
      return fallback;
    }
  };

  const activeIdentity = () => {
    const identities = read(idsKey, {});
    const active = read(activeKey, null);
    if (active?.role === "provider" && identities?.[active.username]) return identities[active.username];
    return identities?.__visitor__ || null;
  };

  const storeKey = (uid) => `pa-demo-store-v${STORE_VERSION}:${uid}`;
  const esc = (value) => String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;");

  const contextMarkup = () => `
    <fieldset class="question-card session-context-card" data-original-session-context>
      <legend><span>س</span>سياق التطبيق للمقارنة اللاحقة</legend>
      <p class="muted">تُستخدم هذه البيانات لتحديد ما إذا كانت الجلسات المتكررة قابلة للمقارنة. لا تغير النتيجة ولا تنتج درجة معيارية.</p>
      <div class="form-grid two-columns">
        <label class="field"><span>المجيب أو مصدر المعلومات</span><select name="sessionRespondent" required>
          <option value="">اختر</option><option value="self">الشخص نفسه</option><option value="parent">والد أو مقدم رعاية</option><option value="teacher">المعلم أو المدرسة</option><option value="provider">مقدم الخدمة</option><option value="multiple">مصادر متعددة</option>
        </select></label>
        <label class="field"><span>بيئة التطبيق</span><select name="sessionSetting" required>
          <option value="">اختر</option><option value="home">المنزل</option><option value="school">المدرسة</option><option value="clinic">المركز أو العيادة</option><option value="remote">عن بُعد</option><option value="community">المجتمع</option><option value="other">أخرى</option>
        </select></label>
        <label class="field"><span>طريقة جمع المعلومات</span><select name="sessionAdministrationMode" required>
          <option value="">اختر</option><option value="questionnaire">استبانة موجهة</option><option value="interview">مقابلة</option><option value="observation">ملاحظة</option><option value="mixed">مصادر مختلطة</option>
        </select></label>
        <label class="field"><span>مستوى الدعم أو التكييف</span><select name="sessionSupportLevel" required>
          <option value="">اختر</option><option value="none">دون تكييف إضافي</option><option value="usual">الدعم المعتاد</option><option value="modified">تكييف مختلف عن المعتاد</option><option value="unknown">غير موثق</option>
        </select></label>
      </div>
      <label class="field"><span>ملاحظة سياقية اختيارية</span><textarea name="sessionContextNote" rows="2" maxlength="600" placeholder="تغيرات في البيئة أو النوم أو الصحة أو اللغة أو الدعم"></textarea></label>
    </fieldset>`;

  const inject = () => {
    const form = document.getElementById("assessment-form");
    const review = form?.querySelector(".review-fields");
    if (!form || !review || form.querySelector("[data-original-session-context]")) return;
    review.insertAdjacentHTML("beforebegin", contextMarkup());
  };

  const capture = (event) => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement) || form.id !== "assessment-form") return;
    const data = new FormData(form);
    pendingContext = {
      respondent: String(data.get("sessionRespondent") || ""),
      setting: String(data.get("sessionSetting") || ""),
      administrationMode: String(data.get("sessionAdministrationMode") || ""),
      supportLevel: String(data.get("sessionSupportLevel") || ""),
      note: String(data.get("sessionContextNote") || "").trim(),
      contractVersion: "pa-original-session-context-v2",
      capturedAt: new Date().toISOString()
    };
    queueMicrotask(attachToLatestSession);
  };

  const attachToLatestSession = () => {
    if (!pendingContext) return;
    const identity = activeIdentity();
    if (!identity?.uid) return;
    const key = storeKey(identity.uid);
    const store = read(key, null);
    if (!store?.cases) return;
    const sessions = store.cases.flatMap((caseRecord) => (caseRecord.sessions || []).map((session) => ({ caseRecord, session })));
    const candidate = sessions
      .filter(({ session }) => !session.administrationContext)
      .sort((a, b) => new Date(b.session.completedAt) - new Date(a.session.completedAt))[0];
    if (!candidate || Date.now() - new Date(candidate.session.completedAt).getTime() > 15000) return;
    candidate.session.administrationContext = { ...pendingContext };
    candidate.session.contextRecordedByUid = identity.uid;
    candidate.session.contextRecordedByRole = identity.role;
    candidate.caseRecord.updatedAt = new Date().toISOString();
    store.updatedAt = candidate.caseRecord.updatedAt;
    localStorage.setItem(key, JSON.stringify(store));
    pendingContext = null;
    window.dispatchEvent(new CustomEvent("pa-original-session-context-saved", { detail: { sessionId: candidate.session.sessionId } }));
  };

  document.addEventListener("submit", capture, true);
  const target = document.getElementById("assessment-content") || document.body;
  new MutationObserver(inject).observe(target, { childList: true, subtree: true });
  inject();
  window.PA_ORIGINAL_SESSION_CONTEXT = { release: RELEASE, attachToLatestSession };
  document.documentElement.dataset.originalSessionContextRelease = RELEASE;
})();
