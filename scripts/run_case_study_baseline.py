"""Predict the lab case-study fluorophores with the trained baseline models.

Runs ``scripts/predict_all_models.py`` once per molecule (it already loads every
trained tree/neural/graph model it finds) and merges the results with the
measured values into one measured-vs-predicted table.

Example (from the repo root on Nibi):

    python scripts/run_case_study_baseline.py \
        --out-dir outputs/case_studies/baseline
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PREDICTOR = PROJECT_ROOT / "scripts" / "predict_all_models.py"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--molecules",
        type=Path,
        default=Path("inputs/case_studies/zhao_fluorophores.csv"),
        help="CSV with name, smiles, solvent_smiles.",
    )
    parser.add_argument(
        "--reference",
        type=Path,
        default=Path("inputs/case_studies/zhao_reference.csv"),
        help="CSV with measured values (experimental_*).",
    )
    parser.add_argument("--tree-model-dir", type=Path, default=Path("models/experiments_fluodb"))
    parser.add_argument(
        "--models",
        default="rf,extratrees,histgb,gbdt",
        help="Comma-separated models to keep in the summary table ('all' keeps every model found).",
    )
    parser.add_argument("--out-dir", type=Path, default=Path("outputs/case_studies/baseline"))
    parser.add_argument(
        "--label-prefix",
        default="Dye",
        help="Relabel molecules in all outputs as <prefix>_1, <prefix>_2, ... (input row order). "
        "Pass an empty string to keep the names from the input CSV.",
    )
    return parser.parse_args()


def predict_one(row: pd.Series, ref: pd.Series | None, args: argparse.Namespace) -> pd.DataFrame:
    out_csv = args.out_dir / "per_molecule" / f"{row['name']}.csv"
    cmd = [
        sys.executable,
        str(PREDICTOR),
        "--smiles", str(row["smiles"]),
        "--solvent-smiles", str(row["solvent_smiles"]),
        "--tree-model-dir", str(args.tree_model_dir),
        "--out", str(out_csv),
    ]
    if ref is not None:
        for flag, col in [
            ("--known-absorption-nm", "experimental_absorption_nm"),
            ("--known-emission-nm", "experimental_emission_nm"),
            ("--known-quantum-yield", "experimental_quantum_yield"),
        ]:
            if pd.notna(ref.get(col)):
                cmd += [flag, str(ref[col])]

    print(f"\n=== {row['name']} ({row['solvent_smiles']}) ===", flush=True)
    result = subprocess.run(cmd, cwd=PROJECT_ROOT, text=True, capture_output=True)
    log = args.out_dir / "per_molecule" / f"{row['name']}.log"
    log.write_text(result.stdout + "\n--- stderr ---\n" + result.stderr, encoding="utf-8")
    if result.returncode != 0 or not out_csv.exists():
        print(f"  FAILED (see {log}): {result.stderr.strip()[-300:]}", flush=True)
        return pd.DataFrame([{"name": row["name"], "status": "failed"}])

    table = pd.read_csv(out_csv)
    table.insert(0, "name", row["name"])
    table.insert(1, "solvent_smiles", row["solvent_smiles"])
    table["status"] = "ok"
    print(f"  ok: {len(table)} model rows", flush=True)
    return table


def main() -> int:
    args = parse_args()
    (args.out_dir / "per_molecule").mkdir(parents=True, exist_ok=True)

    molecules = pd.read_csv(PROJECT_ROOT / args.molecules if not args.molecules.is_absolute() else args.molecules)
    reference = pd.read_csv(PROJECT_ROOT / args.reference if not args.reference.is_absolute() else args.reference)
    if args.label_prefix:
        labels = {name: f"{args.label_prefix}_{i}" for i, name in enumerate(molecules["name"], start=1)}
        molecules["name"] = molecules["name"].map(labels)
        reference["name"] = reference["name"].map(labels)
        reference = reference.dropna(subset=["name"])
    ref_by_name = reference.set_index("name")

    frames = [
        predict_one(row, ref_by_name.loc[row["name"]] if row["name"] in ref_by_name.index else None, args)
        for _, row in molecules.iterrows()
    ]
    long = pd.concat(frames, ignore_index=True)
    long = long.merge(reference, on="name", how="left")
    long.to_csv(args.out_dir / "all_model_predictions.csv", index=False)

    ok = long[long["status"] == "ok"].copy()
    if args.models != "all" and "model" in ok.columns:
        keep = [m.strip() for m in args.models.split(",") if m.strip()]
        filtered = ok[ok["model"].isin(keep)]
        if filtered.empty and not ok.empty:
            print(f"Note: none of {keep} found; keeping all models {sorted(ok['model'].unique())}")
        else:
            ok = filtered

    cols = [
        "name", "solvent_name", "model",
        "experimental_absorption_nm", "predicted_absorption_nm", "absorption_abs_error_nm",
        "experimental_emission_nm", "predicted_emission_nm", "emission_abs_error_nm",
        "experimental_quantum_yield", "predicted_quantum_yield", "quantum_yield_abs_error",
        "nearest_training_similarity", "confidence_label", "outside_applicability_domain",
    ]
    summary = ok[[c for c in cols if c in ok.columns]]
    summary.to_csv(args.out_dir / "measured_vs_predicted.csv", index=False)

    # Average error per model across the molecules (what a chemist will ask first).
    err_cols = [c for c in ["absorption_abs_error_nm", "emission_abs_error_nm", "quantum_yield_abs_error"] if c in ok.columns]
    if err_cols and "model" in ok.columns:
        per_model = ok.groupby("model")[err_cols].mean().round(3).sort_values(err_cols[min(1, len(err_cols) - 1)])
        per_model.to_csv(args.out_dir / "mean_error_by_model.csv")
    else:
        per_model = pd.DataFrame()

    def as_markdown(frame: pd.DataFrame, index: bool) -> str:
        try:
            return frame.to_markdown(index=index)  # needs the optional 'tabulate' package
        except ImportError:
            return "```\n" + frame.to_string(index=index) + "\n```"

    md = ["# Case-study fluorophores: measured vs predicted (baseline models)", ""]
    md.append(as_markdown(summary.round(3), index=False))
    if not per_model.empty:
        md += ["", "## Mean absolute error per model (across molecules)", ""]
        md.append(as_markdown(per_model, index=True))
    failed = long[long["status"] != "ok"]["name"].tolist()
    if failed:
        md += ["", f"Failed molecules: {', '.join(failed)}"]
    (args.out_dir / "report.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print("\n" + summary.round(3).to_string(index=False))
    if not per_model.empty:
        print("\nMean absolute error per model:\n" + per_model.to_string())
    print(f"\nWrote results to {args.out_dir}/")
    return 1 if failed and len(failed) == len(molecules) else 0


if __name__ == "__main__":
    raise SystemExit(main())
