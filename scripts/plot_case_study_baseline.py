"""Plot measured vs predicted emission and quantum yield for the case-study dyes.

Reads the ``measured_vs_predicted.csv`` written by
``scripts/run_case_study_baseline.py`` and draws one row per dye with the
measured value and one model's prediction joined by a line (the gap is the error).

Example:

    python scripts/plot_case_study_baseline.py \
        --input outputs/case_studies/baseline/measured_vs_predicted.csv \
        --model rf
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

MEASURED_COLOR = "#257de0"   # categorical slot 1 (blue)
PREDICTED_COLOR = "#f47230"  # categorical slot 2 (orange)
TEXT_PRIMARY = "#191919"
TEXT_SECONDARY = "#666666"
GRID = "#e6e6e6"
SURFACE = "#ffffff"

PANELS = [
    ("experimental_emission_nm", "predicted_emission_nm", "Emission wavelength (nm)", "{:.0f} nm"),
    ("experimental_quantum_yield", "predicted_quantum_yield", "Quantum yield", "{:.2f}"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--input", type=Path, default=Path("outputs/case_studies/baseline/measured_vs_predicted.csv"))
    parser.add_argument("--model", default="rf", help="Model to plot (rf, extratrees, histgb, gbdt).")
    parser.add_argument("--out", type=Path, default=None, help="Output PNG (default: next to the input).")
    return parser.parse_args()


def style_axis(ax: plt.Axes) -> None:
    ax.set_facecolor(SURFACE)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(TEXT_SECONDARY)
    ax.tick_params(colors=TEXT_SECONDARY, labelsize=10, length=0)
    ax.grid(axis="x", color=GRID, linewidth=1)
    ax.set_axisbelow(True)


def main() -> int:
    args = parse_args()
    df = pd.read_csv(args.input)
    df = df[df["model"] == args.model].copy()
    if df.empty:
        raise SystemExit(f"No rows for model '{args.model}' in {args.input}")
    df = df.sort_values("name", ascending=False)  # Dye_1 at the top
    labels = [f"{n}  ({s})" if isinstance(s, str) else n for n, s in zip(df["name"], df.get("solvent_name", [None] * len(df)))]
    y = range(len(df))

    fig, axes = plt.subplots(1, 2, figsize=(11, 0.6 * len(df) + 1.6), sharey=True, facecolor=SURFACE)
    for ax, (meas_col, pred_col, title, fmt) in zip(axes, PANELS):
        style_axis(ax)
        meas = df[meas_col].to_numpy()
        pred = df[pred_col].to_numpy()
        for yi, m, p in zip(y, meas, pred):
            ax.plot([m, p], [yi, yi], color=TEXT_SECONDARY, linewidth=2, alpha=0.5, zorder=1, solid_capstyle="round")
        ax.scatter(meas, list(y), s=90, color=MEASURED_COLOR, edgecolor=SURFACE, linewidth=2, zorder=3, label="Measured")
        ax.scatter(pred, list(y), s=90, color=PREDICTED_COLOR, edgecolor=SURFACE, linewidth=2, zorder=3,
                   label=f"Predicted ({args.model.upper() if args.model == 'rf' else args.model})")
        span = max(max(meas), max(pred)) - min(min(meas), min(pred))
        for yi, m, p in zip(y, meas, pred):
            ax.annotate(f"error {fmt.format(abs(p - m))}", xy=(max(m, p), yi), xytext=(10, 0),
                        textcoords="offset points", va="center", fontsize=9, color=TEXT_SECONDARY)
        lo, hi = min(min(meas), min(pred)), max(max(meas), max(pred))
        if "quantum_yield" in meas_col:
            ax.set_xlim(-0.02, 1.32)  # QY is bounded 0-1; extra room is for the error labels
            ax.set_xticks([0, 0.2, 0.4, 0.6, 0.8, 1.0])
        else:
            ax.set_xlim(lo - 0.08 * span, hi + 0.32 * span)
        ax.set_title(title, loc="left", fontsize=12, color=TEXT_PRIMARY, pad=10)

    axes[0].set_yticks(list(y))
    axes[0].set_yticklabels(labels, color=TEXT_PRIMARY, fontsize=10)
    handles, legend_labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, legend_labels, loc="upper right", ncol=2, frameon=False, fontsize=10,
               labelcolor=TEXT_PRIMARY, bbox_to_anchor=(0.98, 0.99))
    fig.suptitle("Case-study dyes: measured vs predicted", x=0.01, ha="left", fontsize=14,
                 color=TEXT_PRIMARY, y=0.99)
    fig.tight_layout(rect=(0, 0, 1, 0.95))

    out = args.out or args.input.with_name(f"measured_vs_predicted_{args.model}.png")
    fig.savefig(out, dpi=200, facecolor=SURFACE)
    print(f"Saved {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
