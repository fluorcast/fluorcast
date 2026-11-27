# Rayan — FluorCast Run Log

Cluster: Nibi (Alliance / Compute Canada) · user `rayan` · account `def-yzhao`
Repo on Nibi: `~/scratch/FluorCast` (cloned from `github.com/fluorcast/fluorcast`)
Environment: `~/scratch/chemfluor_env` (python/3.11 + gcc + rdkit modules)

---

## 2026-11-21 — Setup on Nibi + baseline tree-model run

### Setup
- Generated SSH key on Nibi, added to GitHub; cloned org repo to `~/scratch/FluorCast`.
- Created venv `~/scratch/chemfluor_env`, installed `requirements.txt`; imports check `ALL OK`.
- Code version: `main @ ccee29b` (includes merged PRs #1 violin-graphs, #2 uniprop-3d, #3 reproducible-remote-provisioning).

### Test suite (`pytest -q`)
- Result: **511 passed, 26 skipped, 4 failed** (none affect the base workflow).
- `test_fluodb_lite_dataset_frozen` — expected SHA-256 was computed on a Windows (CRLF) copy; repo/Nibi copy is LF. Data content identical → test bug.
- `test_provision_environment_reports_missing_module_command` — `scripts/remote/provision_environment.sh` committed without executable bit (100644) → "Permission denied" on Linux.
- `test_audit_missing_checkpoint_report_json_schema` — UniProp environment audit; fails because `third_party/nablacolors/` is not present.
- `test_hundred_row_lmdb_loads_through_upstream_lmdb_dataset` — needs `third_party/nablacolors/` (gitignored, must be fetched separately; pinned in `third_party/nablacolors.REVISION`, v1.0.0 / 3909538).
- TODO later: fix CRLF hash test + chmod provisioning script; fetch nablacolors before UniProp/transformer work.

### Job: baseline tree models (reproduce previous student)
- Script: `slurm/base_models/run_model_experiments_fluodb.sbatch`
- Command: `sbatch --account=def-yzhao slurm/base_models/run_model_experiments_fluodb.sbatch`
- Job ID: 28351510
- Resources requested: 12 h, 12 CPUs, 96 GB
- Models / targets: rf, extratrees, histgb, gbdt × absorption_nm, emission_nm, quantum_yield
- Outputs: `models/experiments_fluodb/`, `outputs/model_experiments_fluodb/`
- Status: **COMPLETED** (exit 0:0), checked 2026-11-23 via `sacct`
- Wall time: 01:21:38 · Max memory (MaxRSS): ~8.3 GB (8,681,420 K) of 96 GB requested
- Notes: SSH connection dropped during `tail -f`; job unaffected. Next time can request
  less (e.g. 3 h / 16 GB) to queue faster.

### Results (checked 2026-11-23)
Reference from README (previous student):

| Model | Emission MAE (nm) | QY MAE |
|---|---:|---:|
| RF | 23.85 | 0.1505 |
| ExtraTrees | 28.20 | 0.1464 |
| HistGB | 29.31 | 0.1749 |
| GBDT | 40.10 | 0.2087 |

My run:

Source: `outputs/model_experiments_fluodb/model_comparison.md` (on Nibi)

| Model | Absorption MAE (nm) | Emission MAE (nm) | QY MAE |
|---|---:|---:|---:|
| RF | **20.3774** (R² 0.8865) | **23.8493** (R² 0.8375) | 0.1505 (R² 0.5448) |
| ExtraTrees | 24.3980 (R² 0.8075) | 28.2001 (R² 0.7369) | **0.1464** (R² 0.5052) |
| HistGB | 25.5583 (R² 0.8670) | 29.3118 (R² 0.8145) | 0.1749 (R² 0.4818) |
| GBDT | 36.8045 (R² 0.7693) | 40.1038 (R² 0.6956) | 0.2087 (R² 0.3420) |

Train/test rows: absorption 36753/9253 · emission 33105/8166 · QY 24824/6482

- `sacct` → wall time: 01:21:38 , max memory: ~8.3 GB
- Reproduced? **Yes — emission and QY MAE match README exactly for all 4 models.**
  Baseline to beat for transformer work: RF abs 20.38 nm, RF em 23.85 nm, ExtraTrees QY 0.146.

---

## 2026-11-26 — Case-study dyes predicted with baseline models

### Job
- Script: `slurm/run_case_study_baseline.sbatch` → `scripts/run_case_study_baseline.py`
- Command: `sbatch --account=def-yzhao slurm/run_case_study_baseline.sbatch`
- Branch: `feature/case-study-baseline`
- Input: the 5 lab fluorophores with measured values in `inputs/case_studies/` (relabelled Dye_1–Dye_5 in outputs)
- Models: trained tree models from job 28351510 (`models/experiments_fluodb`)
- Outputs (Nibi): `outputs/case_studies/baseline/` — `report.md`, `measured_vs_predicted.csv`,
  `mean_error_by_model.csv`, `all_model_predictions.csv`
- Figure: `scripts/plot_case_study_baseline.py` → `measured_vs_predicted_rf.png`

### Results

All 4 baseline models were evaluated (full per-model table: `measured_vs_predicted.csv`; per-dye/per-model
heatmap below). RF shown here as the reference for emission (best emission model on the full test set).

| Dye | Solvent | Em. measured | Em. RF | Em. error | QY measured | QY RF | Similarity to training |
|---|---|---:|---:|---:|---:|---:|---|
| Dye_1 | CH3CN | 506 | 517 | 11 nm | 0.55 | 0.20 | 0.65 medium |
| Dye_2 | DMF | 451 | 467 | 16 nm | 0.82 | 0.20 | 0.47 low — outside domain |
| Dye_3 | CH2Cl2 | 569 | 530 | **39 nm** | 0.76 | 0.74 | 0.86 high |
| Dye_4 | Toluene | 453 | 460 | 7 nm | 0.98 | 0.64 | 0.71 high |
| Dye_5 | DMSO | 786 | 798 | 12 nm | 0.10 | 0.11 | 0.80 high |

Mean error over the 5 dyes:

| Model | Absorption (nm) | Emission (nm) | QY |
|---|---:|---:|---:|
| RF | 17.8 | **16.9** | 0.268 |
| HistGB | 12.5 | 29.2 | **0.219** |
| GBDT | 27.7 | 32.6 | 0.286 |
| ExtraTrees | 12.4 | 65.6 | 0.276 |

### What this means (plain language)
- RF predicts emission within ~17 nm on average for these dyes — in line with its ~24 nm test-set error.
- **Dye_3** (largest Stokes shift, 158 nm; donor–acceptor structure) is underpredicted by every model
  (~500–530 vs 569 nm) despite similar training molecules → 2D fingerprints likely miss
  charge-transfer / excited-state effects. Motivation for 3D transformer features.
- **QY is underpredicted for bright dyes** (0.55 / 0.82 / 0.98) — models pull toward the dataset average.
- **Dye_2** is outside the applicability domain; ExtraTrees jumps to 672 nm (221 nm error), RF stays reasonable.
  The domain flag works as a warning.
- Caveat: 5 molecules = a demonstration, not a statistical benchmark.

### Comparison rule (decided 2026-11-26)
- Always show **all models**, never one model alone.
- **Reference ("best") model is chosen per property on the full test set**, not on the 5 dyes
  (ranking on 5 molecules is mostly luck): RF for absorption and emission, ExtraTrees for QY.
- When seeds/CIs are available (paper comparison), call a winner only if it is clearly ahead; otherwise mark a tie.
- The transformer will be compared against all baseline models + hybrid on the same splits and seeds.

### Model-comparison heatmaps
Script: `scripts/plot_model_comparison_heatmaps.py` (modes `region`, `case-study`; ★ = best model per row).
Local copies: `outputs/plots/heatmaps/`.

**Region heatmap** (`region`, input `error_by_region_comparison.csv`, emission, ~8,166 test points):

| Region | RF | ExtraTrees | HistGB | GBDT |
|---|---:|---:|---:|---:|
| UV (<400) | **33.7** | 37.6 | 42.0 | 67.5 |
| Blue (400–500) | **21.4** | 26.9 | 26.2 | 34.0 |
| Green (500–550) | **17.2** | 23.3 | 22.6 | 26.5 |
| Yellow/orange (550–600) | **20.4** | 23.8 | 25.2 | 33.9 |
| Red/NIR (≥600) | **34.5** | 35.7 | 40.5 | 59.6 |
| All | **23.8** | 28.2 | 29.3 | 40.1 |

- RF is best in every region for emission.
- Error doubles at the spectral edges (~17 nm green vs ~34 nm UV and red/NIR). Residual signs show
  UV emitters predicted too long and red/NIR too short → predictions pulled toward mid-spectrum.
- ExtraTrees is within ~4% of RF only in red/NIR; GBDT weakest everywhere.
- Emission only for now (baseline job saves region errors for emission); absorption needs the raw predictions.

**Case-study heatmap** (`case-study`, signed error predicted − measured; wavelength colour capped at 60 nm):
- Best on average: ExtraTrees for absorption (12.4 nm), RF for emission (16.9 nm), HistGB for QY (0.22).
- No model wins every dye; in absorption each dye has a different winner.
- QY underpredicted by every model for the bright dyes (Dye_1–Dye_4); only the dim NIR dye (Dye_5) is right.
- Dye_3 emission too short for every model (−39 to −69 nm).

### Questions for Prof. Zhao (chemistry)
- Is Dye_3's large Stokes shift due to charge transfer?
- More dyes with measured values available to grow this test set?
- Priority: emission wavelength or QY?

---

## 2026-11-26 — Regenerating previous manuscript results

### Why
`scripts/manuscript/MAE_Accuracy_Bar_Graphs.py` redraws the manuscript figures from numbers typed into the
script (recorded 2026-07-20). Redrawn locally → `outputs/plots/bar_graphs/` (identical to `manuscript images/`).
To reproduce the numbers themselves and get the raw per-model/split/seed predictions (needed for a fair
transformer comparison), the source experiments are rerun. Code and data have not changed since the numbers
were recorded, so results are expected to match (small differences possible from package versions / MLP).

### Jobs (submitted 2026-11-26 19:35 EST, commit `5c8186f` on main)
Job IDs also saved on Nibi in `outputs/regeneration_job_ids.txt`.

| Job | ID | Regenerates | Output |
|---|---|---|---|
| Paper comparison (5 models × 3 targets × 3 splits × 3 seeds) | 28789514 | fig1, fig2 | `outputs/paper_comparison/` |
| QY binary from regression (after 28789514) | 28789515 | fig4 | `outputs/paper_comparison/qy_binary_from_regression/` |
| Stokes paper comparison | 28789516 | fig1 Stokes bars | `outputs/paper_comparison_stokes/` |
| Hybrid molecule / absorption | 28789518 | fig3a–d | `outputs/hybrid_three_way/molecule/absorption_nm/seed_0/` |
| Hybrid molecule / emission | 28789519 | fig3a–d | `outputs/hybrid_three_way/molecule/emission_nm/seed_0/` |
| Hybrid molecule / QY | 28789523 | fig3a–d | `outputs/hybrid_three_way/molecule/quantum_yield/seed_0/` |
| Hybrid scaffold / absorption | 28789524 | fig3a–d | `outputs/hybrid_three_way/scaffold/absorption_nm/seed_0/` |
| Hybrid scaffold / emission | 28789525 | fig3a–d | `outputs/hybrid_three_way/scaffold/emission_nm/seed_0/` |
| Hybrid scaffold / QY | 28789526 | fig3a–d | `outputs/hybrid_three_way/scaffold/quantum_yield/seed_0/` |

- Status at submit: paper comparison and Stokes running; hybrids pending (resources); QY binary pending (dependency).
- Note: the Stokes job rewrites tracked file `data/processed/fluodb_lite/combined_deduplicated_with_stokes.csv`;
  check `git status` on Nibi afterwards — should be unchanged.

### Outcome of first submission
- All 6 hybrid jobs **COMPLETED** (12–18 min each, nodes c690/c192).
- Paper comparison 28789514 and Stokes 28789516 **FAILED** with `Bus error (core dumped)`
  after 24 and 19 min. Both were on the **same node, c354**; the hybrids (same code and environment) ran fine elsewhere.
  Diagnosis: faulty node, not the code.
- QY binary 28789515 was stuck at `DependencyNeverSatisfied` → cancelled.

### Resubmission (2026-11-26, `--exclude=c354`)
| Job | ID | Node | Status |
|---|---|---|---|
| Paper comparison | 28800822 | c139 | COMPLETED (10:43:52) |
| Stokes paper comparison | 28800829 | c143 | COMPLETED (3:53:40) |
| QY binary from regression | 28800823 | c60 | COMPLETED (0:00:14 — scoring only, check output exists) |

Lesson: if a job dies with a Bus error/segfault early and other jobs with the same code are fine,
check `NodeList` in `sacct` and resubmit with `--exclude=<node>`.

### Results (2026-11-27) — compared with hard-coded values in `MAE_Accuracy_Bar_Graphs.py`
Downloaded to laptop `outputs/` (tar + scp). Best model per target/split = lowest mean MAE over seeds 0,1,2; std = sample std.

- **fig1/fig2 (paper comparison, 9 cases): reproduced exactly** — same best model, MAE, std, RMSE, R² to the
  printed precision (e.g. emission molecule RF 24.85 ± 0.66, R² 0.8250).
- **fig1 Stokes (3 cases): reproduced exactly** (random ET 11.05, molecule RF 17.85, scaffold RF 23.00).
- **fig4 QY classification: reproduced exactly** (accuracy 0.8770 / 0.8015 / 0.7316).
- **fig3 hybrid:** best base model MAE reproduced exactly; hybrid-ensemble MAE differs slightly:

| Case | Hybrid MAE (paper) | Hybrid MAE (mine) | Improvement paper → mine |
|---|---|---|---|
| Absorption / molecule | 22.1534 | 22.1047 | 0.457 → 0.506 |
| Emission / molecule | 26.6456 | 26.6596 | 0.408 → 0.394 |
| QY / molecule | 0.1574 | 0.1584 | 0.0076 → 0.0066 |
| Absorption / scaffold | 35.7370 | 35.7341 | −4.447 → −4.444 |
| Emission / scaffold | 34.5058 | 34.4126 | 1.845 → 1.938 |
| QY / scaffold | 0.1965 | 0.1971 | 0.0051 → 0.0044 |

  Differences are ≤0.1 nm / ≤0.001 QY; conclusions unchanged (hybrid helps slightly except absorption/scaffold,
  where it is ~4.4 nm worse). Likely cause: run-to-run nondeterminism in the hybrid's MLP/meta-learner
  (multi-threaded training), not a code or data change.
- [ ] `git status` on Nibi after the Stokes job: still to confirm clean.

- [x] Compare with values in `MAE_Accuracy_Bar_Graphs.py`; reproduced? **Yes** (hybrid within ~0.1 nm).
- [ ] Redraw figures from own runs.
- [ ] Add property × split heatmap (random/molecule/scaffold, ties from 3 seeds) and absorption-by-region.

---

## Next steps
- [x] Record job ID and results above; compare with README. (Reproduced exactly.)
- [x] Commit this log to the org repo. (PR #4)
- [x] Predict case-study dyes with baseline models.
- [ ] Meet Prof. Zhao: show baseline + case-study figure; agree on chemistry priorities.
- [ ] Phase 2: set up ConforFormer (3D transformer) on Nibi; canary run, then full dataset; compare with RF
  on the same molecule split and on the case-study dyes.
- [ ] Phase 3: UniProp fine-tuning (or SMILES transformer), depending on Phase 2 and prof's priorities.
