# Full content recovery audit — batch 009

## Scope

- Production recovery run: `31136028268` on `main` SHA `ee0f507f1d2d808852dca4b6d6f553d4cbc6746a`.
- Diagnostic artifact: `8978029443` (`content-recovery-diagnostics-31136028268`), digest `sha256:64fac48d938a3bb9d913fa1cc119d2df80b9f180845a361f53b132a7e1b210fd`.
- Validated production baseline used by that run: artifact `8967391081`, run `31100647981`, digest `sha256:29d880540cc281fc8de765ab6177504755cdf5c1090ad27d92b121ae8e605d26`.
- Branches fetched by production recovery: 1024.
- Result before final-integrity failure: 4563 HTML pages, 119 historical restorations, 0 remaining thin pages, completeness ratio 1.0.

## No-loss audit finding

The historical selector is not strictly monotonic in content length. It can replace a current non-redirect page with a shorter candidate when the structural score is at least 8% higher. This contradicts the recovery policy for content-bearing pages: the richer/longer current version must remain the base, and unique material from shorter versions must be merged into it instead of replacing it.

Exactly two of the 119 selected restorations reduced the word count:

- `guided-assessment/index.html`: **1308 → 714 words** (`2277.8 → 3104.0` score). This is a real content-regression risk. The current page is a substantive non-diagnostic preparation guide; the baseline candidate is a different historical directory for 100 guided-question pages. The historical directory contains unique navigation value, but it must not overwrite the current guide. Preserve the current page as the base and integrate/discover the 100-question collection without deleting the current 1308-word guide.
- `family-guide/conditions/prader-willi-syndrome/index.html`: **33 → 31 words**. This path is an intentional `noindex` redirect alias to the expanded canonical guide, so it is classified as alias maintenance rather than loss of editorial content.

All other selected restorations were non-shortening by word count.

## Guided-assessment version disposition

- Current `main`: `guided-assessment/index.html`, 1308 words, title `الأسئلة الموجهة لتنظيم الملاحظات قبل التقييم | منصة روافد`; keep as primary base.
- Validated baseline: same route, 714 words, title `أسئلة التقييم النفسي الاسترشادية`; historical collection index linking `questions-001/` through `questions-100/`.
- The 100 child routes are present in the production recovery inventory even though they are absent as source files on current `main`; therefore the historical index represents unique collection/navigation information rather than a superior replacement for the current route.
- Required merge direction: current 1308-word guide remains intact; expose the historical 100-page question collection through a compatible collection/directory surface or additive section only after link, safety, SEO, and canonical review. Do not replace the current route with the 714-word index.

## Interaction with open work

- Do not modify `scripts/recover_content_full_history_v3.py` or its regression test in this batch; PR #1106 currently owns the obsolete historical-prototype resurrection guard.
- PR #1092 owns lab/assessment workflows and v32 content; PR #1095 owns `learning-paths/caregiver-foundations/**`; PR #1100 owns CI/finalizer cleanup.
- This batch records the no-loss selector defect and the complete restoration ledger without touching those reserved files.

## Complete restoration ledger from run 31136028268

| Path | Selected source | Previous words | Selected words | Δ words | Previous score | Selected score |
|---|---|---:|---:|---:|---:|---:|
| `404/index.html` | `validated-baseline` | 0 | 269 | +269 | 0 | 326.6 |
| `about/index.html` | `validated-baseline` | 0 | 325 | +325 | 0 | 471.2 |
| `accessibility/index.html` | `validated-baseline` | 0 | 417 | +417 | 0 | 635.2 |
| `addiction/family-guide/index.html` | `validated-baseline` | 0 | 594 | +594 | 0 | 796.0 |
| `addiction/index.html` | `validated-baseline` | 0 | 536 | +536 | 0 | 730.6 |
| `addiction/professionals/index.html` | `validated-baseline` | 0 | 565 | +565 | 0 | 742.2 |
| `addiction/recovery-plans/index.html` | `validated-baseline` | 0 | 541 | +541 | 0 | 688.8 |
| `addiction/resources/index.html` | `validated-baseline` | 0 | 477 | +477 | 0 | 646.6 |
| `addiction/substances/index.html` | `validated-baseline` | 0 | 516 | +516 | 0 | 678.4 |
| `addiction/support/index.html` | `validated-baseline` | 0 | 515 | +515 | 0 | 674.4 |
| `addiction/treatment/index.html` | `validated-baseline` | 0 | 520 | +520 | 0 | 688.4 |
| `addiction/types/index.html` | `validated-baseline` | 0 | 541 | +541 | 0 | 699.8 |
| `ai-search/index.html` | `validated-baseline` | 0 | 327 | +327 | 0 | 499.8 |
| `api/index.html` | `validated-baseline` | 0 | 294 | +294 | 0 | 436.4 |
| `article/anxiety-disorders/index.html` | `validated-baseline` | 0 | 487 | +487 | 0 | 653.8 |
| `article/autism-spectrum-disorder/index.html` | `validated-baseline` | 0 | 532 | +532 | 0 | 701.4 |
| `article/depression/index.html` | `validated-baseline` | 0 | 492 | +492 | 0 | 660.2 |
| `article/mental-health/index.html` | `validated-baseline` | 0 | 482 | +482 | 0 | 647.4 |
| `article/obsessive-compulsive-disorder/index.html` | `validated-baseline` | 0 | 501 | +501 | 0 | 669.6 |
| `article/post-traumatic-stress-disorder/index.html` | `validated-baseline` | 0 | 513 | +513 | 0 | 683.0 |
| `article/schizophrenia/index.html` | `validated-baseline` | 0 | 494 | +494 | 0 | 661.6 |
| `article/social-anxiety-disorder/index.html` | `validated-baseline` | 0 | 489 | +489 | 0 | 657.4 |
| `article/what-is-psychology/index.html` | `validated-baseline` | 0 | 489 | +489 | 0 | 655.0 |
| `assessment-lab/index.html` | `validated-baseline` | 0 | 1500 | +1500 | 0 | 2840.8 |
| `assessments/index.html` | `validated-baseline` | 0 | 1552 | +1552 | 0 | 2919.8 |
| `blog/anxiety-normal-vs-disorder/index.html` | `validated-baseline` | 0 | 1046 | +1046 | 0 | 1517.0 |
| `blog/index.html` | `validated-baseline` | 0 | 522 | +522 | 0 | 744.0 |
| `booklets/index.html` | `validated-baseline` | 0 | 331 | +331 | 0 | 494.2 |
| `care-guides/index.html` | `validated-baseline` | 0 | 728 | +728 | 0 | 1201.8 |
| `cognitive-tests/index.html` | `validated-baseline` | 0 | 904 | +904 | 0 | 1597.2 |
| `comparisons/index.html` | `validated-baseline` | 0 | 1122 | +1122 | 0 | 2022.0 |
| `contact/index.html` | `validated-baseline` | 0 | 233 | +233 | 0 | 353.4 |
| `copyright/index.html` | `validated-baseline` | 0 | 456 | +456 | 0 | 632.6 |
| `daily-tools/index.html` | `validated-baseline` | 0 | 604 | +604 | 0 | 945.4 |
| `developers/index.html` | `validated-baseline` | 0 | 452 | +452 | 0 | 669.6 |
| `encyclopedia/index.html` | `validated-baseline` | 0 | 835 | +835 | 0 | 1356.0 |
| `family-guide/conditions/prader-willi-syndrome/index.html` | `0c8b01ce70c37181b536a48820289ded41569082` | 33 | 31 | -2 | 10 | 79.5 |
| `family-guide/index.html` | `validated-baseline` | 0 | 598 | +598 | 0 | 848.4 |
| `glossary/index.html` | `validated-baseline` | 0 | 704 | +704 | 0 | 1118.8 |
| `guided-assessment/index.html` | `validated-baseline` | 1308 | 714 | -594 | 2277.8 | 3104.0 |
| `guides/index.html` | `validated-baseline` | 0 | 578 | +578 | 0 | 845.8 |
| `home/index.html` | `validated-baseline` | 0 | 270 | +270 | 0 | 392.0 |
| `index.html` | `validated-baseline` | 0 | 1106 | +1106 | 0 | 1645.0 |
| `learning-paths/index.html` | `validated-baseline` | 0 | 860 | +860 | 0 | 1419.4 |
| `library/index.html` | `validated-baseline` | 0 | 535 | +535 | 0 | 831.0 |
| `magazine/index.html` | `validated-baseline` | 0 | 591 | +591 | 0 | 888.4 |
| `manifest/index.html` | `validated-baseline` | 0 | 226 | +226 | 0 | 333.6 |
| `mental-health/index.html` | `validated-baseline` | 0 | 485 | +485 | 0 | 657.6 |
| `methodology/index.html` | `validated-baseline` | 0 | 779 | +779 | 0 | 1048.6 |
| `partners/index.html` | `validated-baseline` | 0 | 501 | +501 | 0 | 765.8 |
| `privacy-policy/index.html` | `validated-baseline` | 0 | 439 | +439 | 0 | 589.0 |
| `privacy/index.html` | `validated-baseline` | 0 | 432 | +432 | 0 | 583.2 |
| `provider-assessment-demo/index.html` | `validated-baseline` | 0 | 730 | +730 | 0 | 1119.2 |
| `quick-info/index.html` | `validated-baseline` | 0 | 619 | +619 | 0 | 1019.8 |
| `research/index.html` | `validated-baseline` | 0 | 642 | +642 | 0 | 930.4 |
| `rights/index.html` | `validated-baseline` | 0 | 594 | +594 | 0 | 823.2 |
| `schools/index.html` | `validated-baseline` | 0 | 539 | +539 | 0 | 761.0 |
| `search/index.html` | `validated-baseline` | 0 | 364 | +364 | 0 | 565.0 |
| `sections/index.html` | `validated-baseline` | 0 | 790 | +790 | 0 | 1221.2 |
| `sectors/child/index.html` | `validated-baseline` | 0 | 718 | +718 | 0 | 1060.8 |
| `sectors/family/index.html` | `validated-baseline` | 0 | 685 | +685 | 0 | 1025.0 |
| `sectors/home/index.html` | `validated-baseline` | 0 | 676 | +676 | 0 | 1010.2 |
| `sectors/index.html` | `validated-baseline` | 0 | 514 | +514 | 0 | 790.2 |
| `sectors/women/index.html` | `validated-baseline` | 0 | 694 | +694 | 0 | 1039.8 |
| `special-needs/all-pages/index.html` | `validated-baseline` | 0 | 1153 | +1153 | 0 | 3095.0 |
| `special-needs/conditions/cerebral-palsy/index.html` | `527f0c87f8f45725777a970e344955cd6f59966d` | 985 | 1542 | +557 | 1584.2 | 2387.0 |
| `special-needs/conditions/cornelia-de-lange-syndrome/index.html` | `5846747816455d108e8f53d3277c307c91a7f65a` | 1270 | 1838 | +568 | 2004.2 | 2813.8 |
| `special-needs/conditions/down-syndrome/index.html` | `5846747816455d108e8f53d3277c307c91a7f65a` | 1558 | 2010 | +452 | 2363.4 | 3034.0 |
| `special-needs/conditions/fragile-x-syndrome/index.html` | `5846747816455d108e8f53d3277c307c91a7f65a` | 1244 | 1749 | +505 | 1969.8 | 2701.4 |
| `special-needs/conditions/global-developmental-delay/index.html` | `527f0c87f8f45725777a970e344955cd6f59966d` | 1176 | 1818 | +642 | 1834.0 | 2790.8 |
| `special-needs/conditions/prader-willi-syndrome/index.html` | `5846747816455d108e8f53d3277c307c91a7f65a` | 1317 | 1836 | +519 | 2078.6 | 2819.0 |
| `special-needs/conditions/rett-syndrome/index.html` | `5846747816455d108e8f53d3277c307c91a7f65a` | 1237 | 1758 | +521 | 1975.0 | 2724.2 |
| `special-needs/guides/communication/index.html` | `validated-baseline` | 0 | 806 | +806 | 0 | 1241.2 |
| `special-needs/index.html` | `validated-baseline` | 0 | 1046 | +1046 | 0 | 1608.0 |
| `special-needs/resources/index.html` | `validated-baseline` | 0 | 623 | +623 | 0 | 947.0 |
| `special-needs/tools/index.html` | `validated-baseline` | 0 | 490 | +490 | 0 | 730.6 |
| `specialists-partners/index.html` | `validated-baseline` | 0 | 468 | +468 | 0 | 724.0 |
| `start-here/index.html` | `validated-baseline` | 0 | 521 | +521 | 0 | 809.8 |
| `terms/attention-deficit-hyperactivity-disorder/index.html` | `5846747816455d108e8f53d3277c307c91a7f65a` | 785 | 1521 | +736 | 1280.4 | 2304.0 |
| `terms/autism-spectrum-disorder/index.html` | `5846747816455d108e8f53d3277c307c91a7f65a` | 832 | 1617 | +785 | 1342.4 | 2437.0 |
| `terms/bipolar-disorder/index.html` | `5846747816455d108e8f53d3277c307c91a7f65a` | 739 | 1455 | +716 | 1207.8 | 2204.0 |
| `terms/borderline-personality-disorder/index.html` | `5846747816455d108e8f53d3277c307c91a7f65a` | 704 | 1402 | +698 | 1161.6 | 2135.2 |
| `terms/depression/index.html` | `5846747816455d108e8f53d3277c307c91a7f65a` | 710 | 1418 | +708 | 1168.2 | 2163.0 |
| `terms/generalized-anxiety-disorder/index.html` | `5846747816455d108e8f53d3277c307c91a7f65a` | 729 | 1446 | +717 | 1192.6 | 2189.4 |
| `terms/obsessive-compulsive-disorder/index.html` | `5846747816455d108e8f53d3277c307c91a7f65a` | 744 | 1471 | +727 | 1215.6 | 2228.6 |
| `terms/panic-disorder/index.html` | `5846747816455d108e8f53d3277c307c91a7f65a` | 724 | 1432 | +708 | 1184.8 | 2170.8 |
| `terms/post-traumatic-stress-disorder/index.html` | `5846747816455d108e8f53d3277c307c91a7f65a` | 751 | 1488 | +737 | 1224.0 | 2252.8 |
| `terms/schizophrenia/index.html` | `5846747816455d108e8f53d3277c307c91a7f65a` | 729 | 1448 | +719 | 1190.4 | 2194.8 |
| `terms/social-anxiety-disorder/index.html` | `5846747816455d108e8f53d3277c307c91a7f65a` | 720 | 1428 | +708 | 1180.4 | 2166.0 |
| `terms/specific-phobia/index.html` | `5846747816455d108e8f53d3277c307c91a7f65a` | 698 | 1388 | +690 | 1144.4 | 2104.4 |
| `tips/index.html` | `validated-baseline` | 0 | 645 | +645 | 0 | 1055.2 |
| `tools/index.html` | `validated-baseline` | 0 | 547 | +547 | 0 | 853.8 |
| `trust/index.html` | `validated-baseline` | 0 | 608 | +608 | 0 | 894.4 |
| `women/index.html` | `validated-baseline` | 0 | 523 | +523 | 0 | 773.8 |
| `outside-the-box/prader-willi-syndrome/index.html` | `5846747816455d108e8f53d3277c307c91a7f65a` | 1123 | 1690 | +567 | 1763.4 | 2559.4 |
| `outside-the-box/cerebral-palsy/index.html` | `527f0c87f8f45725777a970e344955cd6f59966d` | 941 | 1470 | +529 | 1518.0 | 2288.8 |
| `outside-the-box/rett-syndrome/index.html` | `5846747816455d108e8f53d3277c307c91a7f65a` | 1098 | 1632 | +534 | 1732.6 | 2488.4 |
| `outside-the-box/fragile-x-syndrome/index.html` | `5846747816455d108e8f53d3277c307c91a7f65a` | 1107 | 1656 | +549 | 1745.4 | 2517.0 |
| `outside-the-box/global-developmental-delay/index.html` | `527f0c87f8f45725777a970e344955cd6f59966d` | 1011 | 1598 | +587 | 1604.6 | 2437.2 |
| `outside-the-box/cornelia-de-lange-syndrome/index.html` | `5846747816455d108e8f53d3277c307c91a7f65a` | 1151 | 1717 | +566 | 1811.0 | 2605.0 |
| `outside-the-box/down-syndrome/index.html` | `5846747816455d108e8f53d3277c307c91a7f65a` | 1264 | 1816 | +552 | 1940.6 | 2719.2 |
| `outside-the-box/autism-spectrum-disorder/index.html` | `5846747816455d108e8f53d3277c307c91a7f65a` | 1220 | 1794 | +574 | 1902.2 | 2692.0 |
| `outside-the-box/attention-deficit-hyperactivity-disorder/index.html` | `5846747816455d108e8f53d3277c307c91a7f65a` | 1177 | 1742 | +565 | 1837.4 | 2623.6 |
| `outside-the-box/depression/index.html` | `5846747816455d108e8f53d3277c307c91a7f65a` | 1095 | 1641 | +546 | 1715.4 | 2497.0 |
| `outside-the-box/generalized-anxiety-disorder/index.html` | `5846747816455d108e8f53d3277c307c91a7f65a` | 1112 | 1664 | +552 | 1742.2 | 2528.6 |
| `outside-the-box/obsessive-compulsive-disorder/index.html` | `5846747816455d108e8f53d3277c307c91a7f65a` | 1138 | 1695 | +557 | 1777.4 | 2571.2 |
| `outside-the-box/panic-disorder/index.html` | `5846747816455d108e8f53d3277c307c91a7f65a` | 1088 | 1628 | +540 | 1705.6 | 2475.8 |
| `outside-the-box/post-traumatic-stress-disorder/index.html` | `5846747816455d108e8f53d3277c307c91a7f65a` | 1145 | 1708 | +563 | 1790.4 | 2590.6 |
| `outside-the-box/schizophrenia/index.html` | `5846747816455d108e8f53d3277c307c91a7f65a` | 1104 | 1651 | +547 | 1729.8 | 2508.2 |
| `outside-the-box/social-anxiety-disorder/index.html` | `5846747816455d108e8f53d3277c307c91a7f65a` | 1089 | 1630 | +541 | 1707.0 | 2478.0 |
| `outside-the-box/specific-phobia/index.html` | `5846747816455d108e8f53d3277c307c91a7f65a` | 1058 | 1591 | +533 | 1660.8 | 2426.0 |
| `terms/adjustment-disorder/index.html` | `5846747816455d108e8f53d3277c307c91a7f65a` | 685 | 1361 | +676 | 1122.0 | 2068.4 |
| `terms/agoraphobia/index.html` | `5846747816455d108e8f53d3277c307c91a7f65a` | 693 | 1375 | +682 | 1134.2 | 2087.0 |
| `terms/antisocial-personality-disorder/index.html` | `5846747816455d108e8f53d3277c307c91a7f65a` | 702 | 1397 | +695 | 1153.8 | 2124.8 |
| `terms/avoidant-personality-disorder/index.html` | `5846747816455d108e8f53d3277c307c91a7f65a` | 695 | 1382 | +687 | 1142.4 | 2104.0 |
| `terms/body-dysmorphic-disorder/index.html` | `5846747816455d108e8f53d3277c307c91a7f65a` | 707 | 1407 | +700 | 1160.2 | 2143.8 |
| `terms/dissociative-identity-disorder/index.html` | `5846747816455d108e8f53d3277c307c91a7f65a` | 715 | 1421 | +706 | 1174.0 | 2166.4 |
| `terms/eating-disorders/index.html` | `5846747816455d108e8f53d3277c307c91a7f65a` | 697 | 1389 | +692 | 1145.8 | 2115.6 |
| `terms/insomnia/index.html` | `5846747816455d108e8f53d3277c307c91a7f65a` | 690 | 1371 | +681 | 1131.4 | 2085.4 |
| `terms/narcissistic-personality-disorder/index.html` | `5846747816455d108e8f53d3277c307c91a7f65a` | 703 | 1398 | +695 | 1156.0 | 2127.2 |
| `terms/selective-mutism/index.html` | `5846747816455d108e8f53d3277c307c91a7f65a` | 684 | 1358 | +674 | 1120.2 | 2064.0 |
| `terms/trichotillomania/index.html` | `5846747816455d108e8f53d3277c307c91a7f65a` | 690 | 1372 | +682 | 1132.8 | 2087.4 |

## Merge gate

- No merge is approved from this audit alone.
- The selector must not be allowed to shorten a substantive current route in the final production artifact.
- HTML, internal links, RTL, mobile, print, Schema, accessibility, discovery files, artifact identity and live SHA matching remain mandatory.
- The current production failure involving `professional-assessment-hub/` is separately owned by PR #1106 and must not be solved by placeholder assets or publication of the obsolete private prototype.
