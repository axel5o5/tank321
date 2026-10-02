# Reproduction

[Back to README](../README.md) · [Methods and assumptions](METHODS.md) · [Current validation boundary](CLEANUP.md)

## Environment

Use CPython 3.13.7 on macOS arm64 to match the tested runtime: NumPy 2.4.2, pandas 3.0.1, SciPy 1.17.1, scikit-learn 1.8.0 and matplotlib 3.10.8.

The three dependency files serve different purposes:

- [requirements-release.lock](../requirements-release.lock): exact hashed runtime dependency snapshot for CPython 3.13/macOS arm64. It is neither a universal cross-platform lock nor a build-tool lock.
- [requirements-release.txt](../requirements-release.txt): direct dependency pins, not the complete hashed transitive environment.
- [requirements.txt](../requirements.txt): broader original minimums; these are not the validated environment.

Run these commands from the repository root:

```sh
python3.13 -m venv .venv
.venv/bin/python -m pip install --require-hashes --only-binary=:all: -r requirements-release.lock
.venv/bin/python -m pip check
.venv/bin/python -I -B run_checks.py
```

A fresh hashed, wheel-only dependency install and `pip check` passed during the current cleanup. See the [current validation boundary](CLEANUP.md) and [historical validation record](../VALIDATION.md) for the tested scope and earlier installation limits.

## Regenerate artifacts from deposited results

```sh
.venv/bin/python -I -B reproduce.py
# Optional separate destination and explicit curve cache:
.venv/bin/python -I -B reproduce.py --output-dir outputs/my-run --value-cache results/pick_values.csv
```

[reproduce.py](../reproduce.py) defaults to deposited replay/projection CSVs in `results/` and the explicit deposited curve cache `results/pick_values.csv`. It runs `headline.py`, `table1.py`, `figure1.py` and `mc_uncertainty.py`, writing their outputs and a local matplotlib cache to `outputs/`. This requires no credentials or undeclared baseline and does not reconstruct raw data. Headline generation still performs million-draw lottery calculations; it is not a full-season rerun. SVG timestamps and generated element identifiers can vary.

`--output-dir` must not overlap published `results/` in either direction. The wrapper also rejects existing symbolic or hard links inside the destination. Existing generated files there may be overwritten. Prefer `outputs/` or an external directory: the integrity checker excludes root `outputs/`, but an arbitrary new directory inside the repository counts as payload.

The combined check-and-artifact command uses the same safe wrapper:

```sh
.venv/bin/python -I -B run_checks.py --artifacts
.venv/bin/python -I -B run_checks.py --artifacts --output-dir outputs/checked
```

The checks disable Python socket connect/DNS/bind operations, verify project-module origins, test scientific invariants and deposited keys/counts/finite values, check manuscript arithmetic, and run a small deterministic cached-curve replay. They do not rerun the full historical or prospective simulations.

For individual artifact scripts (run from the root):

```sh
.venv/bin/python headline.py --value-cache results/pick_values.csv --input-dir results --output-dir outputs
.venv/bin/python table1.py --input-dir results --output-dir outputs
.venv/bin/python figure1.py --input-dir results --output-dir outputs
.venv/bin/python mc_uncertainty.py --input-dir results --output-dir outputs
```

These scripts default to `results/` inputs and `outputs/` outputs. Use the wrapper for its output-path protections.

## Full simulations (expensive)

```sh
.venv/bin/python -I -B reproduce.py --full --output-dir outputs/full
```

`--full` first runs historical replays and prospective simulations with their original scientific defaults, using deposited games and the curve cache. It then generates artifacts from the newly written simulation CSVs, not from the old deposited simulations. The default `--value-cache` remains `results/pick_values.csv`; full reproduction is still not raw-source reconstruction.

Equivalent model-only commands are:

```sh
.venv/bin/python replay.py --value-cache results/pick_values.csv --output-dir outputs/full
.venv/bin/python project_2026_27.py --value-cache results/pick_values.csv --output-dir outputs/full
```

After model-only runs, regenerate artifacts with the individual commands above, changing `--input-dir` and `--output-dir` to `outputs/full`. Running default `reproduce.py` instead would read the deposited simulations again. Full runs can take substantially longer than the bounded checks; scientific defaults are listed in [METHODS.md](METHODS.md).

[build_games.py](../build_games.py) and the raw-data functions in [value.py](../value.py) document original transformations but require upstream raw files deliberately absent from this deposit. Unlike the wrapper, directly invoking replay, projection or headline scripts without `--value-cache` requests raw curve reconstruction and will fail without those files. Deposited-curve reproduction does not independently reconstruct or validate the curves against upstream player data.

## Integrity and CI

```sh
.venv/bin/python -I -B -m unittest discover -s tests/integrity -v
.venv/bin/python -I -B tools/check_integrity.py
```

The standard-library-only checker compares file bytes and inventory with [SHA256SUMS](../SHA256SUMS) and [RELEASE_MANIFEST.json](../RELEASE_MANIFEST.json). It needs neither Git nor third-party packages. The manifest records included files, source hashes, settings and provenance; checksums cover payload files except `SHA256SUMS` itself. Local outputs, environments and caches are excluded. This is consistency checking, not authenticity: the checksum file is unsigned. Any payload edits require a corresponding integrity-metadata refresh and snapshot check.

The [GitHub Actions workflow](../.github/workflows/checks.yml) specifies `macos-15`, arm64, and Python 3.13.7, with an explicit runtime-platform assertion. It runs integrity tests and the snapshot checker, installs hashed runtime wheels, runs `pip check` and offline bounded checks, then checks snapshot integrity again. Hosted CI has not yet run for this cleanup; configuration is not evidence of a successful hosted install or run.
