"""Integrity, manuscript arithmetic and bounded checks using deposited inputs."""
from pathlib import Path
import unittest

import numpy as np
import pandas as pd
from scipy import stats

from ownership import OWNERSHIP
from project_2026_27 import WIN_TOTALS
from replay import replay
from reporting import bottom_by_total
from sim import TEAMS, PickValues
from value import value_vector


class DepositedInputTests(unittest.TestCase):
    def test_game_keys_records_and_scores(self):
        for year in (2023, 2024, 2025):
            g = pd.read_csv(f'data/games_{year}_{str(year+1)[2:]}.csv')
            self.assertEqual(len(g), 1230)
            self.assertTrue(g.gameId.is_unique)
            self.assertFalse(g.isna().any().any())
            self.assertEqual(set(g.home) | set(g.away), set(TEAMS))
            self.assertTrue((g.home != g.away).all())
            self.assertTrue((g.scoreHome != g.scoreAway).all())
            np.testing.assert_array_equal(g.home_win, (g.scoreHome > g.scoreAway).astype(int))
            self.assertTrue(np.isfinite(g.select_dtypes('number')).all().all())
            self.assertTrue((pd.concat([g.home, g.away]).value_counts() == 82).all())
            pd.to_datetime(g.date, errors='raise')

    def test_all_curve_keys_and_finite_values(self):
        p = pd.read_csv('results/pick_values.csv', header=[0, 1], index_col=0)
        self.assertEqual(list(p.index), list(range(1, 61)))
        self.assertEqual(set(p.columns.get_level_values(0)), {'ws4', 'ws_car', 'star'})
        self.assertTrue(np.isfinite(p.to_numpy()).all())
        for curve in ('ws4', 'ws_car', 'star'):
            v = value_vector(curve, n=60, cache_path='results/pick_values.csv')
            self.assertTrue((np.diff(v) <= 0).all())
        self.assertAlmostEqual(value_vector(cache_path='results/pick_values.csv')[0], 22.342857142857145)

    def test_replay_keys_probabilities_and_arithmetic(self):
        for curve in ('ws4', 'ws_car', 'star'):
            d = pd.read_csv(f'results/replay_{curve}.csv')
            self.assertEqual(len(d), 90)
            self.assertFalse(d.duplicated(['team', 'season']).any())
            self.assertEqual(set(d.season), {'2023-24', '2024-25', '2025-26'})
            for _, group in d.groupby('season'):
                self.assertEqual(set(group.team), set(TEAMS))
            self.assertTrue(np.isfinite(d.select_dtypes('number')).all().all())
            self.assertTrue((d.pre_G+d.post_G == 82).all())
            np.testing.assert_allclose(d.post_W_expected-d.post_W_actual, d.post_shortfall, atol=1e-12)
            np.testing.assert_allclose(d.post_W_actual/d.post_G, d.post_winpct, atol=1e-12)
            for col in [c for c in d if c.startswith('P_')]:
                self.assertTrue(d[col].between(0, 1).all())

    def test_market_and_forward_state_coverage(self):
        market = pd.read_csv('data/market_win_totals_2026_27.csv', index_col='team')
        pd.testing.assert_frame_equal(market[['betmgm','kalshi']], WIN_TOTALS, check_dtype=False)
        self.assertEqual(len(market), 30)
        self.assertTrue(market.index.is_unique)
        self.assertTrue((market.betmgm_as_of == '2026-09-23').all())
        self.assertTrue((market.kalshi_as_of == '2026-07-29').all())
        for source in ('betmgm', 'kalshi'):
            s = pd.read_csv(f'results/proj_2026_27_{source}_states.csv')
            m = pd.read_csv(f'results/proj_2026_27_{source}.csv', index_col='team')
            self.assertEqual(len(s), 4500)
            self.assertEqual(set(s.state), set(range(150)))
            self.assertFalse(s.duplicated(['team', 'state']).any())
            self.assertTrue((s.groupby('state').team.nunique() == 30).all())
            self.assertEqual(set(m.index), set(TEAMS))
            self.assertTrue(np.isfinite(s.select_dtypes('number')).all().all())
            self.assertTrue(np.isfinite(m.select_dtypes('number')).all().all())
            cols = ['exp_W','P_playoff','P_rel','P_np3','P_pi910','P_pi78','dV_new','dV_old','dPlayoff']
            means = s.groupby('team')[cols].mean()
            np.testing.assert_allclose(means, m.loc[means.index, cols], atol=1e-12)
            np.testing.assert_array_equal(m.win_total, WIN_TOTALS.loc[m.index, source])
        own = pd.read_csv('results/proj_2026_27_betmgm_ownall.csv')
        self.assertEqual(len(own), 30)
        self.assertEqual(set(own.team), set(TEAMS))
        self.assertTrue((own.owns_2027_pick == 'yes').all())
        self.assertTrue(np.isfinite(own.select_dtypes('number')).all().all())

    def test_table_and_abstract_headline_arithmetic(self):
        abstract = Path('abstract.md').read_text()
        self.assertIn(Path('results/table1.md').read_text().strip(), abstract)
        b = pd.read_csv('results/proj_2026_27_betmgm.csv', index_col=0)
        k = pd.read_csv('results/proj_2026_27_kalshi.csv', index_col=0)
        table = pd.read_csv('results/table1.csv', index_col=0)
        expected = pd.concat([b[b.P_playoff < .9].sort_values('dV_new', ascending=False).head(6),
                              bottom_by_total(b).query('owns_2027_pick == "yes"').sort_values(['win_total','team'], ascending=[False,True])])
        self.assertEqual(list(table.index), list(expected.index))
        np.testing.assert_array_equal(table.dV_new, expected.dV_new)
        np.testing.assert_array_equal(table.dV_old, expected.dV_old)
        np.testing.assert_array_equal(table.dV_new_kalshi, k.loc[table.index].dV_new)
        for source in (b, k):
            self.assertEqual(list(source.head(3).index), ['IND', 'TOR', 'ORL'])
        reductions = [round(100*(1-bottom_by_total(m).dV_new.mean()/bottom_by_total(m).dV_old.mean())) for m in (b,k)]
        self.assertEqual(sorted(reductions), [89,95])
        d = pd.read_csv('results/replay_ws4.csv')
        nc = d[d.P_playoff < .1]
        self.assertEqual(len(nc), 32)
        rho, p = stats.spearmanr(nc.dV_old, nc.post_shortfall)
        self.assertEqual(f'{rho:.2f}', '0.42')
        self.assertEqual(f'{p:.3f}', '0.015')
        rx, ry, rz = (stats.rankdata(v) for v in (nc.dV_old,nc.post_shortfall,nc.W0/nc.pre_G))
        residual = lambda v: v-np.polyval(np.polyfit(rz,v,1),rz)
        pr = stats.pearsonr(residual(rx),residual(ry)).statistic
        pp = 2*stats.t.sf(abs(pr)*np.sqrt((len(nc)-3)/(1-pr**2)),len(nc)-3)
        self.assertEqual(f'{pr:.2f}', '0.32')
        self.assertEqual(f'{pp:.2f}', '0.08')
        own = d[(d.owns_pick != 'owed') & ~((d.dV_old.abs()<.001)&(d.dV_new.abs()<.001))]
        nc, bubble = own[own.P_playoff<.1], own[own.P_playoff.between(.1,.9)]
        self.assertEqual((len(nc),len(bubble)), (29,18))
        self.assertEqual(f'{nc.dV_old.mean():.2f}', '0.30')
        self.assertEqual(f'{nc.dV_new.mean():.3f}', '-0.003')
        self.assertEqual(f'{bubble.dV_old.mean():.2f}', '0.35')
        self.assertEqual(f'{bubble.dV_new.mean():.2f}', '0.53')
        self.assertEqual(round(100*(bubble.dV_new.mean()/bubble.dV_old.mean()-1)), 51)
        self.assertEqual(f'{(bubble.dV_old/bubble.dPlayoff).median():.1f}', '3.0')
        self.assertEqual(f'{(bubble.dV_new/bubble.dPlayoff).median():.1f}', '5.9')

    def test_small_cached_replay_is_finite_and_repeatable(self):
        # Reduced simulation counts for a bounded functional check, not paper estimates.
        values = value_vector('ws4', cache_path='results/pick_values.csv')
        ownership = OWNERSHIP[2026]
        key = ('ws4', 2026, tuple(values), tuple(sorted(ownership.items())))
        cache = {key: PickValues(values, ownership=ownership, n_lottery_sims=2048, pool_size=512)}
        kwargs = dict(N=128, seed=123, pv_cache=cache, value_cache='results/pick_values.csv')
        a, b = replay(2025, **kwargs), replay(2025, **kwargs)
        pd.testing.assert_frame_equal(a,b)
        self.assertEqual(set(a.index), set(TEAMS))
        self.assertTrue(np.isfinite(a.select_dtypes('number')).all().all())
        self.assertTrue((a.pre_G+a.post_G == 82).all())
