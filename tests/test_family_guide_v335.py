from pathlib import Path
import json,re,xml.etree.ElementTree as ET

root=Path(__file__).resolve().parents[1]
api=json.loads((root/'api/family-guide-v1.json').read_text(encoding='utf-8'))
assert api['version']=='1.6.0'
assert len(api['conditions'])==56
slugs=[x['slug'] for x in api['conditions']]
assert len(slugs)==len(set(slugs))
expected_phase3={
    'fetal-alcohol-spectrum-disorders','rett-syndrome','angelman-syndrome',
    'prader-willi-syndrome','williams-syndrome','tourette-syndrome',
    'hydrocephalus','neurofibromatosis-type-1'
}
expected_phase4={
    'spinal-muscular-atrophy','tuberous-sclerosis-complex',
    '22q11-2-deletion-syndrome','charge-syndrome',
    'smith-magenis-syndrome','cri-du-chat-syndrome',
    'joubert-syndrome','16p11-2-deletion-syndrome'
}
expected_phase5={
    'phelan-mcdermid-syndrome','cornelia-de-lange-syndrome',
    'pitt-hopkins-syndrome','kleefstra-syndrome',
    'kabuki-syndrome','kbg-syndrome',
    'rubinstein-taybi-syndrome','sotos-syndrome'
}
expected_phase6={
    'satb2-associated-syndrome','mbd5-haploinsufficiency',
    'adnp-syndrome','dyrk1a-syndrome',
    'med13l-syndrome','christianson-syndrome',
    'coffin-siris-syndrome','wiedemann-steiner-syndrome'
}
expected_phase7={
    'pura-related-neurodevelopmental-disorder',
    'setd1b-related-neurodevelopmental-disorder',
    'hnrnpu-related-neurodevelopmental-disorder',
    'ddx3x-related-neurodevelopmental-disorder',
    'ctnnb1-neurodevelopmental-disorder',
    'okur-chung-neurodevelopmental-syndrome',
    'gria2-related-neurodevelopmental-disorder',
    'gnb5-related-neurodevelopmental-disorder'
}
assert expected_phase3.issubset(set(slugs))
assert expected_phase4.issubset(set(slugs))
assert expected_phase5.issubset(set(slugs))
assert expected_phase6.issubset(set(slugs))
assert expected_phase7.issubset(set(slugs))

required=['title','summary','causes','signs','first_steps','avoid','daily','plan30','plan90','plan_year','urgent','professionals','questions','sources']
for item in api['conditions']:
    slug=item['slug']
    assert item['url'].startswith('https://') and item['data_url'].startswith('https://')
    page=root/'family-guide/conditions'/slug/'index.html'
    data_file=root/'family-guide/conditions'/slug/'data.js'
    assert page.is_file() and data_file.is_file()
    page_text=page.read_text(encoding='utf-8')
    assert '<!-- pt-platform-shell:v1 -->' in page_text
    assert 'data-pt-normalized="1.1.0"' in page_text
    match=re.search(r'\}\)\((\{.*\})\);\s*$',data_file.read_text(encoding='utf-8'),re.S)
    assert match, slug
    condition=json.loads(match.group(1))
    for key in required: assert condition.get(key), (slug,key)
    assert len(condition['sources'])>=3
    assert len(condition['first_steps'])>=3
    assert len(condition['avoid'])>=3
    assert len(condition['daily'])>=3
    for _,url in condition['sources']: assert url.startswith('https://')

for path in [root/'family-guide/index.html',root/'family-guide/family-guide-data.js',root/'family-guide/family-guide-ui.js',root/'family-guide/family-guide.css']:
    assert path.is_file() and path.stat().st_size>500
for tool in ['family-plan','behavior-log','appointment-prep']:
    assert (root/'family-guide/tools'/tool/'index.html').is_file()

text='\n'.join(p.read_text(encoding='utf-8') for p in (root/'family-guide').rglob('*') if p.is_file())
assert 'معاقين' not in text
assert 'TODO' not in text
ET.parse(root/'sitemap-family-guide.xml')
family_sitemap=(root/'sitemap-family-guide.xml').read_text(encoding='utf-8')
special_needs_sitemap=(root/'sitemap-special-needs.xml').read_text(encoding='utf-8')
consolidated={
    'prader-willi-syndrome':'/special-needs/conditions/prader-willi-syndrome/'
}
for slug in slugs:
    family_path=f'/family-guide/conditions/{slug}/'
    if family_path in family_sitemap:
        continue
    assert slug in consolidated, f'unlisted family guide condition: {slug}'
    canonical_path=consolidated[slug]
    page_text=(root/'family-guide/conditions'/slug/'index.html').read_text(encoding='utf-8')
    assert 'content="noindex,follow,noarchive"' in page_text, slug
    assert f'href="https://healthrenewal.org{canonical_path}"' in page_text, slug
    assert canonical_path in special_needs_sitemap, slug
print({'status':'passed','conditions':len(slugs),'tools':3,'version':api['version'],'consolidated':len(consolidated)})
