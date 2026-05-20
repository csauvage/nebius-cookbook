#!/usr/bin/env bash
set -euo pipefail

# Resolve this folder and project root so the script can be run from anywhere.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# Runtime configuration (can be overridden with env vars).
DATA_DIR="${1:-../../data}"
PINECONE_INDEX="${PINECONE_INDEX_NAME:-books-demo}"
PINECONE_NAMESPACE="${PINECONE_NAMESPACE:-}"
EMBED_BATCH="${EMBED_BATCH_SIZE:-1}"
PINECONE_BATCH="${PINECONE_BATCH_SIZE:-200}"
PROGRESS_INTERVAL="${PROGRESS_INTERVAL:-1000}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="${VENV_DIR:-.venv_vectorize}"

# Fail early if the dataset folder is wrong.
if [[ ! -d "$DATA_DIR" ]]; then
  echo "Data directory not found: $DATA_DIR" >&2
  exit 1
fi

# Reuse the project venv or create it once.
if [[ ! -d "$VENV_DIR" ]]; then
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

# Install dependencies in the local venv.
python -m pip install --upgrade pip >/dev/null
python -m pip install -r scripts/requirements.txt

# Load credentials and settings from local env file.
set -a
if [[ ! -f .env.local ]]; then
  echo "Missing .env.local in $(pwd). Create it from .env.vectorize.example or your existing env." >&2
  exit 1
fi
source .env.local
set +a

# Use index/credentials from .env.local when possible, and allow command overrides.
PINECONE_INDEX="${PINECONE_INDEX_NAME:-$PINECONE_INDEX}"

# Run one vectorization pass with one book per embed batch by default.
python scripts/vectorize_goodreads_to_pinecone.py \
  --data-dir "$DATA_DIR" \
  --pinecone-index "$PINECONE_INDEX" \
  --pinecone-batch-size "$PINECONE_BATCH" \
  --embed-batch-size "$EMBED_BATCH" \
  --progress-interval "$PROGRESS_INTERVAL" \
  ${PINECONE_NAMESPACE:+--pinecone-namespace "$PINECONE_NAMESPACE"}
