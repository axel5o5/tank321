"""Verify release bytes and inventory: python -I -B tools/check_integrity.py.

No Git or third-party packages required. Local outputs, environments and caches
are not release payload; listed entries in those locations are rejected too.
This checks consistency, not authenticity (SHA256SUMS is not signed).
"""
import hashlib
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
LOCAL_DIRS = {'.git', '.venv', 'venv', '__pycache__', '.pytest_cache',
              '.mypy_cache', '.ruff_cache'}
METADATA = {'SHA256SUMS', 'RELEASE_MANIFEST.json'}


def excluded(name):
    parts = name.split('/')
    return (parts[0] == 'outputs' or any(part in LOCAL_DIRS for part in parts)
            or any(part == '.env' or part.startswith('.env.') for part in parts)
            or parts[-1] == '.DS_Store' or parts[-1].endswith('.pyc'))


def safe_path(root, name):
    if (not isinstance(name, str) or not name or '\\' in name or ':' in name
            or any(ord(char) < 32 or ord(char) == 127 for char in name)
            or any(part in ('', '.', '..') for part in name.split('/'))
            or excluded(name)):
        raise ValueError(f'Unsafe or excluded release path: {name!r}')
    path = root
    for part in name.split('/'):
        path = path / part
        if path.is_symlink():
            raise ValueError(f'Symlink in release path: {name}')
    return path


def inventory(root):
    """Enumerate payload without following links or relying on Git ignore rules."""
    def walk_error(error):
        raise error

    names = set()
    for folder, dirs, files in os.walk(root, followlinks=False, onerror=walk_error):
        for entry in dirs[:]:
            name = (Path(folder) / entry).relative_to(root).as_posix()
            if excluded(name):
                dirs.remove(entry)
            else:
                safe_path(root, name)
        for entry in files:
            name = (Path(folder) / entry).relative_to(root).as_posix()
            if not excluded(name):
                safe_path(root, name)
                names.add(name)
    return names


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'Duplicate manifest key: {key}')
        result[key] = value
    return result


def check(root):
    """Return mismatch diagnostics; malformed/unsafe metadata raises ValueError."""
    root = Path(root).resolve()
    sums = {}
    text = safe_path(root, 'SHA256SUMS').read_text(encoding='utf-8')
    for number, line in enumerate(text.splitlines(), 1):
        match = re.fullmatch(r'([0-9a-f]{64}) [ *](.+)', line)
        if not match:
            raise ValueError(f'Malformed SHA256SUMS line {number}')
        digest, name = match.groups()
        safe_path(root, name)
        if name in sums or name == 'SHA256SUMS':
            raise ValueError(f'Duplicate or self-referencing checksum: {name}')
        sums[name] = digest
    manifest = json.loads(safe_path(root, 'RELEASE_MANIFEST.json').read_text(
        encoding='utf-8'), object_pairs_hook=unique_object)
    if not isinstance(manifest, dict) or not isinstance(manifest.get('files'), dict):
        raise ValueError('Manifest must contain a files object')
    records = manifest['files']
    for name, record in records.items():
        safe_path(root, name)
        if (name in METADATA or not isinstance(record, dict)
                or not isinstance(record.get('sha256'), str)
                or not re.fullmatch(r'[0-9a-f]{64}', record['sha256'])
                or type(record.get('bytes')) is not int or record['bytes'] < 0):
            raise ValueError(f'Invalid manifest file record: {name}')
    errors = []
    actual = inventory(root) - {'SHA256SUMS'}
    for name in sorted(actual - sums.keys()):
        errors.append(f'Unlisted file: {name}')
    for name in sorted(sums.keys() - actual):
        errors.append(f'Missing file: {name}')
    expected = set(records) | {'RELEASE_MANIFEST.json'}
    for name in sorted(expected - sums.keys()):
        errors.append(f'Missing checksum entry: {name}')
    for name in sorted(sums.keys() - expected):
        errors.append(f'Missing manifest record: {name}')
    for name in sorted(actual & sums.keys()):
        path = safe_path(root, name)
        if not path.is_file():
            raise ValueError(f'Not a regular release file: {name}')
        with path.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        if digest != sums[name]:
            errors.append(f'SHA256 mismatch: {name}')
        if name in records:
            record = records[name]
            if record['sha256'] != digest:
                errors.append(f'Manifest SHA256 mismatch: {name}')
            if record['bytes'] != path.stat().st_size:
                errors.append(f'Manifest byte count mismatch: {name}')
            # source_sha256 records provenance, not necessarily release bytes.
            if (record.get('unchanged_from_source') is True
                    and record.get('source_sha256') != record['sha256']):
                errors.append(f'Unchanged source hash mismatch: {name}')
    return errors


def main():
    try:
        errors = check(ROOT)
    except (OSError, ValueError) as exc:
        errors = [str(exc)]
    if errors:
        print('Release integrity FAILED:\n' + '\n'.join(errors), file=sys.stderr)
        return 1
    print('Release integrity OK: SHA256SUMS, manifest and payload inventory agree.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
