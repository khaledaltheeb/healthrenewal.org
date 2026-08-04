from pathlib import Path
import json,re,xml.etree.ElementTree as ET

root=Path(__file__).resolve().parents[1]
core=json.loads((root/'api/family-guide-v1.json').read_text(encoding='utf-8'))
ext=json.loads((root/'api/family-guide-v1-phase8.json').read_text(encoding='utf-8'))
manifest=json.loads((root/'api/family-guide-v2.json').read_text(encoding='utf-8'))

assert core['version']=='1.6.0' and len(core['conditions'])==56
assert ext['version']=='1.7.0' and len(ext['conditions'])==8
assert manifest['version']=='2.0.0' and manifest['total_conditions']==64
assert sum(feed['count'] for feed in manifest['feeds'])==64

expected={
    'cdkl5-deficiency-disorder','foxg1-syndrome','dravet-syndrome',
    'maternal-dup15q-syndrome','mecp2-duplication-syndrome',
    '1p36-deletion-syndrome','kcnq2-related-disorders',
    'grin2b-related-neurodevelopmental-disorder'
}
core_slugs={x['slug'] for x in core['conditions']}
ext_slugs={x['slug'] for x in ext['conditions']}
assert ext_slugs==expected and core_slugs.isdisjoint(ext_slugs)
assert len(core_slugs|ext_slugs)==64

phase_text=(root/'family-guide/family-guide-phase8-data.js').read_text(encoding='utf-8')
match=re.search(r'window\.FAMILY_GUIDE_PHASE8_DATA=(\[.*\]);\s*\(function',phase_text,re.S)
assert match
phase_items=json.loads(match.group(1))
assert {x['slug'] for x in phase_items}==expected
assert all(set(x)=={'slug','title','en','classification','summary'} for x in phase_items)
checked_texts=[phase_text]

required=['title','summary','causes','signs','first_steps','avoid','daily','plan30','plan90','plan_year','urgent','professionals','questions','sources']
for slug in expected:
    page=root/'family-guide/conditions'/slug/'index.html'
    data_file=root/'family-guide/conditions'/slug/'data.js'
    assert page.is_file() and data_file.is_file(), slug
    html=page.read_text(encoding='utf-8')
    assert '<!-- pt-platform-shell:v1 -->' in html
    assert 'data-pt-normalized="1.1.0"' in html
    assert f'data-condition="{slug}"' in html
    assert 'family-guide-phase8-data.js?v=1.7.0' in html
    assert 'data.js?v=1.7.0' in html
    data_text=data_file.read_text(encoding='utf-8')
    data_match=re.search(r'\}\)\((\{.*\})\);\s*$',data_text,re.S)
    assert data_match, slug
    item=json.loads(data_match.group(1))
    assert item['slug']==slug
    for key in required: assert item.get(key), (slug,key)
    assert len(item['sources'])>=3
    assert len(item['first_steps'])>=3
    assert len(item['avoid'])>=3
    assert len(item['daily'])>=3
    for _,url in item['sources']: assert url.startswith('https://'), (slug,url)
    checked_texts.extend([html,data_text])

index=(root/'family-guide/index.html').read_text(encoding='utf-8')
readme=(root/'family-guide/README.md').read_text(encoding='utf-8')
# The public wording was tightened for search clarity while preserving the
# governed inventory: 56 core guides + 8 phase-eight guides = 64 case guides.
assert '64 دليل حالة' in index
assert 'numberOfItems":64' in index
assert 'family-guide-phase8-data.js?v=1.7.0' in index
assert 'meta name="keywords"' not in index
assert '**64 دليل حالة**' in readme
assert '24 دليل' not in index+readme

for sitemap in ['sitemap.xml','sitemap-family-guide.xml','sitemap-family-guide-phase8.xml','sitemap-index.xml']:
    ET.parse(root/sitemap)
main_sitemap=(root/'sitemap.xml').read_text(encoding='utf-8')
phase_sitemap=(root/'sitemap-family-guide-phase8.xml').read_text(encoding='utf-8')
index_sitemap=(root/'sitemap-index.xml').read_text(encoding='utf-8')
for slug in expected:
    route=f'/family-guide/conditions/{slug}/'
    assert route in phase_sitemap
    assert route in main_sitemap
# Preserve the phase-specific source file for audit/history, but advertise the
# URLs once through the authoritative main sitemap to avoid duplicate ownership.
assert 'sitemap-family-guide-phase8.xml' not in index_sitemap
assert 'sitemap.xml' in index_sitemap

checked_texts.extend([index,readme,main_sitemap,phase_sitemap,index_sitemap])
checked='\n'.join(checked_texts)
assert 'معاقين' not in checked
assert 'TODO' not in checked
print({'status':'passed','core':56,'phase8':8,'total':64,'version':'1.7.0'})
