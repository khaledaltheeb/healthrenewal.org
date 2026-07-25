"use strict";

import { data, esc } from "./institutional-contract-v220-core.js";

export const sourceOptions = [
  ["self","الشخص نفسه"],["caregiver","الأسرة أو مقدم الرعاية"],["teacher","المعلم/المدرسة"],["provider","مقدم خدمة"],["observation","ملاحظة مباشرة"],["records","سجلات وتقارير"],["medical","مصدر صحي عند الحاجة"]
];
export const settingOptions = [["home","المنزل"],["school","المدرسة/التدريب"],["clinic","العيادة/المركز"],["community","المجتمع"],["work","العمل"],["remote","عن بعد"]];

export function checkboxGrid(name, options) {
  return `<div class="institutional-v220-check-grid">${options.map(([value,label])=>`<label class="institutional-v220-check"><input type="checkbox" name="${name}" value="${value}"><span>${label}</span></label>`).join("")}</div>`;
}

export function buildPlanForm() {
  const professionalCategories = [...new Set(data.professional.map((item) => item.category))].sort((a,b)=>a.localeCompare(b,"ar"));
  return `<form method="dialog" id="institutional-plan-form">
    <div class="dialog-heading"><div><p class="eyebrow">نسخة قابلة للتتبع داخل UID الحالي</p><h2 id="institutional-plan-title">إنشاء مخطط تقييم</h2></div><button class="icon-button" value="cancel" aria-label="إغلاق">×</button></div>
    <input type="hidden" name="basePlanId">
    <div class="form-grid">
      <label class="field"><span>الحالة</span><select name="caseId" required></select></label>
      <label class="field"><span>استخدام القرار</span><select name="decisionUse" required><option value="">اختر</option><option value="exploration">استكشاف منظم</option><option value="support_planning">تخطيط دعم</option><option value="progress_monitoring">متابعة تغير</option><option value="comprehensive_evaluation">تقييم شامل بواسطة فريق مؤهل</option><option value="transition">انتقال واستعداد للحياة/العمل</option><option value="safety_review">مراجعة سلامة</option></select></label>
      <label class="field"><span>حالة المخطط</span><select name="planStatus" required><option value="draft">مسودة</option><option value="ready">جاهز للمراجعة</option><option value="active">قيد التنفيذ</option><option value="review_due">مراجعة مستحقة</option><option value="closed">مغلق</option></select></label>
      <label class="field"><span>موعد المراجعة</span><input type="date" name="reviewDate" required></label>
    </div>
    <label class="field"><span>سؤال الإحالة أو القرار</span><textarea name="referralQuestion" rows="3" minlength="15" maxlength="1200" required placeholder="ما القرار الذي ستدعمه المعلومات؟ وما الذي لن تستخدم النتيجة لإثباته؟"></textarea></label>
    <label class="field"><span>النتائج الوظيفية المستهدفة</span><textarea name="targetOutcomes" rows="3" minlength="10" maxlength="1200" required placeholder="مشاركة، تواصل، استقلال، حضور، أمان، تعلم، انتقال..."></textarea></label>
    <fieldset class="institutional-v220-fieldset"><legend>مصادر المعلومات</legend>${checkboxGrid("sources", sourceOptions)}<p class="institutional-v220-source-note">يفضل مصدران مستقلان على الأقل، مع تفسير أي اختلاف بينهما بدل دمجهما آليًا.</p></fieldset>
    <fieldset class="institutional-v220-fieldset"><legend>البيئات والسياقات</legend>${checkboxGrid("settings", settingOptions)}</fieldset>
    <div class="form-grid">
      <label class="field"><span>اللغة والثقافة والمترجم</span><textarea name="languageContext" rows="3" maxlength="900" required placeholder="لغة الشخص، لغة الأداة، اللهجة، المترجم، وأي أثر ثقافي"></textarea></label>
      <label class="field"><span>التكييفات والإتاحة</span><textarea name="accessibility" rows="3" maxlength="900" required placeholder="وسيلة التواصل، دعم بصري، فواصل، جهاز وصول، مكان هادئ..."></textarea></label>
      <label class="field"><span>الموافقة</span><select name="consentStatus" required><option value="">اختر</option><option value="documented">موثقة</option><option value="verbal">شفوية موثقة في السجل</option><option value="not_applicable">غير منطبقة مع توضيح</option><option value="missing">غير مكتملة</option></select></label>
      <label class="field"><span>مشاركة/موافقة الشخص</span><select name="assentStatus" required><option value="">اختر</option><option value="documented">موثقة</option><option value="supported">مشاركة مدعومة</option><option value="not_applicable">غير منطبقة مع توضيح</option><option value="not_obtained">لم تحصل</option></select></label>
      <label class="field"><span>مراجعة السلامة</span><select name="safetyReview" required><option value="">اختر</option><option value="clear">لا خطر مباشر معروف</option><option value="plan_exists">توجد مخاوف وخطة سلامة</option><option value="urgent">خطر مباشر؛ توقف واتبع المسار المحلي</option><option value="not_reviewed">لم تراجع</option></select></label>
      <label class="field"><span>مالك المخطط/المراجع</span><input name="reviewer" minlength="3" maxlength="160" required placeholder="الدور أو الاسم المهني"></label>
    </div>
    <div class="form-grid">
      <label class="field"><span>الأدوات الاستكشافية</span><select class="institutional-v220-multiselect" name="explorerIds" multiple>${data.explorers.map((tool)=>`<option value="${esc(tool.id)}">${esc(tool.title)}</option>`).join("")}</select></label>
      <label class="field"><span>فئات السجل المهني</span><select class="institutional-v220-multiselect" name="professionalCategories" multiple>${professionalCategories.map((category)=>`<option value="${esc(category)}">${esc(category)}</option>`).join("")}</select></label>
    </div>
    <label class="field"><span>مبرر الاختيار وتسلسل التطبيق</span><textarea name="rationale" rows="4" minlength="15" maxlength="1800" required placeholder="لماذا اختير كل مصدر أو أداة؟ وما ترتيبها؟ ومتى يتوقف المسار أو يتغير؟"></textarea></label>
    <label class="field"><span>الحدود والاستبعادات</span><textarea name="exclusions" rows="3" maxlength="1200" required placeholder="ما الذي لا يمكن استنتاجه؟ وما العوامل التي قد تحد صلاحية التفسير؟"></textarea></label>
    <label class="field"><span>خطة المتابعة والتواصل</span><textarea name="followUp" rows="3" maxlength="1200" required placeholder="من يراجع؟ متى؟ كيف تعرض النتائج للشخص والأسرة؟ وما الإجراء التالي؟"></textarea></label>
    <div id="institutional-plan-quality" class="institutional-v220-score" aria-live="polite"></div>
    <div class="dialog-actions"><button class="button ghost" value="cancel">إلغاء</button><button class="button primary" value="default" type="submit">حفظ الإصدار</button></div>
  </form>`;
}
