# Relegating the Tank: Where the NBA's 3-2-1 Lottery Moves the Incentive to Lose

## Introduction
The NBA's 2027-2029 3-2-1 lottery expands to 16 teams, with fewer balls for the three worst records. Building on draft-design theory (Banchio & Munro, SSAC 2020), we quantify how this reform redistributes marginal draft-value incentives across teams and competitive states.

## Methods
We simulate both lotteries with an assumed implementation of 3-2-1's No. 12 floor; 2027 projections apply consecutive-pick restrictions jointly. Pick values use Win Shares in the first four post-draft seasons (Basketball-Reference, 1995-2022 drafts), with career Win Shares and All-NBA rates as checks. At the 2024-2026 All-Star breaks, Bradley-Terry ratings from pre-break games drive 40,000 simulations of remaining games, play-in and draft. Incentive is expected retained draft value gained by losing rather than winning one game, pairing otherwise identical regular-season outcomes and accounting for specified pick obligations. Out-of-contention teams have below 10% modeled playoff probability; bubble teams have 10-90%. Prospective simulations use BetMGM and Kalshi totals with a synthetic schedule.

## Results
Without consecutive-pick restrictions, the three worst teams expect pick 8.1 under 3-2-1 versus 7.5 for other non-play-in teams; the old lottery's worst team expects 3.7.

Across 32 out-of-contention team-seasons, old-lottery incentive correlates with post-break shortfall, defined as projected minus observed regular-season wins (Spearman rho = 0.42, nominal p = 0.015; Figure 1B). Adjusting for pre-break win percentage weakens this exploratory association (partial rho = 0.32, nominal p = 0.08). These tests do not account for team-season dependence or establish causation.

Excluding owed picks and negligible exposure (both absolute incentives below 0.001), mean incentive across 29 out-of-contention team-seasons falls from 0.30 to -0.003 Win Shares per game, reversing sign for some teams. Across 18 bubble team-seasons it rises from 0.35 to 0.53 (+51%). Mean shifts persist under both alternative value curves. Median break-even playoff-berth value (draft gain/playoff-probability loss) rises from 3.0 to 5.9 Win Shares.

For 2026-27, the bottom eight teams' mean incentive falls 89-95% across market scenarios. Indiana, Toronto and Orlando have the largest 3-2-1 point estimates under both market scenarios (Table 1).

## Conclusion
Average modeled draft incentives shift toward the playoff bubble. This supports rule comparison, not a prediction of intentional losing. Code and data: https://github.com/axel5o5/tank321.

**Table 1. BetMGM 2026-27 point estimates (WS/game), all picks fully owned: top six 3-2-1 incentives with P(playoffs)<90%, plus owners among bottom-eight win totals.**

| Team | Win total | 3-2-1 | Old rules |
|---|---|---|---|
| IND | 44.5 | 0.36 | 0.25 |
| TOR | 45.5 | 0.35 | 0.25 |
| ORL | 43.5 | 0.34 | 0.28 |
| POR | 42.5 | 0.31 | 0.28 |
| DET | 49.5 | 0.30 | 0.19 |
| CHA | 39.5 | 0.30 | 0.35 |
| CHI | 29.5 | 0.01 | 0.32 |
| MEM | 29.5 | 0.07 | 0.33 |
| SAC | 21.5 | -0.04 | 0.14 |

![Figure 1](results/figure1.png)

*Figure 1. A: 2025-26 paired lottery incentives. B: old-lottery incentive versus post-break shortfall.*
