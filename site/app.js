'use strict';
(() => {
  const i18n = globalThis.ReplantedI18n;
  const t = (key, values) => i18n.t(key, values);
  let os = navigator.platform.toLowerCase().includes('linux') ? 'linux' : navigator.platform.toLowerCase().includes('mac') ? 'osx' : 'win';
  const systems = Array.from(document.querySelectorAll('[data-os]'), button => button.dataset.os);
  if (!systems.includes(os)) os = systems.includes('win') ? 'win' : systems[0];
  let release = null;
  let manifest = null;
  let loadError = false;
  const status = document.getElementById('release-status');
  const architecture = document.getElementById('architecture');
  function render() {
    document.querySelectorAll('[data-os]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.os === os)));
    const runtime = `${os}-${architecture.value}`;
    status.textContent = loadError ? t('status.error') : manifest ? t('status.ready', {tag: release.tag, runtime}) : t('status.empty');
    for (const component of ['launcher', 'game']) {
      const link = document.getElementById(`${component}-download`);
      const meta = document.getElementById(`${component}-meta`);
      const item = manifest?.[component];
      const pkg = item?.platforms?.[runtime];
      link.removeAttribute('href');
      link.setAttribute('aria-disabled', 'true');
      meta.replaceChildren();
      if (!pkg) { meta.textContent = manifest ? t('package.missing') : t('package.empty'); continue; }
      const base = `https://github.com/${release.repository}/releases/download/`;
      const suffix = typeof pkg.url === 'string' ? pkg.url.slice(base.length) : '';
      const fixedAsset = typeof pkg.url === 'string' && pkg.url.startsWith(base) && /^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}\/[A-Za-z0-9][A-Za-z0-9_.-]*\.zip$/.test(suffix) && !suffix.startsWith('latest/');
      const correctTag = fixedAsset && (['launcher-updates.json', 'launcher-downloads.json', 'downloads.json'].includes(release.manifest) || pkg.url.startsWith(base + encodeURIComponent(release.tag) + '/'));
      if (!fixedAsset || !correctTag || !/^[a-f0-9]{64}$/i.test(pkg.sha256) || !Number.isSafeInteger(pkg.size) || pkg.size < 1) { meta.textContent = t('package.invalid'); continue; }
      link.href = pkg.url;
      link.setAttribute('aria-disabled', 'false');
      meta.textContent = t('package.meta', {version: item.version, size: (pkg.size / 1024 / 1024).toLocaleString(i18n.language, {maximumFractionDigits: 1}), runtime});
      const checksum = document.createElement('span');
      checksum.className = 'checksum';
      checksum.textContent = `SHA-256: ${pkg.sha256}`;
      meta.append(checksum);
    }
  }
  document.querySelectorAll('[data-os]').forEach(button => button.addEventListener('click', () => { os = button.dataset.os; render(); }));
  architecture.addEventListener('change', render);
  i18n.onChange(render);
  async function readJSON(path) {
    const response = await fetch(path, {cache: 'no-cache'});
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  }
  (async () => {
    try {
      release = await readJSON('release.json');
      if (!/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(release.repository)) throw new Error('Repository fehlt');
      document.getElementById('all-releases').href = `https://github.com/${release.repository}/releases`;
      document.getElementById('repository-link').href = `https://github.com/${release.repository}`;
      if (release.published) {
        if (!['updates.json', 'launcher-updates.json', 'launcher-downloads.json', 'downloads.json'].includes(release.manifest) || typeof release.tag !== 'string') throw new Error('Release ungültig');
        if (release.manifest === 'updates.json' && !/^[A-Za-z0-9_.-]+$/.test(release.tag)) throw new Error('Release ungültig');
        manifest = await readJSON(release.manifest);
        if (![1, 2].includes(manifest.schemaVersion) || (!manifest.launcher && !manifest.game)) throw new Error('Manifest ungültig');
      }
    } catch { manifest = null; loadError = true; }
    render();
  })();
  render();
})();
