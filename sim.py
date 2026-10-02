"""League simulator and tanking-incentive model.

For a league state (wins so far, remaining schedule, team ratings) we simulate the rest of the season,
the play-in tournament, and the draft order under both lottery systems, then value each team's
first-round pick with a pick-value curve V(k).

Marginal incentive to lose (Delta) for team i:
    Delta_i = E[ V_i | one fewer win ] - E[ V_i | one more win ]
computed with common random numbers: every other result is held fixed and only one of team i's
remaining results is toggled. Delta > 0 means losing raises the expected value of the team's pick.
The same toggle gives the playoff (and play-in) probability a win is worth, so the cost of tanking is
reported next to its reward.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from lottery import NEW_GROUPS, new_lottery, old_lottery

EAST = ["ATL", "BOS", "BKN", "CHA", "CHI", "CLE", "DET", "IND", "MIA", "MIL", "NYK", "ORL", "PHI", "TOR", "WAS"]
WEST = ["DAL", "DEN", "GSW", "HOU", "LAC", "LAL", "MEM", "MIN", "NOP", "OKC", "PHX", "POR", "SAC", "SAS", "UTA"]
TEAMS = EAST + WEST
IDX = {t: i for i, t in enumerate(TEAMS)}
CONF = np.array([0] * 15 + [1] * 15)
DIVISIONS = [["BOS", "BKN", "NYK", "PHI", "TOR"], ["CHI", "CLE", "DET", "IND", "MIL"],
             ["ATL", "CHA", "MIA", "ORL", "WAS"], ["DEN", "MIN", "OKC", "POR", "UTA"],
             ["GSW", "LAC", "LAL", "PHX", "SAC"], ["DAL", "HOU", "MEM", "NOP", "SAS"]]

GROUP_CODES = {"rel": 1, "np3": 2, "pi910": 3, "pi78": 4}  # 0 = outside the 16-team lottery


def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


class PickValues:
    """Expected first-round pick value by lottery position, old and new systems.

    ownership: {team: spec} with spec kinds from ownership.py ("owed", "protected", "rollover", "lesser", "more").
    Pair deals ("lesser", "more") are valued on realized picks: pools of lottery draws are kept, and each
    simulated season uses one row of each pool.
    ineligible_by_team: {team: set of pick numbers} barred under the consecutive-top-pick rule
            (3-2-1 system only).
    """

    def __init__(self, V: np.ndarray, n_lottery_sims: int = 1_000_000, seed: int = 11,
                 ineligible_by_team: dict[str, set[int]] | None = None,
                 ownership: dict | None = None, pool_size: int = 200_000):
        self.V = np.asarray(V, float)  # V[k-1] = value of pick k, k = 1..30
        self.ineligible = {t: set(bad) for t, bad in (ineligible_by_team or {}).items() if bad}
        self.restricted_teams = tuple(sorted(self.ineligible))
        self.conditional_n = max(1, n_lottery_sims // 4)
        self.lottery_seed = seed
        self.conditional_cache = {}
        if n_lottery_sims < 1 or pool_size < 1:
            raise ValueError("Lottery simulation and pool sizes must be positive")
        self.pool_size = min(pool_size, n_lottery_sims,
                             self.conditional_n if self.ineligible else n_lottery_sims)
        old = old_lottery(n_lottery_sims, seed)
        self.P_old = np.stack([np.bincount(old[:, s], minlength=31)[1:31] / len(old)
                               for s in range(old.shape[1])])  # (14 slots, 30 picks)
        self.old_pool = old[:self.pool_size].copy()
        del old
        new = new_lottery(n_lottery_sims, seed + 1)
        self.P_new = np.zeros((5, 30))
        self.group_cols = {}
        for g, code in GROUP_CODES.items():
            cols = [i for i, l in enumerate(NEW_GROUPS) if l == g]
            self.group_cols[code] = np.array(cols)
            self.P_new[code] = np.bincount(new[:, cols].ravel(), minlength=31)[1:31] / new[:, cols].size
        self.new_pool = new[:self.pool_size].copy()
        del new
        # ownership-adjusted tables
        TV = np.tile(self.V, (30, 1))
        k = np.arange(1, 31)
        self.pairs = []
        for team, spec in (ownership or {}).items():
            i = IDX[team]
            if spec[0] == "owed":
                TV[i] = 0.0
            elif spec[0] == "protected":
                TV[i] = np.where(k <= spec[1], self.V, 0.0)
            elif spec[0] == "rollover":
                TV[i] = np.where(k <= spec[1], self.V, self.V.mean())
            elif spec[0] == "lesser":
                self.pairs.append((i, IDX[spec[1]], "lesser", 0))
            elif spec[0] == "more":
                self.pairs.append((i, IDX[spec[1]], "more", spec[2]))
            else:
                raise ValueError(spec)
        self.adj = self._tables(TV)

    def _tables(self, TV):
        """(TV (30,30) value by pick, OLD (30,14) value by old lottery slot, NEW (30,5) value by 3-2-1 group)."""
        OLD = TV @ self.P_old.T
        NEW = TV @ self.P_new.T
        NEW[:, 0] = 0.0  # non-lottery teams are valued by record order instead
        return TV, OLD, NEW

    def _conditional_lottery(self, key):
        """Joint pool conditional on each restricted team's group (0 = outside lottery).

        Restricted teams occupy the first available columns in their group. Remaining
        columns are exchangeable. Cache keys depend only on group membership, not
        records, so the two-team 2027 case has at most 25 entries.
        """
        if key not in self.conditional_cache:
            available = {g: list(cols) for g, cols in self.group_cols.items()}
            assigned, exclusions = {}, {}
            for team, g in zip(self.restricted_teams, key):
                if g:
                    col = available[g].pop(0)
                    assigned[IDX[team]] = col
                    exclusions[col] = self.ineligible[team]
            # Stable per-key seeds make cache population order irrelevant.
            key_id = sum(int(g) * 5**i for i, g in enumerate(key))
            draws = new_lottery(self.conditional_n, self.lottery_seed + 100 + key_id,
                                ineligible=exclusions)
            P = np.stack([np.bincount(draws[:, col], minlength=31)[1:31] / len(draws)
                          for col in range(16)])
            self.conditional_cache[key] = (P, draws[:self.pool_size].copy(), assigned, available)
        return self.conditional_cache[key]

    def restricted_new_values(self, group, Wj, rk_nl, lot_rows):
        """Coherent conditional expectations and joint realized picks for all teams.

        Analytic values average the exchangeable ordinary columns to reduce noise;
        pair deals use distinct columns from the same joint lottery row.
        """
        TV = self.adj[0]
        T = np.arange(30)[None, :]
        picks = (17 + rk_nl).astype(int)
        values = TV[T, np.minimum(picks - 1, 29)]
        restricted_idx = [IDX[t] for t in self.restricted_teams]
        keys, inverse = np.unique(group[:, restricted_idx], axis=0, return_inverse=True)
        for k, key_array in enumerate(keys):
            rows = np.flatnonzero(inverse == k)
            gg, ww = group[rows], Wj[rows]
            P, pool, assigned, available = self._conditional_lottery(tuple(key_array))
            cols = np.zeros(gg.shape, dtype=int)
            vv = values[rows].copy()
            for code, ordinary_cols in available.items():
                mask = gg == code
                mask[:, restricted_idx] = False
                if ordinary_cols:
                    ranks = _rank_within(mask, ww)
                    mapped = np.asarray(ordinary_cols)[np.minimum(ranks, len(ordinary_cols)-1)]
                    cols[mask] = mapped[mask]
                    expected = TV @ P[ordinary_cols].mean(axis=0)
                    vv = np.where(mask, expected[None, :], vv)
            for team_idx, col in assigned.items():
                cols[:, team_idx] = col
                vv[:, team_idx] = P[col] @ TV[team_idx]
            realized = pool[lot_rows[rows, None], cols]
            picks[rows] = np.where(gg == 0, picks[rows], realized)
            values[rows] = vv
        return values, picks


def _rank_within(mask, Wj):
    """Rank (0 = worst record) of each team among the teams where mask is True, per simulation."""
    key = np.where(mask, Wj, np.inf)
    return np.argsort(np.argsort(key, axis=1), axis=1)


def _values(tables, group, playoff, rk_nl, rk_np, rk_po):
    TV, OLD, NEW = tables
    T = np.arange(30)[None, :]
    v_new = np.where(group == 0, TV[T, np.minimum(16 + rk_nl, 29)], NEW[T, group])  # non-lottery: picks 17-30
    v_old = np.where(~playoff, OLD[T, np.minimum(rk_np, 13)],                          # old lottery slots 0-13
                     TV[T, np.minimum(14 + rk_po, 29)])                                # playoff teams: picks 15-30
    return v_new, v_old


def _realized_picks(i, pv, group, playoff, Wj, rk_nl, rk_np, rk_po, lot_rows):
    """Realized pick numbers of team i under the 3-2-1 and old systems, one lottery draw per simulation."""
    N = Wj.shape[0]
    rows = np.arange(N)
    g = group[:, i]
    same = group == g[:, None]
    k = (same & (Wj < Wj[:, i:i + 1])).sum(axis=1)  # rank within its 3-2-1 group (teams are exchangeable)
    col = np.zeros(N, dtype=np.int64)
    for code, cols in pv.group_cols.items():
        m = g == code
        col[m] = cols[np.minimum(k[m], len(cols) - 1)]
    new_pick = np.where(g == 0, 17 + rk_nl[:, i], pv.new_pool[lot_rows, col])
    old_pick = np.where(playoff[:, i], 15 + rk_po[:, i], pv.old_pool[lot_rows, np.minimum(rk_np[:, i], 13)])
    return new_pick.astype(int), old_pick.astype(int)


def evaluate(Wj: np.ndarray, r: np.ndarray, u: np.ndarray, pv: PickValues, home_adv: float,
             lot_rows: np.ndarray | None = None):
    """Wj: (N, 30) final wins + tiebreak jitter. r: (N, 30) or (30,) ratings. u: (N, 6) uniforms for
    the six play-in games. lot_rows: (N,) lottery-pool rows used for pair deals (common random numbers).
    Returns dict of (N, 30) arrays: v_new, v_old, playoff, playin, group."""
    N = Wj.shape[0]
    rr = np.broadcast_to(r, Wj.shape)
    rows = np.arange(N)
    seed = np.zeros((N, 30), dtype=np.int16)
    playoff = np.zeros((N, 30), dtype=bool)
    group = np.zeros((N, 30), dtype=np.int8)
    for c in (0, 1):
        idx = np.where(CONF == c)[0]
        order = idx[np.argsort(-Wj[:, idx], axis=1)]  # (N, 15) team index by seed
        seed[rows[:, None], order] = np.arange(1, 16)[None, :]
        s7, s8, s9, s10 = order[:, 6], order[:, 7], order[:, 8], order[:, 9]
        a_win = u[:, 3 * c] < sigmoid(rr[rows, s7] - rr[rows, s8] + home_adv)
        wa, la = np.where(a_win, s7, s8), np.where(a_win, s8, s7)
        b_win = u[:, 3 * c + 1] < sigmoid(rr[rows, s9] - rr[rows, s10] + home_adv)
        wb = np.where(b_win, s9, s10)
        c_win = u[:, 3 * c + 2] < sigmoid(rr[rows, la] - rr[rows, wb] + home_adv)
        wc = np.where(c_win, la, wb)
        playoff[rows[:, None], order[:, :6]] = True
        playoff[rows, wa] = True
        playoff[rows, wc] = True
        group[rows, la] = GROUP_CODES["pi78"]
        group[rows, s9] = GROUP_CODES["pi910"]
        group[rows, s10] = GROUP_CODES["pi910"]
        group[rows[:, None], order[:, 10:]] = GROUP_CODES["np3"]
    # relegation: three worst records among the ten non-play-in teams
    key = np.where(group == GROUP_CODES["np3"], Wj, np.inf)
    rk = np.argsort(np.argsort(key, axis=1), axis=1)
    group = np.where((group == GROUP_CODES["np3"]) & (rk < 3), GROUP_CODES["rel"], group).astype(np.int8)

    # pick values under both systems, after ownership
    rk_nl = _rank_within(group == 0, Wj)    # 3-2-1: teams outside the lottery, picks 17-30
    rk_np = _rank_within(~playoff, Wj)      # old: lottery slots
    rk_po = _rank_within(playoff, Wj)       # old: playoff teams, picks 15-30
    v_new, v_old = _values(pv.adj, group, playoff, rk_nl, rk_np, rk_po)
    restricted_picks = None
    if pv.ineligible:
        if lot_rows is None:
            lot_rows = np.random.default_rng(0).integers(0, pv.pool_size, N)
        v_new, restricted_picks = pv.restricted_new_values(group, Wj, rk_nl, lot_rows)
    if pv.pairs:
        if lot_rows is None:
            lot_rows = np.random.default_rng(0).integers(0, pv.pool_size, N)
        for a, b, mode, k in pv.pairs:
            na, oa = _realized_picks(a, pv, group, playoff, Wj, rk_nl, rk_np, rk_po, lot_rows)
            nb, ob = _realized_picks(b, pv, group, playoff, Wj, rk_nl, rk_np, rk_po, lot_rows)
            if restricted_picks is not None:
                na, nb = restricted_picks[:, a], restricted_picks[:, b]
            for pa, pb, out in ((na, nb, v_new), (oa, ob, v_old)):
                better, worse = np.minimum(pa, pb), np.maximum(pa, pb)
                if mode == "lesser":
                    out[:, a] = pv.V[worse - 1]
                else:  # "more": keep the better pick, and the worse one too if it lands at k or better
                    out[:, a] = pv.V[better - 1] + np.where(worse <= k, pv.V[worse - 1], 0.0)

    playin = (seed >= 7) & (seed <= 10)
    return {"v_new": v_new, "v_old": v_old, "playoff": playoff, "playin": playin,
            "group": group, "seed": seed}


def simulate_games(home: np.ndarray, away: np.ndarray, r: np.ndarray, home_adv: float,
                   N: int, rng) -> np.ndarray:
    """Outcomes (N, n_games) of remaining games: 1 = home win. r is (N, 30) or (30,)."""
    rr = np.broadcast_to(r, (N, 30))
    p = sigmoid(rr[:, home] - rr[:, away] + home_adv)
    return (rng.random(p.shape) < p).astype(np.int8)


def incentives(W0: np.ndarray, home: np.ndarray, away: np.ndarray, r: np.ndarray, home_adv: float,
               pv: PickValues, N: int = 20_000, seed: int = 0, teams: list[str] | None = None) -> pd.DataFrame:
    """Simulate the rest of the season from wins W0 (30,) with remaining games (home, away).
    r: (30,) point ratings or (N, 30) sampled ratings. Returns one row per team.

    The toggle flips one of team i's remaining games (chosen at random per simulation): the 'lose'
    world credits the win to that game's opponent, the 'win' world charges the opponent the loss.
    Every other result is identical in the two worlds."""
    rng = np.random.default_rng(seed)
    out = simulate_games(home, away, r, home_adv, N, rng)
    W = np.tile(W0.astype(float), (N, 1))
    np.add.at(W.T, home, out.T)
    np.add.at(W.T, away, 1 - out.T)
    jitter = rng.random((N, 30)) * 0.5
    u = rng.random((N, 6))
    lot = rng.integers(0, pv.pool_size, N)
    base = evaluate(W + jitter, r, u, pv, home_adv, lot)
    rows = []
    ar = np.arange(N)
    for t in teams or TEAMS:
        i = IDX[t]
        mine = np.where((home == i) | (away == i))[0]
        if len(mine) == 0:
            continue
        g = mine[rng.integers(0, len(mine), N)]
        is_home = home[g] == i
        opp = np.where(is_home, away[g], home[g])
        won = np.where(is_home, out[ar, g], 1 - out[ar, g])
        Wlo = W.copy()
        Wlo[:, i] -= won           # i loses the game ...
        Wlo[ar, opp] += won        # ... and its opponent wins it
        Whi = Wlo.copy()
        Whi[:, i] += 1             # i wins the game ...
        Whi[ar, opp] -= 1          # ... and its opponent loses it
        lo = evaluate(Wlo + jitter, r, u, pv, home_adv, lot)
        hi = evaluate(Whi + jitter, r, u, pv, home_adv, lot)
        gcount = np.bincount(base["group"][:, i], minlength=5) / N
        rows.append({
            "team": t, "W0": W0[i], "exp_W": W[:, i].mean(),
            "dV_old": (lo["v_old"][:, i] - hi["v_old"][:, i]).mean(),
            "dV_new": (lo["v_new"][:, i] - hi["v_new"][:, i]).mean(),
            "dPlayoff": (hi["playoff"][:, i].astype(float) - lo["playoff"][:, i]).mean(),
            "dPlayin": (hi["playin"][:, i].astype(float) - lo["playin"][:, i]).mean(),
            "EV_old": base["v_old"][:, i].mean(), "EV_new": base["v_new"][:, i].mean(),
            "P_playoff": base["playoff"][:, i].mean(),
            "P_rel": gcount[1], "P_np3": gcount[2], "P_pi910": gcount[3], "P_pi78": gcount[4],
        })
    return pd.DataFrame(rows).set_index("team")


def fit_ratings(games: pd.DataFrame, C: float = 1.0) -> tuple[np.ndarray, float]:
    """Ridge-penalized Bradley-Terry (logistic) ratings with a home-court intercept."""
    from sklearn.linear_model import LogisticRegression
    X = np.zeros((len(games), 30))
    X[np.arange(len(games)), games.home.map(IDX).to_numpy()] = 1
    X[np.arange(len(games)), games.away.map(IDX).to_numpy()] = -1
    m = LogisticRegression(C=C, fit_intercept=True, max_iter=1000).fit(X, games.home_win)
    return m.coef_[0], float(m.intercept_[0])
