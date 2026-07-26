#!/usr/bin/env python3
"""Build the five remaining claim-level evidence packets for v280.

The source catalogue is intentionally explicit.  The generated claim cards
combine condition-specific clinical boundaries with the already-authored
person-specific profiles.  They do not infer a talent from a diagnosis and
they never turn treatment, medication, crisis response, or medical clearance
into a self-directed experiment.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "content" / "v280" / "capabilities-100-ar.json"
PROFILE_DIR = ROOT / "content" / "v280" / "profiles"
EVIDENCE_DIR = ROOT / "content" / "v280" / "evidence"

UPDATED = "2026-07-27"
VERIFIED = "2026-07-26"

CHARACTERS = {
    "official-current-guidance": (
        "إرشاد رسمي أو بوابة ممارسة مهنية حالية؛ مباشر للممارسة، "
        "ولا يثبت نتيجة فردية مسبقًا."
    ),
    "guideline-backed": (
        "توصية إرشادية مبنية على مراجعة أو توافق مهني؛ يلزم تطبيقها "
        "بحسب العمر والسياق والتفضيلات."
    ),
    "expert-reviewed-living-reference": (
        "مرجع سريري خبير مُراجع ومحدّث دوريًا؛ يدعم الحدود والمراقبة "
        "ولا يثبت نتيجة وظيفية فردية."
    ),
    "systematic-review-direct-heterogeneous": (
        "مراجعة منهجية مباشرة لكن الدراسات أو العينات أو المقاييس متغايرة؛ "
        "تصلح لتحديد اتجاه لا لضمان نتيجة."
    ),
    "systematic-review-limited-directness": (
        "مراجعة منهجية ذات عدد قليل أو مباشرة جزئية للحالة؛ "
        "الاستنتاج حذر وتجريبي."
    ),
    "mixed-sources-no-causal-inference": (
        "مزيج من إرشاد وبحث محكم أو خبرة معاشة؛ "
        "يحدد فرضية أو حدًا ولا يثبت السببية."
    ),
}


def source(
    source_id: str,
    publisher: str,
    title: str,
    url: str,
    year: int,
    source_type: str,
    conditions: list[str],
    character: str,
) -> dict[str, Any]:
    return {
        "id": source_id,
        "publisher": publisher,
        "title": title,
        "url": url,
        "year": year,
        "source_type": source_type,
        "conditions": conditions,
        "character": character,
    }


GENEREVIEWS = "GeneReviews®, University of Washington, Seattle"

SOURCES: dict[str, list[dict[str, Any]]] = {
    "genetic-metabolic": [
        source(
            "genereviews-fmr1-disorders-2024",
            GENEREVIEWS,
            "FMR1 Disorders",
            "https://www.ncbi.nlm.nih.gov/books/NBK1384/",
            2024,
            "peer_reviewed_review",
            ["fragile-x-syndrome"],
            "expert-reviewed-living-reference",
        ),
        source(
            "genereviews-mecp2-disorders-2019",
            GENEREVIEWS,
            "MECP2 Disorders",
            "https://www.ncbi.nlm.nih.gov/books/NBK1497/",
            2019,
            "peer_reviewed_review",
            ["rett-syndrome"],
            "expert-reviewed-living-reference",
        ),
        source(
            "genereviews-angelman-syndrome-2025",
            GENEREVIEWS,
            "Angelman Syndrome",
            "https://www.ncbi.nlm.nih.gov/books/NBK1144/",
            2025,
            "peer_reviewed_review",
            ["angelman-syndrome"],
            "expert-reviewed-living-reference",
        ),
        source(
            "genereviews-prader-willi-syndrome-2024",
            GENEREVIEWS,
            "Prader-Willi Syndrome",
            "https://www.ncbi.nlm.nih.gov/books/NBK1330/",
            2024,
            "peer_reviewed_review",
            ["prader-willi-syndrome"],
            "expert-reviewed-living-reference",
        ),
        source(
            "genereviews-williams-syndrome-2023",
            GENEREVIEWS,
            "Williams Syndrome",
            "https://www.ncbi.nlm.nih.gov/books/NBK1249/",
            2023,
            "peer_reviewed_review",
            ["williams-syndrome"],
            "expert-reviewed-living-reference",
        ),
        source(
            "liverani-cri-du-chat-care-2019",
            "American Journal of Medical Genetics Part A",
            "Children and adults affected by Cri du Chat syndrome: Care's recommendations",
            "https://pubmed.ncbi.nlm.nih.gov/30838120/",
            2019,
            "peer_reviewed_review",
            ["cri-du-chat-syndrome"],
            "mixed-sources-no-causal-inference",
        ),
        source(
            "genereviews-cornelia-de-lange-2020",
            GENEREVIEWS,
            "Cornelia de Lange Syndrome",
            "https://www.ncbi.nlm.nih.gov/books/NBK1104/",
            2020,
            "peer_reviewed_review",
            ["cornelia-de-lange-syndrome"],
            "expert-reviewed-living-reference",
        ),
        source(
            "genereviews-noonan-syndrome-2025",
            GENEREVIEWS,
            "Noonan Syndrome",
            "https://www.ncbi.nlm.nih.gov/books/NBK1124/",
            2025,
            "peer_reviewed_review",
            ["noonan-syndrome"],
            "expert-reviewed-living-reference",
        ),
        source(
            "gravholt-turner-guideline-2024",
            "Aarhus International Turner Syndrome Meeting",
            "Clinical practice guidelines for the care of girls and women with Turner syndrome",
            "https://pubmed.ncbi.nlm.nih.gov/38748847/",
            2024,
            "professional_body_guideline",
            ["turner-syndrome"],
            "guideline-backed",
        ),
        source(
            "zitzmann-klinefelter-guideline-2021",
            "European Academy of Andrology",
            "European Academy of Andrology guidelines on Klinefelter Syndrome",
            "https://pubmed.ncbi.nlm.nih.gov/32959490/",
            2021,
            "professional_body_guideline",
            ["klinefelter-syndrome"],
            "guideline-backed",
        ),
        source(
            "genereviews-22q11-deletion-2025",
            GENEREVIEWS,
            "22q11.2 Deletion Syndrome",
            "https://www.ncbi.nlm.nih.gov/books/NBK1523/",
            2025,
            "peer_reviewed_review",
            ["22q11-deletion-syndrome"],
            "expert-reviewed-living-reference",
        ),
        source(
            "genereviews-smith-magenis-2025",
            GENEREVIEWS,
            "Smith-Magenis Syndrome",
            "https://www.ncbi.nlm.nih.gov/books/NBK1310/",
            2025,
            "peer_reviewed_review",
            ["smith-magenis-syndrome"],
            "expert-reviewed-living-reference",
        ),
        source(
            "genereviews-sotos-syndrome-2025",
            GENEREVIEWS,
            "Sotos Syndrome",
            "https://www.ncbi.nlm.nih.gov/sites/books/NBK1479/",
            2025,
            "peer_reviewed_review",
            ["sotos-syndrome"],
            "expert-reviewed-living-reference",
        ),
        source(
            "genereviews-chd7-disorder-2025",
            GENEREVIEWS,
            "CHD7 Disorder",
            "https://www.ncbi.nlm.nih.gov/books/NBK1117/",
            2025,
            "peer_reviewed_review",
            ["charge-syndrome"],
            "expert-reviewed-living-reference",
        ),
        source(
            "genereviews-kabuki-syndrome-2026",
            GENEREVIEWS,
            "Kabuki Syndrome",
            "https://www.ncbi.nlm.nih.gov/books/NBK62111/",
            2026,
            "peer_reviewed_review",
            ["kabuki-syndrome"],
            "expert-reviewed-living-reference",
        ),
        source(
            "genereviews-rubinstein-taybi-2023",
            GENEREVIEWS,
            "Rubinstein-Taybi Syndrome",
            "https://www.ncbi.nlm.nih.gov/books/NBK1526/",
            2023,
            "peer_reviewed_review",
            ["rubinstein-taybi-syndrome"],
            "expert-reviewed-living-reference",
        ),
        source(
            "genereviews-smith-lemli-opitz-2020",
            GENEREVIEWS,
            "Smith-Lemli-Opitz Syndrome",
            "https://www.ncbi.nlm.nih.gov/books/NBK1143/",
            2020,
            "peer_reviewed_review",
            ["smith-lemli-opitz-syndrome"],
            "expert-reviewed-living-reference",
        ),
        source(
            "bachmann-gagescu-joubert-care-2020",
            "American Journal of Medical Genetics Part A",
            "Healthcare recommendations for Joubert syndrome",
            "https://pubmed.ncbi.nlm.nih.gov/31710777/",
            2020,
            "peer_reviewed_review",
            ["joubert-syndrome"],
            "mixed-sources-no-causal-inference",
        ),
        source(
            "genereviews-tuberous-sclerosis-2024",
            GENEREVIEWS,
            "Tuberous Sclerosis Complex",
            "https://www.ncbi.nlm.nih.gov/books/NBK1220/",
            2024,
            "peer_reviewed_review",
            ["tuberous-sclerosis-complex"],
            "expert-reviewed-living-reference",
        ),
        source(
            "genereviews-neurofibromatosis-1-2025",
            GENEREVIEWS,
            "Neurofibromatosis 1",
            "https://www.ncbi.nlm.nih.gov/books/NBK1109/",
            2025,
            "peer_reviewed_review",
            ["neurofibromatosis-type-1"],
            "expert-reviewed-living-reference",
        ),
        source(
            "genereviews-pah-deficiency-2025",
            GENEREVIEWS,
            "Phenylalanine Hydroxylase Deficiency",
            "https://www.ncbi.nlm.nih.gov/books/NBK1504/",
            2025,
            "peer_reviewed_review",
            ["phenylketonuria"],
            "expert-reviewed-living-reference",
        ),
        source(
            "van-trostenburg-congenital-hypothyroidism-2021",
            "ENDO-European Reference Network",
            "Congenital Hypothyroidism: A 2020–2021 Consensus Guidelines Update",
            "https://pubmed.ncbi.nlm.nih.gov/33272083/",
            2021,
            "professional_body_guideline",
            ["congenital-hypothyroidism"],
            "guideline-backed",
        ),
        source(
            "sue-mitochondrial-care-standards-australia-2022",
            "Royal Australasian College of Physicians",
            "Patient care standards for primary mitochondrial disease in Australia: an Australian adaptation of the Mitochondrial Medicine Society recommendations",
            "https://pubmed.ncbi.nlm.nih.gov/34505344/",
            2022,
            "professional_body_guideline",
            ["mitochondrial-diseases"],
            "guideline-backed",
        ),
    ],
    "motor-neurological": [
        source(
            "dicianno-spina-bifida-mobility-2020",
            "Spina Bifida Association",
            "Mobility guidelines for the care of people with spina bifida",
            "https://pubmed.ncbi.nlm.nih.gov/33325411/",
            2020,
            "professional_body_guideline",
            ["spina-bifida"],
            "guideline-backed",
        ),
        source(
            "cns-pediatric-hydrocephalus-guideline-2021",
            "Congress of Neurological Surgeons",
            "Pediatric hydrocephalus: systematic review and evidence-based guideline update",
            "https://pubmed.ncbi.nlm.nih.gov/34791462/",
            2021,
            "professional_body_guideline",
            ["hydrocephalus"],
            "guideline-backed",
        ),
        source(
            "nice-epilepsy-ng217-2022",
            "National Institute for Health and Care Excellence",
            "Epilepsies in children, young people and adults (NG217)",
            "https://www.nice.org.uk/guidance/ng217",
            2022,
            "official_guideline",
            ["epilepsy"],
            "guideline-backed",
        ),
        source(
            "incog-cognitive-rehabilitation-tbi-2023",
            "INCOG Expert Panel",
            "INCOG 2.0 Guidelines for Cognitive Rehabilitation Following Traumatic Brain Injury",
            "https://pubmed.ncbi.nlm.nih.gov/36594856/",
            2023,
            "professional_body_guideline",
            ["traumatic-brain-injury"],
            "guideline-backed",
        ),
        source(
            "nice-stroke-rehabilitation-ng236-2023",
            "National Institute for Health and Care Excellence",
            "Stroke rehabilitation in adults (NG236)",
            "https://www.nice.org.uk/guidance/ng236",
            2023,
            "official_guideline",
            ["stroke"],
            "guideline-backed",
        ),
        source(
            "fehlings-acute-sci-rehabilitation-2017",
            "AOSpine and Praxis Spinal Cord Institute",
            "Clinical Practice Guideline on the Type and Timing of Rehabilitation after Acute Spinal Cord Injury",
            "https://pubmed.ncbi.nlm.nih.gov/29164029/",
            2017,
            "professional_body_guideline",
            ["spinal-cord-injury"],
            "guideline-backed",
        ),
        source(
            "genereviews-spinal-muscular-atrophy-2024",
            GENEREVIEWS,
            "Spinal Muscular Atrophy",
            "https://www.ncbi.nlm.nih.gov/books/NBK1352/",
            2024,
            "peer_reviewed_review",
            ["spinal-muscular-atrophy"],
            "expert-reviewed-living-reference",
        ),
        source(
            "birnkrant-duchenne-care-part1-2018",
            "DMD Care Considerations Working Group",
            "Diagnosis and management of Duchenne muscular dystrophy, part 1",
            "https://pubmed.ncbi.nlm.nih.gov/29395989/",
            2018,
            "professional_body_guideline",
            ["duchenne-muscular-dystrophy"],
            "guideline-backed",
        ),
        source(
            "genereviews-dystrophinopathies-2022",
            GENEREVIEWS,
            "Dystrophinopathies",
            "https://www.ncbi.nlm.nih.gov/books/NBK1119/",
            2022,
            "peer_reviewed_review",
            ["becker-muscular-dystrophy"],
            "expert-reviewed-living-reference",
        ),
        source(
            "genereviews-cmt-overview-2025",
            GENEREVIEWS,
            "Charcot-Marie-Tooth Hereditary Neuropathy Overview",
            "https://www.ncbi.nlm.nih.gov/books/NBK1358/",
            2025,
            "peer_reviewed_review",
            ["charcot-marie-tooth-disease"],
            "expert-reviewed-living-reference",
        ),
        source(
            "corben-friedreich-ataxia-guideline-2022",
            "Clinical Management Guideline Working Group",
            "Clinical management guidelines for Friedreich ataxia",
            "https://pubmed.ncbi.nlm.nih.gov/36371255/",
            2022,
            "professional_body_guideline",
            ["friedreich-ataxia"],
            "guideline-backed",
        ),
        source(
            "genereviews-spastic-paraplegia-2025",
            GENEREVIEWS,
            "Uncomplicated (Pure) Hereditary Spastic Paraplegia Overview",
            "https://www.ncbi.nlm.nih.gov/books/NBK1509/",
            2025,
            "peer_reviewed_review",
            ["hereditary-spastic-paraplegia"],
            "expert-reviewed-living-reference",
        ),
        source(
            "narayanaswami-myasthenia-consensus-2021",
            "Myasthenia Gravis Foundation of America",
            "International Consensus Guidance for Management of Myasthenia Gravis: 2020 Update",
            "https://pubmed.ncbi.nlm.nih.gov/33144515/",
            2021,
            "professional_body_guideline",
            ["myasthenia-gravis"],
            "guideline-backed",
        ),
        source(
            "de-pauw-dystonia-rehabilitation-2018",
            "Journal of Neurology",
            "Systematic review of rehabilitation for cervical dystonia",
            "https://pubmed.ncbi.nlm.nih.gov/30009212/",
            2018,
            "systematic_review",
            ["dystonia"],
            "systematic-review-limited-directness",
        ),
        source(
            "arthrogryposis-rehabilitation-review-2023",
            "Children",
            "Rehabilitation interventions for children with arthrogryposis multiplex congenita: a systematic review",
            "https://pmc.ncbi.nlm.nih.gov/articles/PMC10217713/",
            2023,
            "systematic_review",
            ["arthrogryposis"],
            "systematic-review-limited-directness",
        ),
        source(
            "genereviews-osteogenesis-imperfecta-2025",
            GENEREVIEWS,
            "COL1A1- and COL1A2-Related Osteogenesis Imperfecta",
            "https://www.ncbi.nlm.nih.gov/books/NBK1295/",
            2025,
            "peer_reviewed_review",
            ["osteogenesis-imperfecta"],
            "expert-reviewed-living-reference",
        ),
        source(
            "genereviews-achondroplasia-2023",
            GENEREVIEWS,
            "Achondroplasia",
            "https://www.ncbi.nlm.nih.gov/books/NBK1152/",
            2023,
            "peer_reviewed_review",
            ["achondroplasia"],
            "expert-reviewed-living-reference",
        ),
        source(
            "va-dod-lower-limb-amputation-cpg-2024",
            "U.S. Department of Veterans Affairs and Department of Defense",
            "Clinical Practice Guideline for Rehabilitation of Individuals with Lower Limb Amputation",
            "https://www.healthquality.va.gov/guidelines/Rehab/amp/index.asp",
            2024,
            "official_guideline",
            ["limb-difference-amputation"],
            "guideline-backed",
        ),
        source(
            "burn-contracture-rehabilitation-review-2024",
            "Burns",
            "Rehabilitation interventions for burn scar contracture: a scoping review",
            "https://pubmed.ncbi.nlm.nih.gov/38250207/",
            2024,
            "systematic_review",
            ["severe-burns-contractures"],
            "systematic-review-limited-directness",
        ),
    ],
    "sensory-communication": [
        source(
            "who-blindness-vision-impairment-2026",
            "World Health Organization",
            "Blindness and vision impairment",
            "https://www.who.int/news-room/fact-sheets/detail/blindness-and-visual-impairment",
            2026,
            "public_health_authority",
            ["blindness", "low-vision"],
            "official-current-guidance",
        ),
        source(
            "liu-low-vision-rehabilitation-2021",
            "International Journal of Ophthalmology",
            "Low vision rehabilitation in improving the quality of life for patients with impaired vision: a systematic review and meta-analysis",
            "https://pubmed.ncbi.nlm.nih.gov/34106601/",
            2021,
            "systematic_review",
            ["blindness", "low-vision"],
            "systematic-review-direct-heterogeneous",
        ),
        source(
            "aap-cerebral-visual-impairment-2024",
            "American Academy of Pediatrics",
            "Diagnosis and Care of Children With Cerebral/Cortical Visual Impairment: Clinical Report",
            "https://pubmed.ncbi.nlm.nih.gov/39558730/",
            2024,
            "professional_body_guideline",
            ["cerebral-visual-impairment"],
            "guideline-backed",
        ),
        source(
            "jcih-early-hearing-position-2019",
            "Joint Committee on Infant Hearing",
            "Year 2019 Position Statement: Principles and Guidelines for Early Hearing Detection and Intervention Programs",
            "https://www.jcih.org/posstatemts.htm",
            2019,
            "professional_body_guideline",
            ["deafness", "hearing-loss"],
            "guideline-backed",
        ),
        source(
            "nhs-inform-deafblindness-2024",
            "NHS inform",
            "Deafblindness",
            "https://www.nhsinform.scot/illnesses-and-conditions/eyes/deafblindness/",
            2024,
            "institutional_fact_sheet",
            ["deafblindness"],
            "official-current-guidance",
        ),
        source(
            "medlineplus-usher-syndrome-2021",
            "U.S. National Library of Medicine",
            "Usher syndrome",
            "https://medlineplus.gov/genetics/condition/usher-syndrome/",
            2021,
            "institutional_fact_sheet",
            ["usher-syndrome"],
            "official-current-guidance",
        ),
        source(
            "genereviews-oculocutaneous-albinism-2023",
            GENEREVIEWS,
            "Oculocutaneous Albinism and Ocular Albinism Overview",
            "https://www.ncbi.nlm.nih.gov/books/NBK590568/",
            2023,
            "peer_reviewed_review",
            ["oculocutaneous-albinism"],
            "expert-reviewed-living-reference",
        ),
        source(
            "genereviews-retinitis-pigmentosa-2023",
            GENEREVIEWS,
            "Nonsyndromic Retinitis Pigmentosa Overview",
            "https://www.ncbi.nlm.nih.gov/books/NBK1417/",
            2023,
            "peer_reviewed_review",
            ["retinitis-pigmentosa"],
            "expert-reviewed-living-reference",
        ),
        source(
            "garcia-filion-optic-nerve-hypoplasia-2013",
            "Current Opinion in Ophthalmology",
            "Optic nerve hypoplasia syndrome: a review of the epidemiology and clinical associations",
            "https://pubmed.ncbi.nlm.nih.gov/23233151/",
            2013,
            "peer_reviewed_review",
            ["optic-nerve-hypoplasia"],
            "mixed-sources-no-causal-inference",
        ),
        source(
            "asha-aphasia-2026",
            "American Speech-Language-Hearing Association",
            "Aphasia — Practice Portal",
            "https://www.asha.org/practice-portal/clinical-topics/aphasia/",
            2026,
            "professional_body_guideline",
            ["aphasia"],
            "official-current-guidance",
        ),
        source(
            "asha-acquired-apraxia-2026",
            "American Speech-Language-Hearing Association",
            "Acquired Apraxia of Speech — Practice Portal",
            "https://www.asha.org/practice-portal/clinical-topics/acquired-apraxia-of-speech/",
            2026,
            "professional_body_guideline",
            ["acquired-apraxia-of-speech"],
            "official-current-guidance",
        ),
        source(
            "asha-dysarthria-adults-2026",
            "American Speech-Language-Hearing Association",
            "Dysarthria in Adults — Practice Portal",
            "https://www.asha.org/practice-portal/clinical-topics/dysarthria-in-adults/",
            2026,
            "professional_body_guideline",
            ["dysarthria"],
            "official-current-guidance",
        ),
        source(
            "odedra-moebius-multidisciplinary-care-2024",
            "American Journal of Medical Genetics Part A",
            "Multidisciplinary Care for Moebius Syndrome and Related Disorders",
            "https://pubmed.ncbi.nlm.nih.gov/38893020/",
            2024,
            "peer_reviewed_review",
            ["moebius-syndrome"],
            "mixed-sources-no-causal-inference",
        ),
        source(
            "asha-cleft-lip-palate-2026",
            "American Speech-Language-Hearing Association",
            "Cleft Lip and Palate — Practice Portal",
            "https://www.asha.org/practice-portal/clinical-topics/cleft-lip-and-palate/",
            2026,
            "professional_body_guideline",
            ["cleft-lip-palate-communication"],
            "official-current-guidance",
        ),
    ],
    "chronic-health": [
        source(
            "ecfs-cystic-fibrosis-care-2024",
            "European Cystic Fibrosis Society",
            "Standards for the care of people with cystic fibrosis: recognising and addressing health issues",
            "https://pubmed.ncbi.nlm.nih.gov/38233247/",
            2024,
            "professional_body_guideline",
            ["cystic-fibrosis"],
            "guideline-backed",
        ),
        source(
            "ash-sickle-cell-pain-2020",
            "American Society of Hematology",
            "ASH 2020 guidelines for sickle cell disease: management of acute and chronic pain",
            "https://pubmed.ncbi.nlm.nih.gov/32559294/",
            2020,
            "professional_body_guideline",
            ["sickle-cell-disease"],
            "guideline-backed",
        ),
        source(
            "wfh-hemophilia-guideline-2020",
            "World Federation of Hemophilia",
            "WFH Guidelines for the Management of Hemophilia, 3rd edition",
            "https://pubmed.ncbi.nlm.nih.gov/32744769/",
            2020,
            "professional_body_guideline",
            ["hemophilia"],
            "guideline-backed",
        ),
        source(
            "ispad-diabetes-school-2022",
            "International Society for Pediatric and Adolescent Diabetes",
            "ISPAD Clinical Practice Consensus Guidelines 2022: Management and support of children and adolescents with diabetes in school",
            "https://pubmed.ncbi.nlm.nih.gov/36537526/",
            2022,
            "professional_body_guideline",
            ["type-1-diabetes"],
            "guideline-backed",
        ),
        source(
            "kdigo-chronic-kidney-disease-2024",
            "Kidney Disease: Improving Global Outcomes",
            "KDIGO 2024 Clinical Practice Guideline for the Evaluation and Management of Chronic Kidney Disease",
            "https://pubmed.ncbi.nlm.nih.gov/38490803/",
            2024,
            "professional_body_guideline",
            ["chronic-kidney-disease"],
            "guideline-backed",
        ),
        source(
            "aha-congenital-heart-neurodevelopment-2024",
            "American Heart Association",
            "Neurodevelopmental Outcomes for Individuals With Congenital Heart Disease: 2024 Scientific Statement",
            "https://pubmed.ncbi.nlm.nih.gov/38385268/",
            2024,
            "professional_body_guideline",
            ["congenital-heart-disease"],
            "guideline-backed",
        ),
        source(
            "acr-juvenile-idiopathic-arthritis-2022",
            "American College of Rheumatology",
            "2021 ACR Guideline for the Treatment of Juvenile Idiopathic Arthritis",
            "https://pubmed.ncbi.nlm.nih.gov/35233986/",
            2022,
            "professional_body_guideline",
            ["juvenile-idiopathic-arthritis"],
            "guideline-backed",
        ),
        source(
            "eular-systemic-lupus-2024",
            "European Alliance of Associations for Rheumatology",
            "EULAR recommendations for the management of systemic lupus erythematosus: 2023 update",
            "https://pubmed.ncbi.nlm.nih.gov/37827694/",
            2024,
            "professional_body_guideline",
            ["systemic-lupus-erythematosus"],
            "guideline-backed",
        ),
        source(
            "ecco-ibd-diagnostics-monitoring-2025",
            "European Crohn's and Colitis Organisation",
            "ECCO-ESGAR-ESP-IBUS Guideline on Diagnostics and Monitoring of Inflammatory Bowel Disease",
            "https://pubmed.ncbi.nlm.nih.gov/40741688/",
            2025,
            "professional_body_guideline",
            ["inflammatory-bowel-disease"],
            "guideline-backed",
        ),
        source(
            "gina-severe-asthma-guide-2026",
            "Global Initiative for Asthma",
            "Difficult-to-Treat and Severe Asthma: Diagnosis and Management",
            "https://ginasthma.org/2026-gina-severe-asthma-guide/",
            2026,
            "professional_body_guideline",
            ["severe-asthma"],
            "guideline-backed",
        ),
        source(
            "golden-anaphylaxis-practice-parameter-2024",
            "Joint Task Force on Practice Parameters",
            "Anaphylaxis: A 2023 practice parameter update",
            "https://pubmed.ncbi.nlm.nih.gov/38108678/",
            2024,
            "professional_body_guideline",
            ["severe-food-allergy"],
            "guideline-backed",
        ),
        source(
            "cog-long-term-follow-up-2023",
            "Children's Oncology Group",
            "Long-Term Follow-Up Guidelines for Survivors of Childhood, Adolescent and Young Adult Cancers, Version 6.0",
            "https://www.survivorshipguidelines.org/",
            2023,
            "professional_body_guideline",
            ["childhood-cancer-late-effects"],
            "guideline-backed",
        ),
        source(
            "nice-me-cfs-ng206-2021",
            "National Institute for Health and Care Excellence",
            "ME/CFS: diagnosis and management (NG206)",
            "https://www.nice.org.uk/guidance/ng206",
            2021,
            "official_guideline",
            ["me-cfs"],
            "guideline-backed",
        ),
        source(
            "who-post-covid-living-guideline-2025",
            "World Health Organization",
            "Clinical management of COVID-19: living guideline, June 2025",
            "https://www.who.int/publications/i/item/B09467",
            2025,
            "official_guideline",
            ["long-covid"],
            "guideline-backed",
        ),
    ],
    "progressive-psychosocial": [
        source(
            "nice-multiple-sclerosis-ng220-2022",
            "National Institute for Health and Care Excellence",
            "Multiple sclerosis in adults: management (NG220)",
            "https://www.nice.org.uk/guidance/ng220",
            2022,
            "official_guideline",
            ["multiple-sclerosis"],
            "guideline-backed",
        ),
        source(
            "nice-parkinson-ng71-2017",
            "National Institute for Health and Care Excellence",
            "Parkinson's disease in adults (NG71)",
            "https://www.nice.org.uk/guidance/ng71",
            2017,
            "official_guideline",
            ["parkinson-disease"],
            "guideline-backed",
        ),
        source(
            "bachoud-levi-huntington-guideline-2019",
            "European Huntington's Disease Network",
            "International Guidelines for the Treatment of Huntington's Disease",
            "https://pmc.ncbi.nlm.nih.gov/articles/PMC6618900/",
            2019,
            "professional_body_guideline",
            ["huntington-disease"],
            "guideline-backed",
        ),
        source(
            "ean-als-guideline-2024",
            "European Academy of Neurology",
            "European Academy of Neurology guideline on the management of amyotrophic lateral sclerosis",
            "https://pubmed.ncbi.nlm.nih.gov/38470068/",
            2024,
            "professional_body_guideline",
            ["amyotrophic-lateral-sclerosis"],
            "guideline-backed",
        ),
        source(
            "genereviews-hypermobile-eds-2024",
            GENEREVIEWS,
            "Hypermobile Ehlers-Danlos Syndrome",
            "https://www.ncbi.nlm.nih.gov/books/NBK1279/",
            2024,
            "peer_reviewed_review",
            ["ehlers-danlos-syndromes"],
            "expert-reviewed-living-reference",
        ),
        source(
            "genereviews-vascular-eds-2025",
            GENEREVIEWS,
            "Vascular Ehlers-Danlos Syndrome",
            "https://www.ncbi.nlm.nih.gov/books/NBK1494/",
            2025,
            "peer_reviewed_review",
            ["ehlers-danlos-syndromes"],
            "expert-reviewed-living-reference",
        ),
        source(
            "genereviews-marfan-2022",
            GENEREVIEWS,
            "FBN1-Related Marfan Syndrome",
            "https://www.ncbi.nlm.nih.gov/books/NBK1335/",
            2022,
            "peer_reviewed_review",
            ["marfan-syndrome"],
            "expert-reviewed-living-reference",
        ),
        source(
            "sosort-scoliosis-guideline-2018",
            "Society on Scoliosis Orthopaedic and Rehabilitation Treatment",
            "2016 SOSORT guidelines: orthopaedic and rehabilitation treatment of idiopathic scoliosis during growth",
            "https://pubmed.ncbi.nlm.nih.gov/29435499/",
            2018,
            "professional_body_guideline",
            ["severe-scoliosis"],
            "guideline-backed",
        ),
        source(
            "nice-chronic-pain-ng193-2021",
            "National Institute for Health and Care Excellence",
            "Chronic pain (primary and secondary) in over 16s (NG193)",
            "https://www.nice.org.uk/guidance/ng193",
            2021,
            "official_guideline",
            ["chronic-pain"],
            "guideline-backed",
        ),
        source(
            "nice-schizophrenia-cg178-2014",
            "National Institute for Health and Care Excellence",
            "Psychosis and schizophrenia in adults: prevention and management (CG178)",
            "https://www.nice.org.uk/guidance/cg178",
            2014,
            "official_guideline",
            ["schizophrenia-functional-support"],
            "guideline-backed",
        ),
        source(
            "nice-bipolar-cg185-2014",
            "National Institute for Health and Care Excellence",
            "Bipolar disorder: assessment and management (CG185)",
            "https://www.nice.org.uk/guidance/cg185",
            2014,
            "official_guideline",
            ["bipolar-disorder-functional-support"],
            "guideline-backed",
        ),
    ],
}

# These condition-specific sources are already in the v280 base catalogue.
BASE_CONDITION_SOURCES = {
    "down-syndrome": [
        "onnivello-down-profiles-2022",
        "yang-down-visuospatial-2014",
        "aap-down-health-2022",
    ],
    "cerebral-palsy": ["jackman-cp-guideline-2022", "nice-cp-ng62"],
    "deafness": ["who-hearing-2026"],
    "hearing-loss": ["who-hearing-2026"],
}

PROFILE_CHARACTER_OVERRIDES = {
    "down-syndrome": "systematic-review-direct-heterogeneous",
    "blindness": "mixed-sources-no-causal-inference",
    "low-vision": "mixed-sources-no-causal-inference",
}


def selection_method(category_label: str, count: int) -> dict[str, Any]:
    return {
        "scope": (
            f"تغطي هذه الموجة الحالات الـ{count} كلها في فئة {category_label}، "
            "بثلاثة ادعاءات محدودة لكل حالة: حدود الملف، والوصول أو التدخل، "
            "والأمان أو التشخيص التفريقي."
        ),
        "selection_order": [
            "إرشاد رسمي أو مهني حديث ومباشر للحالة أو للمجال الوظيفي.",
            "مرجع سريري خبير مُراجع ومحدّث دوريًا للحالات الوراثية أو النادرة.",
            "مراجعة منهجية أو تحليل تجميعي مباشر، مع التصريح بالتغاير ومحدودية الدراسات.",
            "بحث محكم أو توافق خبراء فقط عندما لا يتوفر إرشاد أعلى، ومن دون تحويله إلى قاعدة جماعية.",
        ],
        "exclusions": [
            "المصادر الترويجية وقصص النجاح المنفردة بوصفها دليلًا على صفة أو تدخل.",
            "نتائج البحث الحي في PubMed بوصفها قائمة مصادر منتقاة قبل الفرز والنقد.",
            "بروتوكولات المراجعات التي لم تنشر نتائجها بعد بوصفها دليل فعالية.",
            "أي استنتاج يربط التشخيص بموهبة أو ذكاء أو مهنة من دون قياس مباشر عند الشخص.",
        ],
        "certainty_policy": (
            "لا يعيّن المشروع درجة GRADE من تلقاء نفسه. يصف نوع المصدر، "
            "ومباشرة الدليل، والتغاير، وحدود النقل إلى الفرد. تبقى قوة "
            "التوصية الرسمية للجهة التي أصدرتها."
        ),
        "live_search_boundary": (
            "رابط البحث الحي أداة تحديث للمراجع المتخصص، وليس مصدرًا مختارًا "
            "ولا إثباتًا لفعالية تدخل."
        ),
        "review_boundary": (
            "الانتقاء والترجمة ومطابقة الادعاءات مراجعة داخلية قابلة للتدقيق، "
            "ولم تكتمل مراجعة خارجية مستقلة سريرية وتأهيلية ومن ذوي الخبرة المعاشة."
        ),
    }


def make_claims(
    condition: dict[str, Any],
    profile: dict[str, str],
    source_ids: list[str],
    primary_character: str,
) -> list[dict[str, Any]]:
    slug = condition["slug"]
    title = condition["title_ar"]
    profile_character = PROFILE_CHARACTER_OVERRIDES.get(
        slug, "mixed-sources-no-causal-inference"
    )
    access_sources = list(dict.fromkeys(["who-rehabilitation-2024", *source_ids]))
    profile_sources = list(dict.fromkeys(["who-icf-2001", *source_ids]))
    return [
        {
            "id": f"{slug}-evidence-profile-boundary",
            "type": "profile-boundary",
            "statement": (
                f"{profile['position']} لذلك يظل تشخيص {title} وصفًا لاحتياجات "
                "ومخاطر محتملة، وليس اختبارًا للذكاء أو القيمة أو الموهبة أو المهنة."
            ),
            "what_it_supports": (
                "يدعم حصر الاستدلال في التغاير والوظيفة ثم قياس المجال المقترح "
                f"مباشرةً عند الشخص: {profile['ability_focus']}"
            ),
            "what_it_does_not_support": (
                f"لا يدعم نسبة قدرة ثابتة إلى كل من لديه {title}، ولا اختيار مسار "
                "دراسي أو مهني من اسم التشخيص أو من قصة نجاح فردية."
            ),
            "evidence_character": profile_character,
            "source_ids": profile_sources,
        },
        {
            "id": f"{slug}-evidence-access-intervention",
            "type": "access-and-intervention",
            "statement": (
                f"{profile['access_priority']} ويُختار كل تكييف باتفاق الشخص، "
                "ثم يقاس أثره على جودة المهمة والاستقلال والتعب والرغبة والتعميم."
            ),
            "what_it_supports": (
                "يدعم تجربة وصول صغيرة قابلة للعكس داخل مهمة ذات معنى، لا وصفة "
                f"موحدة؛ والتطبيق العملي المقترح هو: {profile['task_trial']}"
            ),
            "what_it_does_not_support": (
                "لا يضمن أن التكييف سينفع هذا الشخص، ولا يبرر جمع تدخلات كثيرة "
                "دفعة واحدة أو استبدال العلاج الموصوف بتجربة تعليمية أو وظيفية."
            ),
            "evidence_character": primary_character,
            "source_ids": access_sources,
        },
        {
            "id": f"{slug}-evidence-safety-differential",
            "type": "safety-and-differential",
            "statement": (
                f"{profile['safety_priority']} وتبقى قرارات التشخيص والعلاج "
                "والدواء والقيود الطبية وخطة الطوارئ ضمن الفريق السريري المختص."
            ),
            "what_it_supports": (
                "يدعم تقديم الاستقرار والصحة على اختبار الأداء، ثم متابعة هدف "
                f"وظيفي محدود بعد تحقق الأمان: {profile['functional_goal']}"
            ),
            "what_it_does_not_support": (
                "لا يدعم استعمال الصفحة للتشخيص الذاتي أو تعديل الدواء أو التغذية "
                "أو النشاط المحظور، ولا تأخير الإحالة عند عرض جديد أو تدهور أو طارئ."
            ),
            "evidence_character": primary_character,
            "source_ids": source_ids,
        },
    ]


def build_category(
    data: dict[str, Any],
    category: str,
    profiles: list[dict[str, str]],
) -> dict[str, Any]:
    conditions = {
        item["slug"]: item
        for item in data["conditions"]
        if item["category"] == category
    }
    profile_by_slug = {item["slug"]: item for item in profiles}
    if set(profile_by_slug) != set(conditions):
        raise ValueError(f"Profile coverage mismatch for {category}")

    condition_selected_sources: dict[str, list[str]] = defaultdict(list)
    source_characters: dict[str, str] = {}
    output_sources = []
    for item in SOURCES[category]:
        source_characters[item["id"]] = item["character"]
        for slug in item["conditions"]:
            if slug not in conditions:
                raise ValueError(f"Source {item['id']} maps outside {category}: {slug}")
            condition_selected_sources[slug].append(item["id"])
        claim_ids = [
            f"{slug}-evidence-{suffix}"
            for slug in item["conditions"]
            for suffix in (
                "profile-boundary",
                "access-intervention",
                "safety-differential",
            )
        ]
        output_sources.append(
            {
                "id": item["id"],
                "publisher": item["publisher"],
                "title": item["title"],
                "url": item["url"],
                "year": item["year"],
                "source_type": item["source_type"],
                "verified_at": VERIFIED,
                "claims_supported": claim_ids,
                "status": "current",
            }
        )

    packets = []
    for slug, condition in conditions.items():
        selected_ids = condition_selected_sources[slug]
        source_ids = [*BASE_CONDITION_SOURCES.get(slug, []), *selected_ids]
        if not source_ids:
            raise ValueError(f"No condition-specific source for {slug}")
        primary_character = (
            source_characters[selected_ids[0]]
            if selected_ids
            else "guideline-backed"
        )
        packets.append(
            {
                "slug": slug,
                "search_updated": UPDATED,
                "review_state": "curated-not-externally-reviewed",
                "claims": make_claims(
                    condition,
                    profile_by_slug[slug],
                    source_ids,
                    primary_character,
                ),
            }
        )

    return {
        "version": 280,
        "language": "ar",
        "category": category,
        "title": f"حزم الأدلة المنتقاة: {data['categories'][category]}",
        "search_updated": UPDATED,
        "external_review_completed": False,
        "selection_method": selection_method(
            data["categories"][category], len(conditions)
        ),
        "evidence_character_labels": CHARACTERS,
        "sources": output_sources,
        "evidence_packets": packets,
    }


def main() -> None:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    for category in SOURCES:
        profile_payload = json.loads(
            (PROFILE_DIR / f"{category}.json").read_text(encoding="utf-8")
        )
        payload = build_category(data, category, profile_payload["profiles"])
        path = EVIDENCE_DIR / f"{category}-ar.json"
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(
            f"{path.relative_to(ROOT)}: "
            f"{len(payload['evidence_packets'])} packets, "
            f"{len(payload['sources'])} sources"
        )


if __name__ == "__main__":
    main()
