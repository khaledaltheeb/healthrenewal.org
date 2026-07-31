import finalWorker from './index-v10-final.js';

const BUILD_VERSION='10.2.1';
const JSON_HEADERS={'content-type':'application/json; charset=utf-8'};
const MAX_BODY_BYTES=64_000;
const MAX_MESSAGE_LENGTH=3_000;
const SPECIALIST_MESSAGE_PATH=/^\/v1\/specialist\/conversations\/([a-z0-9-]+)\/messages$/i;

export default {
  async scheduled(event,env,ctx){
    if(typeof finalWorker.scheduled==='function')return finalWorker.scheduled(event,env,ctx);
  },

  async fetch(request,env,ctx){
    const url=new URL(request.url);
    const origin=request.headers.get('origin')||'';
    const cors=corsHeaders(origin,env);
    const specialistMessageMatch=url.pathname.match(SPECIALIST_MESSAGE_PATH);

    if(request.method==='POST'&&specialistMessageMatch){
      return handleSpecialistMessage(request,env,ctx,cors,specialistMessageMatch[1]);
    }

    if(request.method==='GET'&&url.pathname==='/health'&&url.searchParams.get('deep')==='1'){
      if(!bootstrapAuthorized(request,env))return json({error:'forbidden',message:'الفحص العميق مقيد بالتشغيل.'},403,cors);
      return withProductionVersion(await finalWorker.fetch(request,env,ctx),origin,env);
    }

    if(request.method==='GET'&&url.pathname==='/v1/admin/email-provider-status'){
      const sessionRequest=new Request(new URL('/v1/auth/session',request.url),{
        method:'GET',
        headers:request.headers,
        redirect:'error'
      });
      const sessionResponse=await finalWorker.fetch(sessionRequest,env,ctx);
      const session=await sessionResponse.clone().json().catch(()=>({}));
      if(!sessionResponse.ok)return sessionResponse;
      if(!['owner','admin'].includes(session.user?.role))return json({error:'forbidden',message:'لا تملك الصلاحية المطلوبة.'},403,cors);

      const headers=new Headers(request.headers);
      headers.set('x-bootstrap-key',String(env.ADMIN_API_KEY||''));
      const deepRequest=new Request(new URL('/health?deep=1',request.url),{method:'GET',headers,redirect:'error'});
      const deepResponse=await finalWorker.fetch(deepRequest,env,ctx);
      const deep=await deepResponse.json().catch(()=>({}));
      const provider=deep.emailProvider||{};
      return json({
        ok:provider.authValid===true,
        provider:'resend',
        configured:provider.configured===true,
        authValid:provider.authValid===true,
        access:provider.access||'unknown',
        code:provider.code||'unknown',
        manualRecoveryAvailable:Boolean(deep.capabilities?.manualRecovery)
      },provider.authValid===true?200:503,cors);
    }

    const response=await finalWorker.fetch(request,env,ctx);
    if(request.method==='GET'&&url.pathname==='/health')return withProductionVersion(response,origin,env);
    return response;
  }
};

async function handleSpecialistMessage(request,env,ctx,cors,conversationId){
  try{
    const actor=await requireSpecialistIdentity(request,env);
    await rateLimit(request,env,'specialist-message-v10-production',100,actor.id);
    const id=validId(conversationId,'معرف المحادثة');
    const conversation=await env.DB.prepare(`
      SELECT id,reference_id,provider_id,visitor_email,status
      FROM conversations
      WHERE id=? AND provider_id=?
      LIMIT 1
    `).bind(id,actor.provider_id).first();
    if(!conversation)fail('المحادثة غير موجودة.',404,'conversation_not_found');
    if(conversation.status!=='open')fail('المحادثة مغلقة.',409,'conversation_closed');

    const body=await parseJson(request);
    const message=cleanString(body.body,MAX_MESSAGE_LENGTH,true);
    const idempotencyKey=cleanString(request.headers.get('idempotency-key')||body.idempotencyKey,120,true);
    if(!/^[a-z0-9-]{12,120}$/i.test(idempotencyKey))fail('مفتاح منع التكرار غير صالح.',400,'invalid_idempotency_key');

    const existing=await env.DB.prepare(`
      SELECT message_id FROM specialist_message_requests
      WHERE idempotency_key=? AND provider_id=? AND conversation_id=?
      LIMIT 1
    `).bind(idempotencyKey,actor.provider_id,id).first();
    if(existing)return json({ok:true,messageId:existing.message_id,duplicate:true},200,cors);

    const now=new Date().toISOString();
    const messageId=crypto.randomUUID();
    const visitorAccess=randomToken(32);
    const visitorHash=await sha256(visitorAccess);
    const visitorTokenId=crypto.randomUUID();
    const visitorTokenExpiresAt=new Date(Date.now()+90*24*60*60*1000).toISOString();

    try{
      await env.DB.batch([
        env.DB.prepare(`
          INSERT INTO messages (id,conversation_id,sender_role,body,created_at)
          VALUES (?,?,'specialist',?,?)
        `).bind(messageId,id,message,now),
        env.DB.prepare(`
          UPDATE conversations SET updated_at=?,last_message_at=?
          WHERE id=? AND provider_id=? AND status='open'
        `).bind(now,now,id,actor.provider_id),
        env.DB.prepare(`
          INSERT INTO specialist_message_requests
          (idempotency_key,provider_id,conversation_id,message_id,created_at)
          VALUES (?,?,?,?,?)
        `).bind(idempotencyKey,actor.provider_id,id,messageId,now),
        env.DB.prepare(`
          INSERT INTO conversation_tokens
          (id,conversation_id,role,token_hash,expires_at,created_at)
          VALUES (?,?,'visitor',?,?,?)
        `).bind(visitorTokenId,id,visitorHash,visitorTokenExpiresAt,now)
      ]);
    }catch(error){
      const replay=await env.DB.prepare(`
        SELECT message_id FROM specialist_message_requests
        WHERE idempotency_key=? AND provider_id=? AND conversation_id=?
        LIMIT 1
      `).bind(idempotencyKey,actor.provider_id,id).first().catch(()=>null);
      if(replay)return json({ok:true,messageId:replay.message_id,duplicate:true},200,cors);
      throw error;
    }

    await identityAudit(env,actor.id,'message_created',actor.id,id,{
      messageId,
      deliveryLink:'visitor_fragment_token',
      visitorTokenExpiresAt
    });

    if(conversation.visitor_email){
      const link=portalLink(env.PORTAL_BASE_URL,id,visitorAccess,'visitor');
      ctx.waitUntil(
        sendEmail(env,{
          to:[conversation.visitor_email],
          subject:`رد من المختص — ${conversation.reference_id}`,
          html:emailLayout('وصل رد جديد',
            `<p>وصل رد جديد في المحادثة ${escapeHtml(conversation.reference_id)}.</p><p><a href="${escapeHtml(link)}">فتح المحادثة والرد</a></p><p>الرابط خاص، وينتهي تلقائيًا.</p>`),
          idempotencyKey:`identity-message/${messageId}`
        }).then(()=>identityAudit(env,actor.id,'visitor_reply_email_sent',actor.id,id,{messageId}))
          .catch(error=>identityAudit(env,actor.id,'visitor_reply_email_failed',actor.id,id,{messageId,error:safeError(error)}).catch(()=>{}))
      );
    }

    return json({ok:true,messageId,createdAt:now,visitorAccessIssued:true},201,cors);
  }catch(error){
    console.error('specialist_message_v10_production_error',safeError(error));
    const status=Number(error.status)||500;
    return json({
      error:error.code||'internal_error',
      message:status===500?'حدث خطأ داخلي.':error.message
    },status,cors);
  }
}

async function requireSpecialistIdentity(request,env){
  if(!env.DB||!env.RATE_LIMIT_SALT)fail('خدمة الهوية غير جاهزة.',503,'identity_unavailable');
  const raw=bearerToken(request);
  const hash=await sha256(raw);
  const now=new Date().toISOString();
  const actor=await env.DB.prepare(`
    SELECT s.id AS session_id,s.token_hash,s.expires_at,s.ip_hash,s.user_agent_hash,
      u.id,u.provider_id,u.role,u.status,p.status AS provider_status
    FROM identity_sessions s
    JOIN identity_users u ON u.id=s.user_id
    LEFT JOIN providers_private p ON p.provider_id=u.provider_id
    WHERE s.token_hash=? AND s.revoked_at IS NULL AND s.expires_at>?
      AND u.status='active'
    LIMIT 1
  `).bind(hash,now).first();
  if(!actor||!constantTimeEqual(hash,actor.token_hash))fail('انتهت جلسة الدخول أو لم تعد صالحة.',401,'session_expired');
  if(!actor.provider_id)fail('الحساب غير مرتبط بملف مهني.',403,'provider_not_linked');
  if(actor.provider_status!=='active')fail('الملف المهني غير نشط.',403,'provider_inactive');

  const userAgentHash=await sha256(`${request.headers.get('user-agent')||''}|${env.RATE_LIMIT_SALT}`);
  if(!constantTimeEqual(userAgentHash,actor.user_agent_hash)){
    await env.DB.prepare(`UPDATE identity_sessions SET revoked_at=? WHERE id=? AND revoked_at IS NULL`).bind(now,actor.session_id).run();
    fail('تغيرت بيئة الجلسة. سجّل الدخول من جديد.',401,'session_binding_mismatch');
  }
  if(String(env.SESSION_BIND_IP||'').toLowerCase()==='strict'){
    const ipHash=await sha256(`${requestIp(request)}|${env.RATE_LIMIT_SALT}`);
    if(!constantTimeEqual(ipHash,actor.ip_hash)){
      await env.DB.prepare(`UPDATE identity_sessions SET revoked_at=? WHERE id=? AND revoked_at IS NULL`).bind(now,actor.session_id).run();
      fail('تغير عنوان الاتصال. سجّل الدخول من جديد.',401,'session_ip_mismatch');
    }
  }
  await env.DB.prepare(`UPDATE identity_sessions SET last_used_at=? WHERE id=?`).bind(now,actor.session_id).run();
  return actor;
}

async function rateLimit(request,env,scope,limit,identity=''){
  if(!env.DB||!env.RATE_LIMIT_SALT)fail('خدمة الحماية غير جاهزة.',503,'rate_limit_unavailable');
  const key=`${scope}:${await sha256(`${scope}|${identity||requestIp(request)}|${env.RATE_LIMIT_SALT}`)}`;
  const bucket=new Date().toISOString().slice(0,13);
  await env.DB.prepare(`
    INSERT INTO rate_limits (key,bucket,count,updated_at)
    VALUES (?,?,1,?)
    ON CONFLICT(key,bucket) DO UPDATE SET count=count+1,updated_at=excluded.updated_at
  `).bind(key,bucket,new Date().toISOString()).run();
  const row=await env.DB.prepare(`SELECT count FROM rate_limits WHERE key=? AND bucket=?`).bind(key,bucket).first();
  if(Number(row?.count||0)>limit)fail('تم تجاوز عدد المحاولات المسموح مؤقتًا.',429,'rate_limited');
}

async function parseJson(request){
  if(!(request.headers.get('content-type')||'').includes('application/json'))fail('يجب إرسال البيانات بصيغة JSON.',415,'unsupported_media_type');
  const declared=Number(request.headers.get('content-length')||0);
  if(declared>MAX_BODY_BYTES)fail('حجم الطلب أكبر من الحد المسموح.',413,'payload_too_large');
  const text=await request.text();
  if(new TextEncoder().encode(text).byteLength>MAX_BODY_BYTES)fail('حجم الطلب أكبر من الحد المسموح.',413,'payload_too_large');
  try{
    const parsed=JSON.parse(text);
    if(!parsed||Array.isArray(parsed)||typeof parsed!=='object')fail('جسم الطلب غير صالح.',400,'invalid_json');
    return parsed;
  }catch(error){
    if(error?.code)throw error;
    fail('تعذر قراءة البيانات المرسلة.',400,'invalid_json');
  }
}

async function sendEmail(env,message){
  if(!env.RESEND_API_KEY||!env.FROM_EMAIL)fail('خدمة البريد غير مهيأة.',503,'email_not_configured');
  const response=await fetch('https://api.resend.com/emails',{
    method:'POST',
    headers:{
      authorization:`Bearer ${env.RESEND_API_KEY}`,
      'content-type':'application/json',
      'idempotency-key':message.idempotencyKey
    },
    body:JSON.stringify({from:env.FROM_EMAIL,to:message.to,subject:message.subject,html:message.html})
  });
  if(!response.ok){
    const detail=await response.text();
    const error=new Error(`resend_http_${response.status}:${detail.slice(0,180)}`);
    error.status=503;
    error.code='email_send_failed';
    throw error;
  }
  return response.json().catch(()=>({}));
}

async function identityAudit(env,actorUserId,eventType,targetUserId,entityId,metadata){
  if(!env.DB)return;
  await env.DB.prepare(`
    INSERT INTO identity_audit_log
    (id,actor_user_id,event_type,target_user_id,entity_id,metadata_json,created_at)
    VALUES (?,?,?,?,?,?,?)
  `).bind(
    crypto.randomUUID(),actorUserId||null,eventType,targetUserId||null,entityId||null,
    JSON.stringify(metadata||{}),new Date().toISOString()
  ).run();
}

function portalLink(base,conversationId,accessToken,role){
  const value=String(base||'').trim();
  let parsed;
  try{parsed=new URL(value);}catch(_){fail('مسار بوابة المحادثة غير مهيأ.',503,'portal_base_unavailable');}
  if(parsed.protocol!=='https:'||parsed.username||parsed.password)fail('مسار بوابة المحادثة غير مهيأ.',503,'portal_base_unavailable');
  const clean=parsed.href.replace(/[?#].*$/,'').replace(/\/?$/,'/');
  return `${clean}#conversation=${encodeURIComponent(conversationId)}&token=${encodeURIComponent(accessToken)}&role=${encodeURIComponent(role)}`;
}

async function withProductionVersion(response,origin,env){
  const data=await response.clone().json().catch(()=>({}));
  if(!data||typeof data!=='object'||data.service!=='pterminology-specialist-identity')return response;
  const checks={...(data.checks||{}),protectedDeepHealth:true,adminProviderStatus:true};
  const ok=data.ok===true&&Object.values(checks).every(Boolean);
  return json({...data,ok,version:BUILD_VERSION,checks},ok?200:503,corsHeaders(origin,env));
}

function bootstrapAuthorized(request,env){
  const supplied=String(request.headers.get('x-bootstrap-key')||'');
  const expected=String(env.ADMIN_API_KEY||'');
  return Boolean(expected)&&constantTimeEqual(supplied,expected);
}

function bearerToken(request){
  const match=(request.headers.get('authorization')||'').match(/^Bearer\s+([A-Za-z0-9_-]{32,500})$/i);
  if(!match)fail('يلزم تسجيل الدخول.',401,'authentication_required');
  return match[1];
}

function validId(value,label='المعرف'){
  const id=cleanString(value,90,true);
  if(!/^[a-z0-9][a-z0-9-]{2,89}$/i.test(id))fail(`${label} غير صالح.`,400,'invalid_id');
  return id;
}

function cleanString(value,max=200,required=false){
  const text=String(value??'').trim();
  if(required&&!text)fail('أحد الحقول المطلوبة فارغ.',400,'missing_field');
  if(text.length>max)fail('أحد الحقول تجاوز الحد المسموح.',400,'field_too_long');
  return text;
}

function requestIp(request){
  return request.headers.get('cf-connecting-ip')||request.headers.get('x-forwarded-for')||'unknown';
}

function randomToken(bytes=32){
  const array=new Uint8Array(bytes);
  crypto.getRandomValues(array);
  let value='';
  for(const byte of array)value+=String.fromCharCode(byte);
  return btoa(value).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'');
}

async function sha256(value){
  const digest=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(String(value)));
  return Array.from(new Uint8Array(digest),byte=>byte.toString(16).padStart(2,'0')).join('');
}

function constantTimeEqual(a,b){
  a=String(a||'');b=String(b||'');let diff=a.length^b.length;
  const length=Math.max(a.length,b.length);
  for(let index=0;index<length;index+=1)diff|=(a.charCodeAt(index)||0)^(b.charCodeAt(index)||0);
  return diff===0;
}

function corsHeaders(origin,env){
  const allowed=String(env.ALLOWED_ORIGINS||'https://khaledaltheeb.github.io').split(',').map(value=>value.trim()).filter(Boolean);
  const headers={
    'access-control-allow-methods':'GET,POST,PATCH,DELETE,OPTIONS',
    'access-control-allow-headers':'authorization,content-type,idempotency-key,x-requested-with,x-bootstrap-key,x-recovery-export-key',
    'access-control-max-age':'86400',
    'cache-control':'no-store',
    'content-security-policy':"default-src 'none'; frame-ancestors 'none'",
    'cross-origin-resource-policy':'same-site',
    'referrer-policy':'no-referrer',
    'strict-transport-security':'max-age=31536000; includeSubDomains',
    'vary':'Origin',
    'x-content-type-options':'nosniff',
    'x-frame-options':'DENY'
  };
  if(origin&&allowed.includes(origin))headers['access-control-allow-origin']=origin;
  return headers;
}

function emailLayout(title,body){
  return `<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>${escapeHtml(title)}</title></head><body style="font-family:Arial,sans-serif;background:#f4f8f7;color:#123;padding:24px"><main style="max-width:640px;margin:auto;background:white;border:1px solid #d9e8e5;border-radius:16px;padding:24px"><h1 style="color:#075f5b">${escapeHtml(title)}</h1>${body}<hr><p style="font-size:13px;color:#567">منصة الصحة النفسية وذوي الاحتياجات الخاصة</p></main></body></html>`;
}

function escapeHtml(value){
  return String(value??'').replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
}

function safeError(error){
  return String(error?.message||error||'unknown').slice(0,240);
}

function fail(message,status=400,code='invalid_request'){
  const error=new Error(message);
  error.status=status;
  error.code=code;
  throw error;
}

function json(payload,status=200,headers={}){
  return new Response(JSON.stringify(payload),{status,headers:{...JSON_HEADERS,...headers}});
}
