#!/usr/bin/env python
"""Query Goodreads vectors in Pinecone using Nebius embeddings."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Iterable

from openai import OpenAI
from pinecone import Pinecone


DEFAULT_EMBEDDING_MODEL = "Qwen/Qwen3-Embedding-8B"
DEFAULT_RETRIEVAL_INSTRUCTION = (
    "Given a user's book preference, retrieve matching books."
)


def load_dotenv_if_present() -> None:
    script_dir = Path(__file__).resolve().parent
    cookbook_dir = script_dir.parent

    for env_name in (".env.local", ".env"):
        env_path = cookbook_dir / env_name
        if not env_path.exists():
            continue

        with env_path.open("rt", encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue

                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()
                if not key:
                    continue
                if value and len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
                    value = value[1:-1]

                os.environ.setdefault(key, value)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Embed a natural-language book query with Nebius and search Pinecone."
    )
    parser.add_argument("query", help="Natural-language book query to search for.")
    parser.add_argument(
        "--instruction",
        default=DEFAULT_RETRIEVAL_INSTRUCTION,
        help="Retrieval instruction prepended to the query before embedding.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=10,
        help="Number of matches to return.",
    )
    parser.add_argument(
        "--pinecone-index",
        default=None,
        help="Pinecone index name. Defaults to PINECONE_INDEX_NAME from the environment.",
    )
    parser.add_argument(
        "--pinecone-namespace",
        default=None,
        help="Pinecone namespace. Defaults to PINECONE_NAMESPACE from the environment if set.",
    )
    parser.add_argument(
        "--embedding-model",
        default=None,
        help="Nebius embedding model. Defaults to NEBIUS_EMBEDDING_MODEL or Qwen/Qwen3-Embedding-8B.",
    )
    parser.add_argument(
        "--show-metadata",
        action="store_true",
        help="Print raw metadata for each match.",
    )
    return parser.parse_args()


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if value:
        return value
    raise SystemExit(f"Missing required environment variable: {name}")


def format_authors(metadata: dict[str, object]) -> str:
    author_names = metadata.get("author_names")
    if isinstance(author_names, list):
        names = [str(item).strip() for item in author_names if str(item).strip()]
        if names:
            return ", ".join(names)

    author = metadata.get("author")
    if isinstance(author, str) and author.strip():
        return author.strip()

    return "(unknown author)"


def iter_metadata_lines(metadata: dict[str, object]) -> Iterable[str]:
    for key in sorted(metadata.keys()):
        yield f"    {key}: {metadata[key]}"


def main() -> None:
    load_dotenv_if_present()
    args = parse_args()

    if args.top_k < 1:
        raise SystemExit("--top-k must be greater than 0.")

    nebius_api_key = require_env("NEBIUS_API_KEY")
    pinecone_api_key = require_env("PINECONE_API_KEY")
    pinecone_index_name = args.pinecone_index or require_env("PINECONE_INDEX_NAME")
    pinecone_namespace = args.pinecone_namespace
    if pinecone_namespace is None:
        pinecone_namespace = os.environ.get("PINECONE_NAMESPACE")

    nebius_base_url = os.environ.get("NEBIUS_BASE_URL", "https://api.studio.nebius.ai").rstrip("/")
    if not nebius_base_url.endswith("/v1"):
        nebius_base_url = f"{nebius_base_url}/v1"

    embedding_model = (
        args.embedding_model
        or os.environ.get("NEBIUS_EMBEDDING_MODEL")
        or DEFAULT_EMBEDDING_MODEL
    )
    query_text = f"Instruct: {args.instruction}\nQuery: {args.query}"

    nebius = OpenAI(api_key=nebius_api_key, base_url=nebius_base_url)
    embedding_response = nebius.embeddings.create(
        model=embedding_model,
        input=[query_text],
        encoding_format="float",
    )

    pinecone = Pinecone(api_key=pinecone_api_key)
    index = pinecone.Index(pinecone_index_name)
    results = index.query(
        vector=embedding_response.data[0].embedding,
        top_k=args.top_k,
        include_metadata=True,
        namespace=pinecone_namespace,
    )

    print(f"query={args.query}")
    print(f"index={pinecone_index_name}")
    print(f"namespace={pinecone_namespace or '(default)'}")
    print(f"model={embedding_model}")
    print("")

    if not results.matches:
        print("No matches.")
        return

    for match in results.matches:
        metadata = dict(match.metadata or {})
        title = str(metadata.get("title") or match.id or "(untitled)")
        authors = format_authors(metadata)
        print(f"{match.score:.3f}  {title}  by {authors}")
        if args.show_metadata:
            for line in iter_metadata_lines(metadata):
                print(line)


if __name__ == "__main__":
    main()
