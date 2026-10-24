#!/usr/bin/env python3
"""Prepare immutable GitHub release assets and assemble a small GitHub Pages site.

Only Python's standard library is required. This tool never uploads or publishes.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import sys
from urllib.error import HTTPError
from urllib.parse import quote, unquote, urlsplit
from urllib.request import Request, urlopen
import zipfile

RUNTIMES = {'linux-x64', 'linux-arm64', 'win-x64', 'win-arm64', 'osx-x64', 'osx-arm64'}
MAX_ASSET = 2 * 1024**3  # GitHub requires each release asset to be below 2 GiB.
MAX_EXPANDED = 16 * 1024**3
MAX_MANIFEST = 1024**2
PROTECTED = {'game-user', 'savegames', 'saves', 'work', 'launcher.json'}
ROOT = Path(__file__).resolve().parents[1]


def unique(pairs):
    obj, seen = {}, set()
    for key, value in pairs:
        if key.casefold() in seen:
            raise ValueError('Duplicate JSON key: ' + key)
        seen.add(key.casefold())
        obj[key] = value
    return obj


def parse(data):
    if len(data) > MAX_MANIFEST:
        raise ValueError('Manifest exceeds 1 MiB')
    return json.loads(data, object_pairs_hook=unique)


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def repo_name(value):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', value) or any(x in ('.', '..') for x in value.split('/')):
        raise ValueError('Use OWNER/REPOSITORY')
    return value


def tag_name(value):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,63}', value):
        raise ValueError('Tag must use 1–64 ASCII letters, numbers, dots, dashes or underscores')
    return value


def safe_path(value):
    if not isinstance(value, str) or not value or len(value) > 1024 or '\\' in value or value.startswith('/'):
        raise ValueError('Unsafe relative path')
    for part in value.split('/'):
        if not part or part in ('.', '..') or part[-1] in ' .' or any(ord(c) < 32 or c in ':*?"<>|' for c in part):
            raise ValueError('Unsafe relative path: ' + value)
        if part.casefold() in PROTECTED or re.fullmatch(r'CON|PRN|AUX|NUL|COM[0-9]|LPT[0-9]', part.split('.')[0], re.I):
            raise ValueError('Mutable/reserved path: ' + value)
    return value


def packages(manifest):
    if not isinstance(manifest, dict) or type(manifest.get('schemaVersion')) is not int or manifest['schemaVersion'] != 1:
        raise ValueError('Unsupported manifest schema')
    if set(manifest) - {'schemaVersion', 'game', 'launcher'} or not any(manifest.get(c) for c in ('game', 'launcher')):
        raise ValueError('Manifest must contain at least one component')
    for component in ('launcher', 'game'):
        if component not in manifest:
            continue
        release = manifest[component]
        if not isinstance(release, dict) or set(release) != {'version', 'platforms'}:
            raise ValueError('Invalid component')
        if not isinstance(release['version'], str) or not re.fullmatch(r'\d{1,6}\.\d{1,6}\.\d{1,6}', release['version'], re.ASCII):
            raise ValueError('Use numeric MAJOR.MINOR.PATCH component versions')
        if not isinstance(release['platforms'], dict) or not release['platforms'] or set(release['platforms']) - RUNTIMES:
            raise ValueError('Invalid platform inventory')
        for runtime, pkg in release['platforms'].items():
            if not isinstance(pkg, dict) or set(pkg) - {'url', 'sha256', 'size', 'entryPoint', 'assets'}:
                raise ValueError('Invalid package')
            if not isinstance(pkg.get('sha256'), str) or not re.fullmatch('[a-fA-F0-9]{64}', pkg['sha256']):
                raise ValueError('SHA-256 missing')
            if type(pkg.get('size')) is not int or not 0 < pkg['size'] < MAX_ASSET:
                raise ValueError('ZIP must be below GitHub’s 2 GiB asset limit')
            uri = urlsplit(pkg.get('url', ''))
            if uri.scheme != 'https' or not uri.hostname or uri.username or uri.password or uri.fragment or len(pkg['url']) > 4096:
                raise ValueError('Use public HTTPS URLs without credentials or fragments')
            safe_path(pkg.get('entryPoint'))
            if pkg.get('assets') is not None:
                if component != 'game':
                    raise ValueError('Only game packages can contain a data root')
                safe_path(pkg['assets'])
            yield component, runtime, pkg


def configured_packages(manifest):
    """Validate the website's existing launcher manifest without rewriting its URLs."""
    if not isinstance(manifest, dict) or type(manifest.get('schemaVersion')) is not int or manifest['schemaVersion'] not in (1, 2):
        raise ValueError('Configured manifest needs schema 1 or 2')
    if manifest['schemaVersion'] == 1:
        yield from packages(manifest)
        return
    if set(manifest) - {'schemaVersion', 'launcher', 'game', 'gameData'}:
        raise ValueError('Unknown configured manifest component')
    programs = {key: value for key, value in manifest.items() if key != 'gameData'}
    programs['schemaVersion'] = 1
    entries = list(packages(programs))
    if any(pkg.get('assets') is not None for _, _, pkg in entries):
        raise ValueError('Schema 2 requires a separate gameData package')
    if 'gameData' in manifest:
        data = manifest['gameData']
        if not isinstance(data, dict) or set(data) != {'version', 'url', 'sha256', 'size', 'assets', 'contentSha256'}:
            raise ValueError('Invalid gameData package')
        if data['assets'] != 'data' or not isinstance(data['contentSha256'], str) or not re.fullmatch('[a-fA-F0-9]{64}', data['contentSha256']):
            raise ValueError('gameData requires data/ and contentSha256')
        probe = {'schemaVersion': 1, 'game': {'version': data['version'], 'platforms': {'linux-x64': {
            key: data[key] for key in ('url', 'sha256', 'size')
        } | {'entryPoint': 'data'}}}}
        list(packages(probe))
        entries.append(('gameData', None, data))
    yield from entries


def release_asset(repository, package):
    """Only immutable asset URLs in this repository, including separate release tags."""
    prefix = f'https://github.com/{repo_name(repository)}/releases/download/'
    url = package['url']
    if not url.startswith(prefix):
        raise ValueError('Package must use an immutable release URL in this repository')
    parts = url[len(prefix):].split('/')
    if len(parts) != 2 or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*\.zip', parts[1]):
        raise ValueError('Invalid release ZIP URL')
    tag = tag_name(parts[0])
    if tag == 'latest':
        raise ValueError('Use a fixed release tag')
    return tag, parts[1]


def verify_configured_manifest(repository, manifest, token=None):
    releases = {}
    for _, _, package in configured_packages(manifest):
        tag, filename = release_asset(repository, package)
        if tag not in releases:
            release = json.loads(fetch(f'https://api.github.com/repos/{repository}/releases/tags/{quote(tag, safe="")}', token))
            # This mode follows explicitly selected links, including development prereleases.
            if release.get('tag_name') != tag or release.get('draft'):
                raise ValueError('Configured package requires a published release tag: ' + tag)
            assets = release.get('assets', [])
            by_name = {asset['name']: asset for asset in assets}
            if len(by_name) != len(assets):
                raise ValueError('Duplicate release asset names')
            releases[tag] = by_name
        asset = releases[tag].get(filename)
        if not asset or asset.get('state') != 'uploaded' or asset.get('browser_download_url') != package['url'] or asset.get('size') != package['size']:
            raise ValueError('Published asset missing or size mismatch: ' + filename)
        if str(asset.get('digest', '')).lower() != 'sha256:' + package['sha256'].lower():
            raise ValueError('Published asset digest missing or mismatches manifest: ' + filename)


def validate_zip(path, pkg):
    if path.is_symlink() or not path.is_file() or path.stat().st_size != pkg['size']:
        raise ValueError('Missing ZIP or size mismatch: ' + str(path))
    with path.open('rb') as source:
        digest = hashlib.file_digest(source, 'sha256').hexdigest()
    if digest.lower() != pkg['sha256'].lower():
        raise ValueError('SHA-256 mismatch: ' + str(path))
    names, size, files = set(), 0, set()
    with zipfile.ZipFile(path) as archive:
        if len(archive.infolist()) > 100000:
            raise ValueError('Too many ZIP entries')
        for item in archive.infolist():
            name = safe_path(item.filename.rstrip('/') if item.is_dir() else item.filename)
            if name.casefold() in names:
                raise ValueError('Duplicate/case-colliding ZIP path')
            names.add(name.casefold())
            mode = item.external_attr >> 16
            if stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR) or item.flag_bits & 1:
                raise ValueError('ZIP contains links, devices or encrypted files')
            size += item.file_size
            if size > MAX_EXPANDED:
                raise ValueError('Expanded ZIP exceeds updater limit')
            if not item.is_dir():
                files.add(name)
                # Stream every entry to verify CRC without loading entire archives.
                with archive.open(item) as stream:
                    while stream.read(1024**2):
                        pass
        if pkg['entryPoint'] not in files:
            raise ValueError('Entry point absent from ZIP root')
        if pkg.get('assets') and not any(x.startswith(pkg['assets'] + '/assets/missions/') for x in files):
            raise ValueError('Data root does not contain assets/missions')


def prepare(manifest_path, archives, output, repository, tag):
    repository, tag = repo_name(repository), tag_name(tag)
    manifest = parse(manifest_path.read_bytes())
    entries = list(packages(manifest))
    if output.exists():
        raise ValueError('Output exists; use a fresh directory')
    sources = []
    used = set()
    base = f'https://github.com/{repository}/releases/download/{quote(tag, safe="")}/'
    for component, runtime, pkg in entries:
        filename = unquote(PurePosixPath(urlsplit(pkg['url']).path).name)
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*\.zip', filename) or filename.casefold() in used:
            raise ValueError('ZIP filenames must be unique ASCII basenames')
        used.add(filename.casefold())
        source = archives / filename
        validate_zip(source, pkg)
        sources.append((source, filename))
        pkg['url'] = base + filename
    # Validation completes before any output is created. Remove partial output on failure.
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        output.mkdir()
        for source, filename in sources:
            shutil.copyfile(source, output / filename)
            package = next(p for _, _, p in entries if p['url'] == base + filename)
            validate_zip(output / filename, package)
        write_json(output / 'updates.json', manifest)
        sums = []
        for file in sorted(output.iterdir()):
            with file.open('rb') as stream:
                sums.append(f'{hashlib.file_digest(stream, "sha256").hexdigest()}  {file.name}')
        (output / 'SHA256SUMS.txt').write_text('\n'.join(sums) + '\n', encoding='utf-8')
        (output / 'RELEASE-NOTES.md').write_text(
            f'# Replanted {tag}\n\n'
            'Unabhängiges, nicht kommerzielles Erhaltungsprojekt. Kein offizielles EA-/Entwicklerprojekt.\n\n'
            '**Vor Veröffentlichung ausfüllen:** Änderungen, getestete Geräte/Betriebssysteme, '
            'Originaldatenvoraussetzungen, Installation, bekannte Grenzen und Saveformat-Kompatibilität.\n\n'
            f'Updatequelle: https://{repository.split("/")[0].lower()}.github.io/{repository.split("/")[1]}/updates.json\n\n'
            'Alle ZIPs und updates.json zuerst gemeinsam in einen Releaseentwurf hochladen. '
            'SHA256SUMS.txt ebenfalls anhängen; erst danach den Release veröffentlichen.\n', encoding='utf-8')
    except BaseException:
        shutil.rmtree(output)
        raise
    return manifest


def fetch(url, token=None, limit=MAX_MANIFEST):
    headers = {'User-Agent': 'Replanted-Public-Distribution/1', 'Accept': 'application/vnd.github+json' if url.startswith('https://api.github.com/') else 'application/octet-stream'}
    # Never send the API token to release/CDN hosts.
    if token and url.startswith('https://api.github.com/'):
        headers['Authorization'] = 'Bearer ' + token
    with urlopen(Request(url, headers=headers), timeout=60) as response:
        data = response.read(limit + 1)
    if len(data) > limit:
        raise ValueError('Remote metadata exceeds size limit')
    return data


def remote_manifest(repository, release, token=None):
    tag = tag_name(release['tag_name'])
    if release.get('draft') or release.get('prerelease'):
        raise ValueError('Only public, stable-channel releases can be offered')
    assets = release.get('assets', [])
    by_name = {asset['name']: asset for asset in assets}
    if len(by_name) != len(assets) or 'updates.json' not in by_name:
        raise ValueError('Release requires a unique updates.json asset')
    prefix = f'https://github.com/{repository}/releases/download/{quote(tag, safe="")}/'
    if by_name['updates.json']['browser_download_url'] != prefix + 'updates.json':
        raise ValueError('Unexpected manifest URL')
    manifest = parse(fetch(prefix + 'updates.json'))
    for _, _, pkg in packages(manifest):
        filename = PurePosixPath(urlsplit(pkg['url']).path).name
        if pkg['url'] != prefix + filename or filename not in by_name:
            raise ValueError('Package URL is not an asset in this exact release')
        asset = by_name[filename]
        if asset.get('state') != 'uploaded' or asset['size'] != pkg['size'] or asset['browser_download_url'] != pkg['url']:
            raise ValueError('Published asset metadata mismatch')
        # GitHub supplies a digest for uploaded assets. Refuse assets without it.
        if str(asset.get('digest', '')).lower() != 'sha256:' + pkg['sha256'].lower():
            raise ValueError('GitHub asset digest missing or mismatches manifest; re-upload the asset')
    return manifest, tag


def build(site, output, repository, offline=False, token=None):
    repository = repo_name(repository)
    if output.exists() or output.resolve().is_relative_to(site.resolve()) or site.resolve().is_relative_to(output.resolve()):
        raise ValueError('Use a fresh output directory separate from site sources')
    source = parse((site / 'release.json').read_bytes())
    configured = source.get('manifest') == 'launcher-updates.json'
    if configured and (source.get('repository') != repository or type(source.get('published')) is not bool):
        raise ValueError('release.json needs the matching repository and a boolean published flag')
    manifest, tag = None, None
    manifest_name = 'launcher-updates.json' if configured else 'updates.json'
    if not offline and (not configured or source['published']):
        # A 404 can mean "no releases" OR "repository inaccessible". Prove public repository access first.
        metadata = json.loads(fetch(f'https://api.github.com/repos/{repository}', token))
        if metadata.get('private') or metadata.get('full_name', '').lower() != repository.lower():
            raise ValueError('Distribution repository must be public')
        if configured:
            manifest = parse((site / manifest_name).read_bytes())
            verify_configured_manifest(repository, manifest, token)
            versions = [manifest[component]['version'] for component in ('launcher', 'game') if manifest.get(component)]
            tag = ' / '.join(versions)
        else:
            try:
                release = json.loads(fetch(f'https://api.github.com/repos/{repository}/releases/latest', token))
            except HTTPError as error:
                if error.code != 404:
                    raise
            else:
                manifest, tag = remote_manifest(repository, release, token)
    shutil.copytree(site, output)
    (output / 'updates.json').unlink(missing_ok=True)
    write_json(output / 'release.json', {'repository': repository, 'published': manifest is not None, 'tag': tag, 'manifest': manifest_name if configured or manifest else None})
    if manifest:
        write_json(output / 'updates.json', manifest)
    (output / '.nojekyll').touch()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    prep = commands.add_parser('prepare', help='Validate existing updater ZIPs and stage a release; no upload')
    prep.add_argument('--manifest', type=Path, required=True)
    prep.add_argument('--archives', type=Path, required=True)
    prep.add_argument('--output', type=Path, required=True)
    prep.add_argument('--repository', default='Naroci/BeastsAndBumpkinsReplanted')
    prep.add_argument('--tag', required=True)
    page = commands.add_parser('build', help='Assemble Pages from configured downloads or latest release; offline preview optional')
    page.add_argument('--site', type=Path, default=ROOT / 'site')
    page.add_argument('--output', type=Path, default=ROOT / 'dist')
    page.add_argument('--repository', default=os.environ.get('GITHUB_REPOSITORY', 'Naroci/BeastsAndBumpkinsReplanted'))
    page.add_argument('--offline', action='store_true')
    args = parser.parse_args()
    if args.command == 'prepare':
        prepare(args.manifest, args.archives, args.output, args.repository, args.tag)
        print(f'Validated release bundle: {args.output} (not uploaded)')
    else:
        build(args.site, args.output, args.repository, args.offline, os.environ.get('GITHUB_TOKEN'))
        print(f'Pages artifact: {args.output}')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyError, TypeError, zipfile.BadZipFile) as error:
        sys.exit(f'distribution: {error}')
