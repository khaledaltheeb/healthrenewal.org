(()=>{
  'use strict';
  const brandName="منصة روافد";
  const tagline="للعافية النفسية والدمج والتمكين";
  const d=document;
  const idle=(fn,timeout=1200)=>{
    if('requestIdleCallback' in window){return requestIdleCallback(fn,{timeout});}
    return setTimeout(fn,0);
  };

  d.documentElement.dataset.brand="rawafid";

  // Keep the homepage WebMCP search available immediately without scanning the page.
  if((location.pathname==='/'||location.pathname==='/index.html')&&!d.getElementById('rawafid-agent-search')){
    const actions=d.querySelector('main .hero .actions,main .actions,.hero .actions');
    const host=actions?.parentElement||d.querySelector('main');
    if(host){
      const form=d.createElement('form');
      form.id='rawafid-agent-search';
      form.method='get';
      form.action='/encyclopedia/';
      form.setAttribute('role','search');
      form.setAttribute('aria-label','البحث في موسوعة روافد');
      form.setAttribute('toolname','rawafid_search_encyclopedia');
      form.setAttribute('tooldescription','يبحث في موسوعة روافد عن مفهوم أو حالة أو موضوع باستخدام عبارة يحددها المستخدم أو الوكيل.');
      form.style.cssText='display:flex;gap:.6rem;flex-wrap:wrap;align-items:center;margin:1rem 0 0;max-width:760px';

      const label=d.createElement('label');
      label.htmlFor='rawafid-agent-search-q';
      label.textContent='ابحث في الموسوعة';
      label.style.cssText='font-weight:800;flex-basis:100%';

      const input=d.createElement('input');
      input.id='rawafid-agent-search-q';
      input.name='q';
      input.type='search';
      input.required=true;
      input.maxLength=160;
      input.placeholder='مثال: القلق، ADHD، التربية الدامجة';
      input.setAttribute('toolparamdescription','الكلمة أو العبارة المطلوب البحث عنها داخل موسوعة روافد.');
      input.style.cssText='flex:1 1 260px;min-height:48px;padding:.65rem .8rem;border:1px solid #b8d6d3;border-radius:12px;font:inherit;background:#fff;color:inherit';

      const button=d.createElement('button');
      button.type='submit';
      button.className='button secondary';
      button.textContent='بحث';

      form.append(label,input,button);
      if(actions?.parentElement===host){actions.insertAdjacentElement('afterend',form);}
      else{host.prepend(form);}
    }
  }

  // Legacy visual normalization and optional declarative annotation are non-critical.
  idle(()=>{
    d.querySelectorAll('img[src*="logo-mark"],img[src*="rawafid-mark"]').forEach((image)=>{
      image.src="/assets/brand/logo-mark.svg";
      image.alt=`شعار ${brandName}`;
    });
    d.querySelectorAll('img[src*="logo-lockup"],img[src*="rawafid-logo"]').forEach((image)=>{
      image.src="/assets/brand/logo-lockup.svg";
      image.alt=`${brandName} — ${tagline}`;
    });
    d.querySelectorAll('[data-site-name]').forEach((node)=>{node.textContent=brandName;});
    d.querySelectorAll('[data-site-tagline]').forEach((node)=>{node.textContent=tagline;});

    const forms=d.forms?Array.from(d.forms):[];
    let index=0;
    for(const form of forms){
      if(form.hasAttribute('toolname')||form.hasAttribute('tooldescription')) continue;
      if(form.querySelector('input[type="password"],input[type="file"],input[autocomplete="cc-number"],input[autocomplete="current-password"],input[autocomplete="new-password"]')) continue;
      const signature=[form.id,form.className,form.getAttribute('role'),form.getAttribute('action')].filter(Boolean).join(' ').toLowerCase();
      const looksLikeSearch=/search|query|find|lookup|بحث|ابحث/.test(signature)||Boolean(form.querySelector('input[name="q"],input[name="query"],input[name="search"],input[type="search"]'));
      if(!looksLikeSearch) continue;
      const fields=Array.from(form.elements||[]).filter((field)=>field&&/^(INPUT|SELECT|TEXTAREA)$/.test(field.tagName)&&!['submit','button','reset'].includes(field.type));
      if(fields.some((field)=>field.required&&!field.name)) continue;
      index+=1;
      form.setAttribute('toolname',`rawafid_search_form_${index}`);
      form.setAttribute('tooldescription','يجهّز نموذج البحث في منصة روافد للوصول إلى محتوى معرفي ذي صلة. يتطلب الإرسال النهائي من المستخدم ما لم يكن النموذج نفسه يقرر خلاف ذلك.');
      for(const field of fields){
        if(!field.name||field.hasAttribute('toolparamdescription')) continue;
        const label=field.labels?.[0];
        if(label) continue;
        const description=field.getAttribute('aria-label')||field.getAttribute('placeholder')||`قيمة الحقل ${field.name}`;
        field.setAttribute('toolparamdescription',description);
      }
    }
  });

  const modelContext=d.modelContext;
  if(!modelContext?.registerTool||window.__rawafidWebMcpBootstrapped) return;
  window.__rawafidWebMcpBootstrapped=true;

  const controller=new AbortController();
  window.__rawafidWebMcpController=controller;
  const register=(tool)=>{
    try{Promise.resolve(modelContext.registerTool(tool,{signal:controller.signal})).catch(()=>{});}catch(_error){}
  };

  register({
    name:'rawafid_get_page_context',
    title:'قراءة سياق الصفحة',
    description:'يعيد معلومات منظمة ومختصرة عن صفحة روافد الحالية، بما في ذلك العنوان والرابط والوصف والعنوان الرئيسي، من دون تعديل الصفحة أو التنقل.',
    inputSchema:{type:'object',properties:{},additionalProperties:false},
    annotations:{readOnlyHint:true,untrustedContentHint:false,consequentialHint:false},
    execute:async()=>{
      const canonical=d.querySelector('link[rel="canonical"]')?.href||location.href;
      const description=d.querySelector('meta[name="description"]')?.content||'';
      const headings=Array.from(d.querySelectorAll('main h1,main h2')).slice(0,12).map((node)=>node.textContent?.trim()).filter(Boolean);
      return {url:location.href,canonical,title:d.title,language:d.documentElement.lang||'ar',direction:d.documentElement.dir||'rtl',description,mainHeading:d.querySelector('main h1,h1')?.textContent?.trim()||'',headings};
    }
  });

  register({
    name:'rawafid_find_on_page',
    title:'البحث داخل الصفحة',
    description:'يبحث داخل النص الظاهر في صفحة روافد الحالية ويعيد مقتطفات قصيرة حول العبارة المطلوبة من دون تعديل الصفحة.',
    inputSchema:{type:'object',properties:{query:{type:'string',minLength:1,maxLength:160,description:'الكلمة أو العبارة المطلوب العثور عليها داخل الصفحة الحالية.'}},required:['query'],additionalProperties:false},
    annotations:{readOnlyHint:true,untrustedContentHint:true,consequentialHint:false},
    execute:async({query})=>{
      const needle=String(query||'').trim();
      if(!needle) return {query:'',matches:[]};
      const text=((d.querySelector('main')||d.body)?.innerText||'').replace(/\s+/g,' ').trim();
      const haystack=text.toLocaleLowerCase();
      const target=needle.toLocaleLowerCase();
      const matches=[];
      let cursor=0;
      while(matches.length<5){
        const position=haystack.indexOf(target,cursor);
        if(position<0) break;
        matches.push(text.slice(Math.max(0,position-120),Math.min(text.length,position+target.length+180)).trim());
        cursor=position+Math.max(target.length,1);
      }
      return {query:needle,count:matches.length,matches};
    }
  });

  register({
    name:'rawafid_search_knowledge',
    title:'البحث في موسوعة روافد',
    description:'ينقل المستخدم إلى بحث موسوعة روافد باستخدام عبارة بحث محددة. استخدمه عندما يريد المستخدم العثور على مفهوم أو حالة أو موضوع داخل المنصة.',
    inputSchema:{type:'object',properties:{query:{type:'string',minLength:1,maxLength:160,description:'عبارة البحث المطلوب استخدامها في موسوعة روافد.'}},required:['query'],additionalProperties:false},
    annotations:{readOnlyHint:false,untrustedContentHint:false,consequentialHint:false},
    execute:async({query})=>{
      const value=String(query||'').trim();
      if(!value) return {status:'invalid',message:'query is required'};
      const target=new URL('/encyclopedia/',location.origin);
      target.searchParams.set('q',value);
      location.assign(target.href);
      return {status:'navigating',url:target.href};
    }
  });

  register({
    name:'rawafid_open_section',
    title:'فتح قسم في روافد',
    description:'ينقل المستخدم إلى أحد الأقسام الرئيسية المعروفة في منصة روافد باستخدام معرّف قسم ثابت وآمن.',
    inputSchema:{type:'object',properties:{section:{type:'string',enum:['home','start','encyclopedia','special_needs','library','research','care_guides','daily_tools','learning_paths','team_partners','api'],description:'القسم الرئيسي المطلوب فتحه.'}},required:['section'],additionalProperties:false},
    annotations:{readOnlyHint:false,untrustedContentHint:false,consequentialHint:false},
    execute:async({section})=>{
      const routes={home:'/',start:'/start/',encyclopedia:'/encyclopedia/',special_needs:'/special-needs/',library:'/library/',research:'/research/',care_guides:'/care-guides/',daily_tools:'/daily-tools/',learning_paths:'/learning-paths/',team_partners:'/specialists-partners/',api:'/api/'};
      const path=routes[section];
      if(!path) return {status:'invalid',message:'Unknown section'};
      const target=new URL(path,location.origin).href;
      location.assign(target);
      return {status:'navigating',url:target};
    }
  });
})();
