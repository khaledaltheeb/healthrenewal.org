const MAX_BODY_BYTES=64_000;
const MAX_MESSAGE_LENGTH=3_000;
const VISITOR_TOKEN_DAYS=30;

export const SPECIALIST_MESSAGE_PATH=/^\/v1\/specialist\/conversations\/([a-z0-9-]+)\/messages$/i;

export async function handleSpecialistReply(request,env,ctx,cors,finalWorker,conversationId){
  try{
    if(!env.DB||!env.RATE_LIMIT_SALT)fail('خدمة الهوية غير جاهزة.',503,'identity_unavailable');
    const actor=await authenticatedSpecialist(request,env,ctx,finalWorker);
    await rateLimit(request,env,'specialist-message-v10',100,actor.id);

    const id=validId(conversationId,'معرف المحادثة');
    const conversation=await env.DB.prepare(`
      SELECT id,reference_id,provider_id,visitor_email,status
      FROM conversations WHERE id=? AND provider_id=? LIMIT 1
    `).bind(id,actor.providerId).first();
    if(!conversation)fail('المحادثة غير موجودة.',404,'conversation_not_found');
    if(conversation.status!=='open')fail('المحادثة مغلقة.',409,'conversation_closed');

    const body=await parseJson(request);
    const message=cleanString(body.body,MAX_MESSAGE_LENGTH,true);
    const key=cleanString(request.headers.get('idempotency-key')||body.idempotencyKey,120,true);
    if(!/^[a-z0-9-]{12,120}$/i.test(key))fail('مفتاح منع التكرار غير صالح.',400,'invalid_idempotency_key');

    const existing=await env.DB.prepare(`
      SELECT message_id FROM specialist_message_requests
      WHERE idempotency_key=? AND provider_id=? AND conversation_id=? LIMIT 1
    `).bind(key,actor.providerId,id).first();
    if(existing)return response({ok:true,messageId:existing.message_id,duplicate:true},200,cors);

    const now=new Date().toISOString();
    const messageId=crypto.randomUUID();
    let visitorLink=null;
    let tokenId=null;
    let tokenHash=null;
    let tokenExpiresAt=null;

    if(conversation.visitor_email){
      const raw=randomToken(32);
      tokenId=crypto.randomUUID();
      tokenHash=await sha256(raw);
      tokenExpiresAt=new Date(Date.now()+VISITOR_TOKEN_DAYS*86_400_000).toISOString();
      visitorLink=portalLink(env.PORTAL_BASE_URL,id,raw);
    }

    const openGuard=`EXISTS(SELECT 1 FROM conversations WHERE id=? AND provider_id=? AND status='open')`;
    const statements=[
      env.DB.prepare(`
        INSERT INTO messages (id,conversation_id,sender_role,body,created_at)
        SELECT ?,?,'specialist',?,? WHERE ${openGuard}
      `).bind(messageId,id,message,now,id,actor.providerId),
      env.DB.prepare(`
        UPDATE conversations SET updated_at=?,last_message_at=?
        WHERE id=? AND provider_id=? AND status='open'
      `).bind(now,now,id,actor.providerId),
      env.DB.prepare(`
        INSERT INTO specialist_message_requests
          (idempotency_key,provider_id,conversation_id,message_id,created_at)
        SELECT ?,?,?,?,?,? WHERE ${openGuard}
      `.replace('SELECT ?,?,?,?,?,?','SELECT ?,?,?,?,?')).bind(key,actor.providerId,id,messageId,now,id,actor.providerId),
      env.DB.prepare(`
        INSERT INTO identity_audit_log
          (id,actor_user_id,event_type,target_user_id,entity_id,metadata_json,created_at)
        SELECT ?,?,'message_created',?,?,?,? WHERE ${openGuard}
      `).bind(crypto.randomUUID(),actor.id,actor.id,id,JSON.stringify({messageId,deliveryLink:visitorLink?'visitor_fragment_token':'not_required',visitorTokenExpiresAt:tokenExpiresAt}),now,id,actor.providerId)
    ];

    if(visitorLink){
      statements.push(
        env.DB.prepare(`DELETE FROM conversation_tokens WHERE conversation_id=? AND role='visitor' AND ${openGuard}`).bind(id,id,actor.providerId),
        env.DB.prepare(`
          INSERT INTO conversation_tokens (id,conversation_id,role,token_hash,expires_at,created_at)
          SELECT ?,?,'visitor',?,?,? WHERE ${openGuard}
        `).bind(tokenId,id,tokenHash,tokenExpiresAt,now,id,actor.providerId)
      );
    }

    let results;
    try{
      results=await env.DB.batch(statements);
    }catch(error){
      const replay=await env.DB.prepare(`
        SELECT message_id FROM specialist_message_requests
        WHERE idempotency_key=? AND provider_id=? AND conversation_id=? LIMIT 1
      `).bind(key,actor.providerId,id).first().catch(()=>null);
      if(replay)return response({ok:true,messageId:replay.message_id,duplicate:true},200,cors);
      throw error;
    }

    if(Number(results?.[0]?.meta?.changes||0)!==1||Number(results?.[1]?.meta?.changes||0)!==1||Number(results?.[2]?.meta?.changes||0)!==1){
      fail('أُغلقت المحادثة أثناء إرسال الرد. لم تُحفظ الرسالة.',409,'conversation_closed');
    }

    if(visitorLink){
      ctx.waitUntil(deliverVisitorReply(env,actor,conversation,id,messageId,visitorLink));
    }

    return response({ok:true,messageId,createdAt:now,visitorAccessIssued:Boolean(visitorLink),notificationQueued:Boolean(visitorLink)},201,cors);
  }catch(error){
    console.error('specialist_reply_v10_error',safeError(error));
    const status=Number(error.status)||500;
    return response({error:error.code||'internal_error',message:status===500?'حدث خطأ داخلي.':error.message},status,cors);
  }
}

async function authenticatedSpecialist(request,env,ctx,finalWorker){
  const sessionRequest=new Request(new URL('/v1/auth/session',request.url),{method:'GET',headers:request.headers,redirect:'error'});
  const sessionResponse=await finalWorker.fetch(sessionRequest,env,ctx);
  const data=await sessionResponse.clone().json().catch(()=>({}));
  if(!sessionResponse.ok){
    const error=new Error(data.message||'يلزم تسجيل الدخول.');
    error.status=sessionResponse.status;
    error.code=data.error||'authentication_required';
    throw error;
  }
  const actor=data.user||{};
  if(!actor.id||!actor.providerId)fail('الحساب غير مرتبط بملف مهني.',403,'provider_not_linked');
  return actor;
}

async function deliverVisitorReply(env,actor,conversation,conversationId,messageId,visitorLink){
  try{
    await sendEmailWithRetry(env,{
      to:[conversation.visitor_email],
      subject:`رد من المختص — ${conversation.reference_id}`,
      html:emailLayout('وصل رد جديد',`<p>وصل رد جديد في المحادثة ${escapeHtml(conversation.reference_id)}.</p><p><a href="${escapeHtml(visitorLink)}">فتح المحادثة والرد</a></p><p>الرابط خاص وينتهي تلقائيًا.</p>`),
      idempotencyKey:`identity-message/${messageId}`
    });
    await audit(env,actor.id,'visitor_reply_email_sent',actor.id,conversationId,{messageId});
  }catch(error){
    await audit(env,actor.id,'visitor_reply_email_failed',actor.id,conversationId,{messageId,error:safeError(error)}).catch(()=>{});
  }
}

async function sendEmailWithRetry(env,message){
  if(!env.RESEND_API_KEY||!env.FROM_EMAIL)fail('خدمة البريد غير مهيأة.',503,'email_not_configured');
  let lastError=null;
  for(let attempt=1;attempt<=3;attempt+=1){
    try{
      const result=await fetch('https://api.resend.com/emails',{method:'POST',headers:{authorization:`Bearer ${env.RESEND_API_KEY}`,'content-type':'application/json','idempotency-key':message.idempotencyKey},body:JSON.stringify({from:env.FROM_EMAIL,to:message.to,subject:message.subject,html:message.html})});
      if(result.ok)return;
      const detail=await result.text();
      lastError=new Error(`resend_http_${result.status}:${detail.slice(0,180)}`);
      if(result.status<500&&result.status!==429)break;
    }catch(error){lastError=error;}
    if(attempt<3)await new Promise(resolve=>setTimeout(resolve,attempt*500));
  }
  throw lastError||new Error('email_send_failed');
}

async function audit(env,actor,eventType,target,entity,metadata){
  await env.DB.prepare(`INSERT INTO identity_audit_log (id,actor_user_id,event_type,target_user_id,entity_id,metadata_json,created_at) VALUES (?,?,?,?,?,?,?)`).bind(crypto.randomUUID(),actor||null,eventType,target||null,entity||null,JSON.stringify(metadata||{}),new Date().toISOString()).run();
}

async function rateLimit(request,env,scope,limit,identity){
  const key=`${scope}:${await sha256(`${scope}|${identity||requestIp(request)}|${env.RATE_LIMIT_SALT}`)}`;
  const bucket=new Date().toISOString().slice(0,13);
  await env.DB.prepare(`INSERT INTO rate_limits (key,bucket,count,updated_at) VALUES (?,?,1,?) ON CONFLICT(key,bucket) DO UPDATE SET count=count+1,updated_at=excluded.updated_at`).bind(key,bucket,new Date().toISOString()).run();
  const row=await env.DB.prepare(`SELECT count FROM rate_limits WHERE key=? AND bucket=?`).bind(key,bucket).first();
  if(Number(row?.count||0)>limit)fail('تم تجاوز عدد المحاولات المسموح مؤقتًا.',429,'rate_limited');
}

async function parseJson(request){
  if(!(request.headers.get('content-type')||'').includes('application/json'))fail('يجب إرسال البيانات بصيغة JSON.',415,'unsupported_media_type');
  const declared=Number(request.headers.get('content-length')||0);
  if(declared>MAX_BODY_BYTES)fail('حجم الطلب أكبر من الحد المسموح.',413,'payload_too_large');
  const text=await request.text();
  if(new TextEncoder().encode(text).byteLength>MAX_BODY_BYTES)fail('حجم الطلب أكبر من الحد المسموح.',413,'payload_too_large');
  try{const parsed=JSON.parse(text);if(!parsed||Array.isArray(parsed)||typeof parsed!=='object')fail('جسم الطلب غير صالح.',400,'invalid_json');return parsed;}catch(error){if(error?.code)throw error;fail('تعذر قراءة البيانات المرسلة.',400,'invalid_json');}
}

function portalLink(base,conversationId,token){
  let url;
  try{url=new URL(String(base||''));}catch(_){fail('مسار بوابة المحادثة غير مهيأ.',503,'portal_base_unavailable');}
  if(url.protocol!=='https:'||url.username||url.password)fail('مسار بوابة المحادثة غير مهيأ.',503,'portal_base_unavailable');
  const clean=url.href.replace(/[?#].*$/,'').replace(/\/?$/,'/');
  return `${clean}#conversation=${encodeURIComponent(conversationId)}&token=${encodeURIComponent(token)}&role=visitor`;
}
function validId(value,label){const id=cleanString(value,90,true);if(!/^[a-z0-9][a-z0-9-]{2,89}$/i.test(id))fail(`${label} غير صالح.`,400,'invalid_id');return id;}
function cleanString(value,max,required){const text=String(value??'').trim();if(required&&!text)fail('أحد الحقول المطلوبة فارغ.',400,'missing_field');if(text.length>max)fail('أحد الحقول تجاوز الحد المسموح.',400,'field_too_long');return text;}
function randomToken(bytes){const array=new Uint8Array(bytes);crypto.getRandomValues(array);let value='';for(const byte of array)value+=String.fromCharCode(byte);return btoa(value).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'');}
async function sha256(value){const digest=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(String(value)));return Array.from(new Uint8Array(digest),byte=>byte.toString(16).padStart(2,'0')).join('');}
function requestIp(request){return request.headers.get('cf-connecting-ip')||request.headers.get('x-forwarded-for')||'unknown';}
function emailLayout(title,body){return `<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>${escapeHtml(title)}</title></head><body><main><h1>${escapeHtml(title)}</h1>${body}</main></body></html>`;}
function escapeHtml(value){return String(value??'').replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));}
function safeError(error){return String(error?.message||error||'unknown').slice(0,240);}
function fail(message,status=400,code='invalid_request'){const error=new Error(message);error.status=status;error.code=code;throw error;}
function response(payload,status,cors){return new Response(JSON.stringify(payload),{status,headers:{'content-type':'application/json; charset=utf-8',...cors}});}
