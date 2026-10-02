"""Draft pick value curves from Basketball-Reference data (GitHub mirror: sumitrodatta/bball-reference-datasets).

V(k) = average value produced by the player taken at overall pick k, over a window of drafts.
Three definitions:
  ws4     : Win Shares in the player's first four NBA seasons (the rookie-scale contract window),
            drafts 1995-2022 (main curve).
  ws_car  : career Win Shares through 2025-26, drafts 1995-2016 (10+ seasons observed).
  star    : share of picks who made at least one All-NBA team, drafts 1995-2018.
Unplayed seasons count as 0. Each curve is made monotone non-increasing with isotonic regression.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression

RAW = "data/raw"


def player_seasons() -> pd.DataFrame:
    a = pd.read_csv(f"{RAW}/Advanced.csv")
    a = a[a.lg == "NBA"].copy()
    a["is_tot"] = a.team.astype(str).str.fullmatch(r"\dTM")
    has_tot = a.groupby(["player_id", "season"]).is_tot.transform("any")
    a = a[~has_tot | a.is_tot]  # keep the combined row for traded players
    return a[["player_id", "season", "ws", "vorp"]]


def pick_values(window: str = "ws4") -> pd.DataFrame:
    d = pd.read_csv(f"{RAW}/Draft Pick History.csv")
    d = d[(d.lg == "NBA") & d.overall_pick.notna()].copy()
    d["overall_pick"] = d.overall_pick.astype(int)
    ps = player_seasons()
    m = d.merge(ps, on="player_id", how="left")
    m["yr"] = m.season_y - m.season_x  # 1 = rookie season
    if window == "ws4":
        drafts = range(1995, 2023)
        mm = m[(m.yr >= 1) & (m.yr <= 4)]
    elif window == "ws_car":
        drafts = range(1995, 2017)
        mm = m[m.yr >= 1]
    elif window == "star":
        # share of picks who made at least one All-NBA team, drafts 1995-2018
        e = pd.read_csv(f"{RAW}/End of Season Teams.csv")
        stars = set(e[(e.type == "All-NBA") & (e.lg == "NBA")].player_id)
        base = d[d.season.isin(range(1995, 2019)) & (d.overall_pick <= 60)].copy()
        base["ws"] = base.player_id.isin(stars).astype(float)
        by_pick = base.groupby("overall_pick").ws.agg(["mean", "count", "std"])
        iso = IsotonicRegression(increasing=False).fit(by_pick.index, by_pick["mean"],
                                                       sample_weight=by_pick["count"])
        by_pick["smooth"] = iso.predict(by_pick.index)
        return by_pick
    else:
        raise ValueError(window)
    val = mm.groupby(["season_x", "overall_pick"]).ws.sum()
    base = d[d.season.isin(drafts)][["season", "overall_pick"]]
    base = base.rename(columns={"season": "season_x"})
    base["ws"] = [val.get((s, k), 0.0) for s, k in zip(base.season_x, base.overall_pick)]
    by_pick = base[base.overall_pick <= 60].groupby("overall_pick").ws.agg(["mean", "count", "std"])
    iso = IsotonicRegression(increasing=False).fit(by_pick.index, by_pick["mean"],
                                                   sample_weight=by_pick["count"])
    by_pick["smooth"] = iso.predict(by_pick.index)
    return by_pick


def value_vector(window: str = "ws4", n: int = 30, cache_path: str | None = None) -> np.ndarray:
    """V[k-1] = smoothed value of pick k; optional explicit archived-curve input.

    The default rebuilds from raw data. Passing a cache reuses a previously
    generated curve and is not a fresh verification of those raw inputs.
    """
    if cache_path is not None:
        table = pd.read_csv(cache_path, header=[0, 1], index_col=0)
        values = table[(window, "smooth")].loc[1:n].to_numpy(dtype=float)
        if len(values) != n or not np.isfinite(values).all() or (np.diff(values) > 0).any():
            raise ValueError("Cached pick values must be finite, complete, and non-increasing")
        return values
    return pick_values(window)["smooth"].loc[1:n].to_numpy()


if __name__ == "__main__":
    for w in ["ws4", "ws_car", "star"]:
        pv = pick_values(w)
        print(w)
        print(pv.loc[[1, 2, 3, 4, 5, 6, 8, 10, 12, 14, 16, 20, 25, 30]].round(2).to_string())
