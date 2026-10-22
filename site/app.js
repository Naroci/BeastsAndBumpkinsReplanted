'use strict';
(() => {
  const i18n = globalThis.ReplantedI18n;
  const t = (key, values) => i18n.t(key, values);
  let os = navigator.platform.toLowerCase().includes('linux') ? 'linux' : navigator.platform.toLowerCase().includes('mac') ? 'osx' : 'win';
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
      const expected = `https://github.com/${release.repository}/releases/download/${encodeURIComponent(release.tag)}/`;
      if (!pkg.url.startsWith(expected) || !/^[a-f0-9]{64}$/i.test(pkg.sha256) || !Number.isSafeInteger(pkg.size) || pkg.size < 1) { meta.textContent = t('package.invalid'); continue; }
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
        if (release.manifest !== 'updates.json' || !/^[A-Za-z0-9_.-]+$/.test(release.tag)) throw new Error('Release ungültig');
        manifest = await readJSON('updates.json');
        if (manifest.schemaVersion !== 1 || (!manifest.launcher && !manifest.game)) throw new Error('Manifest ungültig');
      }
    } catch { manifest = null; loadError = true; }
    render();
  })();
  render();
})();
