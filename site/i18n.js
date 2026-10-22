'use strict';
(() => {
  const messages = globalThis.ReplantedMessages;
  const supported = ['en', 'de', 'fr', 'it', 'es'];
  const storageKey = 'replanted.website.language';
  const select = document.getElementById('language');
  const listeners = [];
  let language = 'en';
  const exact = value => supported.includes(value) ? value : null;
  const browserLanguage = value => typeof value === 'string' ? exact(value.toLowerCase().split('-')[0]) : null;
  function t(key, values = {}) {
    return messages[language][key].replace(/\{(\w+)\}/g, (match, name) => Object.hasOwn(values, name) ? String(values[name]) : match);
  }
  function apply(next) {
    language = next;
    document.documentElement.lang = language;
    document.title = t('page.title');
    select.value = language;
    for (const element of document.querySelectorAll('[data-i18n]')) element.textContent = t(element.dataset.i18n);
    for (const [selector, key, attribute] of [
      ['[data-i18n-aria]', 'i18nAria', 'aria-label'],
      ['[data-i18n-alt]', 'i18nAlt', 'alt'],
      ['[data-i18n-description]', 'i18nDescription', 'content']
    ]) {
      for (const element of document.querySelectorAll(selector)) element.setAttribute(attribute, t(element.dataset[key]));
    }
    listeners.forEach(callback => callback());
  }
  let saved = null;
  try { saved = exact(localStorage.getItem(storageKey)); } catch { /* Storage may be unavailable. */ }
  const requested = exact(new URLSearchParams(location.search).get('lang'));
  const detected = (navigator.languages || [navigator.language]).map(browserLanguage).find(Boolean);
  apply(requested || saved || detected || 'en');
  select.addEventListener('change', () => {
    const next = exact(select.value);
    if (!next) return;
    apply(next);
    try { localStorage.setItem(storageKey, next); } catch { /* Selection still works for this page. */ }
    try {
      const url = new URL(location.href);
      url.searchParams.set('lang', next);
      history.replaceState(null, '', url.href);
    } catch { /* Embedded previews may restrict history updates. */ }
  });
  document.getElementById('language-picker').hidden = false;
  globalThis.ReplantedI18n = {t, get language() { return language; }, onChange(callback) { listeners.push(callback); }};
})();
