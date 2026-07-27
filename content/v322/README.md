# حزمة توسعة أدلة ذوي الاحتياجات الخاصة — v322

يحتوي الملف `special-needs-condition-expansion-ar.json.gz` على مصدر JSON عربي مضغوط
لخمس صفحات مرجعية موسعة. استُخدم الضغط لتقليل حجم الحزمة مع إبقاء المصدر قابلاً
للاستخراج والتحقق بأدوات بايثون القياسية فقط.

للقراءة دون تعديل:

```bash
python - <<'PY'
import gzip
from pathlib import Path
print(gzip.decompress(Path('content/v322/special-needs-condition-expansion-ar.json.gz').read_bytes()).decode('utf-8'))
PY
```

حالة المحتوى: مراجعة تحريرية ومنهجية داخلية؛ المراجعة الخارجية المتخصصة موصى بها ولم تكتمل.
آخر مراجعة مسجلة: 2026-07-27.
