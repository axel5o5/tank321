"""2026-27 prospective projection under the 3-2-1 lottery (not yet a public preregistration).

Team strength comes from BetMGM regular-season win totals (Sept 23, 2026; Kalshi projected wins as a
robustness check). We build a synthetic 82-game NBA schedule, convert win totals into ratings, add
talent uncertainty, simulate to the All-Star break (about two-thirds of games), and at each simulated
break measure every team's marginal incentive to lose under the 3-2-1 lottery and, as a counterfactual,
under the old lottery. Pick ownership follows reported 2027 obligations.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ownership import OWNERSHIP, label
from sim import CONF, DIVISIONS, IDX, TEAMS, PickValues, incentives, sigmoid
from value import value_vector

# Win totals: BetMGM 9/23/2026 (sports.betmgm.com blog) and Kalshi projected wins (via SBR, July 29).
WIN_TOTALS = pd.DataFrame({
    "team": ["ATL", "BOS", "BKN", "CHA", "CHI", "CLE", "DAL", "DEN", "DET", "GSW", "HOU", "IND", "LAC", "LAL", "MEM",
             "MIA", "MIL", "MIN", "NOP", "NYK", "OKC", "ORL", "PHI", "PHX", "POR", "SAC", "SAS", "TOR", "UTA", "WAS"],
    "betmgm": [43.5, 51.5, 24.5, 39.5, 29.5, 47.5, 34.5, 49.5, 49.5, 40.5, 47.5, 44.5, 30.5, 46.5, 29.5,
               46.5, 25.5, 48.5, 27.5, 52.5, 62.5, 43.5, 50.5, 40.5, 42.5, 21.5, 59.5, 45.5, 37.5, 34.5],
    "kalshi": [45.0, 51.0, 26.2, 38.6, 29.5, 47.1, 37.5, 48.9, 51.1, 38.9, 46.8, 44.7, 29.7, 47.4, 30.0,
               46.4, 27.8, 50.0, 28.4, 51.3, 58.9, 45.3, 51.1, 40.3, 40.8, 23.7, 60.8, 44.8, 39.6, 29.6],
}).set_index("team")

OWNERSHIP_2027 = OWNERSHIP[2027]
INELIGIBLE_2027 = {"WAS": {1}, "UTA": {1, 2, 3, 4, 5}}  # no No. 1 twice running; no top 5 three years running


def synthetic_schedule(seed: int = 0) -> tuple[np.ndarray, np.ndarray]:
    """82-game NBA-format schedule: 2 vs each other-conference team, 4 vs division rivals,
    4 vs six and 3 vs four other same-conference teams."""
    rng = np.random.default_rng(seed)
    games = []
    div_of = {t: d for d, ts in enumerate(DIVISIONS) for t in ts}
    for i, a in enumerate(TEAMS):
        for b in TEAMS[i + 1:]:
            ia, ib = IDX[a], IDX[b]
            if CONF[ia] != CONF[ib]:
                n = 2
            elif div_of[a] == div_of[b]:
                n = 4
            else:
                da, db = DIVISIONS[div_of[a]], DIVISIONS[div_of[b]]
                pa, pb = da.index(a), db.index(b)
                # cyclic rule: 3 games when pb in {pa, pa+1} (mod 5) for the ordered division pair
                first, second = (pa, pb) if div_of[a] < div_of[b] else (pb, pa)
                n = 3 if (second - first) % 5 in (0, 1) else 4
            for k in range(n):
                games.append((ia, ib) if k % 2 == 0 else (ib, ia))
    g = np.array(games)
    g = g[rng.permutation(len(g))]
    # order games in rounds where no team plays twice, so every team reaches the break with a
    # similar number of games played (as in a real schedule)
    remaining = list(range(len(g)))
    order = []
    while remaining:
        used, keep = set(), []
        for j in remaining:
            a, b = g[j]
            if a in used or b in used:
                keep.append(j)
            else:
                used.update((a, b))
                order.append(j)
        remaining = keep
    g = g[order]
    return g[:, 0], g[:, 1]


def ratings_from_totals(totals: np.ndarray, home: np.ndarray, away: np.ndarray, h: float) -> np.ndarray:
    target = totals * 1230.0 / totals.sum()
    r = np.zeros(30)
    for _ in range(500):
        p = sigmoid(r[home] - r[away] + h)
        ew = np.bincount(home, p, 30) + np.bincount(away, 1 - p, 30)
        r += 0.5 * (np.log(target / (82 - target)) - np.log(ew / (82 - ew)))
        r -= r.mean()
    return r


def project(source="betmgm", window="ws4", K=150, N=4000, sigma=0.25, h=0.222, frac=2 / 3,
            ownership=OWNERSHIP_2027, seed=7, value_cache=None, progress=False):
    rng = np.random.default_rng(seed)
    home, away = synthetic_schedule(seed)
    totals = WIN_TOTALS.loc[TEAMS, source].to_numpy()
    r_hat = ratings_from_totals(totals, home, away, h)
    V = value_vector(window, cache_path=value_cache)
    pv = PickValues(V, ineligible_by_team=INELIGIBLE_2027, ownership=ownership or {})
    cut = int(round(frac * len(home)))
    frames = []
    for k in range(K):
        r = r_hat + rng.normal(0, sigma, 30)
        p = sigmoid(r[home[:cut]] - r[away[:cut]] + h)
        res = rng.random(cut) < p
        W0 = np.bincount(home[:cut], res, 30) + np.bincount(away[:cut], ~res, 30)
        df = incentives(W0.astype(float), home[cut:], away[cut:], r, h, pv, N=N, seed=seed * 1000 + k)
        df["state"] = k
        frames.append(df)
        if progress and ((k + 1) % 10 == 0 or k + 1 == K):
            print(f"{source}: {k+1}/{K} states complete; {len(pv.conditional_cache)} joint lottery configurations", flush=True)
    allstates = pd.concat(frames)
    summ = allstates.groupby(level=0).agg(
        exp_W=("exp_W", "mean"), P_playoff=("P_playoff", "mean"), P_rel=("P_rel", "mean"),
        P_np3=("P_np3", "mean"), P_pi910=("P_pi910", "mean"), P_pi78=("P_pi78", "mean"),
        dV_new=("dV_new", "mean"), dV_old=("dV_old", "mean"), dPlayoff=("dPlayoff", "mean"))
    summ["win_total"] = WIN_TOTALS.loc[summ.index, source]
    summ["owns_2027_pick"] = [label((ownership or {}).get(t)) for t in summ.index]
    return summ.sort_values("dV_new", ascending=False), allstates


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--value-cache", help="Explicit archived pick-value CSV; otherwise rebuild from raw data")
    args = parser.parse_args()
    pd.set_option("display.width", 200)
    for src in ["betmgm", "kalshi"]:
        summ, allst = project(source=src, value_cache=args.value_cache, progress=True)
        summ.to_csv(f"results/proj_2026_27_{src}.csv")
        allst.to_csv(f"results/proj_2026_27_{src}_states.csv")
        print(f"\n=== 2026-27 projection, {src} win totals (incentive at a simulated All-Star break)")
        print(summ.round(3).to_string())
    # rule effect only: every team owns its pick
    summ, _ = project(source="betmgm", ownership={}, K=100, value_cache=args.value_cache, progress=True)
    summ.to_csv("results/proj_2026_27_betmgm_ownall.csv")
    print("\n=== same, every team owning its own pick")
    print(summ.round(3).to_string())
