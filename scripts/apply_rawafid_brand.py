#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRAND_DIR = ROOT / "assets" / "brand"
BRAND_DIR.mkdir(parents=True, exist_ok=True)

BRAND_NAME = "منصة روافد"
BRAND_LONG = "منصة روافد للعافية النفسية والدمج والتمكين"
TAGLINE = "للعافية النفسية والدمج والتمكين"
DESCRIPTION = (
    "منصة روافد منصة عربية للعافية النفسية والدمج والتمكين، تقدم موسوعة موثقة، "
    "أدلة عملية، أدوات تفاعلية، ومسارات معرفية داعمة للأفراد والأسر والمختصين والمجتمع."
)
PRIMARY = "#0b8f92"
RUNTIME_SOURCE = ROOT / "scripts" / "rawafid_brand_runtime.js"

MARK_SYMBOL = r'''
<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#063f49"/><stop offset=".5" stop-color="#087e82"/><stop offset="1" stop-color="#0d555c"/></linearGradient>
  <radialGradient id="halo"><stop stop-color="#efff67" stop-opacity=".92"/><stop offset="1" stop-color="#efff67" stop-opacity="0"/></radialGradient>
  <linearGradient id="aqua" x1="0" y1="1" x2="1" y2="0"><stop stop-color="#00a7c2"/><stop offset=".52" stop-color="#12d8d0"/><stop offset="1" stop-color="#66f3de"/></linearGradient>
  <linearGradient id="green" x1="0" y1="1" x2="1" y2="0"><stop stop-color="#159b57"/><stop offset=".55" stop-color="#74d43c"/><stop offset="1" stop-color="#d7f33b"/></linearGradient>
  <linearGradient id="gold" x1="0" y1="1" x2="1" y2="0"><stop stop-color="#f08a16"/><stop offset=".55" stop-color="#ffc52f"/><stop offset="1" stop-color="#fff36b"/></linearGradient>
  <radialGradient id="sun"><stop stop-color="#fff76a"/><stop offset=".45" stop-color="#ffc72c"/><stop offset="1" stop-color="#f28a13"/></radialGradient>
  <filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="14"/></filter>
  <filter id="shadow" x="-30%" y="-30%" width="160%" height="180%"><feDropShadow dx="0" dy="11" stdDeviation="10" flood-color="#001a20" flood-opacity=".38"/></filter>
</defs>
<rect x="18" y="18" width="476" height="476" rx="112" fill="url(#bg)" stroke="#35d9d0" stroke-opacity=".38" stroke-width="5"/>
<circle cx="303" cy="155" r="118" fill="url(#halo)" filter="url(#glow)"/>
<g filter="url(#shadow)">
  <circle cx="274" cy="142" r="36" fill="url(#sun)" stroke="#df7112" stroke-width="3"/>
  <path d="M244 395C203 322 203 231 255 171C272 245 275 318 244 395Z" fill="url(#aqua)" stroke="#006e89" stroke-width="3"/>
  <path d="M250 391C270 295 318 221 391 189C381 278 333 349 250 391Z" fill="url(#green)" stroke="#218d42" stroke-width="3"/>
  <path d="M237 391C229 314 191 255 132 222C132 298 169 358 237 391Z" fill="url(#aqua)" stroke="#0087a2" stroke-width="3"/>
  <path d="M245 394C249 317 284 257 343 221C339 297 306 357 245 394Z" fill="url(#gold)" stroke="#db7c13" stroke-width="3"/>
  <path d="M226 396C203 345 164 316 111 305C126 355 166 390 226 396Z" fill="url(#green)" stroke="#2c9639" stroke-width="3"/>
  <path d="M255 404C309 352 368 330 434 342C395 389 334 410 255 404Z" fill="url(#aqua)" stroke="#008ba7" stroke-width="3"/>
  <path d="M83 409C180 447 313 445 445 385C348 471 202 488 83 427Z" fill="url(#aqua)" stroke="#007c98" stroke-width="4"/>
  <path d="M172 457C269 469 363 447 443 402C375 473 276 497 172 474Z" fill="url(#gold)" stroke="#d77d16" stroke-width="3"/>
</g>
'''


def mark_svg() -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" role="img" aria-labelledby="title desc">
<title id="title">شعار منصة روافد</title><desc id="desc">رمز العافية والنمو والدمج والتمكين بألوان زاهية تبعث الأمل</desc>
{MARK_SYMBOL}
</svg>\n'''


def lockup_svg() -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1400 480" role="img" aria-labelledby="title desc">
<title id="title">منصة روافد</title><desc id="desc">{TAGLINE}</desc>
<defs><linearGradient id="word" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#086f7c"/><stop offset=".55" stop-color="#08aeb4"/><stop offset="1" stop-color="#0d7f86"/></linearGradient></defs>
<g transform="translate(26,-16) scale(.93)">{MARK_SYMBOL}</g>
<text x="1360" y="214" direction="rtl" text-anchor="end" font-family="Noto Kufi Arabic, Noto Sans Arabic, Tahoma, Arial, sans-serif" font-size="112" font-weight="900" fill="url(#word)">{BRAND_NAME}</text>
<text x="1360" y="310" direction="rtl" text-anchor="end" font-family="Noto Sans Arabic, Tahoma, Arial, sans-serif" font-size="46" font-weight="700" fill="#0b6f72">{TAGLINE}</text>
<path d="M610 345H1355" stroke="#f4b942" stroke-width="8" stroke-linecap="round" opacity=".85"/>
</svg>\n'''


def social_svg() -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 630" role="img" aria-labelledby="title desc">
<title id="title">{BRAND_NAME}</title><desc id="desc">{TAGLINE}</desc>
<defs><linearGradient id="card" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#e7fffd"/><stop offset=".55" stop-color="#ffffff"/><stop offset="1" stop-color="#fff4cc"/></linearGradient><filter id="soft"><feDropShadow dx="0" dy="18" stdDeviation="22" flood-color="#075f62" flood-opacity=".18"/></filter></defs>
<rect width="1200" height="630" fill="url(#card)"/><circle cx="120" cy="90" r="230" fill="#16c6c7" opacity=".12"/><circle cx="1110" cy="590" r="260" fill="#f4b942" opacity=".16"/><rect x="34" y="34" width="1132" height="562" rx="48" fill="none" stroke="#0b8f92" stroke-opacity=".28" stroke-width="4"/>
<g transform="translate(58,72) scale(.84)" filter="url(#soft)">{MARK_SYMBOL}</g>
<text x="1135" y="260" direction="rtl" text-anchor="end" font-family="Noto Kufi Arabic, Noto Sans Arabic, Tahoma, Arial, sans-serif" font-size="92" font-weight="900" fill="#087e86">{BRAND_NAME}</text>
<text x="1135" y="355" direction="rtl" text-anchor="end" font-family="Noto Sans Arabic, Tahoma, Arial, sans-serif" font-size="43" font-weight="700" fill="#0b6f72">{TAGLINE}</text>
<text x="1135" y="430" direction="rtl" text-anchor="end" font-family="Noto Sans Arabic, Tahoma, Arial, sans-serif" font-size="28" fill="#456f73">معرفة موثوقة • أدلة عملية • أدوات داعمة</text>
</svg>\n'''


def write_assets() -> None:
    (BRAND_DIR / "logo-mark.svg").write_text(mark_svg(), encoding="utf-8")
    (BRAND_DIR / "logo-lockup.svg").write_text(lockup_svg(), encoding="utf-8")
    (BRAND_DIR / "social-card.svg").write_text(social_svg(), encoding="utf-8")
    (BRAND_DIR / "rawafid-brand.css").write_text(''':root{--rawafid-teal:#0b8f92;--rawafid-turquoise:#16c6c7;--rawafid-green:#76c844;--rawafid-gold:#f4b942;--rawafid-deep:#075f62;--rawafid-mist:#effcfb;--brand:var(--rawafid-teal);--accent:var(--rawafid-gold)}
::selection{background:rgba(22,198,199,.24);color:#073f42}.brand img,.site-brand img,[class*="brand"] img{object-fit:contain}.brand img{border-radius:18%}.rawafid-brand-lockup{width:min(560px,100%);height:auto;display:block}.rawafid-tagline{color:#0b6f72;font-weight:700;letter-spacing:.01em}
''', encoding="utf-8")
    if not RUNTIME_SOURCE.is_file():
        raise SystemExit(f"Missing canonical brand runtime: {RUNTIME_SOURCE}")
    (BRAND_DIR / "rawafid-brand.js").write_text(RUNTIME_SOURCE.read_text(encoding="utf-8"), encoding="utf-8")


def render_pngs() -> None:
    import cairosvg
    cairosvg.svg2png(bytestring=mark_svg().encode(), write_to=str(BRAND_DIR / "rawafid-mark.png"), output_width=512, output_height=512)
    cairosvg.svg2png(bytestring=lockup_svg().encode(), write_to=str(BRAND_DIR / "rawafid-logo.png"), output_width=1400, output_height=480)
    cairosvg.svg2png(bytestring=social_svg().encode(), write_to=str(BRAND_DIR / "rawafid-social-card.png"), output_width=1200, output_height=630)
    from PIL import Image
    mark = Image.open(BRAND_DIR / "rawafid-mark.png").convert("RGBA")
    for size, name in ((16,"favicon-16x16.png"),(32,"favicon-32x32.png"),(48,"favicon-48x48.png"),(180,"apple-touch-icon.png"),(192,"android-chrome-192x192.png"),(512,"android-chrome-512x512.png")):
        mark.resize((size,size), Image.Resampling.LANCZOS).save(ROOT / name, optimize=True)
    mark.save(ROOT / "favicon.ico", format="ICO", sizes=[(16,16),(32,32),(48,48),(64,64)])
    Image.open(BRAND_DIR / "rawafid-social-card.png").convert("RGB").save(BRAND_DIR / "rawafid-social-card.jpg", quality=94, optimize=True, progressive=True)


TEXT_EXTENSIONS={".html",".htm",".xml",".json",".webmanifest",".md",".txt",".csv",".py",".js",".mjs",".cjs",".ts",".tsx",".jsx",".yml",".yaml",".svg"}
SKIP_DIRS={".git","node_modules",".venv","venv","vendor","dist","build"}
SKIP_FILES={Path("scripts/apply_rawafid_brand.py"),Path("scripts/rawafid_brand_runtime.js"),Path(".github/workflows/apply-rawafid-brand.yml")}
REPLACEMENTS=(
("بوابة الصحة النفسية وذوي الاحتياجات الخاصة","بوابة منصة روافد"),
("منصة الصحة النفسية وذوي الاحتياجات الخاصة",BRAND_NAME),
("شعار منصة الصحة النفسية وذوي الاحتياجات الخاصة",f"شعار {BRAND_NAME}"),
("البحث في منصة الصحة النفسية",f"البحث في {BRAND_NAME}"),
("# مصطلحات علم النفس | Psychology Terminology","# منصة روافد | Rawafid Platform"),
("Psychology Terminology","Rawafid Platform"),
("معرفة تحترم الإنسان. دعم يوسّع الإمكانات.",TAGLINE),
("https://healthrenewal.org/assets/brand/social-card.svg","https://healthrenewal.org/assets/brand/rawafid-social-card.jpg"),
("/assets/brand/social-card.svg","/assets/brand/rawafid-social-card.jpg"))


def eligible(path:Path)->bool:
    rel=path.relative_to(ROOT)
    if path.suffix.lower() == ".html" and re.fullmatch(r"(?:google|bing|yandex|baidu)[A-Za-z0-9._-]*\.html", path.name, re.I):
        return False
    return rel not in SKIP_FILES and path.suffix.lower() in TEXT_EXTENSIONS and not any(part in SKIP_DIRS for part in rel.parts)


def replace_brand_text()->tuple[int,int]:
    changed=total=0
    for path in ROOT.rglob("*"):
        if not path.is_file() or not eligible(path): continue
        try: text=path.read_text(encoding="utf-8")
        except UnicodeDecodeError: continue
        original=text
        for old,new in REPLACEMENTS:
            n=text.count(old); total+=n
            if n: text=text.replace(old,new)
        if text!=original: path.write_text(text,encoding="utf-8"); changed+=1
    return changed,total


FAVICON_BLOCK='''<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="icon" type="image/svg+xml" href="/assets/brand/logo-mark.svg">
<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png">
<link rel="icon" type="image/png" sizes="16x16" href="/favicon-16x16.png">
<link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">
<link rel="stylesheet" href="/assets/brand/rawafid-brand.css">
<script defer src="/assets/brand/rawafid-brand.js"></script>'''


def enrich_html(text:str)->str:
    text=re.sub(r'<link\s+rel=["\'](?:shortcut )?icon["\'][^>]*>\s*',"",text,flags=re.I)
    text=re.sub(r'<link\s+rel=["\']apple-touch-icon["\'][^>]*>\s*',"",text,flags=re.I)
    text=re.sub(r'<link[^>]+rawafid-brand\.css[^>]*>\s*',"",text,flags=re.I)
    text=re.sub(r'<script[^>]+rawafid-brand\.js[^>]*></script>\s*',"",text,flags=re.I)
    additions=FAVICON_BLOCK
    if 'name="application-name"' not in text and "name='application-name'" not in text: additions+=f'\n<meta name="application-name" content="{BRAND_NAME}">' 
    if 'property="og:site_name"' not in text and "property='og:site_name'" not in text: additions+=f'\n<meta property="og:site_name" content="{BRAND_NAME}">' 
    if 'name="theme-color"' not in text and "name='theme-color'" not in text: additions+=f'\n<meta name="theme-color" content="{PRIMARY}">' 
    if "</head>" not in text: return text
    text=text.replace("</head>",additions+"\n</head>",1)
    return re.sub(r'(<meta\s+name=["\']theme-color["\']\s+content=["\'])#[0-9a-fA-F]{6}(["\'])',rf'\g<1>{PRIMARY}\2',text)


def enrich_all_html()->int:
    changed=0
    for path in ROOT.rglob("*.html"):
        if not eligible(path): continue
        text=path.read_text(encoding="utf-8"); updated=enrich_html(text)
        if updated!=text: path.write_text(updated,encoding="utf-8"); changed+=1
    return changed


def update_homepage(path:Path)->None:
    if not path.is_file(): return
    text=path.read_text(encoding="utf-8")
    text=re.sub(r"<title>.*?</title>",f"<title>{BRAND_NAME} | العافية النفسية والدمج والتمكين</title>",text,count=1,flags=re.S)
    patterns=(("name","description",DESCRIPTION),("name","author",BRAND_NAME),("name","application-name",BRAND_NAME),("property","og:title",f"{BRAND_NAME} | العافية النفسية والدمج والتمكين"),("property","og:description",DESCRIPTION),("name","twitter:title",f"{BRAND_NAME} | العافية النفسية والدمج والتمكين"),("name","twitter:description",DESCRIPTION))
    for attr,key,value in patterns:
        text=re.sub(rf'(<meta\s+{attr}=["\']{re.escape(key)}["\']\s+content=["\']).*?(["\']\s*/?>)',lambda m:m.group(1)+value+m.group(2),text,count=1,flags=re.S)
    text=text.replace('content="#075f5b"',f'content="{PRIMARY}"').replace('--brand:#075f5b','--brand:#0b8f92').replace('--accent:#87345d','--accent:#f4b942')
    path.write_text(text,encoding="utf-8")


def update_manifests()->int:
    changed=0
    for path in ROOT.rglob("manifest.webmanifest"):
        if not eligible(path): continue
        try: data=json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError,UnicodeDecodeError): continue
        data.update({"name":BRAND_LONG,"short_name":"روافد","description":DESCRIPTION,"theme_color":PRIMARY,"background_color":"#f7fffe"})
        data["icons"]=[{"src":"/android-chrome-192x192.png","sizes":"192x192","type":"image/png","purpose":"any maskable"},{"src":"/android-chrome-512x512.png","sizes":"512x512","type":"image/png","purpose":"any maskable"}]
        path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); changed+=1
    return changed


def validate()->dict[str,int]:
    html=[p for p in ROOT.rglob("*.html") if eligible(p)]
    if not html: raise SystemExit("No HTML files found")
    missing=[p for p in html if "/assets/brand/rawafid-brand.css" not in p.read_text(encoding="utf-8")]
    if missing: raise SystemExit(f"Brand stylesheet missing from {len(missing)} HTML files; first={missing[0]}")
    stale=[]; old="منصة الصحة النفسية وذوي الاحتياجات الخاصة"
    for p in ROOT.rglob("*"):
        if p.is_file() and eligible(p):
            try:
                if old in p.read_text(encoding="utf-8"): stale.append(p)
            except UnicodeDecodeError: pass
    if stale: raise SystemExit(f"Legacy platform name remains in {len(stale)} files; first={stale[0]}")
    required=[BRAND_DIR/"logo-mark.svg",BRAND_DIR/"logo-lockup.svg",BRAND_DIR/"rawafid-social-card.jpg",ROOT/"favicon.ico",ROOT/"apple-touch-icon.png",ROOT/"manifest.webmanifest",RUNTIME_SOURCE]
    absent=[p for p in required if not p.is_file() or p.stat().st_size==0]
    if absent: raise SystemExit(f"Missing required brand assets: {absent}")
    deployed_runtime=(BRAND_DIR/"rawafid-brand.js").read_text(encoding="utf-8")
    canonical_runtime=RUNTIME_SOURCE.read_text(encoding="utf-8")
    if deployed_runtime != canonical_runtime:
        raise SystemExit("WebMCP brand runtime drifted from canonical source")
    for marker in ("document.modelContext","registerTool","toolname","tooldescription","inputSchema"):
        if marker not in deployed_runtime:
            raise SystemExit(f"WebMCP runtime missing marker: {marker}")
    homepage=(ROOT/"index.html").read_text(encoding="utf-8")
    for marker in (BRAND_NAME,TAGLINE,"rawafid-social-card.jpg","logo-mark.svg"):
        if marker not in homepage: raise SystemExit(f"Homepage missing brand marker: {marker}")
    return {"html_files":len(html),"stale_brand_files":len(stale)}


def main()->None:
    changed,replacements=replace_brand_text(); write_assets(); render_pngs(); html_changed=enrich_all_html(); update_homepage(ROOT/"index.html")
    if (ROOT/"site/index.html").is_file(): update_homepage(ROOT/"site/index.html")
    manifests=update_manifests(); result=validate(); result.update({"text_files_changed":changed,"text_replacements":replacements,"html_files_enriched":html_changed,"manifests_updated":manifests})
    report=ROOT/"reports/rawafid-brand-rollout.json"; report.parent.mkdir(parents=True,exist_ok=True); report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=="__main__": main()
