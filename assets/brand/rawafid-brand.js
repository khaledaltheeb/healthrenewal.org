(()=>{
  const brandName="منصة روافد";
  const tagline="للعافية النفسية والدمج والتمكين";

  document.documentElement.dataset.brand="rawafid";
  document.querySelectorAll('img[src*="logo-mark"],img[src*="rawafid-mark"]').forEach((image)=>{
    image.src="/assets/brand/logo-mark.svg";
    image.alt=`شعار ${brandName}`;
  });
  document.querySelectorAll('img[src*="logo-lockup"],img[src*="rawafid-logo"]').forEach((image)=>{
    image.src="/assets/brand/logo-lockup.svg";
    image.alt=`${brandName} — ${tagline}`;
  });
  document.querySelectorAll('[data-site-name]').forEach((node)=>{node.textContent=brandName;});
  document.querySelectorAll('[data-site-tagline]').forEach((node)=>{node.textContent=tagline;});

  // Declarative WebMCP: annotate only clearly non-sensitive search forms.
  const searchForms=[...document.querySelectorAll('form')].filter((form)=>{
    if(form.hasAttribute('toolname')||form.hasAttribute('tooldescription')) return false;
    if(form.querySelector('input[type="password"],input[type="file"],input[autocomplete="cc-number"],input[autocomplete="current-password"],input[autocomplete="new-password"]')) return false;
    const signature=[form.id,form.className,form.getAttribute('role'),form.getAttribute('action')]
      .filter(Boolean).join(' ').toLowerCase();
    if(/search|query|find|lookup|بحث|ابحث/.test(signature)) return true;
    return Boolean(form.querySelector('input[name="q"],input[name="query"],input[name="search"],input[type="search"]'));
  });

  searchForms.forEach((form,index)=>{
    const fields=[...form.querySelectorAll('input,select,textarea')].filter((field)=>field.type!=="submit"&&field.type!=="button"&&field.type!=="reset");
    if(fields.some((field)=>field.required&&!field.name)) return;
    form.setAttribute('toolname',`rawafid_search_form_${index+1}`);
    form.setAttribute('tooldescription','يجهّز نموذج البحث في منصة روافد للوصول إلى محتوى معرفي ذي صلة. يتطلب الإرسال النهائي من المستخدم ما لم يكن النموذج نفسه يقرر خلاف ذلك.');
    fields.forEach((field)=>{
      if(!field.name||field.hasAttribute('toolparamdescription')) return;
      const label=field.id?document.querySelector(`label[for="${CSS.escape(field.id)}"]`):null;
      if(label) return;
      const description=field.getAttribute('aria-label')||field.getAttribute('placeholder')||`قيمة الحقل ${field.name}`;
      field.setAttribute('toolparamdescription',description);
    });
  });

  const modelContext=document.modelContext;
  if(!modelContext?.registerTool||window.__rawafidWebMcpBootstrapped) return;
  window.__rawafidWebMcpBootstrapped=true;

  const controller=new AbortController();
  window.__rawafidWebMcpController=controller;
  const register=(tool)=>{
    try{
      Promise.resolve(modelContext.registerTool(tool,{signal:controller.signal})).catch(()=>{});
    }catch(_error){}
  };

  register({
    name:'rawafid_get_page_context',
    title:'قراءة سياق الصفحة',
    description:'يعيد معلومات منظمة ومختصرة عن صفحة روافد الحالية، بما في ذلك العنوان والرابط والوصف والعنوان الرئيسي، من دون تعديل الصفحة أو التنقل.',
    inputSchema:{type:'object',properties:{},additionalProperties:false},
    annotations:{readOnlyHint:true,untrustedContentHint:false,consequentialHint:false},
    execute:async()=>{
      const canonical=document.querySelector('link[rel="canonical"]')?.href||location.href;
      const description=document.querySelector('meta[name="description"]')?.content||'';
      const headings=[...document.querySelectorAll('main h1,main h2')].slice(0,12).map((node)=>node.textContent?.trim()).filter(Boolean);
      return {
        url:location.href,
        canonical,
        title:document.title,
        language:document.documentElement.lang||'ar',
        direction:document.documentElement.dir||'rtl',
        description,
        mainHeading:document.querySelector('main h1,h1')?.textContent?.trim()||'',
        headings
      };
    }
  });

  register({
    name:'rawafid_find_on_page',
    title:'البحث داخل الصفحة',
    description:'يبحث داخل النص الظاهر في صفحة روافد الحالية ويعيد مقتطفات قصيرة حول العبارة المطلوبة من دون تعديل الصفحة.',
    inputSchema:{
      type:'object',
      properties:{
        query:{type:'string',minLength:1,maxLength:160,description:'الكلمة أو العبارة المطلوب العثور عليها داخل الصفحة الحالية.'}
      },
      required:['query'],
      additionalProperties:false
    },
    annotations:{readOnlyHint:true,untrustedContentHint:true,consequentialHint:false},
    execute:async({query})=>{
      const needle=String(query||'').trim();
      if(!needle) return {query:'',matches:[]};
      const text=((document.querySelector('main')||document.body)?.innerText||'').replace(/\s+/g,' ').trim();
      const haystack=text.toLocaleLowerCase();
      const target=needle.toLocaleLowerCase();
      const matches=[];
      let cursor=0;
      while(matches.length<5){
        const position=haystack.indexOf(target,cursor);
        if(position<0) break;
        const start=Math.max(0,position-120);
        const end=Math.min(text.length,position+target.length+180);
        matches.push(text.slice(start,end).trim());
        cursor=position+Math.max(target.length,1);
      }
      return {query:needle,count:matches.length,matches};
    }
  });

  register({
    name:'rawafid_search_knowledge',
    title:'البحث في موسوعة روافد',
    description:'ينقل المستخدم إلى بحث موسوعة روافد باستخدام عبارة بحث محددة. استخدمه عندما يريد المستخدم العثور على مفهوم أو حالة أو موضوع داخل المنصة.',
    inputSchema:{
      type:'object',
      properties:{
        query:{type:'string',minLength:1,maxLength:160,description:'عبارة البحث المطلوب استخدامها في موسوعة روافد.'}
      },
      required:['query'],
      additionalProperties:false
    },
    annotations:{readOnlyHint:false,untrustedContentHint:false,consequentialHint:false},
    execute:async({query})=>{
      const value=String(query||'').trim();
      if(!value) return {status:'invalid',message:'query is required'};
      const url=new URL('/encyclopedia/',location.origin);
      url.searchParams.set('q',value);
      location.assign(url.href);
      return {status:'navigating',url:url.href};
    }
  });

  register({
    name:'rawafid_open_section',
    title:'فتح قسم في روافد',
    description:'ينقل المستخدم إلى أحد الأقسام الرئيسية المعروفة في منصة روافد باستخدام معرّف قسم ثابت وآمن.',
    inputSchema:{
      type:'object',
      properties:{
        section:{
          type:'string',
          enum:['home','start','encyclopedia','special_needs','library','research','care_guides','daily_tools','learning_paths','team_partners','api'],
          description:'القسم الرئيسي المطلوب فتحه.'
        }
      },
      required:['section'],
      additionalProperties:false
    },
    annotations:{readOnlyHint:false,untrustedContentHint:false,consequentialHint:false},
    execute:async({section})=>{
      const routes={
        home:'/',
        start:'/start/',
        encyclopedia:'/encyclopedia/',
        special_needs:'/special-needs/',
        library:'/library/',
        research:'/research/',
        care_guides:'/care-guides/',
        daily_tools:'/daily-tools/',
        learning_paths:'/learning-paths/',
        team_partners:'/specialists-partners/',
        api:'/api/'
      };
      const path=routes[section];
      if(!path) return {status:'invalid',message:'Unknown section'};
      const url=new URL(path,location.origin).href;
      location.assign(url);
      return {status:'navigating',url};
    }
  });
})();
