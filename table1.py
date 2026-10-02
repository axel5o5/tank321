"""Table 1: prospective 2026-27 incentives. Rule: the six largest 3-2-1 incentives among teams with
P(playoffs) < 0.9, plus every team in the bottom eight by win total that fully owns its 2027 pick."""
import pandas as pd
import argparse
from pathlib import Path
from reporting import bottom_by_total

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--input-dir", type=Path, default=Path("results"))
parser.add_argument("--output-dir", type=Path, default=Path("outputs"))
args = parser.parse_args()
args.output_dir.mkdir(parents=True, exist_ok=True)

b = pd.read_csv(args.input_dir / "proj_2026_27_betmgm.csv", index_col=0)
k = pd.read_csv(args.input_dir / "proj_2026_27_kalshi.csv", index_col=0)
top = b[b.P_playoff < 0.9].sort_values("dV_new", ascending=False).head(6)
bottom = bottom_by_total(b)
bottom = bottom[bottom.owns_2027_pick == "yes"].sort_values(["win_total", "team"], ascending=[False, True])
t = pd.concat([top, bottom])[["win_total", "owns_2027_pick", "P_playoff", "P_rel", "dV_new", "dV_old"]]
t["dV_new_kalshi"] = k.loc[t.index, "dV_new"]
t.to_csv(args.output_dir / "table1.csv")
assert (t.owns_2027_pick == "yes").all(), "Caption must be updated if displayed ownership changes"
lines = ["| Team | Win total | 3-2-1 | Old rules |", "|---|---|---|---|"]
for team, r in t.iterrows():
    lines.append(f"| {team} | {r.win_total:.1f} | {r.dV_new:.2f} | {r.dV_old:.2f} |")
(args.output_dir / "table1.md").write_text("\n".join(lines) + "\n")
print(t.round(4).to_string())
print("\n".join(lines))
