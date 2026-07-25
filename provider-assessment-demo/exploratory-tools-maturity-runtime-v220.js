"use strict";
(() => {
  const root = window.PA_EXPLORATORY_V220 = window.PA_EXPLORATORY_V220 || {};
  root.version = "220.1";
  root.specs = root.specs || {};
  root.references = [
    {title:"WHO International Classification of Functioning, Disability and Health (ICF)",url:"https://www.who.int/standards/classifications/international-classification-of-functioning-disability-and-health"},
    {title:"WHO Disability Assessment Schedule 2.0",url:"https://www.who.int/standards/classifications/international-classification-of-functioning-disability-and-health/who-disability-assessment-schedule"},
    {title:"Washington Group/UNICEF Child Functioning Module",url:"https://data.unicef.org/resources/module-child-functioning/"},
    {title:"W3C Web Content Accessibility Guidelines (WCAG) 2.2",url:"https://www.w3.org/TR/WCAG22/"}
  ];
  root.scales = {
    capacity:[["stable","يظهر بصورة مستقرة أو مناسبة للمهمة والسياق",0],["supported","يظهر جزئيًا أو يحتاج تذكيرًا أو تكييفًا",1],["limited","لا يظهر بصورة مستقرة أو يحد المشاركة بوضوح",2],["unknown","غير معروف أو لم يُلاحظ بما يكفي",null]],
    quality:[["adequate","متوفر ومناسب بصورة ثابتة غالبًا",0],["partial","متوفر جزئيًا أو غير ثابت",1],["missing","غير متوفر أو غير مناسب ويحد المشاركة",2],["unknown","غير معروف أو لم يُتحقق منه",null]],
    frequency:[["rare","لا يظهر أو يظهر نادرًا",0],["sometimes","يظهر أحيانًا أو في ظروف محددة",1],["frequent","متكرر ويؤثر في الأداء أو المشاركة",2],["unknown","غير معروف أو لم تُجمع ملاحظات كافية",null]],
    support:[["little","أثر محدود أو لا يحتاج دعمًا إضافيًا",0],["moderate","أثر متوسط ويحتاج تكييفًا أو دعمًا منظمًا",1],["substantial","أثر كبير أو يحتاج دعمًا مباشرًا متكررًا",2],["unknown","غير معروف أو لم يُجرّب دعم كافٍ",null]],
    safety:[["no","لا يوجد خطر مباشر أو علامة عاجلة الآن",0],["concern","توجد مخاوف تستلزم مراجعة قريبة ومسار سلامة",2],["immediate","يوجد خطر مباشر أو وشيك أو علامة عاجلة",5]]
  };
  root.limits = [
    "هذه أداة استكشافية أصلية غير معيارية وغير تشخيصية.",
    "لا تستخدم النتيجة منفردة لتقرير تشخيص أو أهلية أو علاج أو تقييد.",
    "تفسر الإجابات مع سؤال الإحالة والتاريخ والسياق والفرص والتكييفات ومصادر معلومات متعددة.",
    "الإشارة المرتفعة تستدعي معلومات إضافية أو مراجعة مناسبة، ولا تثبت اضطرابًا."
  ];
  root.register = (batch) => {
    for (const [id,spec] of Object.entries(batch || {})) {
      if (root.specs[id]) throw new Error(`Duplicate v220 tool spec: ${id}`);
      root.specs[id] = spec;
    }
  };
})();
