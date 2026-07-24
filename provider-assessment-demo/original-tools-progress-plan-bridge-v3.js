"use strict";

(() => {
  const STORE_VERSION = "3";
  const read = (key, fallback = null) => {
    try { const raw = localStorage.getItem(key); return raw === null ? fallback : JSON.parse(raw); }
    catch (_) { return fallback; }
  };
  const activeIdentity = () => {
    const identities = read(`pa-demo-identities-v${STORE_VERSION}`, {});
    const active = read(`pa-demo-active-v${STORE_VERSION}`, null);
    if (active?.role === "provider" && identities?.[active.username]) return identities[active.username];
    return identities?.__visitor__ || null;
  };
  const activeStore = () => {
    const identity = activeIdentity();
    if (!identity?.uid) return null;
    const store = read(`pa-demo-store-v${STORE_VERSION}:${identity.uid}`, null);
    return store?.uid === identity.uid ? store : null;
  };
  const persistStore = (store) => {
    const identity = activeIdentity();
    if (!identity?.uid || !store || store.uid !== identity.uid) throw new Error("uid_store_mismatch");
    localStorage.setItem(`pa-demo-store-v${STORE_VERSION}:${identity.uid}`, JSON.stringify(store));
    return store;
  };
  const findCase = (caseId) => activeStore()?.cases?.find((item) => item.caseId === caseId) || null;
  const progress = window.PA_ORIGINAL_PROGRESS;
  if (!progress?.buildSeries) return;
  progress.activeIdentity = activeIdentity;
  progress.activeStore = activeStore;
  progress.persistStore = persistStore;
  progress.findCase = findCase;
  progress.buildSeriesByCaseId = (caseId) => {
    const record = findCase(caseId);
    return record ? progress.buildSeries(record) : [];
  };
  progress.goalPlanBridge = "pa-original-progress-plan-bridge-v3";
})();