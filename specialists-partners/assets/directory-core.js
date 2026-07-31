(function attachDirectoryCore(root, factory) {
  'use strict';
  const api = Object.freeze(factory());
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.PT_SPECIALIST_DIRECTORY_CORE = api;
}(typeof globalThis !== 'undefined' ? globalThis : this, function buildDirectoryCore() {
  'use strict';

  const SPECIALTY_RECOMMENDATIONS = Object.freeze({
    speech: ['speech_language', 'aac', 'audiology'],
    hearing: ['audiology', 'speech_language'],
    learning: ['learning_support', 'special_education'],
    autism: ['autism_support', 'speech_language', 'occupational_therapy', 'special_education'],
    development: ['early_intervention', 'speech_language', 'occupational_therapy'],
    behavior: ['behavior_support', 'psychology', 'family_training'],
    independence: ['occupational_therapy', 'special_education', 'family_training'],
    mental_health: ['psychology', 'psychiatry', 'social_work'],
    family: ['family_training', 'psychology', 'social_work'],
    center: ['center']
  });

  function normalizeArabic(value) {
    return String(value ?? '')
      .normalize('NFKD')
      .replace(/[\u0610-\u061A\u0640\u064B-\u065F\u0670\u06D6-\u06ED]/g, '')
      .replace(/[إأآٱ]/g, 'ا')
      .replace(/ى/g, 'ي')
      .replace(/ؤ/g, 'و')
      .replace(/ئ/g, 'ي')
      .toLowerCase()
      .trim()
      .replace(/\s+/g, ' ');
  }

  function same(left, right) {
    return normalizeArabic(left) === normalizeArabic(right);
  }

  function listIncludes(items, value) {
    return !value || (Array.isArray(items) && items.some(item => same(item, value)));
  }

  function ageMatches(items, value) {
    return !value || listIncludes(items, value) || listIncludes(items, 'جميع الأعمار');
  }

  function acceptingRequests(provider) {
    return provider?.communication?.enabled === true &&
      provider?.communication?.acceptsNewRequests !== false &&
      provider?.availability?.status !== 'unavailable';
  }

  function isPublishable(provider) {
    return Boolean(
      provider?.id &&
      provider?.publicationStatus === 'published' &&
      provider?.verification?.status === 'verified' &&
      provider?.consent?.publicProfileApproved === true
    );
  }

  function dateValue(value) {
    const parsed = Date.parse(String(value || ''));
    return Number.isFinite(parsed) ? parsed : 0;
  }

  function compareProviders(left, right) {
    const acceptingDifference = Number(acceptingRequests(right)) - Number(acceptingRequests(left));
    if (acceptingDifference) return acceptingDifference;
    const verificationDifference = dateValue(right?.verification?.lastVerifiedAt) -
      dateValue(left?.verification?.lastVerifiedAt);
    if (verificationDifference) return verificationDifference;
    return String(left?.displayName || '').localeCompare(String(right?.displayName || ''), 'ar', {
      sensitivity: 'base'
    });
  }

  function prepareProviders(records) {
    const unique = new Map();
    (Array.isArray(records) ? records : []).forEach(provider => {
      if (provider?.id) unique.set(provider.id, provider);
    });
    return [...unique.values()].filter(isPublishable).sort(compareProviders);
  }

  function searchableText(provider, labels) {
    return normalizeArabic([
      provider?.displayName,
      provider?.professionalTitle,
      provider?.centerType,
      provider?.shortBio,
      ...(provider?.specialties || []).map(item => labels?.[item] || item),
      ...(provider?.services || []),
      provider?.location?.country,
      provider?.location?.governorate,
      provider?.location?.city,
      provider?.location?.area,
      ...(provider?.serviceAreas || [])
    ].filter(Boolean).join(' '));
  }

  function providerMatches(provider, filters = {}, labels = {}) {
    const query = normalizeArabic(filters.query);
    const country = normalizeArabic(filters.country);
    const city = normalizeArabic(filters.city);
    const area = normalizeArabic(filters.area);
    const areaText = normalizeArabic([
      provider?.location?.area,
      ...(provider?.serviceAreas || [])
    ].filter(Boolean).join(' '));
    const specialties = Array.isArray(filters.specialtyAny)
      ? filters.specialtyAny.filter(Boolean)
      : [];

    return (!query || searchableText(provider, labels).includes(query)) &&
      (!filters.type || provider?.entityType === filters.type) &&
      listIncludes(provider?.specialties, filters.specialty) &&
      (!specialties.length || specialties.some(item =>
        listIncludes(provider?.specialties, item) ||
        (item === 'center' && provider?.entityType === 'center')
      )) &&
      (!country || normalizeArabic(provider?.location?.country).includes(country)) &&
      (!city || normalizeArabic(provider?.location?.city).includes(city)) &&
      (!area || areaText.includes(area)) &&
      listIncludes(provider?.serviceModes, filters.mode) &&
      ageMatches(provider?.ageGroups, filters.age) &&
      listIncludes(provider?.languages, filters.language) &&
      (!filters.verifiedOnly || provider?.verification?.status === 'verified') &&
      (!filters.acceptingOnly || acceptingRequests(provider));
  }

  function filterProviders(records, filters = {}, labels = {}) {
    return (Array.isArray(records) ? records : [])
      .filter(provider => providerMatches(provider, filters, labels))
      .sort(compareProviders);
  }

  function recommendations(need) {
    return [...(SPECIALTY_RECOMMENDATIONS[need] || ['special_education'])];
  }

  function formatUpdatedAt(value, locale = 'ar-JO') {
    if (!value) return 'غير محدد';
    const raw = String(value);
    const parsed = new Date(raw);
    if (Number.isNaN(parsed.getTime())) return String(value);
    const options = /^\d{4}-\d{2}-\d{2}$/.test(raw)
      ? {dateStyle: 'medium'}
      : {dateStyle: 'medium', timeStyle: 'short'};
    return new Intl.DateTimeFormat(locale, options).format(parsed);
  }

  return {
    normalizeArabic,
    same,
    listIncludes,
    ageMatches,
    acceptingRequests,
    isPublishable,
    compareProviders,
    prepareProviders,
    providerMatches,
    filterProviders,
    recommendations,
    formatUpdatedAt
  };
}));
