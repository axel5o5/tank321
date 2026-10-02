"""Output isolation and deposited-input CLI contracts; no full simulations."""
import contextlib
import hashlib
import io
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

import reproduce
import value

ROOT = reproduce.ROOT


def reference_hashes():
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (ROOT / 'results').rglob('*') if p.is_file()}


class ReproductionTests(unittest.TestCase):
    def setUp(self):
        self.before = reference_hashes()
        self.temp = tempfile.TemporaryDirectory(dir=ROOT, prefix='.test-reproduction-')
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name) / 'generated'

    def tearDown(self):
        self.assertEqual(self.before, reference_hashes())

    def test_default_wrapper_contract(self):
        with patch.object(reproduce, 'ROOT', Path(self.temp.name)), \
                patch.object(reproduce, 'run_script') as run, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(reproduce.main([]), 0)
        self.assertEqual([c.args[0] for c in run.call_args_list], list(reproduce.ARTIFACTS))
        for call in run.call_args_list:
            options = call.args[1]
            self.assertEqual(options[options.index('--input-dir') + 1], ROOT / 'results')
            self.assertEqual(options[options.index('--output-dir') + 1], Path(self.temp.name) / 'outputs')
        self.assertIn(ROOT / 'results/pick_values.csv', run.call_args_list[0].args[1])

    def test_full_uses_generated_inputs_and_explicit_curve(self):
        with patch.object(reproduce, 'run_script') as run, contextlib.redirect_stdout(io.StringIO()):
            reproduce.main(['--full', '--output-dir', str(self.output)])
        self.assertEqual([c.args[0] for c in run.call_args_list],
                         ['replay.py', 'project_2026_27.py', *reproduce.ARTIFACTS])
        for call in run.call_args_list[:2]:
            self.assertEqual(call.args[1], ['--value-cache', ROOT / 'results/pick_values.csv',
                                            '--output-dir', self.output])
        for call in run.call_args_list[2:]:
            self.assertEqual(call.args[1][:4], ['--input-dir', self.output, '--output-dir', self.output])

    def test_artifacts_generate_without_changing_references(self):
        cwd, argv = Path.cwd(), sys.argv
        with contextlib.redirect_stdout(io.StringIO()):
            reproduce.main(['--output-dir', str(self.output)])
        self.assertEqual(Path.cwd(), cwd)
        self.assertIs(sys.argv, argv)
        for name in ('headline_numbers.txt', 'table1.csv', 'table1.md',
                     'conditional_state_mcse.csv', 'conditional_rank_mcse.csv'):
            self.assertEqual((self.output / name).read_bytes(), (ROOT / 'results' / name).read_bytes())
        for name in ('figure1.png', 'figure1.svg'):
            self.assertGreater((self.output / name).stat().st_size, 1000)

    def test_artifact_cli_reads_selected_input_directory(self):
        inputs = Path(self.temp.name) / 'inputs'
        inputs.mkdir()
        for source in ('betmgm', 'kalshi'):
            name = f'proj_2026_27_{source}.csv'
            shutil.copyfile(ROOT / 'results' / name, inputs / name)
        import pandas as pd
        path = inputs / 'proj_2026_27_betmgm.csv'
        table = pd.read_csv(path, index_col=0)
        table['dV_new'] += 1
        table.to_csv(path)
        with contextlib.redirect_stdout(io.StringIO()):
            reproduce.run_script('table1.py', ['--input-dir', inputs, '--output-dir', self.output])
        generated = pd.read_csv(self.output / 'table1.csv', index_col=0)
        self.assertTrue((generated.dV_new > 0.9).all())

    def test_model_cli_output_plumbing_preserves_simulation_defaults(self):
        import numpy as np
        import pandas as pd
        sample = pd.read_csv(ROOT / 'results/proj_2026_27_betmgm_states.csv', index_col=0).iloc[:30]
        for script, count, draws in (('replay.py', 9, 40_000), ('project_2026_27.py', 400, 4000)):
            with self.subTest(script=script), patch('sim.PickValues'), \
                    patch('sim.fit_ratings', return_value=(np.zeros(30), 0.222)), \
                    patch('sim.incentives', side_effect=lambda *a, **kw: sample.copy()) as simulate, \
                    contextlib.redirect_stdout(io.StringIO()):
                reproduce.run_script(script, ['--value-cache', ROOT / 'results/pick_values.csv',
                                               '--output-dir', self.output])
                self.assertEqual(simulate.call_count, count)
                self.assertEqual({call.kwargs['N'] for call in simulate.call_args_list}, {draws})
        self.assertEqual({p.name for p in self.output.iterdir()}, set(reproduce.MODEL_INPUTS))

    def test_rejects_reference_overlap_and_links(self):
        for path in (ROOT, ROOT / 'results', ROOT / 'results/nested'):
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, 'published results'):
                reproduce.safe_output_dir(path)
        alias = Path(self.temp.name) / 'alias'
        alias.symlink_to(ROOT / 'results', target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'published results'):
            reproduce.safe_output_dir(alias)
        self.output.mkdir()
        link = self.output / 'table1.csv'
        link.symlink_to(ROOT / 'results/table1.csv')
        with self.assertRaisesRegex(ValueError, 'links'):
            reproduce.safe_output_dir(self.output)
        link.unlink()
        os.link(ROOT / 'results/table1.csv', link)
        with self.assertRaisesRegex(ValueError, 'links'):
            reproduce.safe_output_dir(self.output)

    def test_helpful_missing_curve_and_raw_errors(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr), self.assertRaises(SystemExit) as exc:
            reproduce.main(['--value-cache', str(self.output / 'missing.csv')])
        self.assertEqual(exc.exception.code, 2)
        self.assertIn('Deposited pick-value CSV missing', stderr.getvalue())
        self.assertFalse(self.output.exists())
        with patch.object(value, 'RAW', str(self.output)), \
                self.assertRaisesRegex(FileNotFoundError, '--value-cache results/pick_values.csv'):
            value.value_vector()

    def test_missing_deposited_inputs_fail_before_generation(self):
        stderr = io.StringIO()
        with patch.object(reproduce, 'RESULTS', Path(self.temp.name) / 'missing-results'), \
                patch.object(reproduce, 'run_script') as run, \
                contextlib.redirect_stderr(stderr), self.assertRaises(SystemExit) as exc:
            reproduce.main(['--value-cache', str(ROOT / 'results/pick_values.csv'),
                            '--output-dir', str(self.output)])
        self.assertEqual(exc.exception.code, 2)
        self.assertIn('Deposited inputs missing', stderr.getvalue())
        run.assert_not_called()
        self.assertFalse(self.output.exists())

    def test_script_cli_help(self):
        for script in ('replay.py', 'project_2026_27.py', *reproduce.ARTIFACTS):
            stdout = io.StringIO()
            with self.subTest(script=script), contextlib.redirect_stdout(stdout), \
                    self.assertRaises(SystemExit) as exc:
                reproduce.run_script(script, ['--help'])
            self.assertEqual(exc.exception.code, 0)
            self.assertIn('--output-dir', stdout.getvalue())
            if script in reproduce.ARTIFACTS:
                self.assertIn('--input-dir', stdout.getvalue())
