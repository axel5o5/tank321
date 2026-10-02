"""Offline deposited-input reproduction (not raw-source reconstruction).

By default regenerate headline, table, figure and conditional Monte Carlo error
from deposited results. --full first reruns the expensive replay and prospective
simulations with their original scientific defaults, then uses those new CSVs.
The pick-value curve is explicitly read from results/pick_values.csv by default.
Published results are never an allowed output destination through this wrapper.
"""
import argparse
import os
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
ARTIFACTS = ("headline.py", "table1.py", "figure1.py", "mc_uncertainty.py")
MODEL_INPUTS = (
    *(f"replay_{w}.csv" for w in ("ws4", "ws_car", "star")),
    *(f"proj_2026_27_{s}.csv" for s in ("betmgm", "kalshi", "betmgm_ownall")),
    *(f"proj_2026_27_{s}_states.csv" for s in ("betmgm", "kalshi")),
)


def safe_output_dir(path):
    """Reject overlapping paths and existing links before any generation starts."""
    output = Path(path).resolve()
    reference = RESULTS.resolve()
    if output.is_relative_to(reference) or reference.is_relative_to(output):
        raise ValueError("--output-dir must not overlap published results/; use outputs/ or a separate directory")
    if output.exists():
        if not output.is_dir():
            raise ValueError("--output-dir must be a directory")
        for entry in output.rglob("*"):
            if entry.is_symlink() or (entry.is_file() and entry.stat().st_nlink > 1):
                raise ValueError("--output-dir must not contain symbolic or hard links; use a separate directory")
    return output


def run_script(script, argv):
    previous = sys.argv
    try:
        sys.argv = [script, *map(str, argv)]
        runpy.run_path(str(ROOT / script), run_name="__main__")
    finally:
        sys.argv = previous


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full", action="store_true", help="Rerun expensive simulations before artifacts")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "outputs")
    parser.add_argument("--value-cache", type=Path, default=RESULTS / "pick_values.csv",
                        help="Explicit deposited pick-value CSV (default: results/pick_values.csv)")
    args = parser.parse_args(argv)
    try:
        output = safe_output_dir(args.output_dir)
        cache = args.value_cache.resolve()
        if not cache.is_file():
            raise FileNotFoundError(f"Deposited pick-value CSV missing: {cache}; restore results/pick_values.csv")
        from value import value_vector
        for window in ("ws4", "ws_car", "star"):
            value_vector(window, cache_path=cache)
        required = ([ROOT / "data" / f"games_{y}_{str(y + 1)[2:]}.csv" for y in (2023, 2024, 2025)]
                    if args.full else [RESULTS / name for name in MODEL_INPUTS])
        missing = [str(path) for path in required if not path.is_file()]
        if missing:
            raise FileNotFoundError("Deposited inputs missing: " + ", ".join(missing) +
                                    "; restore the public deposit before reproducing")
        output.mkdir(parents=True, exist_ok=True)
        previous_cwd = Path.cwd()
        previous_mpl = os.environ.get("MPLCONFIGDIR")
        try:
            os.chdir(ROOT)
            os.environ["MPLCONFIGDIR"] = str(output / ".matplotlib")
            if args.full:
                for script in ("replay.py", "project_2026_27.py"):
                    run_script(script, ["--value-cache", cache, "--output-dir", output])
            inputs = output if args.full else RESULTS
            for script in ARTIFACTS:
                options = ["--input-dir", inputs, "--output-dir", output]
                if script == "headline.py":
                    options += ["--value-cache", cache]
                run_script(script, options)
        finally:
            os.chdir(previous_cwd)
            if previous_mpl is None:
                os.environ.pop("MPLCONFIGDIR", None)
            else:
                os.environ["MPLCONFIGDIR"] = previous_mpl
    except (OSError, ValueError, KeyError) as exc:
        parser.error(str(exc))
    print(f"Generated {'full simulation and ' if args.full else ''}artifacts in {output}")
    return 0


if __name__ == "__main__":
    # Also support python -I -B reproduce.py without relying on caller PYTHONPATH.
    sys.path.insert(0, str(ROOT))
    raise SystemExit(main())
