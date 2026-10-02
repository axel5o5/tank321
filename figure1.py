"""Figure 1. (A) 2025-26 at the All-Star break: incentive to lose under the old lottery and under 3-2-1.
(B) Validation over 2023-24 to 2025-26: incentive under the old lottery vs post-break shortfall."""
import matplotlib
import numpy as np
import pandas as pd
from scipy import stats
import argparse
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--input-dir", type=Path, default=Path("results"))
parser.add_argument("--output-dir", type=Path, default=Path("outputs"))
args = parser.parse_args()
args.output_dir.mkdir(parents=True, exist_ok=True)

matplotlib.use("Agg")
import matplotlib.pyplot as plt

SURF, INK, INK2, GRID, BAND = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df", "#f1f0ec"
OLD, NEW = "#77736e", "#2a78d6"

d = pd.read_csv(args.input_dir / "replay_ws4.csv", index_col=0)
fig, (ax, bx) = plt.subplots(1, 2, figsize=(11.5, 6.4), dpi=200, gridspec_kw={"width_ratios": [1.05, 1]})
fig.patch.set_facecolor(SURF)

# Panel A
a = d[(d.season == "2025-26") & (d.P_playoff < 0.9)].copy()
a["pct"] = a.W0 / a.pre_G
a = a.sort_values("pct")
y = np.arange(len(a))[::-1]
out = a.P_playoff < 0.10
ax.set_facecolor(SURF)
ys = y[~out.to_numpy()]
ax.axhspan(ys.min() - 0.5, ys.max() + 0.5, color=BAND, zorder=0)
ax.text(0.74, ys.max(), "Playoff bubble", ha="right", va="center", fontsize=8.5, color=INK2, style="italic")
yo = y[out.to_numpy()]
ax.text(0.74, yo.max(), "Out of contention", ha="right", va="center", fontsize=8.5, color=INK2, style="italic")
ax.axvline(0, color=INK2, lw=0.8, zorder=1)
labels = []
for yy, (t, r) in zip(y, a.iterrows()):
    ax.plot([r.dV_old, r.dV_new], [yy, yy], color=GRID, lw=2, zorder=2, solid_capstyle="round")
    ax.scatter(r.dV_old, yy, s=70, facecolors="none", edgecolors=OLD, zorder=3, linewidths=1.4)
    ax.scatter(r.dV_new, yy, s=36, marker="D", color=NEW, zorder=4, edgecolor=SURF, linewidth=1.2)
    note = {"owed": " (pick owed)", "lesser": " (worse of two picks)"}.get(r.owns_pick, "")
    labels.append(f"{t} {int(r.W0)}-{int(r.pre_G - r.W0)}{note}")
ax.set_yticks(y)
ax.set_yticklabels(labels, fontsize=8, color=INK)
ax.tick_params(axis="y", length=0)
ax.set_xlim(-0.36, 0.75)
ax.set_ylim(-0.7, len(a) - 0.3)
ax.set_xlabel("Retained draft-value gain from losing (Win Shares per game)", fontsize=8.5, color=INK2)
ax.scatter([], [], s=70, facecolors="none", edgecolors=OLD, linewidths=1.4, label="Old lottery")
ax.scatter([], [], s=36, marker="D", color=NEW, label="3-2-1 lottery")
fig.legend(loc="upper right", bbox_to_anchor=(0.99, 0.985), ncol=2, frameon=False, fontsize=8.5, labelcolor=INK)
ax.set_title("A. 2025-26 at the All-Star break, scored under each lottery", loc="left", fontsize=9.5,
             color=INK, fontweight="bold")

# Panel B
b = d[d.P_playoff < 0.10].copy()
rho, p = stats.spearmanr(b.dV_old, b.post_shortfall)
rx, ry, rz = (stats.rankdata(v) for v in (b.dV_old, b.post_shortfall, b.W0 / b.pre_G))
residual = lambda v: v - np.polyval(np.polyfit(rz, v, 1), rz)
partial_rho = stats.pearsonr(residual(rx), residual(ry)).statistic
df = len(b) - 3
partial_p = 2 * stats.t.sf(abs(partial_rho) * np.sqrt(df / (1 - partial_rho**2)), df)
bx.set_facecolor(SURF)
bx.axhline(0, color=INK2, lw=0.8, zorder=1)
bx.scatter(b.dV_old, b.post_shortfall, s=36, color=OLD, edgecolor=SURF, linewidth=1.2, zorder=3)
annot = {("UTA", "2023-24"), ("TOR", "2023-24"), ("HOU", "2023-24"), ("PHI", "2024-25"), ("CHI", "2024-25"),
         ("SAC", "2025-26"), ("NOP", "2025-26"), ("UTA", "2025-26"), ("MEM", "2025-26")}
for t, r in b.iterrows():
    if (t, r.season) in annot:
        bx.annotate(f"{t} {r.season[2:4]}-{r.season[5:]}", (r.dV_old, r.post_shortfall), xytext=(6, 2),
                    textcoords="offset points", fontsize=7.5, color=INK2)
bx.set_xlabel("Incentive to lose at the break, old lottery (Win Shares per game)", fontsize=8.5, color=INK2)
bx.set_ylabel("Wins below projection after the break", fontsize=8.5, color=INK2)
bx.set_title("B. Observational association with post-break shortfall", loc="left", fontsize=9,
             color=INK, fontweight="bold")
bx.text(0.97, 0.25, f"{len(b)} team-seasons, 2023-24 to 2025-26\nUnadjusted rho = {rho:.2f}, p = {p:.3f}\n"
        f"Adjusted for pre-break win%: rho = {partial_rho:.2f}, p = {partial_p:.2f}\n"
        "Nominal p-values; dependence not accounted for",
         transform=bx.transAxes, ha="right", va="bottom", fontsize=7.5, color=INK2)
for axx in (ax, bx):
    axx.tick_params(axis="x", colors=INK2, labelsize=8)
    axx.grid(axis="x", color=GRID, lw=0.6, zorder=0)
    for s in axx.spines.values():
        s.set_visible(False)
bx.tick_params(axis="y", colors=INK2, labelsize=8)
bx.grid(axis="y", color=GRID, lw=0.6, zorder=0)

fig.suptitle("Average modeled draft incentives shift toward the playoff bubble under 3-2-1",
             x=0.015, ha="left", fontsize=11, fontweight="bold", color=INK, y=0.985)
fig.text(0.015, 0.935, "Incentive = expected retained first-round draft value gained by losing one remaining game "
         "instead of winning it, accounting for specified pick obligations.",
         fontsize=8, color=INK2)
fig.tight_layout(rect=[0, 0, 0.985, 0.92], w_pad=3)
fig.savefig(args.output_dir / "figure1.png", facecolor=SURF)
fig.savefig(args.output_dir / "figure1.svg", facecolor=SURF)
plt.close(fig)
print("saved")
