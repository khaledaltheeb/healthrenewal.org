from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SITE = Path(sys.argv[1] if len(sys.argv) > 1 else '_site')
JS = SITE / 'assets/js/lab-v12.js'

PATCHES = [
    (
        "if(mode==='simple_reaction'){prompt='اضغط الآن';answer='اضغط الآن';options=['اضغط الآن'];kind='reaction';delay=350+Math.floor(rnd()*650);explanation='تم تسجيل زمن الاستجابة بعد ظهور الإشارة.';}",
        "if(mode==='simple_reaction'){const cues=['●','▲','■','★','◆'];prompt=`عند ظهور ${cues[(stage+index)%cues.length]} اضغط الآن`;answer='اضغط الآن';options=['اضغط الآن'];kind='reaction';delay=350+((stage*173+index*131)%650);explanation='تم تسجيل زمن الاستجابة بعد ظهور الإشارة.';}",
        'simple reaction stimulus variation',
    ),
    (
        "else if(mode==='matrix_patterns'){const a=1+stage,b=2+(index%3);prompt=`في كل صف يساوي الثالث مجموع الأول والثاني: [${a}, ${b}, ${a+b}] [${a+1}, ${b+1}, ؟]`;answer=String(a+b+2);options=shuffle([String(a+b+2),String(a+b+1),String(a+b+3),String(a*b)],rnd);explanation='العنصر الثالث هو مجموع الأول والثاني.';}",
        "else if(mode==='matrix_patterns'){const a=1+stage,b=2+(index%3),result=a+b+2;prompt=`في كل صف يساوي الثالث مجموع الأول والثاني: [${a}, ${b}, ${a+b}] [${a+1}, ${b+1}, ؟]`;answer=String(result);options=shuffle(unique([String(result),String(result+1),String(result+2),String(result+3)]),rnd);explanation='العنصر الثالث هو مجموع الأول والثاني.';}",
        'matrix unique options',
    ),
    (
        "else if(mode==='trail_switching'){const n=1+(stage+index)%5,letters=['أ','ب','ج','د','هـ'];prompt=`أكمل التسلسل المتناوب: ${n}، ${letters[n-1]}، ${n+1}، ؟`;answer=letters[n];options=shuffle(letters.slice(0,4),rnd);explanation=`بعد ${n+1} يأتي ${letters[n]}.`;}",
        "else if(mode==='trail_switching'){const letters=['أ','ب','ج','د','هـ','و'],n=1+((stage+index)%5);prompt=`أكمل التسلسل المتناوب: ${n}، ${letters[n-1]}، ${n+1}، ؟`;answer=letters[n];options=shuffle(letters,rnd);explanation=`بعد ${n+1} يأتي ${letters[n]}.`;}",
        'trail answer available',
    ),
    (
        "else if(mode==='rule_discovery'){const mult=2+(stage%3),examples=`2→${2*mult}، 3→${3*mult}`;prompt=`اكتشف القاعدة من ${examples}. ما ناتج 4؟`;answer=String(4*mult);options=shuffle([String(4*mult),String(4+mult),String(4*mult+1),String(mult)],rnd);explanation=`القاعدة الضرب في ${mult}.`;}",
        "else if(mode==='rule_discovery'){const mult=2+((stage+index)%4),input=4+(index%3),examples=`2→${2*mult}، 3→${3*mult}`;prompt=`اكتشف القاعدة من ${examples}. ما ناتج ${input}؟`;answer=String(input*mult);options=shuffle(unique([answer,String(input+mult),String(input*mult+1),String(input*mult-1)]),rnd);explanation=`القاعدة الضرب في ${mult}.`;}",
        'rule discovery variation',
    ),
    (
        "else if(mode==='priority_planning'){prompt='لديك تسليم خلال ساعة، رسالة غير عاجلة، وموعد غدًا. ما الأولوية؟';answer='إنهاء التسليم القريب';options=shuffle(['إنهاء التسليم القريب','الرد على الرسالة غير العاجلة','التحضير الكامل لموعد الغد','تأجيل كل شيء'],rnd);explanation='المهمة الأقرب موعدًا والأعلى أثرًا أولًا.';}",
        "else if(mode==='priority_planning'){const sets=[['تسليم خلال ساعة ورسالة غير عاجلة وموعد غدًا','إنهاء التسليم القريب',['إنهاء التسليم القريب','الرد على الرسالة غير العاجلة','التحضير الكامل لموعد الغد','تأجيل كل شيء']],['دواء في موعده وترتيب غرفة ومشاهدة فيديو','أخذ الدواء في موعده',['أخذ الدواء في موعده','ترتيب الغرفة','مشاهدة الفيديو','تأجيل الجميع']],['اتصال طارئ من المدرسة ومشتريات أسبوعية ورسالة اجتماعية','الرد على اتصال المدرسة',['الرد على اتصال المدرسة','شراء الاحتياجات لاحقًا','الرد على الرسالة الاجتماعية','تجاهل الاتصال']]],s=sets[(stage+index)%sets.length];prompt=`المهام: ${s[0]}. ما الأولوية؟`;answer=s[1];options=shuffle(s[2],rnd);explanation='تقدم المهمة الأعلى خطورة أو الأقرب موعدًا أو التي تعتمد عليها مهام أخرى.';}",
        'priority planning variation',
    ),
    (
        "else if(mode==='perspective_taking'){prompt='وضعت ليلى الكتاب في الدرج ثم خرجت. نقل سامر الكتاب إلى الرف. أين ستبحث ليلى أولًا؟';answer='الدرج';options=['الدرج','الرف','الحقيبة','لا يمكن المعرفة'];explanation='ليلى تتصرف وفق معرفتها السابقة لا وفق ما حدث في غيابها.';}",
        "else if(mode==='perspective_taking'){const sets=[['وضعت ليلى الكتاب في الدرج ثم خرجت. نقل سامر الكتاب إلى الرف. أين ستبحث ليلى أولًا؟','الدرج',['الدرج','الرف','الحقيبة','لا يمكن المعرفة']],['ترك عمر الكرة في الحديقة ثم دخل. نقلت أخته الكرة إلى المخزن. أين سيبحث عمر أولًا؟','الحديقة',['الحديقة','المخزن','غرفته','لا يمكن المعرفة']],['رأت سارة الحلوى في الصندوق الأزرق ثم غادرت. نُقلت إلى الصندوق الأحمر. أين ستبحث سارة؟','الصندوق الأزرق',['الصندوق الأزرق','الصندوق الأحمر','الحقيبة','لا يمكن المعرفة']]],s=sets[(stage+index)%sets.length];prompt=s[0];answer=s[1];options=shuffle(s[2],rnd);explanation='الشخص يتصرف وفق المعلومات التي شاهدها قبل غيابه.';}",
        'perspective taking variation',
    ),
    (
        "else if(mode==='social_scenarios'){prompt='شخص رفض مشاركة معلومة شخصية. ما الاستجابة الأنسب؟';answer='احترام الرفض وتغيير الموضوع';options=shuffle(['احترام الرفض وتغيير الموضوع','الإلحاح حتى يجيب','السخرية من رفضه','نشر السؤال أمام الآخرين'],rnd);explanation='الاستجابة المناسبة تحترم الحدود.';}",
        "else if(mode==='social_scenarios'){const sets=[['شخص رفض مشاركة معلومة شخصية. ما الاستجابة الأنسب؟','احترام الرفض وتغيير الموضوع',['احترام الرفض وتغيير الموضوع','الإلحاح حتى يجيب','السخرية من رفضه','نشر السؤال أمام الآخرين']],['زميل يبدو منزعجًا ولا يريد الكلام الآن. ما الأنسب؟','عرض الدعم وترك مساحة',['عرض الدعم وترك مساحة','إجباره على الشرح','اتهامه بالتكبر','إخبار الجميع']],['طفل أخطأ أمام المجموعة. ما الاستجابة الأنسب؟','تصحيح هادئ يحفظ كرامته',['تصحيح هادئ يحفظ كرامته','السخرية منه','مقارنته بالآخرين','تجاهل الأذى']]],s=sets[(stage+index)%sets.length];prompt=s[0];answer=s[1];options=shuffle(s[2],rnd);explanation='الاستجابة المناسبة تحترم الحدود والكرامة والسياق.';}",
        'social scenario variation',
    ),
]


def main() -> None:
    if not JS.exists():
        raise SystemExit(f'Missing cognitive runtime: {JS}')
    text = JS.read_text(encoding='utf-8')
    results = []
    for old, new, label in PATCHES:
        if new in text:
            results.append(label + ':already')
            continue
        if old not in text:
            raise SystemExit(f'Missing quality patch target: {label}')
        text = text.replace(old, new, 1)
        results.append(label + ':patched')
    JS.write_text(text, encoding='utf-8')

    finalizer = Path(__file__).with_name('finalize_cognitive_lab_v202.py')
    hardener = Path(__file__).with_name('harden_cognitive_lab_v203.py')
    provider_route = Path(__file__).with_name('publish_provider_assessment_route_v204.py')
    working_memory = Path(__file__).with_name('publish_working_memory_updating_v205.py')
    prospective_memory = Path(__file__).with_name('publish_prospective_memory_v206.py')
    associative_binding = Path(__file__).with_name('publish_associative_binding_v207.py')
    temporal_order = Path(__file__).with_name('publish_temporal_order_memory_v208.py')
    visual_change = Path(__file__).with_name('publish_visual_change_detection_v210.py')
    bank_hardening = Path(__file__).with_name('harden_cognitive_banks_v211.py')
    copy_hardening = Path(__file__).with_name('harden_cognitive_copy_v209.py')
    subprocess.run([sys.executable, str(finalizer), str(SITE)], check=True)
    subprocess.run([sys.executable, str(hardener), str(SITE)], check=True)
    subprocess.run([sys.executable, str(provider_route), str(SITE)], check=True)
    subprocess.run([sys.executable, str(working_memory), str(SITE)], check=True)
    subprocess.run([sys.executable, str(prospective_memory), str(SITE)], check=True)
    subprocess.run([sys.executable, str(associative_binding), str(SITE)], check=True)
    subprocess.run([sys.executable, str(temporal_order), str(SITE)], check=True)
    subprocess.run([sys.executable, str(visual_change), str(SITE)], check=True)
    subprocess.run([sys.executable, str(bank_hardening), str(SITE)], check=True)
    subprocess.run([sys.executable, str(copy_hardening), str(SITE)], check=True)

    report = {
        'version': 211,
        'legacy_patches': len(PATCHES),
        'results': results,
        'v202_finalizer': True,
        'v203_hardening': True,
        'provider_assessment_route_v204': True,
        'working_memory_updating_v205': True,
        'prospective_memory_v206': True,
        'associative_binding_v207': True,
        'temporal_order_v208': True,
        'visual_change_detection_v210': True,
        'bank_hardening_v211': True,
        'copy_hardening_v209': True,
        'cognitive_tools': 53,
        'total_lab_tools': 93,
    }
    api = SITE / 'api'
    api.mkdir(parents=True, exist_ok=True)
    (api / 'cognitive-quality-v26.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
