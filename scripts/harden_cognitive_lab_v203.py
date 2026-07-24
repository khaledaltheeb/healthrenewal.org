from __future__ import annotations

import json
import sys
from pathlib import Path

SITE = Path(sys.argv[1] if len(sys.argv) > 1 else "_site")
JS = SITE / "assets/js/lab-v12.js"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    if old not in text:
        raise SystemExit(f"Missing v203 patch target: {label}")
    return text.replace(old, new, 1)


def main() -> None:
    if not JS.exists():
        raise SystemExit(f"Missing runtime: {JS}")
    text = JS.read_text(encoding="utf-8")

    old_finish = "function v202Finish(d,stage,rnd,data){let options=[...new Map(data.options.map(x=>[v202Val(x),x])).values()],answer=String(data.answer);if(!options.some(x=>v202Val(x)===answer))options.push(v202Opt(answer));options=shuffle(options,rnd);const values=options.map(v202Val);if(values.filter(x=>x===answer).length!==1)throw new Error(`Invalid answer key: ${d.slug}`);if(values.length<2)throw new Error(`Insufficient choices: ${d.slug}`);const prompt=String(data.prompt||'');const fingerprint=String([...`${d.slug}|${stage}|${prompt}|${answer}`].reduce((h,c)=>Math.imul(h^c.codePointAt(0),16777619)>>>0,2166136261));return{kind:'text',explanation:`الإجابة الصحيحة هي ${answer}.`,audioCount:0,delay:0,study:'',studyMs:0,stimulusWord:'',stimulusInk:'',stimulusRule:'',...data,prompt,answer,options,difficulty:stage+1,fingerprint,bankVersion:202}}"
    new_finish = "function v202Finish(d,stage,rnd,data){let answer=String(data.answer),options=[...new Map((data.options||[]).map(x=>[v202Val(x),x])).values()];if(!answer||/^(?:undefined|NaN|null)$/i.test(answer))throw new Error(`Invalid answer value: ${d.slug}`);if(!options.some(x=>v202Val(x)===answer))options.push(v202Opt(answer));const numeric=Number(answer),sequenceTokens=answer.split(/(?:\\s+|→|-)/).filter(Boolean),fallback=[];if(Number.isFinite(numeric)){for(let n=1;n<=6;n++)fallback.push(String(numeric+n),String(numeric-n))}else if(sequenceTokens.length>1){const last=sequenceTokens.at(-1),replacement=/^\\d+$/.test(last)?String((Number(last)%9)+1):['●','▲','■','◆','★','أ','ب','ج','د','هـ'].find(x=>x!==last)||'□';fallback.push([...sequenceTokens.slice(0,-1),replacement].join(' '),[...sequenceTokens].reverse().join(' '),[...sequenceTokens.slice(1),sequenceTokens[0]].join(' '))}else if(answer==='نعم'||answer==='لا'){fallback.push(answer==='نعم'?'لا':'نعم')}else if(answer==='استجب'||answer==='امتنع'){fallback.push(answer==='استجب'?'امتنع':'استجب')}else fallback.push('خيار مختلف','لا ينطبق','إجابة أخرى');for(const item of fallback){if(options.length>=4)break;if(String(item)!==answer&&!options.some(x=>v202Val(x)===String(item)))options.push(v202Opt(item))}options=shuffle(options,rnd);const values=options.map(v202Val);if(values.filter(x=>x===answer).length!==1)throw new Error(`Invalid answer key: ${d.slug}`);if(values.length<2)throw new Error(`Insufficient choices after repair: ${d.slug}`);if(values.some(x=>/^(?:undefined|NaN|null)$/i.test(x)))throw new Error(`Invalid choice value: ${d.slug}`);const prompt=String(data.prompt||'');if(/undefined|NaN/.test(prompt))throw new Error(`Invalid prompt value: ${d.slug}`);const fingerprint=String([...`${d.slug}|${stage}|${prompt}|${answer}`].reduce((h,c)=>Math.imul(h^c.codePointAt(0),16777619)>>>0,2166136261));return{kind:'text',explanation:`الإجابة الصحيحة هي ${answer}.`,audioCount:0,delay:0,study:'',studyMs:0,stimulusWord:'',stimulusInk:'',stimulusRule:'',...data,prompt,answer,options,difficulty:stage+1,fingerprint,bankVersion:203}}"
    text = replace_once(text, old_finish, new_finish, "strict distractor repair")

    text = replace_once(
        text,
        "seq.push(letters[li+i])",
        "seq.push(letters[(li+i)%letters.length])",
        "trail sequence bounds",
    )
    text = replace_once(
        text,
        "letters[li+length]",
        "letters[(li+length)%letters.length]",
        "trail answer bounds",
    )
    text = replace_once(
        text,
        "letters[Math.max(0,li+length-2)]",
        "letters[(li+length-2+letters.length)%letters.length]",
        "trail distractor bounds",
    )

    fallback = " const legacy=legacyMakeTrialV202(d,stage,index,sessionSeed);return v202Finish(d,stage,rnd,legacy)}"
    randomized_control_memory = """ if(mode==='go_no_go'){const go=pick(symbols),noGo=pick(symbols.filter(x=>x!==go)),shouldGo=rnd()>.38,shown=shouldGo?go:noGo,answer=shouldGo?'استجب':'امتنع';return v202Finish(d,stage,rnd,{prompt:`القاعدة: استجب عند ${go} وامتنع عند ${noGo}. ظهر ${shown}. ماذا تختار؟`,answer,options:['استجب','امتنع'],explanation:shouldGo?`ظهر رمز الاستجابة ${go}.`:`ظهر رمز الامتناع ${noGo}.`})}
 if(mode==='one_back'){const length=5+stage,seq=Array.from({length},()=>pick(symbols)),match=rnd()>.5;seq[length-1]=match?seq[length-2]:pick(symbols.filter(x=>x!==seq[length-2]));return v202Finish(d,stage,rnd,{prompt:`هل يطابق الرمز الأخير الرمز السابق مباشرة؟ ${seq.join(' ')}`,answer:match?'نعم':'لا',options:['نعم','لا'],explanation:match?'الرمزان الأخيران متطابقان.':'الرمزان الأخيران مختلفان.'})}
 if(mode==='two_back'){const length=6+stage,seq=Array.from({length},()=>pick(symbols)),match=rnd()>.5;seq[length-1]=match?seq[length-3]:pick(symbols.filter(x=>x!==seq[length-3]));return v202Finish(d,stage,rnd,{prompt:`هل يطابق الرمز الأخير الرمز الذي سبقه بموقعين؟ ${seq.join(' ')}`,answer:match?'نعم':'لا',options:['نعم','لا'],explanation:match?'الرمز الأخير يطابق رمز الموقع السابق بموقعين.':'الرمز الأخير لا يطابق رمز الموقع السابق بموقعين.'})}
 const legacy=legacyMakeTrialV202(d,stage,index,sessionSeed);return v202Finish(d,stage,rnd,legacy)}"""
    text = replace_once(text, fallback, randomized_control_memory, "session-randomized Go/No-Go and N-back")

    text = text.replace("bankVersion:202", "bankVersion:203")
    text = text.replace("question_pool_version\":202", "question_pool_version\":203")
    JS.write_text(text, encoding="utf-8")

    report = {
        "version": 203,
        "invalid_value_guard": True,
        "distractor_repair": True,
        "trail_bounds_fixed": True,
        "go_no_go_randomized": True,
        "one_back_randomized": True,
        "two_back_randomized": True,
        "minimum_choices": 2,
    }
    api = SITE / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "cognitive-lab-v203.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
