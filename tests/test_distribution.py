import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import stat
import shutil
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
        self.site = self.root / 'site'
        shutil.copytree(d.ROOT / 'site', self.site)
        d.write_json(self.site / 'release.json', {'repository':'Naroci/BeastsAndBumpkinsReplanted','published':False,'tag':None,'manifest':None})
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
        d.build(self.site, self.root / 'dist', 'Naroci/BeastsAndBumpkinsReplanted', offline=True)
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
                d.build(self.site, self.root / 'dist', 'Naroci/BeastsAndBumpkinsReplanted')
        self.assertFalse((self.root / 'dist').exists())

    def test_404_only_means_no_release_after_public_repo_check(self):
        with patch.object(d, 'fetch', side_effect=[json.dumps({'private': False, 'full_name': 'Naroci/BeastsAndBumpkinsReplanted'}).encode(), HTTPError('https://api.github.com', 404, 'Not found', {}, None)]):
            d.build(self.site, self.root / 'dist', 'Naroci/BeastsAndBumpkinsReplanted')
        self.assertFalse(json.loads((self.root / 'dist/release.json').read_text())['published'])

    def test_release_website_and_manifest_are_built_together(self):
        manifest = self.published()
        with patch.object(d, 'fetch', side_effect=[json.dumps({'private': False, 'full_name': 'Naroci/BeastsAndBumpkinsReplanted'}).encode(), json.dumps(self.release).encode(), json.dumps(manifest).encode()]):
            d.build(self.site, self.root / 'dist', 'Naroci/BeastsAndBumpkinsReplanted')
        self.assertTrue(json.loads((self.root / 'dist/release.json').read_text())['published'])
        self.assertEqual(json.loads((self.root / 'dist/updates.json').read_text()), manifest)

    def configured(self, enabled=True):
        self.configured_manifest = json.loads((self.site / 'launcher-updates.json').read_text())
        d.write_json(self.site / 'release.json', {'repository':'Naroci/BeastsAndBumpkinsReplanted','published':enabled,'tag':None,'manifest':'launcher-updates.json'})
        self.responses = {'https://api.github.com/repos/Naroci/BeastsAndBumpkinsReplanted': {'private':False,'full_name':'Naroci/BeastsAndBumpkinsReplanted'}}
        for _, _, package in d.configured_packages(self.configured_manifest):
            tag, filename = d.release_asset('Naroci/BeastsAndBumpkinsReplanted', package)
            url = f'https://api.github.com/repos/Naroci/BeastsAndBumpkinsReplanted/releases/tags/{tag}'
            release = self.responses.setdefault(url, {'tag_name':tag,'draft':False,'prerelease':False,'assets':[]})
            release['assets'].append({'name':filename,'browser_download_url':package['url'],'size':package['size'],'state':'uploaded','digest':'sha256:'+package['sha256']})

    def configured_fetch(self, url, token=None):
        return json.dumps(self.responses[url]).encode()

    def test_configured_schema2_uses_existing_urls_across_tags_and_keeps_source(self):
        self.configured()
        before = (self.site / 'launcher-updates.json').read_bytes()
        with patch.object(d, 'fetch', side_effect=self.configured_fetch) as fetch:
            d.build(self.site, self.root / 'dist', 'Naroci/BeastsAndBumpkinsReplanted')
        # One repository query and one per referenced tag, never ZIP downloads.
        self.assertEqual(fetch.call_count, len(self.responses))
        self.assertEqual(before, (self.site / 'launcher-updates.json').read_bytes())
        self.assertEqual(before, (self.root / 'dist/launcher-updates.json').read_bytes())
        self.assertEqual(json.loads((self.root / 'dist/updates.json').read_text()), self.configured_manifest)
        config = json.loads((self.root / 'dist/release.json').read_text())
        self.assertTrue(config['published'])
        self.assertEqual(config['manifest'], 'launcher-updates.json')
        self.assertEqual(config['tag'], ' / '.join(self.configured_manifest[c]['version'] for c in ('launcher','game')))

    def test_configured_publication_flag_disables_without_querying_latest_release(self):
        self.configured(enabled=False)
        with patch.object(d, 'fetch', side_effect=AssertionError('Unexpected network access')):
            d.build(self.site, self.root / 'dist', 'Naroci/BeastsAndBumpkinsReplanted')
        self.assertFalse(json.loads((self.root / 'dist/release.json').read_text())['published'])
        self.assertFalse((self.root / 'dist/updates.json').exists())
        self.assertTrue((self.root / 'dist/launcher-updates.json').exists())

    def test_offline_build_does_not_offer_unverified_configured_packages(self):
        self.configured()
        with patch.object(d, 'fetch', side_effect=AssertionError('Unexpected network access')):
            d.build(self.site, self.root / 'dist', 'Naroci/BeastsAndBumpkinsReplanted', offline=True)
        self.assertFalse(json.loads((self.root / 'dist/release.json').read_text())['published'])

    def test_missing_configured_zip_blocks_new_artifact(self):
        self.configured()
        next(value for value in self.responses.values() if 'assets' in value)['assets'].clear()
        with patch.object(d, 'fetch', side_effect=self.configured_fetch):
            with self.assertRaisesRegex(ValueError, 'missing or size mismatch'):
                d.build(self.site, self.root / 'dist', 'Naroci/BeastsAndBumpkinsReplanted')
        self.assertFalse((self.root / 'dist').exists())

    def test_configured_digest_mismatch_blocks_new_artifact(self):
        self.configured()
        next(value for value in self.responses.values() if 'assets' in value)['assets'][0]['digest']='sha256:'+'0'*64
        with patch.object(d, 'fetch', side_effect=self.configured_fetch):
            with self.assertRaisesRegex(ValueError, 'digest'):
                d.build(self.site, self.root / 'dist', 'Naroci/BeastsAndBumpkinsReplanted')
        self.assertFalse((self.root / 'dist').exists())

    def test_configured_draft_is_not_offered(self):
        self.configured()
        next(value for value in self.responses.values() if 'assets' in value)['draft']=True
        with patch.object(d, 'fetch', side_effect=self.configured_fetch):
            with self.assertRaisesRegex(ValueError, 'published release'):
                d.build(self.site, self.root / 'dist', 'Naroci/BeastsAndBumpkinsReplanted')

    def test_explicitly_configured_public_prerelease_is_supported(self):
        self.configured()
        next(value for value in self.responses.values() if 'assets' in value)['prerelease']=True
        with patch.object(d, 'fetch', side_effect=self.configured_fetch):
            d.build(self.site, self.root / 'dist', 'Naroci/BeastsAndBumpkinsReplanted')
        self.assertTrue(json.loads((self.root / 'dist/release.json').read_text())['published'])

    def test_schema2_data_inventory_hash_and_embedded_data_are_checked(self):
        manifest=json.loads((self.site / 'launcher-updates.json').read_text())
        manifest['gameData']['contentSha256']='bad'
        with self.assertRaisesRegex(ValueError, 'contentSha256'):
            list(d.configured_packages(manifest))
        del manifest['gameData']
        manifest['game']['platforms']['linux-x64']['assets']='data'
        with self.assertRaisesRegex(ValueError, 'separate gameData'):
            list(d.configured_packages(manifest))

    def test_configured_manifest_rejects_foreign_and_mutable_download_targets(self):
        for url in ['https://github.com/Other/Repo/releases/download/v1/a.zip','https://github.com/Naroci/BeastsAndBumpkinsReplanted/releases/latest/download/a.zip','https://github.com/Naroci/BeastsAndBumpkinsReplanted/releases/download/latest/a.zip','https://github.com/Naroci/BeastsAndBumpkinsReplanted/releases/download/v1/a.zip?token=x','https://github.com/Naroci/BeastsAndBumpkinsReplanted/releases/download/../a.zip']:
            with self.subTest(url=url), self.assertRaises(ValueError):
                d.release_asset('Naroci/BeastsAndBumpkinsReplanted', {'url':url})

    def test_configured_schema1_remains_supported(self):
        self.assertEqual(len(list(d.configured_packages(self.manifest))),1)

    def test_publication_flag_must_be_boolean(self):
        self.configured()
        config=json.loads((self.site / 'release.json').read_text());config['published']='true'
        d.write_json(self.site / 'release.json',config)
        with self.assertRaisesRegex(ValueError, 'boolean published'):
            d.build(self.site, self.root / 'dist', 'Naroci/BeastsAndBumpkinsReplanted')


if __name__ == '__main__':
    unittest.main()
