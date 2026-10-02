# Relegating the Tank

Research code and selected derived inputs for **Where the NBA's 3-2-1 Lottery Moves the Incentive to Lose**. The model compares expected retained first-round draft value from losing versus winning one remaining regular-season game under the old and 3-2-1 lottery rules.

The deposited results support the accompanying [abstract](abstract.md), [Table 1](results/table1.md), and [Figure 1](results/figure1.png). Repository: [github.com/axel5o5/tank321](https://github.com/axel5o5/tank321).

## What the results mean

Historical replays use observed 2023-24, 2024-25 and 2025-26 regular-season game results. Old/new incentive estimates are paired **model counterfactuals**, not observed responses to a changed rule. Prospective 2026-27 break states and schedules are **synthetic**, constructed from dated market win totals; they are not actual 2026-27 game outcomes or a public preregistration.

Across 32 modeled out-of-contention historical team-seasons, the association between old-lottery incentive and post-break shortfall is Spearman rho 0.42 (nominal p 0.015). Adjustment for pre-break win percentage gives partial rho 0.32 (nominal p 0.08). These exploratory, noncausal tests do not account for team-season dependence.

Excluding owed picks and negligible exposure, mean incentive across 29 out-of-contention team-seasons changes from 0.30 to -0.003 Win Shares per game; across 18 bubble team-seasons it changes from 0.35 to 0.53 (+51%). The prospective bottom-eight mean decreases 89–95% across the two market scenarios. Indiana, Toronto and Orlando have the largest prospective point estimates under both scenarios; their exact ordering is not a claim of statistically separated ranks.

The announced No. 12 floor is modeled using an assumed forced-fill implementation in `lottery.py`; this is not a claim to know the NBA's full joint implementation. Consecutive-pick restrictions are applied jointly in prospective simulations (Washington cannot draw No. 1; Utah cannot draw Nos. 1–5). The ownership map covers **selected originating-pick obligations and linked rights, not a full asset portfolio**. Unlisted teams are assumed to own their picks. These are model assumptions, not independent ownership verification. Incoming assets, later picks, cash and second-round compensation are omitted except where explicitly modeled.

Synthetic schedule construction, market inputs, strength uncertainty, the floor mechanism and ownership assumptions limit interpretation. Conditional Monte Carlo standard errors describe finite simulation error only; they omit model, rule, source and real-world predictive uncertainty. These results compare rules and do not predict intentional losing.

## Reproduce from deposited inputs

Use Python 3.13.7. The tested runtime was CPython 3.13.7 on macOS arm64 with NumPy 2.4.2, pandas 3.0.1, SciPy 1.17.1, scikit-learn 1.8.0 and matplotlib 3.10.8. `requirements-release.lock` is the exact hashed runtime dependency snapshot for that platform; it is not a universal cross-platform or build-tool lock. `requirements-release.txt` supplies the direct pins; `requirements.txt` retains broader original minimums and is not the validated environment.

```sh
python3.13 -m venv .venv
.venv/bin/python -m pip install --require-hashes -r requirements-release.lock
.venv/bin/python -I -B run_checks.py
```

The checks require only this deposit and installed packages. They disable Python network connections, verify project-module origins, test synthetic scientific invariants, validate deposited dataset keys/counts/finite values, check manuscript arithmetic and run a small deterministic cached-curve replay. They do not rerun full historical or prospective simulations.

Run from the repository root to regenerate the paper's summary artifacts:

```sh
.venv/bin/python headline.py --value-cache results/pick_values.csv
.venv/bin/python table1.py
.venv/bin/python figure1.py
.venv/bin/python mc_uncertainty.py
```

Alternatively, `python -I -B run_checks.py --artifacts` combines the bounded checks with headline/table/figure generation. Figure SVG timestamps and generated element identifiers can vary. Headline generation includes one million lottery draws, but no full-season rerun.

The full model commands below use deposited historical games and aggregate value curves, and require **no credentials or private baseline**. They can take substantially longer and overwrite the corresponding result tables; regenerate headline/table/figure afterwards.

```sh
.venv/bin/python replay.py --value-cache results/pick_values.csv
.venv/bin/python project_2026_27.py --value-cache results/pick_values.csv
```

Historical defaults: 40,000 season simulations, ridge parameter C=1, seed 0, three seasons and three curves. Forward defaults: 150 synthetic break states per market source, 4,000 inner simulations per state, seed 7, strength sigma 0.25, home advantage 0.222, break fraction 2/3; the all-picks-owned sensitivity uses 100 states. Lottery draws use seed 11 (old), seed 12 (unrestricted new), and deterministic configuration-specific seeds for joint restrictions; there are 250,000 draws per conditional configuration at the default one-million-draw initialization.

`build_games.py` and the raw-data functions in `value.py` document the original transformations. They require upstream raw files that are deliberately absent. Omitting `--value-cache` invokes raw curve reconstruction and will fail without those files. Reproducing models from deposited curves does **not** independently reconstruct or validate those curves against upstream player data.

## Inputs, licensing and integrity

[DATA_SOURCES.md](DATA_SOURCES.md) records provenance and the data dictionary. BetMGM inputs are dated September 23, 2026; Kalshi projections via SBR are dated July 29, 2026, as recorded in the original script. This deposit makes no claim of an independent fresh quote audit.

Original code and documentation are MIT licensed; see [LICENSE](LICENSE). The author separately authorized these selected derived game results, aggregate pick-value curves, dated market inputs and simulation outputs for release. This does not relicense underlying third-party material or guarantee satisfaction of every source's terms; source-specific notices and obligations remain. See [DATA_NOTICE.md](DATA_NOTICE.md).

`RELEASE_MANIFEST.json` identifies included files, source hashes, settings and provenance without private paths; `SHA256SUMS` hashes every release file except itself. Raw player/PBP mirrors, provider captures, credentials, private notes/reviews, internal instructions, private baselines and internal research history are excluded. Public release does not imply conference acceptance, complete raw-source reconstruction, or validated intentional-losing behavior.
