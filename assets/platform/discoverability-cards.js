(() => {
  'use strict';

  const doc = document;
  const normalize = (path) => {
    const cleaned = String(path || '/').replace(/index\.html$/, '');
    return cleaned.endsWith('/') || cleaned.includes('.') ? cleaned : `${cleaned}/`;
  };
  const currentPath = normalize(location.pathname);

  if (!doc.querySelector('link[data-pt-context-v3]')) {
    const contextStyles = doc.createElement('link');
    contextStyles.rel = 'stylesheet';
    contextStyles.href = '/assets/platform/context-navigation-v3.css?v=3';
    contextStyles.dataset.ptContextV3 = 'true';
    doc.head.append(contextStyles);
  }

  const catalog = {
    '/sections/': {
      eyebrow: 'بوابات مؤسسية وخدمات مساندة',
      title: 'صفحات أساسية يجب أن تبقى ظاهرة',
      intro: 'وصول مباشر إلى أدلة الأسرة والبحث والتواصل والحوكمة والمصادر والفريق، مع وصف واضح لغرض كل صفحة.',
      cards: [
        ['الأسر ومقدمو الرعاية', 'دليل الأسرة للرعاية والدعم', '64 دليلًا للحالات النمائية والعصبية والحركية والحسية والوراثية، مع خطوات عملية وخطط متابعة وأدوات للأسرة.', '/family-guide/'],
        ['اكتشاف المحتوى', 'البحث الذكي في المنصة', 'ابحث باللغة الطبيعية داخل محتوى المنصة للوصول إلى الصفحات الأقرب إلى السؤال أو الحالة أو الدليل المطلوب.', '/ai-search/'],
        ['تواصل رسمي', 'تواصل معنا', 'القناة الرسمية للاستفسارات والشراكات والأبحاث والتصحيحات العلمية والدعم التقني والإتاحة والخصوصية.', '/contact/'],
        ['شفافية المصادر', 'سجل المصادر ومسارات التكامل', 'بوابة شفافة للمصادر المسجلة وواجهات البيانات ومسارات التكامل والتحقق من مرجعية المحتوى.', '/source-registry/'],
        ['تعاون مهني', 'الفريق والشركاء ذوو الاختصاص', 'صفحة تعريفية بالفريق والشراكات المهنية ومسارات التعاون المرتبطة بالمنصة.', '/team-and-partners/'],
        ['إتاحة رقمية', 'الإتاحة وخطة التوافق', 'إفادة الإتاحة، وسائل الاستخدام الميسر، وآلية الإبلاغ عن عائق يمنع الوصول إلى المحتوى أو الوظائف.', '/accessibility/']
      ]
    },
    '/learning-paths/': {
      eyebrow: 'تطبيق وتعاون',
      title: 'فرص التدريب والتعاون المؤسسي',
      intro: 'مسار واضح للجهات والمختصين والطلاب الراغبين في التدريب أو التعاون أو المساهمة المنهجية.',
      cards: [
        ['فرص وتعاون', 'فرص التدريب والتعاون', 'استعرض مجالات التدريب والتعاون المؤسسي والمساهمة العلمية وشروط التواصل والمعلومات التي يجب تجهيزها.', '/learning-paths/opportunities/']
      ]
    },
    '/provider-assessment-demo/': {
      eyebrow: 'التطوير المهني',
      title: 'التدريب والسجل المهني',
      intro: 'بوابتان لمقدمي الخدمة والمراكز: تدريب منظم على التقييم، وسجل مهني للمقاييس والفحوص ومسارات الاستخدام المسؤول.',
      cards: [
        ['تدريب مهني', 'أكاديمية التقييم المهني', 'تدريب المراكز ومقدمي الخدمة على مبادئ التقييم متعدد المصادر، اختيار الأدوات، التوثيق، وحدود التفسير.', '/provider-assessment-demo/training/'],
        ['سجل مهني', 'السجل المهني للمقاييس والفحوص', 'واجهة منظمة للمقاييس والفحوص والمجالات المهنية، مع ضوابط الاستخدام والترخيص والتفسير المسؤول.', '/provider-assessment-demo/professional-console.html']
      ]
    },
    '/special-needs/': {
      eyebrow: 'أدلة متخصصة',
      title: 'تقنيات مساعدة ودليل حالة موسع',
      intro: 'وصول مباشر إلى منظومة اختيار التقنيات المساعدة وإلى دليل متكامل لمتلازمة برادر ويلي عبر مراحل الحياة.',
      cards: [
        ['تقنيات مساعدة', 'التقنيات المساعدة', 'دليل الاختيار والتقييم والتجربة والأمان والتدريب والصيانة، مع مسارات أخلاقية وتعليم مستمر.', '/special-needs/assistive-technology/'],
        ['دليل حالة', 'متلازمة برادر ويلي', 'دليل للأسرة والمختصين حول الصحة والتغذية والسلوك والتعليم والمتابعة والدعم عبر مراحل الحياة.', '/special-needs/conditions/prader-willi-syndrome/']
      ]
    },
    '/special-needs/assistive-technology/': {
      eyebrow: 'مسارات تطبيقية ومهنية',
      title: 'أدلة التقنيات المساعدة المتخصصة',
      intro: 'مسارات عملية تساعد الأسرة والمختص ومقدم الخدمة على الاختيار الأخلاقي، تقييم الابتكار، التدريب، والتعليم المستمر.',
      cards: [
        ['اختيار وتقييم', 'قائمة فحص اختيار التقنية المساعدة', 'خطوات منظمة للتقييم والتجربة والملاءمة والأمان والصيانة قبل اعتماد أي تقنية أو جهاز.', '/special-needs/assistive-technology/selection-checklist/'],
        ['تدريب المستخدم', 'مسار التدريب في التقنيات المساعدة', 'خطة تدريب للمستخدم والأسرة والفريق لضمان الاستخدام الفعلي والآمن ومراجعة النتائج.', '/special-needs/assistive-technology/training/'],
        ['أخلاقيات وجودة', 'أخلاقيات وجودة الخدمة', 'إطار لتقديم خدمات تحترم الحقوق والاختيار والخصوصية والكفاءة المهنية والمتابعة.', '/special-needs/assistive-technology/ethics-and-service/'],
        ['ابتكار مسؤول', 'مراجعة ابتكارات التقنيات المساعدة', 'بوابة علمية وأخلاقية لفحص الادعاءات والجدوى والمخاطر قبل التجربة أو التوصية أو النشر.', '/special-needs/assistive-technology/innovation-review/'],
        ['تعليم مستمر', 'التعليم المستمر والتحقق من الدورات', 'دليل للتحقق من الدورات والمزودين ومسارات التعليم المستمر المرتبطة بالممارسة المهنية.', '/special-needs/assistive-technology/continuing-education/']
      ]
    }
  };

  const config = catalog[currentPath];
  if (!config) return;

  const ensureStyles = () => {
    if (doc.getElementById('pt-discoverability-card-styles')) return;
    const style = doc.createElement('style');
    style.id = 'pt-discoverability-card-styles';
    style.textContent = `
      .pt-discovery-section{width:min(var(--pt-content,1180px),calc(100% - 28px));margin:2.75rem auto 0;padding:clamp(1.15rem,3vw,2rem);border:1px solid var(--pt-line,#c9dfdc);border-radius:22px;background:linear-gradient(145deg,rgba(242,250,248,.96),rgba(255,255,255,.98));box-shadow:var(--pt-shadow,0 12px 34px rgba(10,72,71,.10))}
      .pt-discovery-section__eyebrow{margin:0 0 .25rem;color:var(--pt-accent,#8b315c);font-size:.88rem;font-weight:900}
      .pt-discovery-section h2{margin:0;font-size:clamp(1.55rem,3.2vw,2.35rem)}
      .pt-discovery-section__intro{margin:.55rem 0 0;color:var(--pt-muted,#567176)}
      .pt-discovery-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,245px),1fr));gap:1rem;margin-top:1.35rem}
      .pt-discovery-card{display:flex;flex-direction:column;min-height:225px;padding:1.15rem;border:1px solid var(--pt-line,#c9dfdc);border-radius:18px;background:#fff;box-shadow:0 8px 22px rgba(10,72,71,.07)}
      .pt-discovery-card__tag{align-self:flex-start;padding:.2rem .65rem;border:1px solid #a9d5d0;border-radius:999px;background:#f2faf8;color:#064a47;font-size:.78rem;font-weight:900}
      .pt-discovery-card h3{margin:.7rem 0 .35rem;font-size:1.18rem}
      .pt-discovery-card p{flex:1;margin:0 0 1rem;color:var(--pt-muted,#567176)}
      .pt-discovery-card a{align-self:flex-start;min-height:44px;display:inline-flex;align-items:center;padding:.55rem .85rem;border-radius:10px;background:var(--pt-brand,#075f5b);color:#fff!important;font-weight:900;text-decoration:none}
      .pt-discovery-card a:hover{background:var(--pt-brand-strong,#064a47);color:#fff!important}
      @media(max-width:640px){.pt-discovery-section{width:min(100% - 18px,var(--pt-content,1180px))}.pt-discovery-card{min-height:0}}
    `;
    doc.head.append(style);
  };

  const render = () => {
    const main = doc.querySelector('main');
    if (!main || main.querySelector('[data-pt-discoverability-cards="v1"]')) return false;
    ensureStyles();

    const section = doc.createElement('section');
    section.className = 'pt-discovery-section';
    section.dataset.ptDiscoverabilityCards = 'v1';
    const titleId = `pt-discovery-${currentPath.replace(/[^a-z0-9]+/gi, '-').replace(/^-|-$/g, '') || 'root'}`;
    section.setAttribute('aria-labelledby', titleId);

    const eyebrow = doc.createElement('p');
    eyebrow.className = 'pt-discovery-section__eyebrow';
    eyebrow.textContent = config.eyebrow;
    const heading = doc.createElement('h2');
    heading.id = titleId;
    heading.textContent = config.title;
    const intro = doc.createElement('p');
    intro.className = 'pt-discovery-section__intro';
    intro.textContent = config.intro;
    const grid = doc.createElement('div');
    grid.className = 'pt-discovery-grid';

    config.cards.forEach(([tag, title, description, href]) => {
      const card = doc.createElement('article');
      card.className = 'pt-discovery-card';
      const badge = doc.createElement('span');
      badge.className = 'pt-discovery-card__tag';
      badge.textContent = tag;
      const cardTitle = doc.createElement('h3');
      cardTitle.textContent = title;
      const text = doc.createElement('p');
      text.textContent = description;
      const link = doc.createElement('a');
      link.href = href;
      link.textContent = 'فتح الصفحة ←';
      card.append(badge, cardTitle, text, link);
      grid.append(card);
    });

    section.append(eyebrow, heading, intro, grid);
    main.append(section);
    return true;
  };

  const scheduleRender = () => {
    render();
    [50, 250, 750, 1500, 3000, 6000].forEach((delay) => window.setTimeout(render, delay));
  };

  if (doc.readyState === 'loading') {
    doc.addEventListener('DOMContentLoaded', scheduleRender, { once: true });
  } else {
    scheduleRender();
  }
  window.addEventListener('load', scheduleRender, { once: true });

  const observer = new MutationObserver(() => {
    if (!doc.querySelector('[data-pt-discoverability-cards="v1"]')) render();
  });
  observer.observe(doc.documentElement, { childList: true, subtree: true });
  window.setTimeout(() => observer.disconnect(), 20000);
  window.addEventListener('pagehide', () => observer.disconnect(), { once: true });
})();
