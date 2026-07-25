"use strict";

import("./institutional-contract-v220-integration.js").then(() => {
  const release = "2026.07.25-v220";
  document.documentElement.dataset.release = release;
  document.documentElement.dataset.institutionalContract = release;
  document.title = "عقد التقييم والسجل المهني v220 | منصة الصحة النفسية وذوي الاحتياجات الخاصة";
  const description = document.querySelector('meta[name="description"]');
  if (description) description.content = "منصة عربية مؤسسية لإدارة الحالات والجلسات والأدوات الاستكشافية والسجل المهني ضمن عقد v220 يضبط الغرض والمصادر والبيئات والصلاحية والحقوق والمراجعة وخطط المتابعة، دون تشخيص آلي أو فتح مواد محمية.";
  const productName = document.querySelector(".product-name");
  if (productName) productName.textContent = "عقد التقييم والسجل المهني v220";
  const heroEyebrow = document.querySelector(".hero .eyebrow");
  if (heroEyebrow) heroEyebrow.textContent = "منصة مؤسسية محلية لإدارة الحالات ومسارات التقييم";
  const heroTitle = document.getElementById("hero-title");
  if (heroTitle) heroTitle.textContent = "أنشئ حالة، ابنِ مخطط تقييم متعدد المصادر، ونفّذ الاستكشاف والسجل المهني في مسار واحد قابل للتتبع.";
  const heroLead = document.querySelector(".hero .lead");
  if (heroLead) heroLead.textContent = "إدارة حالات وجلسات متكررة، أدوات استكشافية أصلية، سجل زمني، مخططات تقييم متعددة المصادر والبيئات، وتوثيق مهني يفرض الغرض وصلاحية النتيجة والتكييفات والحدود والمراجعة. تحفظ البيانات محليًا داخل المتصفح بواسطة UID مستقل.";
  const heroCardTitle = document.querySelector(".hero-card > strong");
  if (heroCardTitle) heroCardTitle.textContent = "العقد المؤسسي المنشور v220";
}).catch((error) => {
  console.error("تعذر تحميل عقد التقييم المؤسسي v220", error);
});
