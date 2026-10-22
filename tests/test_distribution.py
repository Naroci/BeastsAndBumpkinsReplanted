import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
import zipfile

SPEC = importlib.util.spec_from_file_location('distribution', Path(__file__).resolve().parents[1] / 'scripts/distribution.py')
d = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(d)


class DistributionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.archive = self.root / 'launcher-linux-x64-0.2.0.zip'
        self.zip({'replanted-launcher': b'fixture executable', 'licenses/NOTICE.txt': b'fixture notice'})
        self.pkg = self.package()
        self.manifest = {'schemaVersion': 1, 'launcher': {'version': '0.2.0', 'platforms': {'linux-x64': self.pkg}}}
        self.path = self.root / 'input.json'
        self.save()

    def zip(self, contents):
        with zipfile.ZipFile(self.archive, 'w') as archive:
            for name, value in contents.items():
                archive.writestr(name, value)

    def package(self):
        return {'url': 'https://downloads.example.org/' + self.archive.name, 'sha256': hashlib.sha256(self.archive.read_bytes()).hexdigest(), 'size': self.archive.stat().st_size, 'entryPoint': 'replanted-launcher'}

    def save(self):
        d.write_json(self.path, self.manifest)

    def prepare(self):
        return d.prepare(self.path, self.root, self.root / 'bundle', 'Naroci/BeastsAndBumpkinsReplanted', 'v0.2.0')

    def test_prepare_preserves_exact_zip_bytes_and_source_manifest(self):
        before = self.path.read_bytes()
        result = self.prepare()
        self.assertEqual((self.root / 'bundle' / self.archive.name).read_bytes(), self.archive.read_bytes())
        self.assertEqual(before, self.path.read_bytes())
        self.assertEqual(result['launcher']['platforms']['linux-x64']['url'], f'https://github.com/Naroci/BeastsAndBumpkinsReplanted/releases/download/v0.2.0/{self.archive.name}')
        self.assertIn('updates.json', (self.root / 'bundle/SHA256SUMS.txt').read_text())
        with self.assertRaisesRegex(ValueError, 'Output exists'):
            self.prepare()

    def test_tampered_archive_is_rejected_without_output(self):
        self.archive.write_bytes(self.archive.read_bytes() + b'tampered')
        with self.assertRaisesRegex(ValueError, 'size mismatch'):
            self.prepare()
        self.assertFalse((self.root / 'bundle').exists())

    def test_same_size_tampering_is_rejected(self):
        self.archive.write_bytes(b'x' * self.pkg['size'])
        with self.assertRaisesRegex(ValueError, 'SHA-256 mismatch'):
            self.prepare()

    def test_zip_traversal_and_savefiles_are_rejected(self):
        for name in ['../escape', '/absolute', 'dir\\escape', 'game-user/save.bin', 'profile/launcher.json', 'dir/CON.txt']:
            with self.subTest(name=name):
                self.zip({'replanted-launcher': b'fixture', name: b'bad'})
                with self.assertRaises(ValueError):
                    d.validate_zip(self.archive, self.package())

    def test_case_collision_is_rejected(self):
        self.zip({'replanted-launcher': b'fixture', 'A': b'a', 'a': b'b'})
        with self.assertRaisesRegex(ValueError, 'colliding'):
            d.validate_zip(self.archive, self.package())

    def test_symlink_entry_is_rejected(self):
        with zipfile.ZipFile(self.archive, 'w') as archive:
            info = zipfile.ZipInfo('replanted-launcher')
            info.create_system = 3
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            archive.writestr(info, '/tmp/target')
        with self.assertRaisesRegex(ValueError, 'links'):
            d.validate_zip(self.archive, self.package())

    def test_entrypoint_must_exist_without_wrapper(self):
        self.zip({'wrapper/replanted-launcher': b'fixture'})
        with self.assertRaisesRegex(ValueError, 'Entry point'):
            d.validate_zip(self.archive, self.package())

    def test_zip_crc_is_checked(self):
        raw = self.archive.read_bytes()
        self.archive.write_bytes(raw.replace(b'fixture executable', b'broken! executable'))
        with self.assertRaises(zipfile.BadZipFile):
            d.validate_zip(self.archive, self.package())

    def test_duplicate_json_keys_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            d.parse(b'{"schemaVersion":1,"SCHEMAVERSION":1}')

    def test_versions_runtimes_urls_and_limits(self):
        for field, value in [('size', 2 * 1024**3), ('size', True), ('url', 'http://unsafe.example/x.zip'), ('url', 'https://user:password@example.org/x.zip'), ('sha256', '0')]:
            with self.subTest(field=field, value=value):
                manifest = copy.deepcopy(self.manifest)
                manifest['launcher']['platforms']['linux-x64'][field] = value
                with self.assertRaises(ValueError):
                    list(d.packages(manifest))
        for value in ['0.2', 'v0.2.0', '1.2.3-beta']:
            manifest = copy.deepcopy(self.manifest)
            manifest['launcher']['version'] = value
            with self.assertRaises(ValueError):
                list(d.packages(manifest))
        self.manifest['launcher']['platforms']['unknown'] = self.pkg
        with self.assertRaises(ValueError):
            list(d.packages(self.manifest))

    def test_all_six_platform_keys_and_game_data_root(self):
        for runtime in d.RUNTIMES:
            manifest = {'schemaVersion': 1, 'game': {'version': '1.0.0', 'platforms': {runtime: self.pkg}}}
            self.assertEqual(next(d.packages(manifest))[1], runtime)
        self.zip({'bin/bbgame': b'fixture', 'data/assets/missions/one': b'mission'})
        pkg = self.package() | {'entryPoint': 'bin/bbgame', 'assets': 'data'}
        d.validate_zip(self.archive, pkg)
        pkg['assets'] = 'wrong-root'
        with self.assertRaisesRegex(ValueError, 'Data root'):
            d.validate_zip(self.archive, pkg)

    def test_no_release_site_has_no_invalid_update_manifest(self):
        d.build(d.ROOT / 'site', self.root / 'dist', 'Naroci/BeastsAndBumpkinsReplanted', offline=True)
        status = json.loads((self.root / 'dist/release.json').read_text())
        self.assertFalse(status['published'])
        self.assertFalse((self.root / 'dist/updates.json').exists())
        self.assertTrue((self.root / 'dist/.nojekyll').exists())

    def published(self):
        manifest = self.prepare()
        prefix = 'https://github.com/Naroci/BeastsAndBumpkinsReplanted/releases/download/v0.2.0/'
        self.release = {'tag_name': 'v0.2.0', 'draft': False, 'prerelease': False, 'assets': [
            {'name': 'updates.json', 'browser_download_url': prefix + 'updates.json'},
            {'name': self.archive.name, 'browser_download_url': prefix + self.archive.name, 'size': self.pkg['size'], 'state': 'uploaded', 'digest': 'sha256:' + self.pkg['sha256']}]}
        return manifest

    def test_published_assets_match_exact_release_hash_and_size(self):
        manifest = self.published()
        with patch.object(d, 'fetch', return_value=json.dumps(manifest).encode()):
            actual, tag = d.remote_manifest('Naroci/BeastsAndBumpkinsReplanted', self.release)
        self.assertEqual(actual, manifest)
        self.assertEqual(tag, 'v0.2.0')

    def test_mismatched_or_missing_digest_blocks_publication(self):
        manifest = self.published()
        for digest in [None, 'sha256:' + '0' * 64]:
            self.release['assets'][1]['digest'] = digest
            with patch.object(d, 'fetch', return_value=json.dumps(manifest).encode()):
                with self.assertRaisesRegex(ValueError, 'digest'):
                    d.remote_manifest('Naroci/BeastsAndBumpkinsReplanted', self.release)

    def test_cross_release_url_and_incomplete_release_block_publication(self):
        manifest = self.published()
        bad = copy.deepcopy(manifest)
        bad['launcher']['platforms']['linux-x64']['url'] = self.pkg['url'].replace('downloads.example.org', 'untrusted.example.org')
        with patch.object(d, 'fetch', return_value=json.dumps(bad).encode()):
            with self.assertRaisesRegex(ValueError, 'exact release'):
                d.remote_manifest('Naroci/BeastsAndBumpkinsReplanted', self.release)
        self.release['assets'].pop()
        with patch.object(d, 'fetch', return_value=json.dumps(manifest).encode()):
            with self.assertRaises(ValueError):
                d.remote_manifest('Naroci/BeastsAndBumpkinsReplanted', self.release)

    def test_prerelease_is_not_offered(self):
        self.published()
        self.release['prerelease'] = True
        with self.assertRaisesRegex(ValueError, 'stable-channel'):
            d.remote_manifest('Naroci/BeastsAndBumpkinsReplanted', self.release)

    def test_api_failure_is_not_treated_as_no_release(self):
        with patch.object(d, 'fetch', side_effect=HTTPError('https://api.github.com', 403, 'Forbidden', {}, None)):
            with self.assertRaises(HTTPError):
                d.build(d.ROOT / 'site', self.root / 'dist', 'Naroci/BeastsAndBumpkinsReplanted')
        self.assertFalse((self.root / 'dist').exists())

    def test_404_only_means_no_release_after_public_repo_check(self):
        with patch.object(d, 'fetch', side_effect=[json.dumps({'private': False, 'full_name': 'Naroci/BeastsAndBumpkinsReplanted'}).encode(), HTTPError('https://api.github.com', 404, 'Not found', {}, None)]):
            d.build(d.ROOT / 'site', self.root / 'dist', 'Naroci/BeastsAndBumpkinsReplanted')
        self.assertFalse(json.loads((self.root / 'dist/release.json').read_text())['published'])

    def test_release_website_and_manifest_are_built_together(self):
        manifest = self.published()
        with patch.object(d, 'fetch', side_effect=[json.dumps({'private': False, 'full_name': 'Naroci/BeastsAndBumpkinsReplanted'}).encode(), json.dumps(self.release).encode(), json.dumps(manifest).encode()]):
            d.build(d.ROOT / 'site', self.root / 'dist', 'Naroci/BeastsAndBumpkinsReplanted')
        self.assertTrue(json.loads((self.root / 'dist/release.json').read_text())['published'])
        self.assertEqual(json.loads((self.root / 'dist/updates.json').read_text()), manifest)


if __name__ == '__main__':
    unittest.main()
