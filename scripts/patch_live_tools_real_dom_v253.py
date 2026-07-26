#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

VERSION = 253
STYLE_ID = "tools-real-dom-marshmallow-v253-style"
RUNTIME_ID = "tools-real-dom-marshmallow-v253-runtime"
REPORT = "tools-real-dom-marshmallow-v253.json"
MARKER = "v253"

STYLE = f'''<style id="{STYLE_ID}">
html[data-tools-real-dom="v253"] body main :where(
section,article,form,fieldset,[data-quiz],[data-question],[data-result],[role="radiogroup"],
[class*="quiz"],[class*="question"],[class*="result"],[class*="score"],
[class*="card"],[class*="panel"],[class*="box"]
){{background:linear-gradient(145deg,#fff,#e5faf5)!important;background-color:#fff!important;color:#173f45!important;border-color:#b8ddd7!important;text-shadow:none!important;color-scheme:light!important}}
html[data-tools-real-dom="v253"] body main :where(
[data-option],[role="radio"],.option,.choice,.answer,[class*="option"],[class*="choice"],[class*="answer"],
[role="radiogroup"] button,[data-question] button
){{background:linear-gradient(145deg,#fff,#fff0f5)!important;background-color:#fff!important;color:#173f45!important;border:1px solid #efc4d3!important;border-radius:14px!important;text-shadow:none!important;color-scheme:light!important}}
html[data-tools-real-dom="v253"] body main :where([data-option],[role="radio"],.option,.choice,.answer,[class*="option"],[class*="choice"],[class*="answer"]) :where(*){{color:#173f45!important;text-shadow:none!important}}
html[data-tools-real-dom="v253"] body main :where(.selected,.is-selected,[aria-checked="true"],label:has(input:checked)){{background:linear-gradient(145deg,#fff,#f2edff)!important;border:2px solid #715293!important;color:#173f45!important}}
html[data-tools-real-dom="v253"] body main :where(h1,h2,h3,h4,h5,h6){{color:#5b2946!important;text-shadow:none!important}}
html[data-tools-real-dom="v253"] body main :where(p,li,dd,small,.hint,.help,.description,.explanation){{color:#4d686b!important;text-shadow:none!important}}
html[data-tools-real-dom="v253"] body main :where(label,legend,strong,b,dt,output,span){{color:#173f45!important;text-shadow:none!important}}
html[data-tools-real-dom="v253"] body main :where(input,select,textarea){{background:#fff!important;color:#173f45!important;border-color:#78aca5!important;color-scheme:light!important}}
html[data-tools-real-dom="v253"] body main :where(button,.button,[role="button"],input[type="submit"],input[type="button"]){{background:linear-gradient(145deg,#fff,#e5faf5)!important;color:#103f42!important;border:2px solid #61b3a8!important}}
html[data-tools-real-dom="v253"] body main :where(button,input,select,textarea,label,[role="radio"]):focus-visible{{outline:3px solid #0a7f78!important;outline-offset:3px!important}}
html[data-tools-real-dom="v253"] body main :where(button:disabled,input:disabled,select:disabled,textarea:disabled,[aria-disabled="true"]){{background:#edf3f2!important;color:#526769!important;border-color:#aebfbd!important;opacity:1!important}}
@media(prefers-color-scheme:dark){{html[data-tools-real-dom="v253"],html[data-tools-real-dom="v253"] body{{color-scheme:light!important}}}}
@media(prefers-contrast:more){{html[data-tools-real-dom="v253"] body main :where(section,article,form,fieldset,[data-question],[data-option],[role="radio"],button){{background:#fff!important;color:#000!important;border-color:#000!important;box-shadow:none!important}}}}
@media(prefers-reduced-motion:reduce){{html[data-tools-real-dom="v253"] body *{{animation-duration:.01ms!important;animation-iteration-count:1!important;transition-duration:.01ms!important;scroll-behavior:auto!important}}}}
</style>'''

RUNTIME = f'''<script id="{RUNTIME_ID}">
(()=>{{"use strict";
const V="{MARKER}",Q=(r,s)=>[...r.querySelectorAll(s)],X=new Set(["SCRIPT","STYLE","LINK","META","IMG","VIDEO","CANVAS","SVG","PATH"]);
const S=["section","article","form","fieldset","[data-quiz]","[data-question]","[data-result]","[role='radiogroup']","[class*='quiz']","[class*='question']","[class*='result']","[class*='score']","[class*='card']","[class*='panel']","[class*='box']"].join(",");
const O=["[data-option]","[role='radio']",".option",".choice",".answer","[class*='option']","[class*='choice']","[class*='answer']","[role='radiogroup'] button","[data-question] button"].join(",");
const T="h1,h2,h3,h4,h5,h6,p,li,dd,dt,span,small,strong,b,em,i,label,legend,output";
const C=v=>{{const m=String(v||"").match(/rgba?\\(\\s*(\\d+(?:\\.\\d+)?)\\s*,\\s*(\\d+(?:\\.\\d+)?)\\s*,\\s*(\\d+(?:\\.\\d+)?)(?:\\s*,\\s*(\\d*(?:\\.\\d+)?))?\\s*\\)/i);return m?[+m[1],+m[2],+m[3],m[4]===undefined||m[4]===""?1:+m[4]]:null}};
const L=c=>{{const a=c.slice(0,3).map(n=>{{n/=255;return n<=.04045?n/12.92:Math.pow((n+.055)/1.055,2.4)}});return .2126*a[0]+.7152*a[1]+.0722*a[2]}};
const dark=e=>{{if(!(e instanceof HTMLElement)||X.has(e.tagName))return false;const r=e.getBoundingClientRect(),s=getComputedStyle(e),c=C(s.backgroundColor);return r.width>=180&&r.height>=44&&s.display!=="none"&&s.visibility!=="hidden"&&+s.opacity>=.05&&c&&c[3]>.45&&L(c)<.42}};
const I=(e,k,v)=>e.style.setProperty(k,v,"important");
const opt=e=>e.matches(O),sel=e=>e.matches(".selected,.is-selected,[aria-checked='true']")||!!e.querySelector("input:checked");
const paint=e=>{{if(!(e instanceof HTMLElement)||X.has(e.tagName))return;let bg="linear-gradient(145deg,#fff,#e5faf5)",bd="#b8ddd7",co="#173f45";if(opt(e)){{bg=sel(e)?"linear-gradient(145deg,#fff,#f2edff)":"linear-gradient(145deg,#fff,#fff0f5)";bd=sel(e)?"#715293":"#efc4d3"}}if(e.matches(".correct,.is-correct,[data-state='correct']")){{bd="#68aa96";co="#155f4b"}}if(e.matches(".incorrect,.is-incorrect,[data-state='incorrect']")){{bg="linear-gradient(145deg,#fff,#fff0f5)";bd="#c88294";co="#8d243d"}}I(e,"background",bg);I(e,"background-color","#fff");I(e,"color",co);I(e,"border-color",bd);I(e,"text-shadow","none");I(e,"color-scheme","light");if(opt(e)){{I(e,"border-style","solid");I(e,"border-width",sel(e)?"2px":"1px");I(e,"border-radius","14px")}}e.setAttribute("data-tools-runtime-painted",V);Q(e,T).forEach(n=>{{I(n,"color",co);I(n,"text-shadow","none")}});Q(e,"h1,h2,h3,h4,h5,h6").forEach(n=>I(n,"color","#5b2946"));Q(e,"p,small,.hint,.help,.description,.explanation").forEach(n=>I(n,"color","#4d686b"))}};
let ob=null,pending=false;const apply=()=>{{pending=false;const m=document.querySelector("main");if(!m)return;if(ob)ob.disconnect();const a=new Set(Q(m,S+","+O));Q(m,"*").forEach(e=>{{if(dark(e))a.add(e)}});a.forEach(paint);document.documentElement.setAttribute("data-tools-real-dom",V);document.documentElement.setAttribute("data-tools-real-dom-applied",String(a.size));if(ob)ob.observe(m,{{subtree:true,childList:true,attributes:true,attributeFilter:["class","style","aria-checked","data-state","hidden"]}})}};
const go=()=>{{if(pending)return;pending=true;requestAnimationFrame(apply)}};const start=()=>{{if(!document.querySelector("main"))return;ob=new MutationObserver(go);apply();[50,250,750,1500].forEach(t=>setTimeout(go,t))}};document.readyState==="loading"?document.addEventListener("DOMContentLoaded",start,{{once:true}}):start();
}})();
</script>'''


def block_pattern(tag: str, block_id: str) -> re.Pattern[str]:
    return re.compile(
        rf"<{tag}\b[^>]*\bid\s*=\s*([\"']){re.escape(block_id)}\1[^>]*>.*?</{tag}>",
        re.I | re.S,
    )


def replace_or_insert(text: str, tag: str, block_id: str, block: str, closing: str) -> tuple[str, bool, bool]:
    pattern = block_pattern(tag, block_id)
    matches = list(pattern.finditer(text))
    if len(matches) > 1:
        raise SystemExit(f"duplicate {block_id}")
    if matches:
        old = matches[0].group(0)
        if old == block:
            return text, False, False
        return text[: matches[0].start()] + block + text[matches[0].end() :], True, True
    if closing.lower() not in text.lower():
        raise SystemExit(f"missing {closing}")
    return re.sub(re.escape(closing), lambda m: block + m.group(0), text, count=1, flags=re.I), True, False


def mark_html(text: str) -> tuple[str, bool]:
    match = re.search(r"<html\b[^>]*>", text, re.I | re.S)
    if not match:
        raise SystemExit("missing html")
    tag = match.group(0)
    attr = re.search(r"\bdata-tools-real-dom\s*=\s*([\"'])(.*?)\1", tag, re.I | re.S)
    canonical = 'data-tools-real-dom="v253"'
    if attr:
        if attr.group(0) == canonical:
            return text, False
        new_tag = tag[: attr.start()] + canonical + tag[attr.end() :]
    else:
        new_tag = tag[:-1] + " " + canonical + ">"
    return text[: match.start()] + new_tag + text[match.end() :], True


def patch(site: Path) -> dict[str, object]:
    root = site / "tools"
    pages = sorted(root.rglob("*.html")) if root.is_dir() else []
    if not pages:
        raise SystemExit("no tools pages")
    routes: list[str] = []
    changed = 0
    replaced_styles = 0
    replaced_runtimes = 0
    for page in pages:
        source = page.read_text(encoding="utf-8")
        text, c1 = mark_html(source)
        text, c2, r2 = replace_or_insert(text, "style", STYLE_ID, STYLE, "</head>")
        text, c3, r3 = replace_or_insert(text, "script", RUNTIME_ID, RUNTIME, "</body>")
        if c1 or c2 or c3:
            page.write_text(text, encoding="utf-8")
            changed += 1
        replaced_styles += int(r2)
        replaced_runtimes += int(r3)
        if text.count(f'id="{STYLE_ID}"') != 1 or text.count(f'id="{RUNTIME_ID}"') != 1:
            raise SystemExit(f"invalid blocks: {page}")
        for token in ("data-tools-real-dom=\"v253\"", "data-tools-runtime-painted", "MutationObserver", "style.setProperty(k,v,\"important\")"):
            if token not in text:
                raise SystemExit(f"missing {token}: {page}")
        routes.append(page.relative_to(site).as_posix())
    quiz = site / "tools/quiz/index.html"
    if not quiz.is_file():
        raise SystemExit("missing tools/quiz/index.html")
    digest = hashlib.sha256(quiz.read_bytes()).hexdigest()
    report = {
        "version": VERSION,
        "status": "patched",
        "scope": "tools/**/*.html",
        "pages": len(pages),
        "changed": changed,
        "unchanged": len(pages) - changed,
        "replaced_styles": replaced_styles,
        "replaced_runtimes": replaced_runtimes,
        "quiz": "tools/quiz/index.html",
        "quiz_sha256": digest,
        "real_dom_runtime": True,
        "computed_dark_surface_repair": True,
        "inline_important_override": True,
        "routes": routes,
    }
    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / REPORT).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", type=Path)
    args = parser.parse_args()
    report = patch(args.site.resolve())
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
