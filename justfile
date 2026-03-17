default:
    @just --list

host := "127.0.0.1"
port := "8765"

setup:
    uv sync
    uv run articraft-dataset --repo-root . init-storage
    uv run articraft-workbench --repo-root . init-storage
    uv run articraft-dataset --repo-root . validate
    uv run articraft-dataset --repo-root . build-manifest

dataset-validate:
    uv run articraft-dataset --repo-root . validate

dataset-manifest:
    uv run articraft-dataset --repo-root . build-manifest

viewer:
    #!/usr/bin/env bash
    set -euo pipefail
    uv run articraft-dataset --repo-root . validate
    uv run articraft-dataset --repo-root . build-manifest
    (
      for _ in {1..60}; do
        if curl -fsS http://{{host}}:{{port}}/health >/dev/null; then
          open http://{{host}}:{{port}}/docs >/dev/null 2>&1 || uv run python -m webbrowser http://{{host}}:{{port}}/docs >/dev/null 2>&1 || true
          exit 0
        fi
        sleep 0.25
      done
    ) >/dev/null 2>&1 &
    exec uv run uvicorn viewer.api.app:app --reload --host {{host}} --port {{port}}
