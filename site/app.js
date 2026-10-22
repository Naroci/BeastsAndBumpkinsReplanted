'use strict';
(() => {
  let os = navigator.platform.toLowerCase().includes('linux') ? 'linux' : navigator.platform.toLowerCase().includes('mac') ? 'osx' : 'win';
  let release = null;
  let manifest = null;
  let loadError = false;
  const status = document.getElementById('release-status');
  const architecture = document.getElementById('architecture');
  function render() {
    document.querySelectorAll('[data-os]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.os === os)));
    const runtime = `${os}-${architecture.value}`;
    status.textContent = loadError ? 'Release-Informationen derzeit nicht erreichbar. Bitte die GitHub-Releases direkt öffnen.' : manifest ? `Release ${release.tag} · ${runtime} · Download als ZIP` : 'Noch kein Download veröffentlicht. Neue Pakete erscheinen hier nach ihrer Freigabe.';
    for (const component of ['launcher', 'game']) {
      const link = document.getElementById(`${component}-download`);
      const meta = document.getElementById(`${component}-meta`);
      const item = manifest?.[component];
      const pkg = item?.platforms?.[runtime];
      link.removeAttribute('href');
      link.setAttribute('aria-disabled', 'true');
      meta.replaceChildren();
      if (!pkg) { meta.textContent = manifest ? 'Für diese Plattform noch nicht veröffentlicht.' : 'Noch kein Paket veröffentlicht.'; continue; }
      const expected = `https://github.com/${release.repository}/releases/download/${encodeURIComponent(release.tag)}/`;
      if (!pkg.url.startsWith(expected) || !/^[a-f0-9]{64}$/i.test(pkg.sha256) || !Number.isSafeInteger(pkg.size) || pkg.size < 1) { meta.textContent = 'Ungültige Paketinformationen. Bitte Releasehinweise prüfen.'; continue; }
      link.href = pkg.url;
      link.setAttribute('aria-disabled', 'false');
      meta.textContent = `Version ${item.version} · ${(pkg.size / 1024 / 1024).toLocaleString('de-DE', {maximumFractionDigits: 1})} MiB · ${runtime}`;
      const checksum = document.createElement('span');
      checksum.className = 'checksum';
      checksum.textContent = `SHA-256: ${pkg.sha256}`;
      meta.append(checksum);
    }
  }
  document.querySelectorAll('[data-os]').forEach(button => button.addEventListener('click', () => { os = button.dataset.os; render(); }));
  architecture.addEventListener('change', render);
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
