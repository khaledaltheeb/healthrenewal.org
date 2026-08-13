from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path
from scripts.publish_special_needs_reference_cluster_v1 import PAGES, main

class ReferenceClusterTests(unittest.TestCase):
    def test_page_contract(self):
        self.assertEqual(len(PAGES), 8)
        self.assertEqual(len({p['slug'] for p in PAGES}), len(PAGES))
        for p in PAGES:
            self.assertGreaterEqual(len(p['questions']), 5)
            self.assertGreaterEqual(len(p['actions']), 4)
            self.assertGreaterEqual(len(p['myths']), 3)
            self.assertGreaterEqual(len(p['sources']), 1)
            self.assertGreater(len(p['desc']), 100)
    def test_publish(self):
        with tempfile.TemporaryDirectory() as tmp:
            import sys
            old=sys.argv[:]
            try:
                sys.argv=['publisher',tmp]
                self.assertEqual(main(),0)
            finally:
                sys.argv=old
            root=Path(tmp)
            report=json.loads((root/'api/special-needs-reference-cluster-v1.json').read_text(encoding='utf-8'))
            self.assertEqual(report['status'],'passed')
            self.assertEqual(report['referencePages'],8)
            for p in PAGES:
                text=(root/'special-needs/reference'/p['slug']/'index.html').read_text(encoding='utf-8')
                self.assertIn('<h1>',text)
                self.assertIn('canonical',text)
                self.assertIn('المراجع الأساسية',text)
                self.assertIn('حدود الاستخدام',text)
                self.assertIn('application/ld+json',text)
if __name__=='__main__': unittest.main()
