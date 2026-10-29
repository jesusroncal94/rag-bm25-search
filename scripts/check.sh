#!/usr/bin/env bash
# The one check agents and CI run before calling a change done.
set -euo pipefail
cd "$(dirname "$0")/.."

# Build the service image (installs requirements.txt), then run the tests inside it.
# The repository is mounted over /srv so the tests see the working tree.
docker build -q -t rag-bm25-search-check .
MSYS_NO_PATHCONV=1 docker run --rm -v "$(pwd -W 2>/dev/null || pwd):/srv" -w /srv \
  --entrypoint python rag-bm25-search-check -m pytest -q
