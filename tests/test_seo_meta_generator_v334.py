import json
import re
import unittest

from scripts.seo_meta_generator_v334 import (
    EntityIdentity,
    ImageMetadata,
    PageSeoInput,
    SEOMetaGenerator,
)


class SeoMetaGeneratorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.generator = SEOMetaGenerator(
            base_url="https://healthrenewal.org/",
            site_name="منصة روافد",
            publisher=EntityIdentity(
                name="منصة روافد",
                url="/",
                entity_type="Organization",
            ),
            logo_path="assets/logo.png",
            twitter_handle="pterminology",
            theme_color="#ffffff",
            default_preconnects=("https://fonts.gstatic.com",),
        )

    def page(self, **overrides):
        values = {
            "page_path": "encyclopedia/autism-spectrum/",
            "title": "طيف التوحد: دليل علمي شامل",
            "description": "شرح علمي واضح لطيف التوحد والعلامات والتقييم والدعم المبني على الأدلة للأسرة ومقدمي الخدمة.",
            "image": ImageMetadata(
                path="assets/images/autism-guide.webp",
                alt="دليل عربي موثوق حول طيف التوحد",
            ),
            "language": "ar-JO",
            "schema_kind": "medical_webpage",
            "social_type": "article",
            "medical_specialty": "Psychiatric",
            "medical_condition": "Autism Spectrum Disorder",
        }
        values.update(overrides)
        return PageSeoInput(**values)

    def extract_json_ld(self, output: str):
        match = re.search(
            r'<script type="application/ld\+json">(.*?)</script>',
            output,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(match)
        return json.loads(match.group(1))

    def test_omits_obsolete_meta_keywords(self):
        output = self.generator.generate_head_tags(self.page())
        self.assertNotIn('name="keywords"', output)

    def test_does_not_fabricate_hreflang(self):
        output = self.generator.generate_head_tags(self.page())
        self.assertNotIn('hreflang=', output)

    def test_emits_only_declared_translation_cluster(self):
        output = self.generator.generate_head_tags(
            self.page(
                translations={
                    "ar-JO": "encyclopedia/autism-spectrum/",
                    "en": "en/encyclopedia/autism-spectrum/",
                },
                x_default_url="encyclopedia/autism-spectrum/",
            )
        )
        self.assertIn('hreflang="ar-JO"', output)
        self.assertIn('hreflang="en"', output)
        self.assertIn('hreflang="x-default"', output)
        self.assertNotIn('hreflang="es"', output)

    def test_escapes_html_but_keeps_json_ld_semantics(self):
        output = self.generator.generate_head_tags(
            self.page(
                title='طيف التوحد & الدعم <المبكر>',
                description='محتوى "علمي" & موثوق <للقارئ>',
            )
        )
        self.assertIn("&amp;", output)
        self.assertIn("&lt;", output)
        schema = self.extract_json_ld(output)
        primary = schema["@graph"][0]
        self.assertEqual(primary["name"], "طيف التوحد & الدعم <المبكر>")
        self.assertEqual(primary["description"], 'محتوى "علمي" & موثوق <للقارئ>')

    def test_does_not_hard_truncate_title_or_description(self):
        title = "عنوان عربي تفصيلي " * 12
        description = "وصف عربي فريد ومفيد للقارئ ومحركات البحث " * 15
        output = self.generator.generate_head_tags(
            self.page(title=title, description=description)
        )
        self.assertIn(title.strip(), output)
        self.assertIn(description.strip(), output)
        self.assertNotIn("...", output)

    def test_medical_schema_is_opt_in(self):
        medical = self.extract_json_ld(self.generator.generate_head_tags(self.page()))
        medical_primary = medical["@graph"][0]
        self.assertEqual(medical_primary["@type"], "MedicalWebPage")
        self.assertEqual(medical_primary["specialty"], "Psychiatric")
        self.assertEqual(medical_primary["about"]["@type"], "MedicalCondition")

        ordinary = self.extract_json_ld(
            self.generator.generate_head_tags(
                self.page(
                    schema_kind="webpage",
                    medical_specialty=None,
                    medical_condition=None,
                )
            )
        )
        ordinary_primary = ordinary["@graph"][0]
        self.assertEqual(ordinary_primary["@type"], "WebPage")
        self.assertNotIn("specialty", ordinary_primary)
        self.assertNotIn("about", ordinary_primary)

    def test_reviewer_is_emitted_only_when_verified_and_supplied(self):
        without_reviewer = self.extract_json_ld(
            self.generator.generate_head_tags(self.page())
        )["@graph"][0]
        self.assertNotIn("reviewedBy", without_reviewer)

        reviewer = EntityIdentity(
            name="مراجع علمي موثّق",
            url="reviewers/scientific-reviewer/",
            entity_type="Person",
        )
        with_reviewer = self.extract_json_ld(
            self.generator.generate_head_tags(self.page(reviewer=reviewer))
        )["@graph"][0]
        self.assertEqual(with_reviewer["reviewedBy"]["@type"], "Person")
        self.assertEqual(with_reviewer["reviewedBy"]["name"], "مراجع علمي موثّق")

    def test_canonical_stays_inside_project_path(self):
        output = self.generator.generate_head_tags(self.page())
        self.assertIn(
            'rel="canonical" href="https://healthrenewal.org/encyclopedia/autism-spectrum/"',
            output,
        )
        with self.assertRaises(ValueError):
            self.generator.generate_head_tags(
                self.page(page_path="https://example.com/hijack/")
            )

    def test_social_metadata_includes_accessible_image_alt(self):
        output = self.generator.generate_head_tags(self.page())
        self.assertIn('property="og:image:alt"', output)
        self.assertIn('name="twitter:image:alt"', output)
        self.assertIn('name="twitter:site" content="@pterminology"', output)
        self.assertIn('property="og:locale" content="ar_JO"', output)


if __name__ == "__main__":
    unittest.main()
