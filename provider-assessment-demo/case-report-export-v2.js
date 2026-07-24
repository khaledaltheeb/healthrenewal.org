"use strict";

(() => {
  const previewId = "case-report-preview";
  const exportButtonId = "export-case-report-html";

  const safeFilename = (value) => String(value || "report")
    .trim()
    .replace(/[\\/:*?"<>|\s]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 120) || "report";

  const download = (content, filename) => {
    const blob = new Blob([content], { type: "text/html;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 0);
  };

  const exportCompleteHtml = () => {
    const form = document.getElementById("case-report-form");
    const preview = document.getElementById(previewId);
    const article = preview?.querySelector("[data-report-preview]");
    const contract = preview?.querySelector("[data-report-contract-sections]");
    if (!form || !article || !contract) {
      if (typeof toast === "function") toast("تعذر تصدير التقرير الكامل قبل اكتمال عقد التفسير.");
      return;
    }

    const caseId = form.elements.caseId?.value || "case";
    const reportId = form.elements.reportId?.value || "draft";
    const title = `تقرير ${caseId} — ${reportId}`;
    const documentHtml = `<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>${title.replaceAll("<", "&lt;").replaceAll(">", "&gt;")}</title>
<style>
  :root{font-family:Tahoma,Arial,sans-serif;color:#172526;background:#fff}body{margin:0;padding:28px;line-height:1.75}article{max-width:1050px;margin:auto}header{border-bottom:3px solid #0b6b66;margin-bottom:18px}section{margin:18px 0;break-inside:avoid}h2,h3{color:#0b5c58}table{width:100%;border-collapse:collapse}th,td{border:1px solid #aab9b8;padding:8px;text-align:right;vertical-align:top}.summary-grid,.report-contract-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.summary-grid>div,.report-contract-grid>div{border:1px solid #cbd8d7;border-radius:8px;padding:8px}.summary-grid dt,.report-contract-grid dt{font-size:.85rem;color:#4d6261}.summary-grid dd,.report-contract-grid dd{margin:3px 0 0;font-weight:700;white-space:pre-wrap}.report-disclaimer{border-right:5px solid #b88912;background:#fff8df;padding:12px;border-radius:8px}.family-facing-summary{border-right:5px solid #376fa3;background:#f4f8ff;padding:12px;border-radius:8px}.report-audit-list{padding-right:22px}@media(max-width:700px){body{padding:14px}.summary-grid,.report-contract-grid{grid-template-columns:1fr}}@media print{body{padding:0}}
</style>
</head>
<body>${article.outerHTML}</body>
</html>`;
    download(documentHtml, `${safeFilename(caseId)}-${safeFilename(reportId)}-complete.html`);
    if (typeof toast === "function") toast("تم تصدير تقرير HTML كامل يتضمن عقد التفسير وسجل المراجعة.");
  };

  document.addEventListener("click", (event) => {
    const button = event.target.closest(`#${exportButtonId}`);
    if (!button) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    const form = document.getElementById("case-report-form");
    if (!form?.reportValidity()) return;
    form.dispatchEvent(new Event("input", { bubbles: true }));
    setTimeout(exportCompleteHtml, 0);
  }, true);

  window.PA_CASE_REPORT_EXPORT_V2 = Object.freeze({
    version: "2026.07.24-report-export.2",
    includesInterpretationContract: true,
    includesFamilySummary: true,
    includesReviewAudit: true,
    networkTransfer: false
  });
})();