"""Offline deposited-input checks; run with python -I -B run_checks.py."""
import argparse
import importlib
import importlib.metadata
import json
import os
from pathlib import Path
import runpy
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifacts', action='store_true', help='Also regenerate headline, table and figure')
    args = parser.parse_args()
    if not sys.flags.isolated or not sys.dont_write_bytecode:
        parser.error('Use python -I -B run_checks.py')
    sys.path.insert(0, str(ROOT))
    os.chdir(ROOT)
    def offline(event, args):
        if event in ('socket.connect', 'socket.getaddrinfo', 'socket.bind'):
            raise RuntimeError('Network access is disabled for these checks')
    sys.addaudithook(offline)
    with tempfile.TemporaryDirectory(prefix='tank-checks-') as temp:
        os.environ['MPLCONFIGDIR'] = temp
        origins = {}
        for name in ('lottery', 'sim', 'ownership', 'value', 'replay', 'project_2026_27', 'reporting'):
            module = importlib.import_module(name)
            path = Path(module.__file__).resolve()
            if not path.is_relative_to(ROOT):
                raise RuntimeError(f'Project import escaped candidate: {name}')
            origins[name] = str(path.relative_to(ROOT))
        suite = unittest.TestSuite()
        for folder in ('tests/release', 'tests/deposited'):
            suite.addTests(unittest.TestLoader().discover(str(ROOT / folder), pattern='test_*.py'))
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        if not result.wasSuccessful():
            return 1
        if args.artifacts:
            for script, argv in [('headline.py', ['--value-cache', 'results/pick_values.csv']),
                                 ('table1.py', []), ('figure1.py', [])]:
                sys.argv = [script] + argv
                runpy.run_path(str(ROOT / script), run_name='__main__')
        print(json.dumps({'scope': 'deposited-input checks and bounded replay smoke',
                          'isolated': True, 'network': 'disabled', 'tests': result.testsRun,
                          'module_origins': origins,
                          'python': sys.version.split()[0],
                          'packages': {name: importlib.metadata.version(name) for name in
                                       ('numpy', 'pandas', 'scipy', 'scikit-learn', 'matplotlib')},
                          'full_simulations_rerun': False, 'raw_reconstruction': False}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
