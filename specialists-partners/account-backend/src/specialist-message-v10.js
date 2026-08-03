const JSON_HEADERS={'content-type':'application/json; charset=utf-8'};
const MAX_BODY_BYTES=64_000;
const MAX_MESSAGE_LENGTH=3_000;
const DEFAULT_LINK_DAYS=7;
const DEFAULT_OUTBOX_LIMIT=25;
const MAX_OUTBOX_ATTEMPTS=8;
const LEASE_MINUTES=5;

export async function handleSpecialistMessageV10(request,env,ctx,cors,actor,conversationId){
  try{
    assertEnvironment(env);
    const provider=await activeProvider(env,actor);
    await rateLimit(request,env,'specialist-message-v10',100,actor.id);

    const id=validId(conversationId,'معرف المحادثة');
    const body=await parseJson(request);
    const message=cleanString(body.body,MAX_MESSAGE_LENGTH,true);
    const idempotencyKey=cleanString(request.headers.get('idempotency-key')||body.idempotencyKey,120,true);
    if(!/^[a-z0-9-]{12,120}$/i.test(idempotencyKey))fail('مفتاح منع التكرار غير صالح.',400,'invalid_idempotency_key');

    const prior=await idempotencyRecord(env,idempotencyKey);
    if(prior)return duplicateResponse(prior,provider.provider_id,id,cors);

    const conversation=await env.DB.prepare(`
      SELECT id,reference_id,provider_id,visitor_email,status
      FROM conversations
      WHERE id=? AND provider_id=?
      LIMIT 1
    `).bind(id,provider.provider_id).first();
    if(!conversation)fail('المحادثة غير موجودة.',404,'conversation_not_found');
    if(conversation.status!=='open')fail('المحادثة مغلقة.',409,'conversation_closed');

    const now=new Date().toISOString();
    const messageId=crypto.randomUUID();
    const statements=[];
    let tokenId=null;
    let tokenCreatedAt=null;
    let tokenExpiresAt=null;
    let outboxId=null;

    statements.push(env.DB.prepare(`
      INSERT INTO messages (id,conversation_id,sender_role,body,created_at)
      SELECT ?,?,'specialist',?,?
      WHERE EXISTS (
        SELECT 1 FROM conversations
        WHERE id=? AND provider_id=? AND status='open'
      )
      AND NOT EXISTS (
        SELECT 1 FROM specialist_message_requests WHERE idempotency_key=?
      )
    `).bind(messageId,id,message,now,id,provider.provider_id,idempotencyKey));

    statements.push(env.DB.prepare(`
      UPDATE conversations SET updated_at=?,last_message_at=?
      WHERE id=? AND provider_id=? AND status='open'
        AND EXISTS (SELECT 1 FROM messages WHERE id=? AND conversation_id=?)
    `).bind(now,now,id,provider.provider_id,messageId,id));

    statements.push(env.DB.prepare(`
      INSERT INTO specialist_message_requests
        (idempotency_key,provider_id,conversation_id,message_id,created_at)
      SELECT ?,?,?,?,?
      WHERE EXISTS (SELECT 1 FROM messages WHERE id=? AND conversation_id=?)
    `).bind(idempotencyKey,provider.provider_id,id,messageId,now,messageId,id));

    const visitorEmail=cleanString(conversation.visitor_email,254,false);
    if(visitorEmail){
      const accessToken=randomToken(32);
      const tokenHash=await sha256(accessToken);
      tokenId=crypto.randomUUID();
      tokenCreatedAt=now;
      tokenExpiresAt=new Date(Date.now()+linkDays(env)*86_400_000).toISOString();
      const link=portalLink(env.PORTAL_BASE_URL,id,accessToken,'visitor');
      outboxId=crypto.randomUUID();
      const payload={
        to:[visitorEmail],
        subject:`رد من المختص — ${conversation.reference_id}`,
        html:emailLayout('وصل رد جديد',`<p>وصل رد جديد في المحادثة ${escapeHtml(conversation.reference_id)}.</p><p><a href="${escapeHtml(link)}">فتح المحادثة والرد</a></p><p>الرابط خاص وينتهي تلقائيًا.</p>`),
        idempotencyKey:`identity-message/${messageId}`
      };
      const aad=outboxAad(outboxId,messageId,id,tokenId);
      const encrypted=await encryptOutboxPayload(env,payload,aad);

      statements.push(env.DB.prepare(`
        INSERT INTO conversation_tokens
          (id,conversation_id,role,token_hash,expires_at,created_at)
        SELECT ?,?,'visitor',?,?,?
        WHERE EXISTS (SELECT 1 FROM messages WHERE id=? AND conversation_id=?)
      `).bind(tokenId,id,tokenHash,tokenExpiresAt,tokenCreatedAt,messageId,id));

      statements.push(env.DB.prepare(`
        INSERT INTO specialist_message_outbox (
          id,message_id,conversation_id,provider_id,conversation_token_id,
          recipient_email,payload_ciphertext,payload_iv,status,attempt_count,
          next_attempt_at,created_at,updated_at
        )
        SELECT ?,?,?,?,?,?,?,?,'queued',0,?,?,?
        WHERE EXISTS (SELECT 1 FROM messages WHERE id=? AND conversation_id=?)
      `).bind(
        outboxId,messageId,id,provider.provider_id,tokenId,visitorEmail,
        encrypted.ciphertext,encrypted.iv,now,now,now,messageId,id
      ));
    }

    statements.push(env.DB.prepare(`
      INSERT INTO identity_audit_log
        (id,actor_user_id,event_type,target_user_id,entity_id,metadata_json,created_at)
      SELECT ?,?,'message_created',?,?,?,?
      WHERE EXISTS (SELECT 1 FROM messages WHERE id=? AND conversation_id=?)
    `).bind(
      crypto.randomUUID(),actor.id,actor.id,id,
      JSON.stringify({messageId,delivery:outboxId?'durable_encrypted_outbox':'not_required',tokenExpiresAt}),
      now,messageId,id
    ));

    let results;
    try{
      results=await env.DB.batch(statements);
    }catch(error){
      const replay=await idempotencyRecord(env,idempotencyKey).catch(()=>null);
      if(replay)return duplicateResponse(replay,provider.provider_id,id,cors);
      throw error;
    }

    if(Number(results?.[0]?.meta?.changes||0)!==1){
      const replay=await idempotencyRecord(env,idempotencyKey);
      if(replay)return duplicateResponse(replay,provider.provider_id,id,cors);
      const current=await env.DB.prepare(`SELECT status FROM conversations WHERE id=? AND provider_id=?`).bind(id,provider.provider_id).first();
      if(!current)fail('المحادثة غير موجودة.',404,'conversation_not_found');
      if(current.status!=='open')fail('المحادثة مغلقة.',409,'conversation_closed');
      fail('تعذر حفظ الرد بأمان.',409,'message_commit_failed');
    }

    if(outboxId&&ctx?.waitUntil){
      ctx.waitUntil(processSpecialistMessageOutbox(env,{limit:5,conversationId:id}).catch(error=>{
        console.error('specialist_message_outbox_inline_error',safeError(error));
      }));
    }

    return json({
      ok:true,
      messageId,
      createdAt:now,
      visitorAccessIssued:Boolean(tokenId),
      notificationQueued:Boolean(outboxId)
    },201,cors);
  }catch(error){
    console.error('specialist_message_v10_error',safeError(error));
    const status=Number(error.status)||500;
    return json({error:error.code||'internal_error',message:status===500?'حدث خطأ داخلي.':error.message},status,cors);
  }
}

export async function processSpecialistMessageOutbox(env,options={}){
  if(!env?.DB)return {processed:0,sent:0,retried:0,failed:0,superseded:0};
  const limit=boundedInteger(options.limit,DEFAULT_OUTBOX_LIMIT,1,100);
  const now=new Date().toISOString();
  const bindings=[now,now];
  let scope='';
  if(options.conversationId){scope='AND conversation_id=?';bindings.push(validId(options.conversationId,'معرف المحادثة'));}
  bindings.push(limit);
  const rows=await env.DB.prepare(`
    SELECT * FROM specialist_message_outbox
    WHERE (
      (status IN ('queued','retry') AND next_attempt_at<=?)
      OR (status='sending' AND lease_expires_at IS NOT NULL AND lease_expires_at<=?)
    )
    ${scope}
    ORDER BY created_at ASC
    LIMIT ?
  `).bind(...bindings).all();

  const summary={processed:0,sent:0,retried:0,failed:0,superseded:0};
  for(const row of rows.results||[]){
    const outcome=await processOutboxRow(env,row);
    summary.processed+=1;
    summary[outcome]=(summary[outcome]||0)+1;
  }
  return summary;
}

export async function specialistMessageHealth(env){
  let schema=false;
  try{
    const row=await env.DB.prepare(`
      SELECT COUNT(*) AS count FROM pragma_table_info('specialist_message_outbox')
      WHERE name IN (
        'id','message_id','conversation_id','provider_id','conversation_token_id',
        'recipient_email','payload_ciphertext','payload_iv','status','attempt_count',
        'next_attempt_at','lease_expires_at','provider_message_id','last_error',
        'created_at','updated_at','sent_at'
      )
    `).first();
    schema=Number(row?.count||0)===17;
  }catch(error){
    console.error('specialist_message_outbox_health_error',safeError(error));
  }
  return {
    specialistReplyLink:true,
    messageOutboxSchema:schema,
    messageOutboxEncryption:outboxSecret(env).length>=32
  };
}

async function processOutboxRow(env,row){
  const now=new Date().toISOString();
  const leaseExpiresAt=new Date(Date.now()+LEASE_MINUTES*60_000).toISOString();
  const claimed=await env.DB.prepare(`
    UPDATE specialist_message_outbox
    SET status='sending',lease_expires_at=?,updated_at=?
    WHERE id=? AND (
      (status IN ('queued','retry') AND next_attempt_at<=?)
      OR (status='sending' AND lease_expires_at IS NOT NULL AND lease_expires_at<=?)
    )
  `).bind(leaseExpiresAt,now,row.id,now,now).run();
  if(Number(claimed?.meta?.changes||0)!==1)return 'superseded';

  const newerSent=await env.DB.prepare(`
    SELECT id FROM specialist_message_outbox
    WHERE conversation_id=? AND status='sent' AND created_at>?
    LIMIT 1
  `).bind(row.conversation_id,row.created_at).first();
  if(newerSent){
    await supersedeOutbox(env,row,'newer_delivery_already_sent');
    return 'superseded';
  }

  try{
    const aad=outboxAad(row.id,row.message_id,row.conversation_id,row.conversation_token_id);
    const payload=await decryptOutboxPayload(env,row.payload_ciphertext,row.payload_iv,aad);
    const provider=await sendEmailWithRetry(env,payload);
    const sentAt=new Date().toISOString();
    await env.DB.batch([
      env.DB.prepare(`
        UPDATE specialist_message_outbox
        SET status='sent',attempt_count=attempt_count+1,provider_message_id=?,last_error=NULL,
          payload_ciphertext='',payload_iv='',lease_expires_at=NULL,sent_at=?,updated_at=?
        WHERE id=? AND status='sending'
      `).bind(provider.id||null,sentAt,sentAt,row.id),
      env.DB.prepare(`
        DELETE FROM conversation_tokens
        WHERE conversation_id=? AND role='visitor' AND id<>? AND created_at<=?
      `).bind(row.conversation_id,row.conversation_token_id,row.created_at),
      auditStatement(env,'visitor_reply_email_sent',row.provider_id,row.conversation_id,{
        messageId:row.message_id,outboxId:row.id,providerMessageId:provider.id||null
      },sentAt)
    ]);
    return 'sent';
  }catch(error){
    const attempt=Number(row.attempt_count||0)+1;
    const retryable=error.retryable!==false;
    const permanent=!retryable||attempt>=MAX_OUTBOX_ATTEMPTS;
    const updatedAt=new Date().toISOString();
    const status=permanent?'failed':'retry';
    const nextAttemptAt=permanent?updatedAt:new Date(Date.now()+retryDelayMs(attempt)).toISOString();
    const statements=[
      env.DB.prepare(`
        UPDATE specialist_message_outbox
        SET status=?,attempt_count=?,next_attempt_at=?,lease_expires_at=NULL,last_error=?,
          payload_ciphertext=CASE WHEN ?='failed' THEN '' ELSE payload_ciphertext END,
          payload_iv=CASE WHEN ?='failed' THEN '' ELSE payload_iv END,updated_at=?
        WHERE id=? AND status='sending'
      `).bind(status,attempt,nextAttemptAt,safeError(error),status,status,updatedAt,row.id),
      auditStatement(env,permanent?'visitor_reply_email_failed':'visitor_reply_email_retry',row.provider_id,row.conversation_id,{
        messageId:row.message_id,outboxId:row.id,attempt,error:safeError(error)
      },updatedAt)
    ];
    if(permanent&&row.conversation_token_id){
      statements.push(env.DB.prepare(`DELETE FROM conversation_tokens WHERE id=?`).bind(row.conversation_token_id));
    }
    await env.DB.batch(statements);
    return permanent?'failed':'retried';
  }
}

async function supersedeOutbox(env,row,reason){
  const now=new Date().toISOString();
  const statements=[
    env.DB.prepare(`
      UPDATE specialist_message_outbox
      SET status='superseded',payload_ciphertext='',payload_iv='',lease_expires_at=NULL,
        last_error=?,updated_at=? WHERE id=? AND status='sending'
    `).bind(reason,now,row.id),
    auditStatement(env,'visitor_reply_email_superseded',row.provider_id,row.conversation_id,{messageId:row.message_id,outboxId:row.id,reason},now)
  ];
  if(row.conversation_token_id)statements.push(env.DB.prepare(`DELETE FROM conversation_tokens WHERE id=?`).bind(row.conversation_token_id));
  await env.DB.batch(statements);
}

function auditStatement(env,eventType,providerId,conversationId,metadata,createdAt){
  return env.DB.prepare(`
    INSERT INTO identity_audit_log
      (id,actor_user_id,event_type,target_user_id,entity_id,metadata_json,created_at)
    VALUES (?,NULL,?,NULL,?,?,?)
  `).bind(crypto.randomUUID(),eventType,conversationId,JSON.stringify({providerId,...metadata}),createdAt);
}

async function activeProvider(env,actor){
  if(!actor?.id||!actor.provider_id)fail('الحساب غير مرتبط بملف مهني.',403,'provider_not_linked');
  const provider=await env.DB.prepare(`SELECT provider_id,status FROM providers_private WHERE provider_id=? LIMIT 1`).bind(actor.provider_id).first();
  if(!provider||provider.status!=='active')fail('الملف المهني غير نشط.',403,'provider_inactive');
  return provider;
}

async function idempotencyRecord(env,key){
  return env.DB.prepare(`
    SELECT idempotency_key,provider_id,conversation_id,message_id
    FROM specialist_message_requests WHERE idempotency_key=? LIMIT 1
  `).bind(key).first();
}

function duplicateResponse(record,providerId,conversationId,cors){
  if(record.provider_id!==providerId||record.conversation_id!==conversationId){
    fail('مفتاح منع التكرار مستخدم لطلب آخر.',409,'idempotency_key_reused');
  }
  return json({ok:true,messageId:record.message_id,duplicate:true},200,cors);
}

async function sendEmailWithRetry(env,message){
  if(!env.RESEND_API_KEY||!env.FROM_EMAIL)fail('خدمة البريد غير مهيأة.',503,'email_not_configured');
  const attempts=boundedInteger(env.OUTBOX_INLINE_EMAIL_ATTEMPTS,3,1,3);
  let lastError=null;
  for(let attempt=1;attempt<=attempts;attempt+=1){
    try{
      const response=await fetch('https://api.resend.com/emails',{
        method:'POST',
        headers:{authorization:`Bearer ${env.RESEND_API_KEY}`,'content-type':'application/json','idempotency-key':message.idempotencyKey},
        body:JSON.stringify({from:env.FROM_EMAIL,to:message.to,subject:message.subject,html:message.html})
      });
      const text=await response.text();
      let data={};
      try{data=JSON.parse(text);}catch(_){}
      if(response.ok)return data;
      const error=new Error(`resend_http_${response.status}:${String(data.message||text).slice(0,180)}`);
      error.retryable=response.status===429||response.status>=500;
      lastError=error;
      if(!error.retryable)throw error;
    }catch(error){
      if(error.retryable===false)throw error;
      lastError=error;
    }
    if(attempt<attempts)await sleep(attempt*250);
  }
  const error=new Error(safeError(lastError));
  error.retryable=lastError?.retryable!==false;
  throw error;
}

async function encryptOutboxPayload(env,payload,aad){
  const key=await outboxCryptoKey(env,['encrypt']);
  const iv=crypto.getRandomValues(new Uint8Array(12));
  const encoded=new TextEncoder().encode(JSON.stringify(payload));
  const ciphertext=await crypto.subtle.encrypt({name:'AES-GCM',iv,additionalData:new TextEncoder().encode(aad)},key,encoded);
  return {ciphertext:toBase64Url(new Uint8Array(ciphertext)),iv:toBase64Url(iv)};
}

async function decryptOutboxPayload(env,ciphertext,iv,aad){
  const key=await outboxCryptoKey(env,['decrypt']);
  try{
    const plaintext=await crypto.subtle.decrypt({name:'AES-GCM',iv:fromBase64Url(iv),additionalData:new TextEncoder().encode(aad)},key,fromBase64Url(ciphertext));
    const value=JSON.parse(new TextDecoder().decode(plaintext));
    if(!value||!Array.isArray(value.to)||!value.to.length||!value.subject||!value.html||!value.idempotencyKey)throw new Error('invalid_outbox_payload');
    return value;
  }catch(error){
    const wrapped=new Error(`outbox_decrypt_failed:${safeError(error)}`);
    wrapped.retryable=false;
    throw wrapped;
  }
}

async function outboxCryptoKey(env,usages){
  const secret=outboxSecret(env);
  if(secret.length<32)fail('مفتاح تشفير مهام البريد غير مهيأ.',503,'outbox_encryption_unavailable');
  const digest=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(`specialist-message-outbox-v10\u0000${secret}`));
  return crypto.subtle.importKey('raw',digest,{name:'AES-GCM'},false,usages);
}

function outboxSecret(env){return String(env.OUTBOX_ENCRYPTION_KEY||env.RATE_LIMIT_SALT||'');}
function outboxAad(outboxId,messageId,conversationId,tokenId){return `${outboxId}|${messageId}|${conversationId}|${tokenId||''}`;}
function retryDelayMs(attempt){return Math.min(6*60*60_000,Math.max(60_000,2**Math.min(attempt,8)*60_000));}
function linkDays(env){return boundedInteger(env.VISITOR_REPLY_LINK_DAYS,DEFAULT_LINK_DAYS,1,30);}
function boundedInteger(value,fallback,min,max){const number=Number.parseInt(String(value??''),10);return Number.isFinite(number)?Math.min(max,Math.max(min,number)):fallback;}

function portalLink(base,conversationId,accessToken,role){
  const value=String(base||'').trim();
  let parsed;
  try{parsed=new URL(value);}catch(_){fail('مسار بوابة المحادثة غير مهيأ.',503,'portal_base_unavailable');}
  if(parsed.protocol!=='https:'||parsed.username||parsed.password||parsed.search||parsed.hash)fail('مسار بوابة المحادثة غير مهيأ.',503,'portal_base_unavailable');
  const clean=parsed.href.replace(/\/?$/,'/');
  return `${clean}#conversation=${encodeURIComponent(conversationId)}&token=${encodeURIComponent(accessToken)}&role=${encodeURIComponent(role)}`;
}

async function rateLimit(request,env,scope,limit,identity=''){
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
  try{const parsed=JSON.parse(text);if(!parsed||Array.isArray(parsed)||typeof parsed!=='object')fail('جسم الطلب غير صالح.',400,'invalid_json');return parsed;}
  catch(error){if(error?.code)throw error;fail('تعذر قراءة البيانات المرسلة.',400,'invalid_json');}
}

function assertEnvironment(env){if(!env?.DB||!env.RATE_LIMIT_SALT)fail('خدمة الرسائل غير جاهزة.',503,'message_service_unavailable');}
function validId(value,label='المعرف'){const id=cleanString(value,90,true);if(!/^[a-z0-9][a-z0-9-]{2,89}$/i.test(id))fail(`${label} غير صالح.`,400,'invalid_id');return id;}
function cleanString(value,max=200,required=false){const text=String(value??'').trim();if(required&&!text)fail('أحد الحقول المطلوبة فارغ.',400,'missing_field');if(text.length>max)fail('أحد الحقول تجاوز الحد المسموح.',400,'field_too_long');return text;}
function requestIp(request){return request.headers.get('cf-connecting-ip')||request.headers.get('x-forwarded-for')||'unknown';}
function randomToken(bytes=32){const array=new Uint8Array(bytes);crypto.getRandomValues(array);return toBase64Url(array);}
function toBase64Url(bytes){let value='';for(const byte of bytes)value+=String.fromCharCode(byte);return btoa(value).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'');}
function fromBase64Url(value){const text=String(value||'');const padded=text.replace(/-/g,'+').replace(/_/g,'/')+'='.repeat((4-text.length%4)%4);return Uint8Array.from(atob(padded),character=>character.charCodeAt(0));}
async function sha256(value){const digest=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(String(value)));return Array.from(new Uint8Array(digest),byte=>byte.toString(16).padStart(2,'0')).join('');}
function emailLayout(title,body){return `<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>${escapeHtml(title)}</title></head><body style="font-family:Arial,sans-serif;background:#f4f8f7;color:#123;padding:24px"><main style="max-width:640px;margin:auto;background:white;border:1px solid #d9e8e5;border-radius:16px;padding:24px"><h1 style="color:#075f5b">${escapeHtml(title)}</h1>${body}<hr><p style="font-size:13px;color:#567">منصة روافد</p></main></body></html>`;}
function escapeHtml(value){return String(value??'').replace(/[&<>"']/g,character=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[character]));}
function safeError(error){return String(error?.message||error||'unknown').slice(0,240);}
function sleep(milliseconds){return new Promise(resolve=>setTimeout(resolve,milliseconds));}
function fail(message,status=400,code='invalid_request'){const error=new Error(message);error.status=status;error.code=code;throw error;}
function json(payload,status=200,headers={}){return new Response(JSON.stringify(payload),{status,headers:{...JSON_HEADERS,...headers}});}

export const __test={portalLink,retryDelayMs,encryptOutboxPayload,decryptOutboxPayload,outboxAad};
