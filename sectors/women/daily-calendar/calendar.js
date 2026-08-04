(() => {
  "use strict";
  const loadScript = (src) => new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = src;
    script.defer = true;
    script.onload = resolve;
    script.onerror = reject;
    document.head.append(script);
  });
  loadScript("calendar-enhancements.js?v=2.0.0")
    .then(() => loadScript("calendar-core.js?v=2.0.0"))
    .catch(() => {
      const status = document.getElementById("calendarStatus");
      if (status) status.textContent = "تعذر تحميل إحدى وحدات التقويم. أعيدي فتح الصفحة أو تحققي من الاتصال.";
    });
})();
