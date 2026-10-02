# Methods, settings and interpretation

[Back to README](../README.md) · [Reproduction](REPRODUCTION.md)

## Question and evidence

The model compares expected retained first-round draft value from losing versus winning one remaining regular-season game under the old and 3-2-1 lottery rules. Positive incentive means losing increases modeled retained value; negative incentive means losing decreases it. Win Share curves measure value per game in Win Shares; the `star` curve measures All-NBA rate, not Win Shares.

Historical replays use observed 2023–24, 2024–25 and 2025–26 regular-season game results, all played under the old lottery. Old/new estimates are paired model counterfactuals, not observed responses to a rule change. Prospective 2026–27 break states and schedules are synthetic, constructed from dated market win totals; they are not actual game outcomes or a public preregistration.

Across 32 modeled out-of-contention historical team-seasons, old-lottery incentive and post-break shortfall have Spearman rho 0.42 (nominal p 0.015). Adjustment for pre-break win percentage gives partial rho 0.32 (nominal p 0.08). These exploratory, noncausal tests do not account for team-season dependence.

Excluding owed picks and negligible exposure, mean incentive across 29 out-of-contention team-seasons changes from 0.30 to −0.003 Win Shares per game; across 18 bubble team-seasons it changes from 0.35 to 0.53 (+51%). The prospective bottom-eight mean decreases 89–95% across the two market scenarios. Indiana, Toronto and Orlando have the largest prospective point estimates under both scenarios; their exact ordering is not a claim of statistically separated ranks.

## Scientific defaults

The cleanup leaves these settings unchanged:

| Component | Defaults |
|---|---|
| Historical replay | 40,000 season simulations; ridge parameter C=1; seed 0; three seasons and three curves (`ws4`, `ws_car`, `star`) |
| Prospective projection | Primary `ws4` curve; 150 synthetic break states per market source; 4,000 inner simulations per state; seed 7; strength sigma 0.25; home advantage 0.222; break fraction 2/3 |
| All-picks-owned sensitivity | BetMGM source; 100 synthetic states; full ownership assumed |
| Model lottery caches | One-million-draw initialization; seed 11 for old and 12 for unrestricted new; deterministic configuration-specific seeds for joint restrictions; 250,000 draws per conditional configuration at the default initialization |

Historical ratings are fit to pre-break results; the largest gap between game dates identifies the break. Prospective schedules contain 82 games per team and are synthetic rather than actual schedules. Market totals are rescaled to 1,230 league wins for rating calibration; deposited market inputs retain the original unscaled numbers. See [replay.py](../replay.py), [project_2026_27.py](../project_2026_27.py) and [sim.py](../sim.py) for implementation.

## Rule and ownership assumptions

The announced No. 12 floor uses an assumed forced-fill implementation in [lottery.py](../lottery.py); this is not a claim to know the NBA's full joint implementation. Consecutive-pick restrictions are applied jointly in prospective simulations: Washington cannot draw No. 1, and Utah cannot draw Nos. 1–5.

The [ownership map](../ownership.py) covers selected originating-pick obligations and linked rights, not a full asset portfolio. Unlisted teams are assumed to own their picks. These are model assumptions, not independent ownership verification. Incoming assets, later picks, cash and second-round compensation are omitted except where explicitly modeled. Source annotations include HoopsRumors, CBS Sports, RotoWire, Third Apron and cited NBA transaction releases.

## Inputs and provenance

The [data provenance and dictionary](../DATA_SOURCES.md) describe transformations, units, cohort definitions and coverage. Historical derived games trace to NBA CDN play-by-play via [shufinskiy/nba_data](https://github.com/shufinskiy/nba_data); aggregate draft-value curves trace to Basketball-Reference-derived data via [sumitrodatta/bball-reference-datasets](https://github.com/sumitrodatta/bball-reference-datasets). Original transformations are documented in [build_games.py](../build_games.py) and [value.py](../value.py).

Curves use weighted decreasing isotonic smoothing. `ws4` covers first-four-season Win Shares for drafts 1995–2022 (unplayed seasons count as zero); `ws_car` covers career Win Shares through the recorded 2025–26 cutoff for drafts 1995–2016; `star` covers at least one All-NBA selection for drafts 1995–2018. Deposited curves include 60 positions; models use positions 1–30. Using these aggregates does not independently verify player matching, historical coverage or raw source revisions.

BetMGM inputs are dated September 23, 2026; Kalshi projections via Sportsbook Review are dated July 29, 2026, as recorded in the original script. No independent fresh quote audit is claimed. The exported market CSV matches the script's `WIN_TOTALS` constants.

Original software and documentation are [MIT licensed](../LICENSE). The author separately authorized the selected derived game results, aggregate pick-value curves, dated market inputs and simulation outputs. This does not relicense underlying third-party material or guarantee satisfaction of every source's terms. Source-specific obligations remain; see [DATA_NOTICE.md](../DATA_NOTICE.md).

## Limits

Synthetic schedule construction, market inputs, strength uncertainty, the floor mechanism and ownership assumptions limit interpretation. Conditional Monte Carlo standard errors describe finite simulation error only, conditional on fixed lottery caches, specified market values, one synthetic schedule and other model choices. They omit shared-cache, model, rule, source and real-world predictive uncertainty. They are not confidence intervals for real-world behavior, and top point estimates are not confidently separated ranks.

These results compare lottery rules; they do not predict intentional losing. Bounded checks do not establish causal validity, complete raw-source reconstruction, independent ownership verification, source-rights clearance or conference acceptance. See [the cleanup validation boundary](CLEANUP.md) and [historical validation](../VALIDATION.md).
