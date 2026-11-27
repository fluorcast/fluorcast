"""Heatmaps showing which model is best in which case.

Two modes share one heatmap style (rows = cases, columns = models, the best
model in each row marked with a star and an outline):

region
    Emission error by spectral region (UV, blue, green, yellow/orange, red/NIR)
    from ``error_by_region_comparison.csv`` written by the baseline job. Cell
    text is the MAE in nm; colour is how much worse than the best model in that
    row (0% = best). A bottom row gives the overall test-set MAE.

    python scripts/plot_model_comparison_heatmaps.py region \
        --input outputs/model_experiments_fluodb/error_by_region_comparison.csv

case-study
    Absorption, emission and quantum-yield error per case-study dye from
    ``measured_vs_predicted.csv`` written by ``run_case_study_baseline.py``.
    Cell text is the signed error (predicted - measured); colour is the absolute
    error. A bottom row gives each model's mean absolute error.

    python scripts/plot_model_comparison_heatmaps.py case-study \
        --input outputs/case_studies/baseline/measured_vs_predicted.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

# One-hue sequential ramp (light = good / small error, dark = bad / large error).
RAMP = ["#f4f8fd", "#cce3fd", "#9dc8f7", "#6aabf1", "#338ced", "#2370cd", "#1757ac", "#0e3d7e"]
CMAP = LinearSegmentedColormap.from_list("seq_blue", RAMP)
TEXT_PRIMARY = "#191919"
TEXT_SECONDARY = "#666666"
SURFACE = "#ffffff"
BEST_OUTLINE = "#191919"

MODEL_ORDER = ["rf", "extratrees", "histgb", "gbdt", "mlp", "hybrid"]
MODEL_LABELS = {"rf": "RF", "extratrees": "ExtraTrees", "histgb": "HistGB", "gbdt": "GBDT", "mlp": "MLP", "hybrid": "Hybrid"}
REGION_ORDER = ["UV", "blue", "green", "yellow/orange", "red/NIR"]
REGION_LABELS = {
    "UV": "UV  (<400 nm)",
    "blue": "Blue  (400–500)",
    "green": "Green  (500–550)",
    "yellow/orange": "Yellow/orange  (550–600)",
    "red/NIR": "Red/NIR  (≥600)",
}


def ordered_models(models: list[str]) -> list[str]:
    known = [m for m in MODEL_ORDER if m in models]
    return known + sorted(m for m in models if m not in MODEL_ORDER)


def text_color_for(value01: float) -> str:
    return SURFACE if value01 > 0.55 else TEXT_PRIMARY


def draw_heatmap(
    ax: plt.Axes,
    color_values: np.ndarray,
    cell_text: list[list[str]],
    row_labels: list[str],
    col_labels: list[str],
    best_cols: list[int | None],
    vmax: float,
    summary_rows: int = 0,
) -> None:
    """Draw a heatmap; the last ``summary_rows`` rows are set apart below a gap."""
    n_rows, n_cols = color_values.shape
    gap = 0.35 if summary_rows else 0.0
    ax.set_facecolor(SURFACE)
    for r in range(n_rows):
        y = r + (gap if r >= n_rows - summary_rows else 0)
        for c in range(n_cols):
            v = color_values[r, c]
            frac = 0.0 if np.isnan(v) else min(v / vmax, 1.0) if vmax > 0 else 0.0
            face = "#f0f0f0" if np.isnan(v) else CMAP(frac)
            ax.add_patch(Rectangle((c + 0.04, y + 0.04), 0.92, 0.92, facecolor=face, edgecolor=SURFACE, linewidth=0))
            label = cell_text[r][c]
            is_best = best_cols[r] == c
            if is_best:
                label = f"★ {label}"
                ax.add_patch(Rectangle((c + 0.04, y + 0.04), 0.92, 0.92, fill=False, edgecolor=BEST_OUTLINE, linewidth=2))
            ax.text(c + 0.5, y + 0.5, label, ha="center", va="center", fontsize=10,
                    fontweight="bold" if is_best else "normal",
                    color=TEXT_SECONDARY if np.isnan(v) else text_color_for(frac))
    ax.set_xlim(0, n_cols)
    ax.set_ylim(n_rows + gap, 0)
    ax.set_xticks([c + 0.5 for c in range(n_cols)])
    ax.set_xticklabels(col_labels, fontsize=10, color=TEXT_PRIMARY)
    ax.xaxis.tick_top()
    ax.set_yticks([r + 0.5 + (gap if r >= n_rows - summary_rows else 0) for r in range(n_rows)])
    ax.set_yticklabels(row_labels, fontsize=10, color=TEXT_PRIMARY)
    ax.tick_params(length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)


def add_colorbar(fig: plt.Figure, ax, vmax: float, label: str, fmt: str) -> None:
    sm = plt.cm.ScalarMappable(cmap=CMAP, norm=plt.Normalize(0, vmax))
    cbar = fig.colorbar(sm, ax=ax, orientation="horizontal", fraction=0.05, pad=0.04, aspect=40)
    cbar.outline.set_visible(False)
    cbar.ax.tick_params(labelsize=9, colors=TEXT_SECONDARY, length=0)
    cbar.ax.xaxis.set_major_formatter(matplotlib.ticker.FormatStrFormatter(fmt))
    cbar.set_label(label, fontsize=9, color=TEXT_SECONDARY)


def run_region(args: argparse.Namespace) -> Path:
    df = pd.read_csv(args.input)
    models = ordered_models(df["model"].unique().tolist())
    regions = [r for r in REGION_ORDER if r in set(df["wavelength_region"])]
    mae = df.pivot(index="wavelength_region", columns="model", values="mean_absolute_error").reindex(index=regions, columns=models)
    counts = df.groupby("wavelength_region")["rows"].first().reindex(regions)
    # Regions partition the test set, so the row-weighted mean equals the overall test MAE.
    weighted = df.assign(w=df["rows"] * df["mean_absolute_error"]).groupby("model")[["w", "rows"]].sum()
    overall = (weighted["w"] / weighted["rows"]).reindex(models)
    table = pd.concat([mae, overall.to_frame().T.set_axis(["All regions"])])

    best = table.min(axis=1)
    pct_worse = (table.sub(best, axis=0)).div(best, axis=0) * 100
    best_cols = [int(np.nanargmin(row.to_numpy())) for _, row in table.iterrows()]
    cell_text = [[f"{v:.1f}" for v in row] for row in table.to_numpy()]
    row_labels = [f"{REGION_LABELS.get(r, r)}   n={int(counts[r]):,}" for r in regions] + [f"All regions   n={int(counts.sum()):,}"]

    vmax = args.vmax
    fig, ax = plt.subplots(figsize=(2.0 + 1.35 * len(models) + 2.2, 0.62 * len(table) + 2.4), facecolor=SURFACE)
    draw_heatmap(ax, pct_worse.to_numpy(), cell_text, row_labels, [MODEL_LABELS.get(m, m) for m in models],
                 best_cols, vmax, summary_rows=1)
    add_colorbar(fig, ax, vmax, f"% worse than the best model in that row (capped at {vmax:.0f}%)", "%.0f%%")
    fig.suptitle("Emission error (MAE, nm) by spectral region — ★ = best model per row",
                 x=0.01, ha="left", fontsize=12.5, color=TEXT_PRIMARY)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    out = args.out or args.input.with_name("region_error_heatmap.png")
    fig.savefig(out, dpi=200, facecolor=SURFACE)
    return out


# (title, measured col, predicted col, signed format, mean format, colour cap or None)
# The cap keeps one extreme miss from washing out the other cells; text still shows the true value.
CASE_PANELS = [
    ("Absorption (nm)", "experimental_absorption_nm", "predicted_absorption_nm", "{:+.0f}", "{:.1f}", 60.0),
    ("Emission (nm)", "experimental_emission_nm", "predicted_emission_nm", "{:+.0f}", "{:.1f}", 60.0),
    ("Quantum yield", "experimental_quantum_yield", "predicted_quantum_yield", "{:+.2f}", "{:.2f}", None),
]


def run_case_study(args: argparse.Namespace) -> Path:
    df = pd.read_csv(args.input)
    models = ordered_models(df["model"].unique().tolist())
    dyes = sorted(df["name"].unique().tolist(), key=lambda s: (len(s), s))
    solvents = df.groupby("name")["solvent_name"].first() if "solvent_name" in df.columns else None

    fig, axes = plt.subplots(1, len(CASE_PANELS), figsize=(4.6 * len(CASE_PANELS) + 1.2, 0.62 * (len(dyes) + 1) + 2.6),
                             facecolor=SURFACE, sharey=False)
    for i, (ax, (title, meas_col, pred_col, signed_fmt, mean_fmt, cap)) in enumerate(zip(axes, CASE_PANELS)):
        signed = (df[pred_col] - df[meas_col]).to_frame("err").assign(name=df["name"], model=df["model"])
        grid = signed.pivot(index="name", columns="model", values="err").reindex(index=dyes, columns=models)
        abs_grid = grid.abs()
        mean_row = abs_grid.mean(axis=0)
        color_table = pd.concat([abs_grid, mean_row.to_frame().T.set_axis(["Mean |error|"])])
        cell_text = [[signed_fmt.format(v) for v in row] for row in grid.to_numpy()]
        cell_text.append([mean_fmt.format(v) for v in mean_row.to_numpy()])
        best_cols = [int(np.nanargmin(row.to_numpy())) for _, row in color_table.iterrows()]
        if i == 0:
            labels = [f"{d}  ({solvents[d]})" if solvents is not None else d for d in dyes] + ["Mean |error|"]
        else:
            labels = [""] * (len(dyes) + 1)
        data_max = float(np.nanmax(abs_grid.to_numpy())) or 1.0
        vmax = min(data_max, cap) if cap else data_max
        draw_heatmap(ax, color_table.to_numpy(), cell_text, labels, [MODEL_LABELS.get(m, m) for m in models],
                     best_cols, vmax, summary_rows=1)
        ax.set_title(title, loc="left", fontsize=11.5, color=TEXT_PRIMARY, pad=28)
        bar_label = f"absolute error (colour capped at {cap:.0f})" if cap and data_max > cap else "absolute error"
        add_colorbar(fig, ax, vmax, bar_label, "%.2f" if "yield" in title.lower() else "%.0f")

    fig.suptitle("Case-study dyes: error per model (predicted − measured) — ★ = closest model per dye",
                 x=0.01, ha="left", fontsize=12.5, color=TEXT_PRIMARY)
    fig.text(0.01, 0.005, f"Only {len(dyes)} dyes — illustrates behaviour; choose the reference model from the full test set, not from this figure.",
             fontsize=9, color=TEXT_SECONDARY)
    fig.tight_layout(rect=(0, 0.03, 1, 0.94))
    out = args.out or args.input.with_name("case_study_error_heatmap.png")
    fig.savefig(out, dpi=200, facecolor=SURFACE)
    return out


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="mode", required=True)
    region = sub.add_parser("region", help="Emission MAE by spectral region.")
    region.add_argument("--input", type=Path, default=Path("outputs/model_experiments_fluodb/error_by_region_comparison.csv"))
    region.add_argument("--vmax", type=float, default=100.0, help="Cap for the '%% worse than best' colour scale.")
    region.add_argument("--out", type=Path, default=None)
    case = sub.add_parser("case-study", help="Per-dye error for every model.")
    case.add_argument("--input", type=Path, default=Path("outputs/case_studies/baseline/measured_vs_predicted.csv"))
    case.add_argument("--out", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out = run_region(args) if args.mode == "region" else run_case_study(args)
    print(f"Saved {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
