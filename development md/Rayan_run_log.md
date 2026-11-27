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

### Results (RF)

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

### Questions for Prof. Zhao (chemistry)
- Is Dye_3's large Stokes shift due to charge transfer?
- More dyes with measured values available to grow this test set?
- Priority: emission wavelength or QY?

---

## Next steps
- [x] Record job ID and results above; compare with README. (Reproduced exactly.)
- [x] Commit this log to the org repo. (PR #4)
- [x] Predict case-study dyes with baseline models.
- [ ] Meet Prof. Zhao: show baseline + case-study figure; agree on chemistry priorities.
- [ ] Phase 2: set up ConforFormer (3D transformer) on Nibi; canary run, then full dataset; compare with RF
  on the same molecule split and on the case-study dyes.
- [ ] Phase 3: UniProp fine-tuning (or SMILES transformer), depending on Phase 2 and prof's priorities.
