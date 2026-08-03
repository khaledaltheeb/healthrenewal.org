from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "sectors" / "women" / "daily-calendar"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise SystemExit(f"Missing patch marker: {label}")
    return text.replace(old, new, 1)


def patch_javascript() -> None:
    path = APP / "calendar.js"
    text = path.read_text(encoding="utf-8")

    if "const noonBoostBank = [" not in text:
        bank = '''  const noonBoostBank = [
    "منتصف اليوم ليس اختبارًا لقدرتك؛ خذي نفسًا واختاري ما تحتاجينه الآن.",
    "أنوثتك ليست قالبًا واحدًا؛ هي طريقتك الخاصة في الحضور والاختيار والاعتناء بنفسك.",
    "ربما لا تحتاجين إلى مزيد من القوة الآن؛ ربما تحتاجين إلى دقيقة أمان وهدوء.",
    "ارفعي كتفيك ثم اتركيهما يهبطان؛ ليس عليك حمل اليوم كله دفعة واحدة.",
    "ضعي لمستك الجميلة في بقية اليوم: كلمة رقيقة لنفسك وحد واضح مع الآخرين.",
    "أنتِ أكثر من قائمة مهام؛ اختاري لحظة صغيرة تعيدك إلى نفسك.",
    "لا تهملي إشارات جسدك كي تكملي الصورة المثالية؛ الإصغاء شكل من أشكال القوة.",
    "رتبي ما بقي من اليوم حول طاقتك الحقيقية، لا حول توقعات غير واقعية.",
    "لمسة عطر تحبينها أو كوب دافئ أو ضوء لطيف قد تكون إشارة عودة لا رفاهية زائدة.",
    "قولي لنفسك: أستطيع تعديل الخطة من دون أن أعتذر عن احتياجي.",
    "اختاري الآن شيئًا واحدًا يخفف عنك بدل إضافة مهمة جديدة.",
    "الجمال في هذا الظهر أن تمنحي نفسك حضورًا كاملًا ولو لدقيقة.",
    "إن كان الصباح ثقيلًا، فالظهر بداية ثانية لا تحتاج إلى إذن.",
    "كوني حنونة وحازمة معًا: رقيقة مع نفسك وواضحة مع ما يستنزفك.",
    "لا تقارني إيقاعك بإيقاع امرأة أخرى؛ لكل جسد وحياة موسم مختلف.",
    "اسألي جسدك الآن: ماء أم حركة أم طعام أم هدوء أم دعم؟ ثم اختاري الأقرب.",
    "يمكنك أن تكوني طموحة وأن تستريحي؛ الأمران لا يتعارضان.",
    "اجعلي بقية اليوم أخف بدرجة واحدة فقط؛ هذا تعديل كافٍ ومؤثر.",
    "قوتك اليوم قد تظهر في طلب المساعدة أو تأجيل ما لا يحتمل طاقتك.",
    "احتفظي بمساحة وردية صغيرة في يومك: شيء تختارينه أنتِ لنفسك فقط.",
    "لا يلزم أن تكوني بخير تمامًا كي تكملي بلطف ووعي.",
    "انظري لما أنجزته منذ الصباح، ثم اختاري الخطوة التالية بلا جلد للذات.",
    "الهدوء ليس غياب الإنجاز؛ أحيانًا هو الطريقة الأذكى لحماية طاقتك.",
    "امنحي نفسك جملة صادقة: أنا أستحق أن أُعامل باحترام، مني ومن الآخرين."
  ];

'''
        text = replace_once(text, "  const factBank = [", bank + "  const factBank = [", "noon bank")

    if 'noonTime: "12:30"' not in text:
        text = replace_once(
            text,
            '      dailyTime: "08:00",\n',
            '      dailyTime: "08:00",\n      noonTime: "12:30",\n',
            "default noon time",
        )

    if "noon: pick(noonBoostBank" not in text:
        text = replace_once(
            text,
            "      morning: pick(morningBank, ordinal + month * 3),\n",
            "      morning: pick(morningBank, ordinal + month * 3),\n      noon: pick(noonBoostBank, ordinal * 13 + month * 19),\n",
            "daily noon content",
        )

    if "function ensureNoonCard()" not in text:
        function = '''
  function ensureNoonCard() {
    let card = $("noonCheckIn");
    if (card) return card;
    card = document.createElement("section");
    card.id = "noonCheckIn";
    card.className = "daily-item noon-checkin";
    card.innerHTML = `
      <span>وقفة الظهر · 12:30</span>
      <h3>كيف تشعرين الآن؟</h3>
      <div class="noon-feelings" role="group" aria-label="اختاري شعورك الآن">
        <button type="button" class="noon-feeling" data-feeling="هادئة" aria-pressed="false">هادئة</button>
        <button type="button" class="noon-feeling" data-feeling="بخير" aria-pressed="false">بخير</button>
        <button type="button" class="noon-feeling" data-feeling="متعبة" aria-pressed="false">متعبة</button>
        <button type="button" class="noon-feeling" data-feeling="قلقة" aria-pressed="false">قلقة</button>
        <button type="button" class="noon-feeling" data-feeling="أحتاج استراحة" aria-pressed="false">أحتاج استراحة</button>
      </div>
      <p id="dailyNoonBoost" class="noon-boost"></p>
      <p id="noonStatus" class="noon-status" aria-live="polite"></p>`;
    card.addEventListener("click", (event) => {
      const button = event.target.closest("button[data-feeling]");
      if (!button) return;
      const key = isoDate(selectedDate);
      state.logs[key] = {
        ...(state.logs[key] || {}),
        noonFeeling: button.dataset.feeling,
        noonCheckedAt: new Date().toISOString()
      };
      saveState();
      card.querySelectorAll("button[data-feeling]").forEach((item) => {
        item.setAttribute("aria-pressed", String(item === button));
      });
      $("noonStatus").textContent = `سُجل شعورك: ${button.dataset.feeling}. خذي من الدفعة ما يناسبك واتركي الباقي.`;
    });
    const grid = document.querySelector(".daily-grid");
    const morning = ensureMorningCard().closest("section");
    grid.insertBefore(card, morning.nextSibling);
    return card;
  }

'''
        text = replace_once(text, "  function renderToday() {", function + "  function renderToday() {", "noon card")

    if 'const noonCard = ensureNoonCard();' not in text:
        text = replace_once(
            text,
            '    ensureMorningCard().textContent = content.morning;\n    $("dailyFact").textContent = content.fact;',
            '    ensureMorningCard().textContent = content.morning;\n    const noonCard = ensureNoonCard();\n    noonCard.querySelector("#dailyNoonBoost").textContent = content.noon;\n    $("dailyFact").textContent = content.fact;',
            "render noon card",
        )

    if "button.dataset.feeling === entry.noonFeeling" not in text:
        text = replace_once(
            text,
            '    const entry = state.logs[key] || {};\n    $("mood").value = entry.mood ?? "";',
            '    const entry = state.logs[key] || {};\n    noonCard.querySelectorAll("button[data-feeling]").forEach((button) => {\n      button.setAttribute("aria-pressed", String(button.dataset.feeling === entry.noonFeeling));\n    });\n    $("noonStatus").textContent = entry.noonFeeling ? `شعور الظهر المسجل: ${entry.noonFeeling}` : "";\n    $("mood").value = entry.mood ?? "";',
            "restore noon selection",
        )

    if '$("noonTime").value = s.noonTime;' not in text:
        text = replace_once(
            text,
            '    $("dailyTime").value = s.dailyTime;\n',
            '    $("dailyTime").value = s.dailyTime;\n    $("noonTime").value = s.noonTime;\n',
            "populate noon time",
        )

    if 'noonTime: /^\\d{2}:\\d{2}$/' not in text:
        text = replace_once(
            text,
            '      dailyTime: /^\\d{2}:\\d{2}$/.test($("dailyTime").value) ? $("dailyTime").value : "08:00",\n',
            '      dailyTime: /^\\d{2}:\\d{2}$/.test($("dailyTime").value) ? $("dailyTime").value : "08:00",\n      noonTime: /^\\d{2}:\\d{2}$/.test($("noonTime").value) ? $("noonTime").value : "12:30",\n',
            "read noon time",
        )

    if 'kind === "noon"' not in text:
        text = replace_once(
            text,
            '    if (kind === "period") return state.settings.privacyMode === "explicit" ? "نافذة الدورة المتوقعة" : "متابعة شخصية";\n',
            '    if (kind === "period") return state.settings.privacyMode === "explicit" ? "نافذة الدورة المتوقعة" : "متابعة شخصية";\n    if (kind === "noon") return state.settings.privacyMode === "neutral" ? "وقفة شخصية" : "كيف أشعر الآن؟";\n',
            "noon event title",
        )

    if "UID:noon-${isoDate(date)}" not in text:
        noon_event = '''      const [noonHour, noonMinute] = state.settings.noonTime.split(":").map(Number);
      const noonStartDate = new Date(date.getFullYear(), date.getMonth(), date.getDate(), noonHour, noonMinute);
      const noonEndDate = new Date(noonStartDate.getTime() + 5 * 60000);
      const noonStart = icsLocal(noonStartDate, state.settings.noonTime);
      const noonEnd = icsLocal(noonEndDate, `${String(noonEndDate.getHours()).padStart(2, "0")}:${String(noonEndDate.getMinutes()).padStart(2, "0")}`);
      lines.push("BEGIN:VEVENT", `UID:noon-${isoDate(date)}@healthrenewal.org`, `DTSTAMP:${icsStamp(now)}`, `DTSTART;TZID=${state.settings.timezone}:${noonStart}`, `DTEND;TZID=${state.settings.timezone}:${noonEnd}`, `SUMMARY:${icsEscape(eventTitle("noon"))}`, `DESCRIPTION:${icsEscape(`كيف تشعرين الآن؟\\nدفعة الظهر: ${content.noon}\\nhttps://healthrenewal.org/sectors/women/daily-calendar/`)}`, "BEGIN:VALARM", "ACTION:DISPLAY", `DESCRIPTION:${icsEscape(eventTitle("noon"))}`, alarmTrigger(state.settings.reminderMinutes), "END:VALARM", "END:VEVENT");
'''
        text = replace_once(
            text,
            '    }\n    const info = state.settings.includeCycleInExport ? cycleInfo(today) : null;',
            noon_event + '    }\n    const info = state.settings.includeCycleInExport ? cycleInfo(today) : null;',
            "noon ICS event",
        )

    text = text.replace(
        'details: `رسالة الصباح: ${content.morning}\\n\\nتطبيق 10 دقائق: ${content.ten}',
        'details: `رسالة الصباح: ${content.morning}\\n\\nوقفة الظهر: كيف تشعرين الآن؟ — ${content.noon}\\n\\nتطبيق 10 دقائق: ${content.ten}',
        1,
    )
    path.write_text(text, encoding="utf-8")


def patch_html() -> None:
    path = APP / "index.html"
    text = path.read_text(encoding="utf-8")
    text = text.replace("calendar.css?v=1.0.0", "calendar.css?v=1.1.0")
    text = text.replace("calendar.js?v=1.0.0", "calendar.js?v=1.1.0")
    text = text.replace(
        "تقويم عربي سنوي لصحة المرأة: معلومة ونصيحة وفكرة واقتراح وتمرين يومي لعشر دقائق،",
        "تقويم عربي سنوي لصحة المرأة: رسالة صباحية، ووقفة ظهر تسأل كيف تشعرين الآن، ومعلومة ونصيحة وفكرة واقتراح وتمرين يومي لعشر دقائق،",
    )
    text = text.replace(
        "كل يوم يتضمن <strong>معلومة</strong>",
        "كل يوم يبدأ برسالة صباحية إيجابية، ويتضمن عند الظهر سؤال <strong>كيف تشعرين الآن؟</strong> مع دفعة نفسية أنثوية متجددة، ثم <strong>معلومة</strong>",
    )
    text = text.replace("خمس خطوات متكاملة ليوم واحد", "محطات متكاملة من الصباح إلى الظهر")
    daily_label = '''        <label>وقت تطبيق العشر دقائق
          <input id="dailyTime" type="time" value="19:00">
        </label>'''
    if 'id="noonTime"' not in text:
        text = replace_once(
            text,
            daily_label,
            daily_label + '''
        <label>وقت وقفة الظهر
          <input id="noonTime" type="time" value="12:30">
        </label>''',
            "noon time field",
        )
    text = text.replace(
        '"365 بطاقة يومية","توقع تقريبي لموعد الدورة"',
        '"365 بطاقة يومية","رسالة صباحية ووقفة ظهر تفاعلية","توقع تقريبي لموعد الدورة"',
    )
    path.write_text(text, encoding="utf-8")


def patch_css() -> None:
    path = APP / "calendar.css"
    text = path.read_text(encoding="utf-8")
    if ".noon-checkin{" not in text:
        text += '''

.noon-checkin{grid-column:1/-1;background:linear-gradient(135deg,#fff8fc 0%,#f9dce9 48%,#f2c7da 100%);border:1px solid #d9a7c0;box-shadow:0 16px 34px rgba(112,40,87,.12);position:relative;overflow:hidden}
.noon-checkin::after{content:"✦";position:absolute;inset-inline-end:22px;top:14px;font-size:2.2rem;color:rgba(112,40,87,.14)}
.noon-checkin h3{margin:.35rem 0 .8rem;color:#5b2148;font-size:clamp(1.25rem,2.7vw,1.65rem)}
.noon-feelings{display:flex;flex-wrap:wrap;gap:.55rem;margin:.75rem 0 1rem}
.noon-feeling{border:1px solid #b96a91;background:#fffafd;color:#5b2148;border-radius:999px;padding:.55rem .85rem;font:inherit;font-weight:800;cursor:pointer;transition:transform .16s ease,background .16s ease,color .16s ease}
.noon-feeling:hover{transform:translateY(-1px);background:#f2d2e1}
.noon-feeling[aria-pressed="true"]{background:#702857;color:#fff;border-color:#702857;box-shadow:0 0 0 3px rgba(112,40,87,.14)}
.noon-boost{font-size:1.05rem;line-height:1.9;color:#4b243e;margin:.4rem 0}
.noon-status{min-height:1.5em;margin:.45rem 0 0;color:#702857;font-weight:800;font-size:.92rem}
@media (prefers-reduced-motion:reduce){.noon-feeling{transition:none}.noon-feeling:hover{transform:none}}
'''
    path.write_text(text, encoding="utf-8")


def patch_metadata() -> None:
    sw_path = APP / "service-worker.js"
    sw = sw_path.read_text(encoding="utf-8")
    sw = sw.replace("hr-women-calendar-v1", "hr-women-calendar-v2")
    sw = sw.replace("calendar.css?v=1.0.0", "calendar.css?v=1.1.0")
    sw = sw.replace("calendar.js?v=1.0.0", "calendar.js?v=1.1.0")
    sw_path.write_text(sw, encoding="utf-8")

    manifest_path = APP / "manifest.webmanifest"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["description"] = "تقويم يومي عربي لصحة المرأة مع رسالة صباحية، وقفة ظهر تفاعلية ودفعة نفسية أنثوية، تطبيق عشر دقائق، وتتبع اختياري ومحلي للدورة."
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    editorial_path = APP / "editorial-manifest.json"
    editorial = json.loads(editorial_path.read_text(encoding="utf-8"))
    elements = editorial["yearCoverage"]["dailyRequiredElements"]
    for item in ("middayCheckIn", "feminineNoonBoost"):
        if item not in elements:
            elements.append(item)
    editorial["calendarIntegration"]["middayReminder"] = True
    editorial["calendarIntegration"]["defaultNoonTime"] = "12:30"
    editorial_path.write_text(json.dumps(editorial, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    api_path = ROOT / "api" / "women-daily-calendar-v1.json"
    api = json.loads(api_path.read_text(encoding="utf-8"))
    api.pop("integrationTrigger", None)
    api.update({
        "version": "1.1.0",
        "dailyElements": 8,
        "middayCheckIn": True,
        "feminineNoonBoost": True,
        "defaultNoonTime": "12:30",
    })
    api_path.write_text(json.dumps(api, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def patch_tests() -> None:
    path = ROOT / "tests" / "test_women_daily_calendar.py"
    text = path.read_text(encoding="utf-8")
    if 'assert "noonBoostBank" in js' not in text:
        text = replace_once(
            text,
            '    assert "morningBank" in js\n',
            '    assert "morningBank" in js\n    assert "noonBoostBank" in js\n    assert "كيف تشعرين الآن؟" in js\n    assert "UID:noon-${isoDate(date)}" in js\n    assert "noonTime" in js\n',
            "noon JavaScript tests",
        )
    text = text.replace(
        '    assert len(manifest["yearCoverage"]["dailyRequiredElements"]) == 6\n',
        '    assert len(manifest["yearCoverage"]["dailyRequiredElements"]) == 8\n    assert manifest["calendarIntegration"]["middayReminder"] is True\n    assert manifest["calendarIntegration"]["defaultNoonTime"] == "12:30"\n',
    )
    text = text.replace(
        '    assert api_report["dailyElements"] == 6\n',
        '    assert api_report["dailyElements"] == 8\n    assert api_report["middayCheckIn"] is True\n    assert api_report["feminineNoonBoost"] is True\n',
    )
    if 'assert "id=\\"noonTime\\"" in html' not in text:
        text = replace_once(
            text,
            '    assert "تقويم الهاتف" in html\n',
            '    assert "تقويم الهاتف" in html\n    assert "id=\\"noonTime\\"" in html\n    assert "كيف تشعرين الآن؟" in html\n',
            "noon HTML tests",
        )
    path.write_text(text, encoding="utf-8")


def main() -> None:
    patch_javascript()
    patch_html()
    patch_css()
    patch_metadata()
    patch_tests()
    temporary_workflow = ROOT / ".github" / "workflows" / "one-time-add-women-noon-checkin.yml"
    if temporary_workflow.exists():
        temporary_workflow.unlink()
    Path(__file__).unlink()


if __name__ == "__main__":
    main()
