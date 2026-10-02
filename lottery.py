"""NBA draft lottery engines.

old_lottery  : 2019-2026 rules. 14 non-playoff teams ordered worst to best record.
               No. 1 odds per 1,000 combinations: 140,140,140,125,105,90,75,60,45,30,20,15,10,5.
               Picks 1-4 are drawn; picks 5-14 follow reverse record order.

new_lottery  : "3-2-1" rules for the 2027-2029 lotteries (NBA release, May 28, 2026).
               16 teams; all 16 positions drawn one ball at a time.
               Balls: 3 worst records 2 each ("relegated"), other non-play-in teams 3 each,
               No. 9 and No. 10 play-in seeds 2 each, losers of the 7-vs-8 games 1 each.
               Relegated teams cannot fall below pick 12 (floor mechanism not published;
               implemented as a forced fill, see the FLOOR note in new_lottery).
               Optional per-team ineligible slots implement the rule that a team cannot pick
               No. 1 in consecutive drafts or top 5 in three consecutive drafts.
"""
from __future__ import annotations

import numpy as np

OLD_COMBOS = np.array([140, 140, 140, 125, 105, 90, 75, 60, 45, 30, 20, 15, 10, 5], dtype=float)

# 3-2-1 groups in lottery-slot order (16 slots)
NEW_GROUPS = ["rel"] * 3 + ["np3"] * 7 + ["pi910"] * 4 + ["pi78"] * 2
NEW_BALLS = np.array([2] * 3 + [3] * 7 + [2] * 4 + [1] * 2, dtype=float)
NEW_PROTECTED = np.array([True] * 3 + [False] * 13)
FLOOR = 12


def old_lottery(n_sims: int = 1_000_000, seed: int = 0, combos=OLD_COMBOS) -> np.ndarray:
    """pick[s, slot] for slot 0..13 (slot 0 = worst record). Ties are ignored."""
    rng = np.random.default_rng(seed)
    n = len(combos)
    # Gumbel-top-k == sequential weighted draws without replacement (redraw of repeats)
    keys = np.log(combos)[None, :] + rng.gumbel(size=(n_sims, n))
    top4 = np.argsort(-keys, axis=1)[:, :4]
    rows = np.arange(n_sims)[:, None]
    drawn = np.zeros((n_sims, n), dtype=bool)
    drawn[rows, top4] = True
    pick = np.zeros((n_sims, n), dtype=np.int16)
    pick[rows, top4] = np.arange(1, 5, dtype=np.int16)[None, :]
    undrawn_rank = np.cumsum(~drawn, axis=1)  # 1-based rank among undrawn, in record order
    return np.where(drawn, pick, 4 + undrawn_rank).astype(np.int16)


def new_lottery(n_sims: int = 1_000_000, seed: int = 0, balls=NEW_BALLS,
                protected=NEW_PROTECTED, floor: int = FLOOR,
                ineligible: dict[int, set[int]] | None = None) -> np.ndarray:
    """pick[s, slot] for the 16 lottery slots.

    FLOOR: picks are drawn one ball at a time. Before drawing pick p (p <= floor), if the
    number of undrawn protected teams equals the number of slots left up to the floor
    (floor - p + 1), the draw is restricted to protected teams. The NBA has not published its
    mechanism; this forced fill reproduces the league's published group odds and Tankathon's
    pick 10/11/12 odds for relegated teams (8.1/14.4/25.1%), which a post-draw "bump" does not.

    ineligible: {slot_index: set of pick numbers that team may not receive}. When such a
    team's ball would be drawn for an ineligible pick, it is excluded from that draw.
    """
    rng = np.random.default_rng(seed)
    n = len(balls)
    ineligible = ineligible or {}
    avail = np.ones((n_sims, n), dtype=bool)
    pick = np.zeros((n_sims, n), dtype=np.int16)
    rows = np.arange(n_sims)
    for p in range(1, n + 1):
        w = np.where(avail, balls[None, :], 0.0)
        for slot, bad in ineligible.items():
            if p in bad:
                w[:, slot] = 0.0
        if p <= floor:
            undrawn_prot = (avail & protected[None, :]).sum(axis=1)
            force = undrawn_prot == (floor - p + 1)
            if force.any():
                w[force] = np.where(protected[None, :], w[force], 0.0)
        tot = w.sum(axis=1, keepdims=True)
        u = rng.random((n_sims, 1)) * tot
        choice = (np.cumsum(w, axis=1) < u).sum(axis=1)
        choice = np.minimum(choice, n - 1)
        pick[rows, choice] = p
        avail[rows, choice] = False
    return pick


def summarize(pick: np.ndarray, labels: list[str]) -> dict:
    """Probability tables by group label: P(No.1), P(top 3/5/10), E[pick], full distribution."""
    out = {}
    n_picks = pick.max()
    for g in dict.fromkeys(labels):
        cols = [i for i, l in enumerate(labels) if l == g]
        p = pick[:, cols].ravel()
        dist = np.bincount(p, minlength=n_picks + 1)[1:] / len(p)
        out[g] = {
            "p1": float((p == 1).mean()),
            "top3": float((p <= 3).mean()),
            "top5": float((p <= 5).mean()),
            "top10": float((p <= 10).mean()),
            "mean": float(p.mean()),
            "dist": dist,
        }
    return out


if __name__ == "__main__":
    new = new_lottery(400_000, seed=1)
    s = summarize(new, NEW_GROUPS)
    print("3-2-1 group odds (simulated):  No.1  top3  top5  top10  E[pick]")
    for g, v in s.items():
        print(f"  {g:6s} {100*v['p1']:5.1f} {100*v['top3']:5.1f} {100*v['top5']:5.1f}"
              f" {100*v['top10']:5.1f}  {v['mean']:5.2f}")
    rel = s["rel"]["dist"]
    print("  relegated P(pick 10/11/12/13+):", [round(100 * x, 1) for x in rel[9:12]],
          round(100 * rel[12:].sum(), 2))
    old = old_lottery(400_000, seed=2)
    p = old
    print("old system E[pick] by slot:", np.round(p.mean(axis=0), 2))
    print("old system P(No.1) by slot:", np.round(100 * (p == 1).mean(axis=0), 1))
