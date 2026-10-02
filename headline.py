"""Headline numbers from --input-dir CSVs, written to --output-dir (default outputs/)."""
import numpy as np
import pandas as pd
from scipy import stats
import argparse
from pathlib import Path

from lottery import NEW_GROUPS, new_lottery, old_lottery, summarize
from value import value_vector
from reporting import bottom_by_total

out = []
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--value-cache", help="Explicit archived pick-value CSV; otherwise rebuild from raw data")
parser.add_argument("--input-dir", type=Path, default=Path("results"))
parser.add_argument("--output-dir", type=Path, default=Path("outputs"))
args = parser.parse_args()
V = value_vector("ws4", cache_path=args.value_cache)
args.output_dir.mkdir(parents=True, exist_ok=True)


def say(s):
    print(s)
    out.append(s)


# 1. Lottery level
new = summarize(new_lottery(1_000_000, seed=3), NEW_GROUPS)
old = old_lottery(1_000_000, seed=4)
say("LOTTERY 3-2-1 group odds (No.1/top3/top5/top10) and expected pick: " + "; ".join(
    f"{g} {100*v['p1']:.1f}/{100*v['top3']:.1f}/{100*v['top5']:.1f}/{100*v['top10']:.1f} E={v['mean']:.2f}"
    for g, v in new.items()))
rel = new["rel"]["dist"]
say(f"LOTTERY relegated P(pick 10/11/12) = {100*rel[9]:.1f}/{100*rel[10]:.1f}/{100*rel[11]:.1f}; "
    f"P(13+) = {100*rel[12:].sum():.2f}")
say(f"LOTTERY old system expected pick: worst {old[:, 0].mean():.2f}, 4th worst {old[:, 3].mean():.2f}")
say(f"VALUE ws4: V(1)={V[0]:.1f}, V(5)={V[4]:.1f}, V(10)={V[9]:.1f}, V(14)={V[13]:.1f}, V(30)={V[29]:.1f}")

# 2. Validation: three seasons played under the old lottery
for w in ["ws4", "ws_car", "star"]:
    d = pd.read_csv(args.input_dir / f"replay_{w}.csv", index_col=0)
    nc = d[d.P_playoff < 0.10].copy()
    rho, p = stats.spearmanr(nc.dV_old, nc.post_shortfall)
    nc["rk"] = nc.groupby("season").dV_old.rank(pct=True)
    hi, lo = nc[nc.rk > 0.5].post_shortfall, nc[nc.rk <= 0.5].post_shortfall
    per = {s: stats.spearmanr(x.dV_old, x.post_shortfall)[0] for s, x in nc.groupby("season")}
    # partial Spearman controlling for pre-break win percentage (residualized ranks)
    rx, ry, rz = (stats.rankdata(v) for v in (nc.dV_old, nc.post_shortfall, nc.W0 / nc.pre_G))
    res = lambda a: a - np.polyval(np.polyfit(rz, a, 1), rz)
    pr = stats.pearsonr(res(rx), res(ry)).statistic
    # One fitted control: n - 3 degrees of freedom, not pearsonr's n - 2.
    # This remains an approximate iid partial-rank test, not clustered inference.
    df = len(nc) - 3
    pp = 2 * stats.t.sf(abs(pr) * np.sqrt(df / (1 - pr**2)), df)
    rho_w = stats.spearmanr(nc.dV_old, nc.W0 / nc.pre_G)[0]
    say(f"VALIDATION[{w}]: out-of-contention team-seasons n={len(nc)}; Spearman rho(incentive, post-break wins "
        f"below projection) = {rho:.2f} (p={p:.3f}); top half by incentive {hi.mean():.1f} wins below projection vs "
        f"bottom half {lo.mean():.1f}; per season " + ", ".join(f"{s} {v:.2f}" for s, v in per.items())
        + f"; corr(incentive, pre-break win%) {rho_w:.2f}; partial rho given win% {pr:.2f} (p={pp:.3f})")

# 3. Replay under 3-2-1
for w in ["ws4", "ws_car", "star"]:
    d = pd.read_csv(args.input_dir / f"replay_{w}.csv", index_col=0)
    own = d[(d.owns_pick != "owed") & ~((d.dV_old.abs() < 1e-3) & (d.dV_new.abs() < 1e-3))]
    for scope, dd in [("2025-26", own[own.season == "2025-26"]), ("3 seasons", own)]:
        nc = dd[dd.P_playoff < 0.10]
        bub = dd[(dd.P_playoff >= 0.10) & (dd.P_playoff <= 0.90)]
        thr = 0.01 if w != "star" else 0.0005
        say(f"REPLAY[{w}, {scope}]: out of contention n={len(nc)} mean incentive old {nc.dV_old.mean():.3f} -> "
            f"3-2-1 {nc.dV_new.mean():.3f} ({100 * (nc.dV_new.mean() / nc.dV_old.mean() - 1):+.0f}%); above {thr}: "
            f"{(nc.dV_old > thr).sum()} -> {(nc.dV_new > thr).sum()}; bubble n={len(bub)} "
            f"({', '.join(bub.index)}) {bub.dV_old.mean():.3f} -> {bub.dV_new.mean():.3f} "
            f"({100 * (bub.dV_new.mean() / bub.dV_old.mean() - 1):+.0f}%)")
        if w == "ws4":
            lam_o, lam_n = (bub.dV_old / bub.dPlayoff).median(), (bub.dV_new / bub.dPlayoff).median()
            say(f"REPLAY[{w}, {scope}]: bubble break-even playoff value (median incentive / playoff-odds cost per "
                f"game) old {lam_o:.1f} -> 3-2-1 {lam_n:.1f} Win Shares; cost per game {bub.dPlayoff.mean():.3f}")

# 4. 2026-27 projection
for f in ["betmgm", "kalshi", "betmgm_ownall"]:
    pj = pd.read_csv(args.input_dir / f"proj_2026_27_{f}.csv", index_col=0)
    bottom = bottom_by_total(pj)
    band = pj[(pj.win_total >= 38) & (pj.win_total <= 46)]
    band_own = band[band.owns_2027_pick != "no"]
    say(f"PROJ[{f}]: bottom-8 by win total ({', '.join(bottom.index)}) mean incentive 3-2-1 {bottom.dV_new.mean():.3f} "
        f"vs old {bottom.dV_old.mean():.3f} ({100 * (bottom.dV_new.mean() / bottom.dV_old.mean() - 1):+.0f}%); "
        f"38-46 win teams owning their pick n={len(band_own)} 3-2-1 {band_own.dV_new.mean():.3f} vs old "
        f"{band_own.dV_old.mean():.3f} ({100 * (band_own.dV_new.mean() / band_own.dV_old.mean() - 1):+.0f}%)")
    lot = pj[pj.P_playoff < 0.9]
    say(f"PROJ[{f}]: top 6 by 3-2-1 incentive among teams with P(playoffs)<0.9: " +
        ", ".join(f"{t} {v:.2f}" for t, v in lot.dV_new.head(6).items()))

(args.output_dir / "headline_numbers.txt").write_text("\n".join(out) + "\n")
