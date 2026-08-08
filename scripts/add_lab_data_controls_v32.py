from __future__ import annotations

import argparse
import json
from pathlib import Path

START = "/* lab-data-controls-v32:start */"
END = "/* lab-data-controls-v32:end */"
BLOCK = r'''
/* lab-data-controls-v32:start */
(()=>{
 'use strict';
 const readDefinition=()=>{
  const node=document.getElementById('lab-definition');
  if(!node)return null;
  try{return JSON.parse(node.textContent||'null')}catch{return null}
 };
 const keyFor=d=>`pterminology:v12:${d.slug}`;
 const safeState=d=>{
  try{
   const raw=localStorage.getItem(keyFor(d));
   if(!raw)return null;
   const parsed=JSON.parse(raw);
   return parsed&&typeof parsed==='object'?parsed:null;
  }catch{return null}
 };
 const download=(name,payload)=>{
  const blob=new Blob([JSON.stringify(payload,null,2)],{type:'application/json;charset=utf-8'});
  const url=URL.createObjectURL(blob),anchor=document.createElement('a');
  anchor.href=url;anchor.download=name;anchor.rel='noopener';document.body.appendChild(anchor);anchor.click();anchor.remove();
  setTimeout(()=>URL.revokeObjectURL(url),0);
 };
 const announce=(host,message)=>{
  const node=host.querySelector('.lab-data-controls-v32__status');
  if(node)node.textContent=message;
 };
 const mount=()=>{
  const d=readDefinition(),host=document.querySelector('[data-v12-lab]');
  if(!d?.slug||!host||document.querySelector('.lab-data-controls-v32'))return;
  const section=document.createElement('section');
  section.className='lab-data-controls-v32';
  section.setAttribute('aria-labelledby','lab-data-controls-v32-title');
  section.innerHTML=`<style>
   .lab-data-controls-v32{margin-block:1.25rem;padding:1rem;border:1px solid #b9ddd8;border-radius:1rem;background:#fff;line-height:1.8}
   .lab-data-controls-v32__actions{display:flex;flex-wrap:wrap;gap:.65rem;margin-block:.75rem}
   .lab-data-controls-v32 button{min-height:44px;min-width:44px;padding:.7rem 1rem;border-radius:.8rem;border:1px solid #537b76;background:#fff;color:#173b37;font:inherit;font-weight:800;cursor:pointer}
   .lab-data-controls-v32 button:focus-visible{outline:3px solid #0b7a75;outline-offset:3px}
   .lab-data-controls-v32__danger{border-color:#9b2c2c!important;color:#7b2020!important}
   @media print{.lab-data-controls-v32{display:none!important}}
  </style><h2 id="lab-data-controls-v32-title">بيانات هذه الجلسة على جهازك</h2>
  <p>الحفظ محلي في هذا المتصفح. يمكنك تصدير نسخة JSON إلى جهازك، طباعة الصفحة، أو حذف السجل المحلي. هذه الأزرار لا ترسل إجاباتك إلى خادم.</p>
  <div class="lab-data-controls-v32__actions">
   <button type="button" data-lab-export>تصدير السجل محليًا</button>
   <button type="button" data-lab-print>طباعة الصفحة</button>
   <button type="button" class="lab-data-controls-v32__danger" data-lab-delete>حذف السجل المحلي</button>
  </div><p class="lab-data-controls-v32__status" role="status" aria-live="polite"></p>`;
  host.insertAdjacentElement('afterend',section);
  section.querySelector('[data-lab-export]').addEventListener('click',()=>{
   const state=safeState(d);
   download(`${d.slug}-local-session.json`,{schema_version:32,slug:d.slug,title:d.title||d.slug,exported_at:new Date().toISOString(),storage:'local-only',state});
   announce(section,'تم إنشاء ملف محلي من السجل الحالي.');
  });
  section.querySelector('[data-lab-print]').addEventListener('click',()=>window.print());
  section.querySelector('[data-lab-delete]').addEventListener('click',()=>{
   if(!window.confirm('حذف السجل المحفوظ لهذه الأداة من هذا المتصفح؟ لا يمكن التراجع عن الحذف.'))return;
   localStorage.removeItem(keyFor(d));
   announce(section,'تم حذف السجل المحلي لهذه الأداة.');
   window.setTimeout(()=>window.location.reload(),120);
  });
 };
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',mount,{once:true});else mount();
})();
/* lab-data-controls-v32:end */
'''.strip()


def patch(site: Path) -> dict:
    runtime = site / "assets" / "js" / "lab-v12.js"
    if not runtime.is_file():
        raise SystemExit(f"missing runtime: {runtime}")
    source = runtime.read_text(encoding="utf-8")
    if START not in source:
        source = source.rstrip() + "\n\n" + BLOCK + "\n"
        runtime.write_text(source, encoding="utf-8")
    assessment = sorted((site / "assessment-lab").glob("*/index.html"))
    cognitive = sorted((site / "cognitive-lab").glob("*/index.html"))
    checks = {
        "marker": START in source and END in source,
        "outside_rerendering_host": "host.insertAdjacentElement('afterend',section)" in source,
        "export_local_json": "new Blob([JSON.stringify(payload,null,2)]" in source and "URL.createObjectURL(blob)" in source,
        "print": "window.print()" in source,
        "delete_local_only": "localStorage.removeItem(keyFor(d))" in source,
        "no_network_transport": all(token not in BLOCK for token in ("fetch(", "XMLHttpRequest", "sendBeacon", "WebSocket")),
        "confirm_before_delete": "window.confirm(" in source,
        "live_status": 'aria-live="polite"' in source,
        "touch_target": "min-height:44px" in source and "min-width:44px" in source,
    }
    report = {
        "version": 32,
        "status": "passed" if len(assessment) == 40 and len(cognitive) == 53 and all(checks.values()) else "failed",
        "assessment_pages": len(assessment),
        "cognitive_pages": len(cognitive),
        "total_tools": len(assessment) + len(cognitive),
        **checks,
    }
    api = site / "api"
    api.mkdir(parents=True, exist_ok=True)
    (api / "lab-data-controls-v32.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if report["status"] != "passed":
        raise SystemExit(report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("site", nargs="?", type=Path, default=Path("_site"))
    args = parser.parse_args()
    print(json.dumps(patch(args.site.resolve()), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
