#!/usr/bin/env python3
from pathlib import Path
import base64, html, json, zlib


def _inflate_gzip_payload(blob: bytes) -> bytes:
    """Inflate a gzip member while validating the DEFLATE stream, independent of a damaged trailer CRC."""
    if len(blob) < 18 or blob[:2] != b'\x1f\x8b' or blob[2] != 8:
        raise ValueError('invalid gzip member')
    flags = blob[3]
    pos = 10
    if flags & 0x04:
        if pos + 2 > len(blob):
            raise ValueError('truncated gzip extra header')
        xlen = int.from_bytes(blob[pos:pos + 2], 'little')
        pos += 2 + xlen
    for mask in (0x08, 0x10):
        if flags & mask:
            end = blob.find(b'\x00', pos)
            if end < 0:
                raise ValueError('truncated gzip text header')
            pos = end + 1
    if flags & 0x02:
        pos += 2
    if pos >= len(blob) - 8:
        raise ValueError('truncated gzip payload')
    # The historical publisher payload has a damaged gzip trailer CRC. The raw
    # DEFLATE stream is still authoritative and is validated by zlib itself.
    return zlib.decompress(blob[pos:-8], -zlib.MAX_WBITS)


_boot = Path(__file__).resolve().parents[1] / 'content' / 'v501' / 'bootstrap'
_manifest = _boot / 'manifest.json.gz.b64'
_manifest.write_text(''.join(p.read_text(encoding='ascii') for p in sorted(_boot.glob('manifest.part*'))), encoding='ascii')
_payload = ''.join(p.read_text(encoding='ascii') for p in sorted(_boot.glob('publisher.part*')))
_code_blob = base64.b64decode(_payload)
try:
    _code = _inflate_gzip_payload(_code_blob).decode('utf-8')
except Exception as exc:
    raise RuntimeError(f'wave002 publisher payload is not recoverable: {type(exc).__name__}: {exc}') from exc
exec(compile(_code, __file__, 'exec'), globals(), globals())

_base_publish = publish


def _write_knowledge_hub(site: Path, report: dict) -> None:
    pages = report['pages']
    route = '/special-needs/knowledge/'
    canonical = BASE + route
    groups = {}
    for page in pages:
        groups.setdefault(page['axis'], []).append(page)
    sections = []
    item_list = []
    pos = 1
    for axis in sorted(groups):
        links = []
        for page in groups[axis]:
            links.append(f'<li><a href="{html.escape(page["route"])}">{html.escape(page["title"])}</a></li>')
            item_list.append({'@type':'ListItem','position':pos,'url':BASE + page['route'],'name':page['title']})
            pos += 1
        sections.append(f'<section><h2>{html.escape(axis)}</h2><p>أدلة مترابطة تغطي نوايا البحث العملية في هذا المحور، مع ربط القرار بالمراجع وحدود الاستخدام والقياس.</p><ul>{"".join(links)}</ul></section>')
    desc = 'مركز روافد المعرفي للاحتياجات الخاصة: 100 دليل عربي موثق، منظّم حسب المحور ونية البحث، مع منع التكرار وربط الصفحات بالمصادر الأصلية.'
    ld = {'@context':'https://schema.org','@graph':[{'@type':'CollectionPage','name':'مكتبة روافد المعرفية للاحتياجات الخاصة','url':canonical,'description':desc,'inLanguage':'ar'},{'@type':'BreadcrumbList','itemListElement':[{'@type':'ListItem','position':1,'name':'الرئيسية','item':BASE+'/'},{'@type':'ListItem','position':2,'name':'ذوو الاحتياجات الخاصة','item':BASE+'/special-needs/'},{'@type':'ListItem','position':3,'name':'المكتبة المعرفية','item':canonical}]},{'@type':'ItemList','numberOfItems':len(item_list),'itemListElement':item_list}]}
    text = f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>مكتبة روافد المعرفية للاحتياجات الخاصة | منصة روافد</title><meta name="description" content="{html.escape(desc)}"><meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large"><link rel="canonical" href="{canonical}"><meta property="og:type" content="website"><meta property="og:locale" content="ar_AR"><meta property="og:site_name" content="منصة روافد"><meta property="og:title" content="مكتبة روافد المعرفية للاحتياجات الخاصة"><meta property="og:description" content="{html.escape(desc)}"><meta property="og:url" content="{canonical}"><meta property="og:image" content="{BASE}/assets/brand/rawafid-social-card.jpg"><meta name="twitter:card" content="summary_large_image"><script type="application/ld+json">{json.dumps(ld,ensure_ascii=False)}</script><link rel="stylesheet" href="/assets/brand/rawafid-brand.css"><link rel="stylesheet" href="/assets/platform/platform-core.css?v=1.1.0"><style>body{{font-family:system-ui,sans-serif;line-height:1.9}}main{{max-width:1100px;margin:auto;padding:1rem}}.hero{{padding:2rem 0;border-bottom:1px solid #ddd}}section{{margin:1.25rem 0;padding:1.25rem;border:1px solid #e1e5e8;border-radius:14px}}li{{margin:.35rem 0}}</style></head><body><main><header class="hero"><p>ذوو الاحتياجات الخاصة · مركز موضوعي</p><h1>مكتبة روافد المعرفية للاحتياجات الخاصة</h1><p>{html.escape(desc)}</p><p>تضم هذه الموجة {report['page_count']} صفحة من أصل {report['candidate_pool_count']} مرشحًا. فُحصت المسارات والعناوين الحالية قبل النشر، واستُبعدت المرشحات المتعارضة تلقائيًا. الحد الأدنى للنص المرئي في الأدلة المنشورة: {report['minimum_word_count']} كلمة.</p></header><section><h2>كيف تستخدم المكتبة؟</h2><p>ابدأ بالمحور الأقرب إلى السؤال الفعلي، ثم انتقل إلى الدليل المتخصص بدل الاعتماد على صفحة عامة. داخل كل دليل ستجد أسئلة تحاكي نوايا البحث، خطوات تطبيق أو تقييم، مؤشرات متابعة، حدود استخدام وسلامة، وروابط للمراجع الأساسية. وجود موضوع في المكتبة لا يعني تشخيص شخص بعينه، ولا يحول المعلومات العامة إلى توصية علاجية فردية.</p></section>{''.join(sections)}</main></body></html>'''
    out = site / 'special-needs' / 'knowledge' / 'index.html'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding='utf-8')


def publish(site: Path):
    report = _base_publish(site)
    _write_knowledge_hub(site, report)
    return report
