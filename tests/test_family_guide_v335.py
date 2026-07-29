from pathlib import Path
import json,re,xml.etree.ElementTree as ET
root=Path(__file__).resolve().parents[1]
data=json.loads((root/'api/family-guide-v1.json').read_text(encoding='utf-8'))
assert data['version']=='1.0.0'
assert len(data['conditions'])>=8
slugs=[x['slug'] for x in data['conditions']]
assert len(slugs)==len(set(slugs))
required=['title','summary','causes','signs','first_steps','avoid','daily','plan30','plan90','plan_year','urgent','professionals','questions','sources']
for c in data['conditions']:
    for k in required: assert c.get(k), (c['slug'],k)
    assert (root/'family-guide/conditions'/c['slug']/'index.html').is_file()
    assert len(c['sources'])>=3
    for _,u in c['sources']: assert u.startswith('https://')
for path in [root/'family-guide/index.html',root/'family-guide/family-guide-data.js',root/'family-guide/family-guide-ui.js',root/'family-guide/family-guide.css']:
    assert path.is_file() and path.stat().st_size>500
for tool in ['family-plan','behavior-log','appointment-prep']:
    assert (root/'family-guide/tools'/tool/'index.html').is_file()
text='\n'.join(p.read_text(encoding='utf-8') for p in (root/'family-guide').rglob('*') if p.is_file())
assert 'معاقين' not in text
assert 'TODO' not in text
ET.parse(root/'sitemap-family-guide.xml')
listed=(root/'sitemap-family-guide.xml').read_text(encoding='utf-8')
for s in slugs: assert f'/family-guide/conditions/{s}/' in listed
print({'status':'passed','conditions':len(slugs),'tools':3})
