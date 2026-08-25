# ADDICTION ATLAS — MASTER AGENT BRIEF

> **INTERNAL AGENT DOCUMENT — NOT SITE CONTENT**
> Repository: `khaledaltheeb/healthrenewal.org`
> Sector: Addiction / الإدمان
> Status: authoritative handoff brief for subsequent agents until superseded by a newer version.

## 1. Mission
Build a world-class Arabic interactive knowledge system inside the Addiction sector, working title:

**الأطلس العربي التفاعلي للمواد ذات التأثير النفساني والإدمان**

It is not a single article or a shallow table. It must function as:
- a scientific Arabic encyclopedia of psychoactive/addictive substances;
- a structured, extensible database;
- interactive search/filter/sort;
- a central **Compare Two Substances** tool;
- indexable, high-value substance comparison pages when genuine search/educational intent exists;
- printable professional reference material for awareness, counseling, courses, universities and specialists;
- a continuously updateable evidence base.

Do not delete, hide, or lose useful existing published pages while implementing this project.

## 2. Scientific integrity rules
Never collapse all risk into a single simplistic number. Keep distinct:
- acute toxicity;
- overdose risk;
- serious harm from a single exposure;
- addiction liability / reinforcement;
- tolerance;
- physical dependence;
- psychological dependence;
- withdrawal severity;
- medical danger of withdrawal;
- neurotoxicity;
- cardiovascular harm;
- respiratory harm;
- hepatic/renal harm;
- psychiatric harm;
- long-term harm;
- polysubstance interaction risk;
- antidote/specific emergency treatment availability;
- evidence-based treatment availability;
- evidence certainty.

Do **not** invent values such as “80% addicted after first use”, “15% first-dose death risk”, or “recovery difficulty 3/10”. If a valid source does not support a numerical estimate for a specific population/context, state uncertainty instead.

Preferred uncertainty language:
- documented / possible / rare / unknown;
- high / moderate / limited / insufficient evidence;
- documented cases after one exposure, when applicable.

Any Rawafid composite risk score must have a published methodology, version, weights, limitations, and source mapping. Never present an internal score as a universally accepted medical scale.

## 3. Substance coverage
Cover, progressively and evidence-first:
- opioids;
- stimulants;
- sedatives/hypnotics;
- cannabis/cannabinoids;
- synthetic and semi-synthetic cannabinoids;
- hallucinogens/psychedelics;
- dissociatives;
- inhalants;
- alcohol;
- nicotine/tobacco within addiction context;
- misused prescription medications;
- relevant OTC misuse;
- NPS/new psychoactive substances;
- nitazenes;
- synthetic cathinones;
- other emerging substances identified by credible monitoring systems.

Publishing tiers:
A. Major substances — full encyclopedia page.
B. Less common/specialized substances — full page only when evidence is sufficient.
C. Emerging NPS with sparse evidence — evidence-limited record; never fill missing fields by guessing.

## 4. Mandatory naming model for every substance
This section is a **project owner requirement** and must be implemented systematically.

### 4.1 Names visible to the user
Every substance page must show, when applicable:
1. **Arabic name** — الاسم العربي.
2. **English name** — الاسم الإنجليزي.
3. **Commonly used name / common name** — الاسم المتعارف عليه, if different from the formal name.
4. **Scientific/chemical name** when useful and materially different.
5. Important legitimate synonyms may be shown naturally if they help the user identify the substance.

Recommended page identity block:
- `display_name_ar`
- `display_name_en`
- `common_name_ar`
- `common_name_en`
- `scientific_name`
- `recognized_synonyms`

The H1 and visible identity area must be human-readable and not stuffed with aliases.

### 4.2 Arabic-letter transliteration of the English name — internal alias
The project owner specifically wants a version of the **English name written in Arabic letters**, not the translated Arabic name.

Examples of the concept only:
- English lexical form -> Arabic-script phonetic/transliterated variant.

Store this as a distinct field, e.g.:
- `english_name_ar_transliteration`

This is **not the Arabic translation** and must never overwrite `display_name_ar`.

Use it primarily for:
- internal site search matching;
- synonym/alias resolution;
- query normalization;
- typo-tolerant lookup;
- redirect/route alias resolution where appropriate;
- analytics/search-intent discovery.

Do **not** emit it as invisible keyword-stuffed HTML solely to manipulate search engines.

### 4.3 Misspellings and spelling variants — internal search/SEO intelligence
Maintain structured arrays such as:
- `search_aliases_ar`
- `search_aliases_en`
- `transliteration_variants_ar`
- `common_misspellings_ar`
- `common_misspellings_en`
- `spacing_variants`
- `hyphenation_variants`
- `legacy_spellings`

These must be curated, evidence/query-informed, and deduplicated.

Use them for:
- internal search;
- typo correction (“هل تقصد…؟”);
- query normalization;
- site search autocomplete;
- analytics aggregation;
- optional non-indexed redirect aliases to the canonical substance URL;
- deciding which **natural, useful** variants deserve mention in visible prose.

### 4.4 SEO safety rule for hidden variants
Never implement “hidden SEO keywords” as:
- hidden text matching background color;
- `display:none` keyword blocks;
- off-screen spam blocks;
- massive invisible alias lists;
- `meta name="keywords"` expecting Google ranking benefit.

Google does not use the meta-keywords tag for ranking, and keyword stuffing/hidden text creates spam risk. The safe implementation is **internal alias/search intelligence + natural visible wording + canonical routing**, not invisible keyword dumps.

If a misspelling has genuine, material search demand and users benefit from clarification, it may appear naturally in a short visible note, FAQ, or explanatory sentence — never as a repeated list.

### 4.5 Canonical alias routing
If alternate spelling/transliteration URLs are supported:
- all aliases must resolve/redirect to one canonical substance URL;
- do not create separately indexable thin pages for each misspelling;
- prevent duplicate sitemap entries;
- canonical must be consistent across title, internal links, sitemap and redirects.

Example canonical pattern:
`/addiction/substances/{canonical-slug}`

### 4.6 Search normalization
The internal search engine should normalize at least:
- Arabic hamza/alef variants when appropriate;
- Arabic ya/alif-maqsura where appropriate;
- ta marbuta/ha only when linguistically justified;
- tatweel removal;
- diacritic removal for matching;
- whitespace and punctuation;
- Arabic/English case-insensitive matching;
- transliteration aliases;
- common spelling mistakes;
- English hyphen/space variants.

Never rewrite the displayed canonical name merely because normalized search matching uses another form.

## 5. Core data fields per substance
Where evidence exists, support:

### Identity
- Arabic/English/common/scientific names;
- aliases and controlled internal search variants;
- drug class;
- chemical family when relevant;
- legitimate medical use when applicable.

### Physical form
- plant/resin/powder/crystals/tablets/capsules/liquid/gas/vapor/patch/other;
- warning: appearance never proves identity, purity, concentration or contents.

### Epidemiology
- users/prevalence;
- geography;
- year;
- age/sex when relevant and available;
- trend over time;
- source/method.

### Mechanism and effects
- mechanism of action;
- receptors/transmitters;
- CNS/PNS effects;
- acute psychological/physical effects;
- approximate onset/duration only when useful and safe;
- never confuse effect duration with toxicology-test detection windows.

### Acute risk
- acute toxicity;
- overdose risk;
- major toxicity signs;
- possible fatal mechanisms;
- emergency warning signs.

### Single-exposure harm
- documented permanent harm after one exposure, if any;
- brain, nerves, heart, stroke/hypoxia/seizure, liver, kidney, psychiatric injury;
- evidence certainty per claim.

### Addiction/dependence
- reinforcement;
- tolerance;
- physical dependence;
- psychological dependence;
- use disorder potential;
- evidence about speed of progression when defensible;
- no invented “first-use addiction probability”.

### Withdrawal/recovery
- symptoms;
- severity;
- approximate course where evidence supports it;
- whether withdrawal can be medically dangerous;
- evidence-based behavioral treatment;
- evidence-based pharmacotherapy;
- never reduce “recovery difficulty” to a fabricated number.

### Short- and long-term harms
Separate short-term from long-term and cover relevant systems:
- brain/cognition;
- nerves;
- cardiovascular;
- respiratory;
- liver;
- kidney;
- GI;
- immune system if supported;
- mental health;
- social/functional harm where strong sources support it.

### Special populations
When supported:
- pregnancy/fetus;
- adolescents;
- older adults;
- relevant comorbidities.

### Polysubstance interactions
- alcohol;
- opioids;
- sedatives;
- stimulants;
- other material combinations.
Do not turn interaction information into instructions for achieving stronger effects.

### Emergency treatment
Use the label:
**الاستجابة للتسمم والعلاج النوعي**
not “substances that reduce the drug effect”.

State:
- whether a specific antidote exists;
- whether treatment is supportive;
- emergency warning signs;
- evidence-based interventions such as naloxone for opioid overdose when applicable.
Never publish home recipes intended to “cancel” a drug effect.

### Mortality
Separate:
- direct poisoning/overdose deaths;
- deaths where the drug was present/contributory;
- indirect/attributable burden where valid methodology exists.

Every mortality number must include:
**year + geography + metric definition + source + methodological note**.
Never present US-only data as global.

### Review/evidence
- sources;
- evidence grade;
- last updated;
- last scientific review;
- methodological notes;
- follow site policy for “reviewed by Rawafid team”; never invent individual reviewer names.

## 6. Interactive atlas homepage
Build an institutional data interface, not superficial cards.

Core navigation:
- المواد
- الفئات
- قارن بين مادتين
- المقارنات الشائعة
- الانتشار
- الوفيات والأضرار
- الدماغ والأعصاب
- العلاج والتعافي
- المواد الجديدة NPS
- المنهج والمصادر

Search must support Arabic/English/formal/common names plus internal aliases and typo normalization.

Sortable dimensions should include, where methodologically defensible:
- acute toxicity;
- overdose risk;
- dependence/addiction dimension;
- withdrawal danger;
- neurological harm;
- cardiovascular harm;
- respiratory harm;
- chronic organ harm;
- serious single-exposure harm;
- prevalence;
- comparable mortality metrics;
- treatment availability;
- evidence strength;
- data recency.

Never label a substance “the safest drug”. Lower risk on one dimension does not mean safe overall.

## 7. Central feature: Compare Two Substances
This is a **primary product feature**, not an optional extra.

UX:
- select/search substance A;
- select/search substance B;
- compare;
- swap sides;
- open each full substance page;
- stable shareable comparison URL;
- print A4;
- PDF export if high-quality implementation is available;
- excellent mobile behavior.

Compare at minimum:
- names/class/form;
- prevalence;
- mechanism;
- onset/duration where appropriate;
- acute toxicity;
- overdose risk;
- severe single-exposure harm;
- addiction/dependence;
- tolerance;
- withdrawal severity/medical danger;
- brain/nerves;
- heart;
- respiration;
- liver/kidney;
- psychiatric effects;
- short-term harm;
- long-term harm;
- documented permanent harm;
- polysubstance risk;
- mortality with time/geography context;
- antidote/specific emergency response;
- evidence-based treatment;
- recovery considerations;
- evidence strength;
- data date.

Never automatically conclude “A is safer than B”. Prefer axis-specific conclusions.

## 8. Comparison pages are a core SEO/content strategy
Owner requirement: focus strongly on genuine comparison search intents such as:
- الفرق بين الهيروين والفنتانيل
- الهيروين مقابل الفنتانيل
- الكوكايين أم الميثامفيتامين: ما الفرق؟
- الترامادول مقابل المورفين
- القنب الطبيعي مقابل القنبيات الصناعية

Comparison route example:
`/addiction/compare/fentanyl-vs-heroin`

Canonical pair rule:
- A-vs-B and B-vs-A must not become two indexable duplicates;
- one deterministic `canonical_pair_key` per pair.

Only index comparison pages when:
- real search intent or clear educational value exists;
- both substances have sufficient evidence;
- the page contains a genuine comparative synthesis, not two copied summaries;
- unique explanatory content exists;
- comparison-specific FAQ/questions are useful and accurate;
- source coverage is adequate.

**Do not generate all pairwise combinations across thousands of substances.** That would create thin/doorway/scaled-content risk.

Natural search intent coverage may include:
- الفرق بين X وY;
- X مقابل Y;
- which has higher overdose risk?;
- differences in effect;
- differences in withdrawal;
- differences in treatment;
- differences in neurological/cardiac risk.

No keyword stuffing and no “which is safe?” framing.

## 9. Substance page structure
Canonical route:
`/addiction/substances/{slug}`

Recommended sections:
1. identity/summary;
2. multidimensional risk card;
3. definition/classification;
4. forms/identity caveat;
5. prevalence;
6. mechanism;
7. acute effects;
8. duration;
9. toxicity/overdose;
10. emergency signs;
11. single-exposure injury;
12. brain/nerves;
13. heart/respiration;
14. liver/kidney/other organs;
15. psychiatric effects;
16. addiction/dependence/tolerance;
17. withdrawal;
18. long-term harms;
19. polysubstance interactions;
20. special populations when applicable;
21. emergency response/specific treatment;
22. use-disorder treatment/recovery;
23. mortality with correct context;
24. high-certainty knowledge;
25. limited/uncertain evidence;
26. useful FAQ;
27. related comparisons;
28. sources;
29. review/update metadata.

No filler and no generic paragraphs reusable across unrelated substances.

## 10. Print/export
Any filtered result or two-substance comparison should print professionally in RTL A4:
- Rawafid identity;
- report/comparison title;
- selected substances/filters;
- print date;
- source-data dates;
- clear tables;
- indicator definitions;
- uncertainty/safety caveat;
- compact sources;
- live-page URL/QR if feasible;
- dedicated `@media print` CSS;
- avoid destructive page breaks inside key rows/cards.

## 11. Source hierarchy
Prefer:
1. WHO;
2. UNODC World Drug Report/data portal;
3. EUDA;
4. NIH/NIDA;
5. CDC/NCHS with explicit US context;
6. SAMHSA;
7. FDA/EMA/regulators where applicable;
8. Cochrane/systematic reviews;
9. strong clinical guidelines;
10. high-quality peer-reviewed studies.

Rules:
- newest reliable evidence, not newest date at any cost;
- epidemiology numbers always include geography/year;
- do not compare incompatible metrics as if normalized;
- do not use commercial rehab sites as primary scientific sources;
- surface uncertainty and conflicting evidence.

## 12. Safety/editorial boundaries
The section is for education, prevention, counseling, health risk and treatment.
Never provide operational guidance for:
- drug manufacture;
- preparation optimization;
- recreational dosing;
- maximizing route efficiency;
- evading drug tests;
- obtaining illegal substances;
- mixing substances for stronger effects.

Emergency and treatment information may be provided in prevention/medical form.

## 13. Suggested data model
`Substance`:
- id;
- slug;
- display_name_ar;
- display_name_en;
- common_name_ar;
- common_name_en;
- scientific_name;
- recognized_synonyms;
- english_name_ar_transliteration;
- search_aliases_ar;
- search_aliases_en;
- transliteration_variants_ar;
- common_misspellings_ar;
- common_misspellings_en;
- spacing_variants;
- hyphenation_variants;
- classes;
- physical_forms;
- mechanisms;
- acute_effects;
- duration_summary;
- risk dimensions with methodology refs;
- dependence/withdrawal dimensions;
- organ harms;
- single-exposure harms;
- long-term harms;
- emergency response;
- treatment options;
- evidence grades;
- sources;
- reviewed_at;
- updated_at;
- content_status.

`Source`:
- organization/journal;
- title;
- URL/DOI;
- publication_date;
- accessed_date;
- geography;
- source_type;
- evidence_level.

`EpidemiologyRecord`:
- substance_id;
- metric;
- value/range;
- unit;
- geography;
- population;
- year;
- source_id.

`MortalityRecord`:
- substance_id;
- metric_type: direct/overdose/mentioned/contributory/attributable;
- value/range;
- geography;
- year;
- definition;
- source_id.

`ComparisonPage`:
- substance_a;
- substance_b;
- canonical_pair_key;
- indexable;
- search_intent;
- editorial_summary;
- custom_faq;
- comparison_specific_sources;
- reviewed_at.

`EvidenceGrade`:
- grade;
- definition;
- criteria;
- version.

All sensitive numeric fields should require source linkage before publication.

## 14. SEO implementation standard
Apply the site's comprehensive SEO standard:
- crawlability/indexability;
- canonical;
- valid sitemap;
- truthful lastmod;
- unique title/meta description;
- semantic headings;
- strong internal linking;
- Open Graph;
- applicable valid structured data;
- accessibility;
- Core Web Vitals;
- image SEO when real images add value;
- no keyword stuffing;
- no hidden text;
- no doorway pages;
- no scaled-content abuse;
- no duplicate comparison permutations.

Important current-rule reminder:
- `meta name="keywords"` is not used by Google Search for indexing/ranking.
- hidden keyword blocks and repetitive spelling variants are not an acceptable substitute for helpful visible content.
- programmatic meta descriptions are acceptable for database-driven pages only when descriptive, unique and human-readable.

Use aliases/misspellings for search understanding and query matching rather than invisible spam.

## 15. Accessibility/performance
- mobile-first;
- excellent RTL;
- WCAG-aware;
- keyboard-operable filters/sort/compare;
- screen-reader labels;
- do not encode risk through color alone;
- responsive tables;
- pagination/virtualization rather than loading thousands of records at once;
- fast Core Web Vitals;
- charts must have text/table alternatives.

## 16. Educational concept pages
Create high-value explanatory pages for:
- addiction vs dependence vs tolerance;
- what withdrawal means;
- what overdose means;
- why “lower toxicity” does not mean “safe”;
- neurotoxicity;
- why polysubstance use raises mortality risk;
- what NPS are;
- how to read atlas risk ratings;
- how mortality data should be interpreted;
- how evidence certainty is graded.

## 17. Execution order
Phase 0: audit current Addiction sector and preserve useful content.
Phase 1: taxonomy, data schema, evidence-grading method, risk dimensions, canonical rules, source model.
Phase 2: atlas landing, search/filter/sort, compare-two tool, print mode.
Phase 3: first high-priority reference set spanning multiple drug classes to validate schema.
Phase 4: high-value comparison pages selected by real search intent + evidence.
Phase 5: expansion into additional major substances and NPS.
Phase 6: rigorous QA — facts, sources, duplicates, schema validation, RTL/mobile/print/accessibility, sitemap/canonical/indexability/internal links/Core Web Vitals.

## 18. Definition of Done — substance page
A substance page is not done until:
- names/classification are correct;
- English + Arabic + common names are implemented;
- internal transliteration/search aliases exist where useful;
- no unsupported numeric claims;
- missing evidence remains explicitly unknown;
- acute toxicity is distinct from addiction;
- short/long-term harms are separated;
- withdrawal is covered correctly;
- emergency content is safe;
- evidence uncertainty is visible;
- sources are strong;
- content is unique;
- related comparisons are linked when useful;
- canonical/indexability/SEO are correct;
- mobile/RTL/print works;
- page has review/update date.

## 19. Definition of Done — comparison page
An indexable comparison page is not done until:
- one canonical pair key;
- genuine intent/value;
- sufficient data for both substances;
- differences are synthesized, not merely concatenated;
- no blanket “safer” claim;
- key comparison dimensions present;
- numbers include year/geography/source context;
- evidence grade present;
- links to both substance pages;
- related educational links;
- unique title/meta/H1;
- no keyword stuffing;
- no thin/doorway pattern;
- printable layout;
- valid, applicable structured data only.

## 20. Instructions to the next agent
1. Read this file in full before touching the Addiction atlas.
2. Inspect the actual repository/framework/routes before designing implementation details.
3. Preserve published useful pages/content.
4. Verify current scientific claims against authoritative sources at execution time.
5. Treat **Compare Two Substances + high-value comparison search pages** as core architecture.
6. Treat **English/Arabic/common names + transliteration/typo alias intelligence** as core architecture.
7. Never implement hidden keyword spam; use aliases/search normalization/canonical routing correctly.
8. Do not mass-create all pairwise comparison pages.
9. Keep data separated from presentation so sources and statistics can be updated safely.
10. Test RTL, mobile, printing and accessibility.
11. Every sensitive claim must be traceable to a source.
12. If evidence is insufficient, say so rather than inventing certainty.

**This document is the internal execution reference for the Addiction Atlas until replaced by a later version.**
