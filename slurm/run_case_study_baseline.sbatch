#!/bin/bash
#SBATCH --job-name=case_baseline
#SBATCH --output=outputs/slurm/case_baseline-%j.out
#SBATCH --error=outputs/slurm/case_baseline-%j.err
#SBATCH --time=00:30:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G

# Predict the lab case-study fluorophores with the trained baseline tree models
# (models/experiments_fluodb, from slurm/base_models/run_model_experiments_fluodb.sbatch).
#
# Submit from the repo root:
#   sbatch --account=def-yzhao slurm/run_case_study_baseline.sbatch

set -euo pipefail

PROJECT_ROOT="${FLUORCAST_REPO:-${SLURM_SUBMIT_DIR:-$HOME/scratch/FluorCast}}"
cd "$PROJECT_ROOT"

module purge || true
module load python/3.11
module load gcc
module load rdkit

if [[ -n "${FLUORCAST_ACTIVATE:-}" ]]; then
  source "$FLUORCAST_ACTIVATE"
elif [[ -f "$HOME/scratch/chemfluor_env/bin/activate" ]]; then
  source "$HOME/scratch/chemfluor_env/bin/activate"
fi

TREE_MODEL_DIR="${FLUORCAST_TREE_MODEL_DIR:-models/experiments_fluodb}"
OUT_DIR="${FLUORCAST_OUT_DIR:-outputs/case_studies/baseline}"

if [[ ! -d "$TREE_MODEL_DIR" ]]; then
  echo "ERROR: trained models not found at $TREE_MODEL_DIR." >&2
  echo "Run slurm/base_models/run_model_experiments_fluodb.sbatch first." >&2
  exit 2
fi

mkdir -p outputs/slurm "$OUT_DIR"

echo "Date:       $(date)"
echo "Host:       $(hostname)"
echo "Git commit: $(git rev-parse --short HEAD)"
echo "Models:     $TREE_MODEL_DIR"
echo

python -u scripts/run_case_study_baseline.py \
  --tree-model-dir "$TREE_MODEL_DIR" \
  --out-dir "$OUT_DIR"
