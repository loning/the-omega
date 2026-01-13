#!/bin/bash
#SBATCH --job-name=job-name
#SBATCH --output=logs/job-name_%j.out
#SBATCH --error=logs/job-name_%j.err
#SBATCH --partition=A100
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=128G
#SBATCH --gres=gpu:1
#SBATCH --time=72:00:00

###############################################################################
# Job description:
# Training objective: ...
# Data: ...
# Target: ...
# GPU: ...
# Estimated time: ...
###############################################################################

echo "=========================================="


# Environment setup (do NOT load system cuda - conflicts with conda torch)
source ~/.bashrc
conda activate torch

# Force unbuffered output
export PYTHONUNBUFFERED=1

# Set Python path
cd /mnt/rna01/zwlexa/project/TCR
export PYTHONPATH="$PWD:$PYTHONPATH"

# Create log directory if needed

# GPU info
echo "GPU Info:"
nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv
echo ""