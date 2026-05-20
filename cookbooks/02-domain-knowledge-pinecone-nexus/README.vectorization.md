# Vectorizing Goodreads datasets into Pinecone

The script in this recipe will:

1. analyze available Goodreads JSON dumps,
2. build a text payload from books, authors, works, and genres,
3. call Nebius embeddings with `Qwen/Qwen3-Embedding-8B`, and
4. upsert vectors into Pinecone in fixed-size batches (150 or 200).

## Files

Use datasets from the Goodreads mirror in one of these forms:

- `goodreads_books.json` or `goodreads_books.json.gz`
- `goodreads_book_authors.json` or `goodreads_book_authors.json.gz`
- `goodreads_book_works.json` or `goodreads_book_works.json.gz`
- `goodreads_book_genres_initial.json` or `goodreads_book_genres_initial.json.gz`

## Install

```bash
cd cookbooks/02-domain-knowledge-pinecone-nexus
python -m venv .venv
source .venv/bin/activate
pip install -r scripts/requirements.txt
```

Load environment variables:

```bash
cp .env.vectorize.example .env.local
source .env.local
```

## Analyze only

```bash
cd cookbooks/02-domain-knowledge-pinecone-nexus
source .venv/bin/activate
source .env.local
python scripts/vectorize_goodreads_to_pinecone.py \
  --data-dir ../../data \
  --analyze-only
```

## Run with progress (1 embed chunk per book)

```bash
cd cookbooks/02-domain-knowledge-pinecone-nexus
chmod +x scripts/run_vectorize_goodreads.sh
export PINECONE_INDEX_NAME=books-demo
export PINECONE_NAMESPACE=goodreads
export DATA_DIR=../../data
export EMBED_BATCH_SIZE=1
export PINECONE_BATCH_SIZE=200   # or 150
export PROGRESS_INTERVAL=500      # progress every 500 upserts
./scripts/run_vectorize_goodreads.sh
```

If you only want to run the vectorizer command directly:

```bash
cd cookbooks/02-domain-knowledge-pinecone-nexus
source .venv/bin/activate
source .env.local
python scripts/vectorize_goodreads_to_pinecone.py \
  --data-dir ../../data \
  --pinecone-batch-size 200 \
  --embed-batch-size 1 \
  --progress-interval 500
```

## Run vectorization (200 per Pinecone batch)

```bash
cd cookbooks/02-domain-knowledge-pinecone-nexus
source .venv/bin/activate
source .env.local
python scripts/vectorize_goodreads_to_pinecone.py \
  --data-dir ../../data \
  --pinecone-namespace "$PINECONE_NAMESPACE" \
  --pinecone-batch-size 200
```

To use 150 per batch:

```bash
--pinecone-batch-size 150
```

## Notes

- Books are prioritized and enriched with author names and genre labels when available.
- You can skip datasets with `--skip-books`, `--skip-authors`, `--skip-works`, `--skip-genres`.
- Use `--include-empty-text` if you want to keep records with no extractable text.
- Progress is printed every `N` upserts using `--progress-interval N`.
