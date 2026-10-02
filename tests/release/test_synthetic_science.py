"""Bounded scientific invariants, using invented values and league states only."""
import tempfile
from pathlib import Path
import unittest

import numpy as np
import pandas as pd

from lottery import NEW_PROTECTED, new_lottery, old_lottery
from project_2026_27 import synthetic_schedule
from reporting import bottom_by_total
from sim import IDX, PickValues, _rank_within, evaluate, incentives
from value import value_vector


def groups(was, uta, n):
    group = np.full(30, -1, dtype=int)
    group[IDX['WAS']], group[IDX['UTA']] = was, uta
    for code, total in ((1, 3), (2, 7), (3, 4), (4, 2), (0, 14)):
        free = np.flatnonzero(group == -1)
        group[free[:total - (group == code).sum()]] = code
    return np.tile(group, (n, 1))


class SyntheticScienceTests(unittest.TestCase):
    def test_lottery_permutations_floor_and_repeatability(self):
        for engine, size in ((old_lottery, 14), (new_lottery, 16)):
            picks = engine(1024, seed=19)
            np.testing.assert_array_equal(np.sort(picks, axis=1), np.tile(np.arange(1, size+1), (1024, 1)))
            np.testing.assert_array_equal(picks, engine(1024, seed=19))
            if size == 16:
                self.assertTrue((picks[:, NEW_PROTECTED] <= 12).all())

    def test_all_25_joint_configurations_conserve_probability(self):
        n = 128
        pv = PickValues(np.r_[1., np.zeros(29)], n_lottery_sims=2048, pool_size=n,
                        ineligible_by_team={'WAS': {1}, 'UTA': {1, 2, 3, 4, 5}})
        W = np.random.default_rng(10).random((n, 30)) * 82
        for was in range(5):
            for uta in range(5):
                with self.subTest(was=was, uta=uta):
                    g = groups(was, uta, n)
                    values, picks = pv.restricted_new_values(g, W, _rank_within(g == 0, W), np.arange(n))
                    np.testing.assert_allclose(values.sum(axis=1), 1, atol=1e-12)
                    np.testing.assert_array_equal(np.sort(picks, axis=1), np.tile(np.arange(1, 31), (n, 1)))
                    self.assertTrue((picks[:, IDX['WAS']] != 1).all())
                    self.assertTrue((picks[:, IDX['UTA']] > 5).all())
                    P, _, _, _ = pv._conditional_lottery((uta, was))
                    np.testing.assert_allclose(P.sum(axis=0), np.r_[np.ones(16), np.zeros(14)], atol=1e-12)

    def test_cache_order_is_invariant(self):
        kwargs = dict(n_lottery_sims=1024, pool_size=128,
                      ineligible_by_team={'WAS': {1}, 'UTA': {1, 2, 3, 4, 5}})
        a, b = PickValues(np.arange(30., 0., -1), **kwargs), PickValues(np.arange(30., 0., -1), **kwargs)
        a._conditional_lottery((4, 1))
        b._conditional_lottery((1, 4))
        np.testing.assert_array_equal(a._conditional_lottery((1, 1))[1], b._conditional_lottery((1, 1))[1])

    def test_pair_ownership_uses_shared_restricted_draw(self):
        n = 128
        pv = PickValues(np.arange(30., 0., -1), n_lottery_sims=1024, pool_size=n,
                        ineligible_by_team={'WAS': {1}, 'UTA': {1, 2, 3, 4, 5}},
                        ownership={'BKN': ('lesser', 'HOU'), 'NOP': ('more', 'MIL', 4)})
        rng = np.random.default_rng(4)
        W, u, lot = rng.random((n, 30))*82, rng.random((n, 6)), np.arange(n)
        out = evaluate(W, np.zeros(30), u, pv, 0, lot)
        g = out['group']
        _, picks = pv.restricted_new_values(g, W, _rank_within(g == 0, W), lot)
        worse = np.maximum(picks[:, IDX['BKN']], picks[:, IDX['HOU']])
        np.testing.assert_array_equal(out['v_new'][:, IDX['BKN']], pv.V[worse-1])
        a, b = picks[:, IDX['NOP']], picks[:, IDX['MIL']]
        better, worse = np.minimum(a, b), np.maximum(a, b)
        np.testing.assert_array_equal(out['v_new'][:, IDX['NOP']], pv.V[better-1] + np.where(worse <= 4, pv.V[worse-1], 0))

    def test_small_pool_incentives_are_finite_and_repeatable(self):
        pv = PickValues(np.arange(30., 0., -1), n_lottery_sims=128, pool_size=200000,
                        ownership={'BKN': ('lesser', 'HOU')})
        self.assertEqual(pv.pool_size, 128)
        args = (np.arange(30.), np.array([IDX['BKN']]), np.array([IDX['HOU']]), np.zeros(30), 0, pv)
        a = incentives(*args, N=128, teams=['BKN'], seed=7)
        pd.testing.assert_frame_equal(a, incentives(*args, N=128, teams=['BKN'], seed=7))
        self.assertTrue(np.isfinite(a.to_numpy()).all())

    def test_synthetic_schedule_and_cohort_ties(self):
        home, away = synthetic_schedule(seed=7)
        self.assertEqual(len(home), 1230)
        self.assertTrue((home != away).all())
        np.testing.assert_array_equal(np.bincount(np.r_[home, away], minlength=30), np.full(30, 82))
        frame = pd.DataFrame({'team': ['CCC', 'BBB', 'AAA'], 'win_total': [30., 20., 20.]})
        selected = bottom_by_total(frame, n=1)
        self.assertEqual(selected.iloc[0]['team'], 'AAA')
        pd.testing.assert_frame_equal(selected, bottom_by_total(frame.iloc[::-1], n=1))

    def test_explicit_synthetic_curve_and_missing_inputs(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'invented_curve.csv'
            frame = pd.DataFrame({('ws4', 'smooth'): np.arange(30., 0., -1)}, index=np.arange(1, 31))
            frame.to_csv(path)
            np.testing.assert_array_equal(value_vector(cache_path=str(path)), np.arange(30., 0., -1))
            with self.assertRaises(ValueError):
                value_vector(n=31, cache_path=str(path))
            with self.assertRaises(FileNotFoundError):
                value_vector(cache_path=str(Path(temp) / 'absent.csv'))
        # The smoke runner uses an empty cwd; this must fail instead of finding private raw data.
        with self.assertRaises(FileNotFoundError):
            value_vector()


if __name__ == '__main__':
    unittest.main()
