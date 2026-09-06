# مستكشف نمط الاجترار الفكري — Technical Spec v1.0

Status: Rawafid exploratory tool — NOT clinically validated and NOT diagnostic.

## Construct
A self-report exploratory profile of repetitive negative thinking patterns, especially repetitive return to upsetting thoughts without reaching a useful conclusion.

## Intended use
- Adult self-reflection.
- Help users notice repetitive thinking patterns and their impact on daily functioning.
- Prepare clearer notes for discussion with a qualified professional if desired.

## Not intended for
- Diagnosis of depression, anxiety, OCD, PTSD or any psychiatric disorder.
- Suicide/self-harm risk assessment.
- Determining treatment.
- Assessing children.

## Target population
Adults 18+ who can read Arabic comfortably.

## Reference timeframe
«خلال الأسبوعين الماضيين».

## Response scale
0 = أبدًا
1 = قليلًا
2 = أحيانًا
3 = كثيرًا
4 = معظم الوقت

## Dimensions
1. **Repetition / التكرار** — returning repeatedly to the same upsetting thought.
2. **Difficulty disengaging / صعوبة التوقف** — difficulty shifting attention away once repetitive thinking begins.
3. **Self-focused negative review / مراجعة الذات السلبية** — repeatedly revisiting personal mistakes, shortcomings or perceived failures.
4. **Problem-solving blockage / تعطيل الوصول للحل** — thinking feels active but does not produce useful decisions or action.
5. **Functional interference / الأثر على الحياة اليومية** — interference with sleep, concentration, tasks and presence with others.

## Blueprint
32 items total:
- Repetition: 7
- Difficulty disengaging: 7
- Self-focused negative review: 6
- Problem-solving blockage: 6
- Functional interference: 6

No item should contain clinical jargon. Every item must pass `.self-tests/ITEM_WRITING_STANDARD.md`.

## Scoring
Each item scores 0–4.
Total range: 0–128.
Dimension scores are reported as percentage of that dimension's maximum.

Because this version is exploratory and not normed, no clinical cutoffs are used.
Descriptive result bands for user feedback only:
- 0–24%: منخفض في إجاباتك الحالية
- 25–44%: محدود
- 45–64%: ملحوظ
- 65–79%: مرتفع
- 80–100%: مرتفع جدًا

These labels describe response intensity only. They do not indicate disorder severity.

## Result logic
Report:
- overall response-intensity percentage;
- strongest two dimensions;
- plain-language explanation;
- possible confounds: acute stress, sleep loss, major life event, pain/illness, recent conflict, workload;
- reflection questions;
- conditional suggestion to seek professional assessment if repetitive thinking is persistent, distressing or functionally disruptive.

## Missing answers
Do not calculate final result unless every item is answered. UI should guide user back to unanswered items.

## Privacy
All answers and scoring remain in runtime browser memory. No localStorage/sessionStorage/IndexedDB/cookie/query-string/dataLayer transmission. No item-level analytics.

## Safety
This tool intentionally contains no self-harm item because it is not a risk-assessment instrument. General support text should tell the user that urgent safety concerns require direct professional/emergency help and should not be evaluated by this quiz.

## Evidence rationale
The construct is informed by research on rumination and repetitive negative thinking as processes associated with emotional distress across diagnostic categories. This tool does NOT reproduce a proprietary scale and does NOT claim equivalence to RRS, PTQ, RRQ or any other established instrument.

## Versioning
v1.0 — initial exploratory version, 2026-08-25.
