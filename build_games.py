"""Build a season's regular-season game results from cdn.nba.com play-by-play (GitHub mirror shufinskiy/nba_data)
and check them against Basketball-Reference final records.

usage: python3 build_games.py [season_start_year]   (default 2025 -> 2025-26)
"""
import sys

import pandas as pd

RAW = "data/raw"
ALIAS = {"BRK": "BKN", "CHO": "CHA", "PHO": "PHX"}


def build(y: int) -> pd.DataFrame:
    cols = ["gameId", "timeActual", "teamTricode", "scoreHome", "scoreAway", "orderNumber"]
    p = pd.read_csv(f"{RAW}/cdnnba_{y}.csv", usecols=cols, low_memory=False)
    p = p[p.gameId.astype(str).str.startswith(f"2{str(y)[2:]}")]  # regular season only
    p = p.sort_values(["gameId", "orderNumber"])
    p["scoreHome"] = pd.to_numeric(p.scoreHome, errors="coerce")
    p["scoreAway"] = pd.to_numeric(p.scoreAway, errors="coerce")
    g = p.groupby("gameId")
    final = g[["scoreHome", "scoreAway"]].max()
    start = g.timeActual.min()
    p["dH"] = g.scoreHome.diff().fillna(0)
    p["dA"] = g.scoreAway.diff().fillna(0)
    sc = p[(p.dH > 0) | (p.dA > 0)].dropna(subset=["teamTricode"])
    home = sc[sc.dH > 0].groupby("gameId").teamTricode.agg(lambda s: s.value_counts().index[0])
    away = sc[sc.dA > 0].groupby("gameId").teamTricode.agg(lambda s: s.value_counts().index[0])
    games = pd.DataFrame({"home": home, "away": away}).join(final).join(start)
    games["date"] = (pd.to_datetime(games.timeActual, utc=True, format="ISO8601")
                     .dt.tz_convert("America/New_York").dt.date)
    games = games.drop(columns="timeActual").reset_index()
    games["home_win"] = (games.scoreHome > games.scoreAway).astype(int)
    return games.sort_values(["date", "gameId"])


def check(games: pd.DataFrame, y: int) -> pd.DataFrame:
    w = pd.concat([games.assign(team=games.home, win=games.home_win),
                   games.assign(team=games.away, win=1 - games.home_win)])
    rec = w.groupby("team").win.agg(["sum", "count"]).rename(columns={"sum": "W", "count": "G"})
    rec["L"] = rec.G - rec.W
    ts = pd.read_csv(f"{RAW}/Team Summaries.csv")
    ts = ts[(ts.season == y + 1) & ts.abbreviation.notna()][["abbreviation", "w", "l"]]
    ts["team"] = ts.abbreviation.replace(ALIAS)
    chk = rec.join(ts.set_index("team")[["w", "l"]])
    chk["ok"] = (chk.W == chk.w) & (chk.L == chk.l)
    return chk


if __name__ == "__main__":
    y = int(sys.argv[1]) if len(sys.argv) > 1 else 2025
    games = build(y)
    out = f"data/games_{y}_{str(y + 1)[2:]}.csv"
    games.to_csv(out, index=False)
    chk = check(games, y)
    d = pd.to_datetime(pd.Series(sorted(games.date.unique())))
    gap = d.diff().dt.days
    i = gap.idxmax()
    print(f"{out}: {len(games)} games, {games.date.min()} to {games.date.max()}; records match "
          f"Basketball-Reference for {chk.ok.sum()} of {len(chk)} teams; All-Star break: last games "
          f"{d[i - 1].date()}, resume {d[i].date()}")
    if not chk.ok.all():
        print(chk[~chk.ok])
