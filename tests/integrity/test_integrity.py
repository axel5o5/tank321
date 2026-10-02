"""Run with python -I -B -m unittest discover -s tests/integrity -v."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('check_integrity', ROOT / 'tools/check_integrity.py')
integrity = importlib.util.module_from_spec(spec)
spec.loader.exec_module(integrity)


class IntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'payload.txt').write_bytes(b'release\n')
        self.digest = hashlib.sha256(b'release\n').hexdigest()
        self.records = {'payload.txt': {'sha256': self.digest, 'bytes': 8,
                                      'source_sha256': self.digest,
                                      'unchanged_from_source': True}}
        self.snapshot()

    def snapshot(self):
        manifest = json.dumps({'files': self.records}).encode()
        (self.root / 'RELEASE_MANIFEST.json').write_bytes(manifest)
        (self.root / 'SHA256SUMS').write_text(
            f'{self.digest}  payload.txt\n'
            f'{hashlib.sha256(manifest).hexdigest()}  RELEASE_MANIFEST.json\n')

    def test_valid_snapshot_and_changed_provenance(self):
        self.assertEqual(integrity.check(self.root), [])
        self.records['payload.txt'].update(source_sha256='0' * 64, unchanged_from_source=False)
        self.snapshot()
        self.assertEqual(integrity.check(self.root), [])

    def test_tampered_payload(self):
        (self.root / 'payload.txt').write_bytes(b'changed')
        errors = integrity.check(self.root)
        self.assertIn('SHA256 mismatch: payload.txt', errors)
        self.assertIn('Manifest SHA256 mismatch: payload.txt', errors)
        self.assertIn('Manifest byte count mismatch: payload.txt', errors)

    def test_regenerated_snapshot_passes(self):
        payload = b'coordinator-approved new snapshot\n'
        (self.root / 'payload.txt').write_bytes(payload)
        self.digest = hashlib.sha256(payload).hexdigest()
        self.records['payload.txt'].update(sha256=self.digest, bytes=len(payload),
                                           unchanged_from_source=False)
        self.snapshot()
        self.assertEqual(integrity.check(self.root), [])

    def test_missing_and_unlisted_files(self):
        (self.root / 'payload.txt').unlink()
        (self.root / 'extra.txt').touch()
        errors = integrity.check(self.root)
        self.assertIn('Missing file: payload.txt', errors)
        self.assertIn('Unlisted file: extra.txt', errors)

    def test_local_files_are_excluded(self):
        for name in ('outputs/result.csv', '.git/config', '.venv/bin/python',
                     'venv/local', '__pycache__/module.pyc', '.pytest_cache/state',
                     '.mypy_cache/state', '.ruff_cache/state', '.env', '.env.local',
                     '.DS_Store'):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()
        self.assertEqual(integrity.check(self.root), [])

    def test_unsafe_and_excluded_paths(self):
        for name in ('../outside', '/absolute', 'a/../b', './payload.txt',
                     'a//b', 'a\\b', 'C:/file', 'outputs/file', '.env',
                     '.venv/file', 'bad\x00name'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                integrity.safe_path(self.root, name)

    def test_symlink_file_and_directory_rejected(self):
        for target in (self.root / 'payload.txt', self.root):
            link = self.root / 'link'
            link.symlink_to(target)
            with self.assertRaisesRegex(ValueError, 'Symlink'):
                integrity.check(self.root)
            link.unlink()

    def test_bad_checksum_records(self):
        path = self.root / 'SHA256SUMS'
        original = path.read_text()
        for addition in ('bad line\n', f'{self.digest}  payload.txt\n',
                         f'{self.digest}  SHA256SUMS\n', f'{self.digest}  ../escape\n'):
            path.write_text(original + addition)
            with self.subTest(addition=addition), self.assertRaises(ValueError):
                integrity.check(self.root)

    def test_manifest_inventory_and_metadata(self):
        self.records = {}
        self.snapshot()
        self.assertIn('Missing manifest record: payload.txt', integrity.check(self.root))
        self.records = {'extra.txt': {'sha256': self.digest, 'bytes': 8}}
        self.snapshot()
        self.assertIn('Missing checksum entry: extra.txt', integrity.check(self.root))

    def test_manifest_hash_bytes_and_source_consistency(self):
        self.records['payload.txt'].update(sha256='0' * 64, bytes=0)
        self.snapshot()
        errors = integrity.check(self.root)
        self.assertIn('Manifest SHA256 mismatch: payload.txt', errors)
        self.assertIn('Manifest byte count mismatch: payload.txt', errors)
        self.assertIn('Unchanged source hash mismatch: payload.txt', errors)

    def test_manifest_itself_is_hashed(self):
        path = self.root / 'RELEASE_MANIFEST.json'
        path.write_text(path.read_text() + '\n')
        self.assertIn('SHA256 mismatch: RELEASE_MANIFEST.json', integrity.check(self.root))

    def test_manifest_checksum_cannot_be_omitted(self):
        (self.root / 'SHA256SUMS').write_text(f'{self.digest}  payload.txt\n')
        self.assertIn('Missing checksum entry: RELEASE_MANIFEST.json',
                      integrity.check(self.root))

    def test_manifest_paths_are_checked(self):
        for name in ('../escape', 'outputs/file', 'SHA256SUMS', 'RELEASE_MANIFEST.json'):
            self.records = {name: {'sha256': self.digest, 'bytes': 8}}
            self.snapshot()
            with self.subTest(name=name), self.assertRaises(ValueError):
                integrity.check(self.root)

    def test_invalid_manifest_and_duplicate_keys(self):
        path = self.root / 'RELEASE_MANIFEST.json'
        for text in ('[]', '{"files": []}', '{"files": {}, "files": {}}',
                     '{"files": {"payload.txt": {"bytes": true, "sha256": "bad"}}}'):
            path.write_text(text)
            with self.subTest(text=text), self.assertRaises(ValueError):
                integrity.check(self.root)


if __name__ == '__main__':
    unittest.main()
