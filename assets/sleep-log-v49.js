(function (root) {
  'use strict';

  const STORAGE_KEY = 'pt-sleep-log-v49';
  const MAX_RECORDS = 180;
  const CHART_RECORDS = 14;
  const CHART = { width: 720, height: 300, left: 56, right: 24, top: 24, bottom: 52 };
  const SVG_PRIVACY_NOTICE = 'يتضمن ملف SVG تواريخ النوم ومدته ودرجات الجودة والطاقة. لا يتضمن الملاحظات النصية. راجع الملف قبل مشاركته؛ المشاركة اختيارية وخارج التخزين المحلي.';

  function minutes(value) {
    if (!/^\d{2}:\d{2}$/.test(value || '')) return null;
    const [h, m] = value.split(':').map(Number);
    if (h > 23 || m > 59) return null;
    return h * 60 + m;
  }

  function durationMinutes(bedtime, wakeTime) {
    const start = minutes(bedtime);
    const end = minutes(wakeTime);
    if (start === null || end === null) return null;
    const value = end >= start ? end - start : 1440 - start + end;
    return value > 0 && value <= 1440 ? value : null;
  }

  function isValidDate(value) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(value || '')) return false;
    const [year, month, day] = value.split('-').map(Number);
    const date = new Date(Date.UTC(year, month - 1, day));
    return date.getUTCFullYear() === year && date.getUTCMonth() === month - 1 && date.getUTCDate() === day;
  }

  function validate(record) {
    const errors = [];
    const fieldErrors = {};
    const addError = (field, message) => { errors.push(message); fieldErrors[field] = message; };
    if (!isValidDate(record.date)) addError('date', 'أدخل تاريخًا صحيحًا.');
    const duration = durationMinutes(record.bedtime, record.wakeTime);
    if (duration === null) {
      addError('bedtime', 'تحقق من وقت النوم.');
      addError('wakeTime', 'تحقق من وقت الاستيقاظ وأنه يختلف عن وقت النوم.');
    }
    ['quality', 'energy'].forEach((name) => {
      const raw = record[name];
      const value = Number(raw);
      if (raw === undefined || raw === null || String(raw).trim() === '' || !Number.isInteger(value) || value < 0 || value > 10) {
        addError(name, `يجب أن تكون قيمة ${name === 'quality' ? 'جودة النوم' : 'الطاقة'} عددًا صحيحًا بين 0 و10.`);
      }
    });
    if ((record.note || '').length > 500) addError('note', 'الملاحظة يجب ألا تتجاوز 500 حرف.');
    return { valid: errors.length === 0, errors, fieldErrors, duration };
  }

  function summarize(record) {
    const checked = validate(record);
    if (!checked.valid) return { errors: checked.errors };
    const hours = Math.round((checked.duration / 60) * 10) / 10;
    const flags = [];
    if (hours < 4 || hours > 12) flags.push('مدة النوم المسجلة بعيدة عن النطاق المعتاد وتستحق مراجعة الظروف أو استشارة مختص إذا تكررت.');
    if (Number(record.quality) <= 3) flags.push('جودة النوم منخفضة حسب تقييمك الشخصي؛ راقب التكرار والأثر الوظيفي بدل الحكم من ليلة واحدة.');
    if (Number(record.energy) <= 3) flags.push('الطاقة منخفضة؛ تجنب القيادة أو المهام الخطرة عند النعاس الشديد.');
    return { hours, flags, message: 'هذه خلاصة تنظيمية غير تشخيصية ولا تمثل مقياسًا سريريًا.' };
  }

  function upsert(records, record) {
    const normalized = records.filter((item) => item.date !== record.date);
    normalized.push(record);
    normalized.sort((a, b) => a.date.localeCompare(b.date));
    return normalized.slice(-MAX_RECORDS);
  }

  function safeParse(value) {
    try { const parsed = JSON.parse(value || '[]'); return Array.isArray(parsed) ? parsed : []; }
    catch (_) { return []; }
  }

  function storageRead(storage, key = STORAGE_KEY) {
    try { return { ok: true, records: safeParse(storage.getItem(key)) }; }
    catch (error) { return { ok: false, records: [], error }; }
  }

  function storageWrite(storage, records, key = STORAGE_KEY) {
    try { storage.setItem(key, JSON.stringify(records)); return { ok: true }; }
    catch (error) { return { ok: false, error }; }
  }

  function storageDelete(storage, key = STORAGE_KEY) {
    try { storage.removeItem(key); return { ok: true }; }
    catch (error) { return { ok: false, error }; }
  }

  function toCsv(records) {
    const header = ['date','bedtime','wakeTime','quality','energy','note'];
    const escape = (value) => `"${String(value ?? '').replace(/"/g, '""')}"`;
    return '\uFEFF' + [header.join(','), ...records.map((r) => header.map((k) => escape(r[k])).join(','))].join('\n');
  }

  function chartData(records) {
    return records.filter((record) => validate(record).valid).slice(-CHART_RECORDS).map((record) => ({
      date: record.date, hours: summarize(record).hours, quality: Number(record.quality), energy: Number(record.energy)
    }));
  }

  function chartDescription(points) {
    if (!points.length) return 'لا توجد بيانات كافية لعرض مخطط الاتجاهات.';
    const first = points[0];
    const last = points[points.length - 1];
    return `يعرض المخطط ${points.length} سجلًا من ${first.date} إلى ${last.date}. آخر سجل: ${last.hours} ساعة نوم، جودة ${last.quality} من 10، وطاقة ${last.energy} من 10.`;
  }

  function xmlEscape(value) {
    return String(value).replace(/[&<>"']/g, (character) => ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&apos;' }[character]));
  }

  function chartMarkup(points) {
    if (!points.length) return '<text x="50%" y="50%" text-anchor="middle">لا توجد بيانات محفوظة</text>';
    const { width, height, left, right, top, bottom } = CHART;
    const plotWidth = width - left - right;
    const plotHeight = height - top - bottom;
    const x = (index) => left + (points.length === 1 ? plotWidth / 2 : (index / (points.length - 1)) * plotWidth);
    const yHours = (value) => top + plotHeight - (Math.min(14, Math.max(0, value)) / 14) * plotHeight;
    const yScore = (value) => top + plotHeight - (Math.min(10, Math.max(0, value)) / 10) * plotHeight;
    const line = (key, yFn) => points.map((point, index) => `${index ? 'L' : 'M'} ${x(index).toFixed(1)} ${yFn(point[key]).toFixed(1)}`).join(' ');
    const ticks = [0,2,4,6,8,10,12,14].map((tick) => {
      const yy = yHours(tick).toFixed(1);
      return `<line x1="${left}" y1="${yy}" x2="${width-right}" y2="${yy}" class="grid-line"/><text x="${left-10}" y="${Number(yy)+4}" text-anchor="end">${tick}</text>`;
    }).join('');
    const labels = points.map((point, index) => `<text x="${x(index).toFixed(1)}" y="${height-22}" text-anchor="middle">${xmlEscape(point.date.slice(5))}</text>`).join('');
    return `${ticks}<line x1="${left}" y1="${top}" x2="${left}" y2="${height-bottom}" class="axis"/><line x1="${left}" y1="${height-bottom}" x2="${width-right}" y2="${height-bottom}" class="axis"/>${labels}<path d="${line('hours', yHours)}" class="series series-hours"/><path d="${line('quality', yScore)}" class="series series-quality"/><path d="${line('energy', yScore)}" class="series series-energy"/>`;
  }

  function chartSvgDocument(records) {
    const points = chartData(records);
    if (!points.length) return null;
    const description = chartDescription(points);
    const style = 'text{font:12px Tahoma,Arial,sans-serif;fill:#173f45}.axis{stroke:#173f45;stroke-width:1.5}.grid-line{stroke:#d6e7e4;stroke-width:1}.series{fill:none;stroke-width:3;stroke-linecap:round;stroke-linejoin:round}.series-hours{stroke:#006f68}.series-quality{stroke:#7c3aed;stroke-dasharray:9 5}.series-energy{stroke:#a13c62;stroke-dasharray:2 5}';
    return `<?xml version="1.0" encoding="UTF-8"?>\n<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${CHART.width} ${CHART.height}" role="img" aria-labelledby="title desc"><title id="title">مخطط اتجاهات النوم والجودة والطاقة</title><desc id="desc">${xmlEscape(description)}</desc><style>${style}</style><rect width="100%" height="100%" fill="#ffffff"/>${chartMarkup(points)}</svg>\n`;
  }

  const api = { STORAGE_KEY, MAX_RECORDS, CHART_RECORDS, SVG_PRIVACY_NOTICE, durationMinutes, isValidDate, validate, summarize, upsert, safeParse, storageRead, storageWrite, storageDelete, toCsv, chartData, chartDescription, chartSvgDocument };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  root.PTSleepLog = api;

  if (typeof document === 'undefined') return;
  const form = document.querySelector('[data-sleep-log]');
  if (!form) return;
  const status = form.querySelector('[role="status"]');
  const results = document.querySelector('[data-sleep-results]');
  const consent = form.querySelector('[name="localConsent"]');
  const chart = document.querySelector('[data-sleep-chart]');
  const chartText = document.querySelector('[data-sleep-chart-text]');
  const chartWrap = chart && chart.closest('.chart-wrap');
  if (chartWrap) {
    chartWrap.tabIndex = 0;
    chartWrap.setAttribute('role', 'region');
    chartWrap.setAttribute('aria-label', 'مخطط اتجاهات النوم القابل للتمرير أفقيًا عند الحاجة');
  }
  const printButton = document.querySelector('[data-print-sleep]');
  const exportChartButton = document.createElement('button');
  exportChartButton.type = 'button';
  exportChartButton.setAttribute('data-export-sleep-chart', '');
  exportChartButton.setAttribute('aria-describedby', 'sleep-chart-export-privacy');
  exportChartButton.textContent = 'تصدير المخطط SVG';
  printButton.insertAdjacentElement('afterend', exportChartButton);
  const exportChartPrivacy = document.createElement('p');
  exportChartPrivacy.id = 'sleep-chart-export-privacy';
  exportChartPrivacy.setAttribute('data-export-sleep-chart-privacy', '');
  exportChartPrivacy.textContent = SVG_PRIVACY_NOTICE;
  exportChartButton.insertAdjacentElement('afterend', exportChartPrivacy);

  function announce(text) { status.textContent = text; }
  function readRecords() {
    const result = storageRead(localStorage);
    if (!result.ok) announce('التخزين المحلي غير متاح في هذا المتصفح. يمكنك استخدام الأداة دون حفظ.');
    return result.records;
  }

  function clearFieldErrors() {
    form.querySelectorAll('[aria-invalid="true"]').forEach((field) => field.removeAttribute('aria-invalid'));
    form.querySelectorAll('[data-field-error]').forEach((node) => { node.textContent = ''; node.hidden = true; });
  }

  function showFieldErrors(fieldErrors) {
    clearFieldErrors();
    let firstInvalid = null;
    Object.entries(fieldErrors).forEach(([name, message]) => {
      const field = form.elements.namedItem(name);
      const error = form.querySelector(`[data-field-error="${name}"]`);
      if (!field) return;
      field.setAttribute('aria-invalid', 'true');
      if (error) { error.textContent = message; error.hidden = false; }
      if (!firstInvalid) firstInvalid = field;
    });
    if (firstInvalid && typeof firstInvalid.focus === 'function') firstInvalid.focus();
  }

  function renderChart(records) {
    const points = chartData(records);
    const description = chartDescription(points);
    chartText.textContent = description;
    chart.removeAttribute('aria-labelledby');
    chart.setAttribute('aria-label', description);
    chart.innerHTML = chartMarkup(points);
  }

  function render() {
    const records = readRecords();
    results.innerHTML = records.length ? records.slice().reverse().map((record) => {
      const summary = summarize(record);
      return `<tr><td>${record.date}</td><td>${summary.hours ?? '—'} ساعة</td><td>${record.quality}/10</td><td>${record.energy}/10</td><td>${(record.note || '').replace(/[<>&]/g, '')}</td></tr>`;
    }).join('') : '<tr><td colspan="5">لا توجد سجلات محفوظة على هذا الجهاز.</td></tr>';
    renderChart(records);
  }

  function recordFromForm() { return Object.fromEntries(new FormData(form).entries()); }
  form.addEventListener('input', (event) => {
    const field = event.target;
    if (!field.name || !field.hasAttribute('aria-invalid')) return;
    field.removeAttribute('aria-invalid');
    const error = form.querySelector(`[data-field-error="${field.name}"]`);
    if (error) { error.textContent = ''; error.hidden = true; }
  });

  form.addEventListener('submit', (event) => {
    event.preventDefault();
    const record = recordFromForm();
    const checked = validate(record);
    if (!checked.valid) { showFieldErrors(checked.fieldErrors); announce(`تعذر حساب الخلاصة. صحح ${Object.keys(checked.fieldErrors).length} حقول موضحة أدناه.`); return; }
    clearFieldErrors();
    const summary = summarize(record);
    document.querySelector('[data-sleep-summary]').textContent = `${summary.hours} ساعة. ${summary.message} ${summary.flags.join(' ')}`;
    if (!consent.checked) { announce('تم الحساب دون حفظ. فعّل خيار الحفظ المحلي لحفظ السجل.'); return; }
    const next = upsert(readRecords(), record);
    const saved = storageWrite(localStorage, next);
    if (!saved.ok) { announce('تم الحساب، لكن تعذر الحفظ المحلي. تحقق من إعدادات الخصوصية أو مساحة التخزين.'); return; }
    render();
    announce('تم حفظ السجل محليًا على هذا الجهاز بعد موافقتك.');
  });

  document.querySelector('[data-delete-sleep]').addEventListener('click', () => {
    const deleted = storageDelete(localStorage);
    if (!deleted.ok) { announce('تعذر حذف السجلات المحلية. تحقق من إعدادات الخصوصية ثم أعد المحاولة.'); return; }
    form.reset(); clearFieldErrors(); render(); announce('حُذفت جميع سجلات النوم المحلية من هذا الجهاز.');
  });
  printButton.addEventListener('click', () => window.print());
  document.querySelector('[data-export-json]').addEventListener('click', () => download('sleep-log.json', JSON.stringify(readRecords(), null, 2), 'application/json'));
  document.querySelector('[data-export-csv]').addEventListener('click', () => download('sleep-log.csv', toCsv(readRecords()), 'text/csv;charset=utf-8'));
  exportChartButton.addEventListener('click', () => {
    const svg = chartSvgDocument(readRecords());
    if (!svg) { announce('لا توجد سجلات صالحة لتصدير المخطط. احفظ سجلًا واحدًا على الأقل أولًا.'); return; }
    download('sleep-trends.svg', svg, 'image/svg+xml;charset=utf-8');
    announce('تم تجهيز مخطط الاتجاهات كملف SVG قابل للطباعة والمشاركة. راجع الملف قبل مشاركته.');
  });
  function download(name, content, type) {
    const url = URL.createObjectURL(new Blob([content], { type }));
    const link = document.createElement('a'); link.href = url; link.download = name; link.click(); URL.revokeObjectURL(url);
  }
  render();
}(typeof window !== 'undefined' ? window : globalThis));
