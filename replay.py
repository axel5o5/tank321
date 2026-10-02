"""Replay a season from its All-Star break under the old and the 3-2-1 lottery.

For seasons 2023-24, 2024-25 and 2025-26 (all played under the old lottery) we measure each team's
incentive to lose at the break, adjusted for pick ownership, and compare it with how the team actually
did after the break relative to a projection from its pre-break results. The same break states are then
re-scored under the 3-2-1 rules.

usage: python3 replay.py --value-cache results/pick_values.csv --output-dir outputs
       (all three seasons, three value curves; expensive)
Without --value-cache, raw source data (not deposited here) is required.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from ownership import OWNERSHIP
from sim import IDX, TEAMS, PickValues, fit_ratings, incentives
from value import value_vector

SEASONS = [2023, 2024, 2025]  # season start years


def break_dates(g: pd.DataFrame):
    d = pd.Series(sorted(g.date.unique()))
    gap = d.diff().dt.days
    i = gap.idxmax()
    return d[i - 1], d[i]


def wins(games, t):
    return int(((games.home == t) & (games.home_win == 1)).sum() + ((games.away == t) & (games.home_win == 0)).sum())


def replay(y: int, window="ws4", N=40_000, C=1.0, seed=0, pv_cache=None, *, value_cache=None):
    g = pd.read_csv(f"data/games_{y}_{str(y + 1)[2:]}.csv", parse_dates=["date"])
    last, resume = break_dates(g)
    pre, post = g[g.date <= last], g[g.date >= resume]
    r, h = fit_ratings(pre, C=C)
    W0 = np.array([wins(pre, t) for t in TEAMS], float)
    if pv_cache is None:
        pv_cache = {}
    values = value_vector(window, cache_path=value_cache)
    ownership = OWNERSHIP.get(y + 1, {})
    key = (window, y + 1, tuple(values), tuple(sorted(ownership.items())))
    if key not in pv_cache:
        pv_cache[key] = PickValues(values, ownership=ownership)
    pv = pv_cache[key]
    home, away = post.home.map(IDX).to_numpy(), post.away.map(IDX).to_numpy()
    df = incentives(W0, home, away, r, h, pv, N=N, seed=seed)
    df["season"] = f"{y}-{str(y + 1)[2:]}"
    df["pre_G"] = [((pre.home == t) | (pre.away == t)).sum() for t in df.index]
    df["post_G"] = [((post.home == t) | (post.away == t)).sum() for t in df.index]
    df["post_W_actual"] = [wins(post, t) for t in df.index]
    df["post_W_expected"] = df.exp_W - df.W0
    df["post_shortfall"] = df.post_W_expected - df.post_W_actual  # wins below projection
    df["post_winpct"] = df.post_W_actual / df.post_G
    df["owns_pick"] = [OWNERSHIP.get(y + 1, {}).get(t, ("own",))[0] for t in df.index]
    return df


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("windows", nargs="*", metavar="{ws4,ws_car,star}")
    parser.add_argument("--value-cache", help="Explicit deposited pick-value CSV; otherwise rebuild from raw inputs")
    parser.add_argument("--output-dir", type=Path, default=Path("outputs"))
    args = parser.parse_args()
    if any(w not in ("ws4", "ws_car", "star") for w in args.windows):
        parser.error("windows must be ws4, ws_car or star")
    pd.set_option("display.width", 220)
    windows = args.windows or ["ws4", "ws_car", "star"]
    for w in windows:
        value_vector(w, cache_path=args.value_cache)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for w in windows:
        frames = []
        for y in SEASONS:
            df = replay(y, window=w, value_cache=args.value_cache)
            frames.append(df)
        allr = pd.concat(frames)
        allr.to_csv(args.output_dir / f"replay_{w}.csv")
        print(f"\n=== {w}")
        cols = ["season", "W0", "pre_G", "P_playoff", "P_rel", "dV_old", "dV_new", "dPlayoff", "post_winpct",
                "post_shortfall", "owns_pick"]
        print(allr[allr.P_playoff < 0.9].sort_values(["season", "dV_old"], ascending=[True, False])[cols]
              .round(3).to_string())
