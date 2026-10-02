"""Conditional outer-state Monte Carlo error from deposited synthetic states.

These SEs condition on fixed lottery caches and model/input choices. They are
not predictive intervals or uncertainty over market inputs, schedules or rules.
"""
import numpy as np
import pandas as pd

rows, contrasts = [], []
for source in ('betmgm', 'kalshi'):
    states = pd.read_csv(f'results/proj_2026_27_{source}_states.csv')
    summary = pd.read_csv(f'results/proj_2026_27_{source}.csv', index_col='team')
    assert len(states) == 4500 and states.state.nunique() == 150
    assert not states.duplicated(['team', 'state']).any()
    means = states.groupby('team').dV_new.mean()
    np.testing.assert_allclose(means, summary.loc[means.index].dV_new, atol=1e-12)
    for team, group in states.groupby('team'):
        rows.append({'source': source, 'team': team, 'states': len(group),
                     'mean_dV_new': group.dV_new.mean(),
                     'conditional_state_mcse': group.dV_new.sem()})
    pivot = states.pivot(index='state', columns='team', values='dV_new')
    for a, b in zip(summary.index[:5], summary.index[1:6]):
        difference = pivot[a]-pivot[b]
        contrasts.append({'source': source, 'team_a': a, 'team_b': b,
                          'mean_difference': difference.mean(),
                          'conditional_paired_mcse': difference.sem()})
pd.DataFrame(rows).to_csv('results/conditional_state_mcse.csv', index=False)
pd.DataFrame(contrasts).to_csv('results/conditional_rank_mcse.csv', index=False)
print('Saved conditional Monte Carlo error only; no real-world predictive intervals.')
