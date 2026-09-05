(() => {
  'use strict';
  const d=document,b=d.body;
  if(!b||b.dataset.ptShellReady==='true')return;
  b.dataset.ptShellReady='true';
  b.classList.add('pt-platform');
  if(!d.documentElement.lang)d.documentElement.lang='ar';
  if(!d.documentElement.dir)d.documentElement.dir='rtl';

  const url=(p='')=>`/${String(p).replace(/^\/+/, '')}`;
  const normalizePath=(value)=>new URL(value,location.origin).pathname.replace(/index\.html$/,'');
  const path=normalizePath(location.href);
  const title=(d.querySelector('h1')?.textContent||d.title||'منصة روافد').trim();
  const reduce=matchMedia('(prefers-reduced-motion: reduce)');
  const idle=(fn,timeout=1200)=>{
    if('requestIdleCallback' in window)return requestIdleCallback(fn,{timeout});
    return setTimeout(fn,0);
  };
  const make=(tag,a={},kids=[])=>{
    const n=d.createElement(tag);
    for(const[k,v]of Object.entries(a)){
      if(k==='class')n.className=v;
      else if(k==='text')n.textContent=v;
      else n.setAttribute(k,v);
    }
    for(const x of (Array.isArray(kids)?kids:[kids])){
      if(x)n.append(x instanceof Node?x:d.createTextNode(String(x)));
    }
    return n;
  };
  const primary=[['ابدأ هنا','start-here/'],['الموسوعة','encyclopedia/'],['الأدلة','care-guides/'],['ذوو الاحتياجات الخاصة','special-needs/'],['المكتبة','library/'],['الأدوات','daily-tools/'],['المجلة','magazine/'],['كل الأقسام','sections/']];

  const main=d.querySelector('main');
  if(main&&!main.id)main.id='main-content';
  if(main){
    const directChildren=b.children;
    let skip=null;
    for(let i=0;i<directChildren.length;i+=1){
      const node=directChildren[i];
      if(node.tagName==='A'&&(node.classList.contains('skip')||node.getAttribute('href')===`#${main.id}`)){skip=node;break;}
    }
    if(skip){skip.classList.add('pt-skip-link');skip.href=`#${main.id}`;}
    else if(!d.querySelector('.pt-skip-link'))b.prepend(make('a',{class:'pt-skip-link',href:`#${main.id}`,text:'تجاوز إلى المحتوى الرئيسي'}));
  }

  let oldHeader=null;
  for(const node of b.children){if(node.tagName==='HEADER'){oldHeader=node;break;}}
  let localNav=null;
  if(oldHeader){
    if(path==='/'){
      oldHeader.hidden=true;
      oldHeader.setAttribute('aria-hidden','true');
      oldHeader.dataset.replacedByPlatformShell='true';
    }else{
      const sourceNav=oldHeader.querySelector('nav');
      if(sourceNav){
        const links=[];
        for(const source of sourceNav.querySelectorAll('a[href]')){
          const label=source.textContent.trim();
          if(!label)continue;
          const a=make('a',{href:source.getAttribute('href'),text:label});
          try{if(normalizePath(a.href)===path)a.setAttribute('aria-current','page');}catch(_){}
          links.push(a);
          if(links.length===8)break;
        }
        if(links.length){
          localNav=make('nav',{class:'pt-local-context-nav','aria-label':'روابط القسم الحالي'},links);
          oldHeader.hidden=true;
          oldHeader.setAttribute('aria-hidden','true');
          oldHeader.dataset.replacedByPlatformShell='true';
        }else oldHeader.classList.add('pt-section-header');
      }else oldHeader.classList.add('pt-section-header');
    }
  }

  const globalNav=make('nav',{class:'pt-global-nav',id:'pt-global-nav','aria-label':'التنقل الرئيسي في منصة روافد'});
  for(const [label,p] of primary){
    const href=url(p),a=make('a',{href,text:label}),target=normalizePath(href);
    if(path===target||(target!=='/'&&path.startsWith(target)))a.setAttribute('aria-current','page');
    globalNav.append(a);
  }
  const brand=make('a',{class:'pt-global-brand',href:url(''),'aria-label':'العودة إلى الصفحة الرئيسية لمنصة روافد'},[
    make('img',{src:url('assets/brand/logo-mark.svg'),alt:'',width:'44',height:'44'}),
    make('span',{},[make('span',{text:'منصة روافد'}),make('small',{text:'العافية النفسية • الدمج • التمكين'})])
  ]);
  const menu=make('button',{class:'pt-menu-button',type:'button','aria-controls':'pt-global-nav','aria-expanded':'false','aria-label':'فتح قائمة التنقل',text:'القائمة'});
  const search=make('button',{class:'pt-search-button',type:'button','aria-label':'فتح البحث الذكي في منصة روافد','aria-haspopup':'dialog','aria-controls':'pt-platform-search'},[
    make('span',{text:'بحث'}),make('span',{'aria-hidden':'true',text:'⌕'})
  ]);
  const progress=make('div',{class:'pt-reading-progress','aria-hidden':'true'});
  const shell=make('header',{class:'pt-global-shell','data-platform-shell':'v5'},[
    make('div',{class:'pt-global-shell__inner'},[brand,globalNav,make('div',{class:'pt-global-actions'},[search,menu])]),progress
  ]);

  const trail=[make('a',{href:url(''),text:'الرئيسية'})];
  let parent=null;
  for(const [label,p] of primary){
    const target=normalizePath(url(p));
    if(target!=='/'&&path.startsWith(target)&&(!parent||target.length>parent[1].length))parent=[label,target,p];
  }
  if(parent&&path!==parent[1])trail.push(d.createTextNode(' / '),make('a',{href:url(parent[2]),text:parent[0]}));
  if(path!=='/')trail.push(d.createTextNode(' / '),make('span',{'aria-current':'page',text:title}));
  const context=make('div',{class:'pt-context-strip'},[
    make('div',{class:'pt-context-strip__inner'},[make('span',{class:'pt-breadcrumb-trail'},trail),make('span',{text:'معرفة موثوقة • لغة إنسانية • حدود مهنية واضحة'})])
  ]);

  let anchor=null;
  for(const node of b.children){if(!node.classList?.contains('pt-skip-link')){anchor=node;break;}}
  if(anchor){
    b.insertBefore(shell,anchor);
    b.insertBefore(context,anchor);
    if(localNav)b.insertBefore(localNav,anchor);
  }else{
    b.append(shell,context);
    if(localNav)b.append(localNav);
  }

  menu.addEventListener('click',()=>{
    const open=globalNav.classList.toggle('is-open');
    menu.setAttribute('aria-expanded',String(open));
    menu.setAttribute('aria-label',open?'إغلاق قائمة التنقل':'فتح قائمة التنقل');
  });
  const closeNav=()=>{globalNav.classList.remove('is-open');menu.setAttribute('aria-expanded','false');menu.setAttribute('aria-label','فتح قائمة التنقل');};
  globalNav.addEventListener('click',e=>{if(e.target.closest('a'))closeNav();});
  d.addEventListener('click',e=>{if(globalNav.classList.contains('is-open')&&!globalNav.contains(e.target)&&!menu.contains(e.target))closeNav();},{passive:true});

  let dialog=null,input=null;
  const ensureDialog=()=>{
    if(dialog)return dialog;
    const supported=typeof HTMLDialogElement!=='undefined';
    dialog=make(supported?'dialog':'div',{class:'pt-search-dialog',id:'pt-platform-search','aria-labelledby':'pt-search-title'});
    if(!supported){dialog.hidden=true;dialog.setAttribute('role','dialog');dialog.setAttribute('aria-modal','true');}
    const close=()=>{if(supported&&dialog.open)dialog.close();else dialog.hidden=true;search.focus();};
    const closeBtn=make('button',{class:'pt-icon-button',type:'button','aria-label':'إغلاق البحث',text:'إغلاق'});
    closeBtn.addEventListener('click',close);
    input=make('input',{type:'search',name:'q',maxlength:'300',autocomplete:'off',spellcheck:'false',placeholder:'ابحث عن موضوع أو حالة أو دليل أو أداة…','aria-label':'عبارة البحث'});
    dialog.append(make('div',{class:'pt-search-dialog__body'},[
      make('div',{class:'pt-search-dialog__head'},[
        make('div',{},[make('h2',{id:'pt-search-title',text:'ابحث في منصة روافد'}),make('p',{text:'اكتب ما تبحث عنه بلغة طبيعية للوصول إلى الصفحات والأدلة والأدوات الأقرب إلى مقصدك.'})]),closeBtn
      ]),
      make('form',{action:url('ai-search/'),method:'get',role:'search'},[input,make('button',{type:'submit',text:'بحث'})])
    ]));
    b.append(dialog);
    dialog.addEventListener('click',e=>{if(supported&&e.target===dialog)close();});
    return dialog;
  };
  const openSearch=()=>{
    const target=ensureDialog();
    if(typeof target.showModal==='function')target.showModal();else target.hidden=false;
    setTimeout(()=>input?.focus(),0);
  };
  search.addEventListener('click',openSearch);
  d.addEventListener('keydown',e=>{
    if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'){e.preventDefault();openSearch();}
    if(e.key==='Escape'&&dialog&&typeof dialog.showModal!=='function'&&!dialog.hidden){dialog.hidden=true;search.focus();}
  });

  let oldFooter=null;
  for(const node of b.children){if(node.tagName==='FOOTER'){oldFooter=node;break;}}
  if(oldFooter){oldFooter.hidden=true;oldFooter.setAttribute('aria-hidden','true');oldFooter.dataset.replacedByPlatformShell='true';}
  const governanceLinks=[
    make('a',{href:url('about/'),text:'عن روافد'}),
    make('a',{href:url('trust/'),text:'الثقة والمنهجية'}),
    make('a',{href:url('accessibility/'),text:'الإتاحة'}),
    make('a',{href:url('contact/'),text:'تواصل معنا'}),
    make('a',{href:url('copyright/'),text:'حقوق النشر'}),
    make('a',{href:url('sections/'),text:'دليل الأقسام'})
  ];
  b.append(make('footer',{class:'pt-global-footer','data-platform-footer':'v5'},[
    make('div',{class:'pt-global-footer__inner'},[
      make('p',{text:`© ${new Date().getFullYear()} منصة روافد. جميع الحقوق محفوظة.`}),
      make('nav',{'aria-label':'روابط الحوكمة والشفافية'},governanceLinks)
    ])
  ]));

  const top=make('button',{class:'pt-back-to-top',type:'button','aria-label':'العودة إلى أعلى الصفحة',title:'العودة إلى أعلى الصفحة',text:'↑'});
  top.addEventListener('click',()=>scrollTo({top:0,behavior:reduce.matches?'auto':'smooth'}));
  b.append(top);
  let ticking=false;
  const paint=()=>{
    const root=d.documentElement;
    const y=root.scrollTop||b.scrollTop;
    const max=Math.max(1,root.scrollHeight-root.clientHeight);
    progress.style.width=`${Math.min(100,Math.max(0,y/max*100))}%`;
    top.classList.toggle('is-visible',y>700);
    ticking=false;
  };
  addEventListener('scroll',()=>{if(!ticking){requestAnimationFrame(paint);ticking=true;}},{passive:true});

  const loadSecondaryAssets=()=>{
    if(!d.querySelector('link[data-pt-context-v3]'))d.head.append(make('link',{rel:'stylesheet',href:url('assets/platform/context-navigation-v3.css?v=3'),'data-pt-context-v3':'true'}));
    if(!d.querySelector('script[data-pt-discoverability-loader]'))d.head.append(make('script',{src:url('assets/platform/discoverability-cards.js?v=1.1.0'),async:'','data-pt-discoverability-loader':'v1.1'}));
  };

  const enhanceQuickInfo=()=>{
    if(!path.startsWith('/quick-info/')||!main)return;
    const hero=main.querySelector('.hero');
    const cover=hero?.querySelector('img.cover[src*="/assets/quick-info/"]');
    const heading=hero?.querySelector('h1');
    if(!cover||!heading)return;
    const pageTitle=heading.textContent.trim();
    cover.replaceWith(make('div',{class:'quick-info-rtl-cover',dir:'rtl',role:'img','aria-label':cover.getAttribute('alt')||pageTitle,'data-quick-info-cover':'rtl-v1'},[
      make('span',{class:'quick-info-rtl-cover__label',text:'معلومات سريعة'}),
      make('strong',{class:'quick-info-rtl-cover__title',text:pageTitle}),
      make('img',{class:'quick-info-rtl-cover__logo',src:url('assets/brand/logo-mark.svg'),alt:'',width:'92',height:'92','aria-hidden':'true'})
    ]));
  };

  const buildToc=()=>{
    if(!main||path==='/'||b.dataset.ptNoToc==='true'||d.querySelector('[data-pt-disable-toc],.tool-shell,.assessment-shell,.quiz-shell,.dashboard'))return;
    const headings=[];
    for(const h of main.querySelectorAll('h2')){
      if(h.textContent.trim().length>=4)headings.push(h);
      if(headings.length===14)break;
    }
    if(headings.length<4)return;
    const ids=new Set(Array.from(d.querySelectorAll('[id]'),node=>node.id));
    const links=headings.map((h,i)=>{
      if(!h.id){
        const base=h.textContent.toLowerCase().replace(/[\u064B-\u065F\u0670]/g,'').replace(/[^\u0600-\u06ff\w\s-]/g,'').trim().replace(/\s+/g,'-').replace(/-+/g,'-')||`section-${i+1}`;
        let id=base,n=2;
        while(ids.has(id))id=`${base}-${n++}`;
        h.id=id;ids.add(id);
      }
      h.classList.add('pt-toc-target');
      return make('a',{href:`#${h.id}`,text:h.textContent.trim()});
    });
    const toc=make('nav',{class:'pt-page-toc','aria-label':'فهرس محتوى الصفحة'},[
      make('div',{class:'pt-page-toc__head'},[make('strong',{text:'في هذه الصفحة'}),make('span',{text:`${links.length} محاور`})]),
      make('div',{class:'pt-page-toc__links'},links)
    ]);
    const article=main.querySelector('article')||main,hero=article.querySelector('.hero'),h1=article.querySelector('h1');
    if(hero?.nextSibling)article.insertBefore(toc,hero.nextSibling);
    else if(h1?.parentElement===article&&h1.nextSibling)article.insertBefore(toc,h1.nextSibling);
    else article.prepend(toc);
  };

  const hardenExternalLinks=()=>{
    if(!main)return;
    for(const a of main.querySelectorAll('a[href^="http"]')){
      try{
        if(new URL(a.href).origin!==location.origin){
          a.rel=`${a.rel||''} noopener noreferrer`.trim();
          if(!a.getAttribute('aria-label')&&!a.textContent.includes('يفتح'))a.title=a.title||'رابط خارجي';
        }
      }catch(_){}
    }
  };

  // Everything below is useful but non-critical for first paint and interaction readiness.
  idle(()=>{loadSecondaryAssets();enhanceQuickInfo();buildToc();hardenExternalLinks();paint();},1400);
})();
