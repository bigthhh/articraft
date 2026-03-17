default:
    @just --list

host := "127.0.0.1"
port := "8765"

setup:
    uv sync --group dev
    uv run pre-commit install --hook-type pre-commit --hook-type pre-push
    uv run articraft-dataset --repo-root . init-storage
    uv run articraft-workbench --repo-root . init-storage
    uv run articraft-dataset --repo-root . validate
    uv run articraft-dataset --repo-root . build-manifest

hooks-install:
    uv run pre-commit install --hook-type pre-commit --hook-type pre-push

format:
    uv run ruff format .

lint:
    uv run ruff check .

smoke-tests:
    find tests -name 'test_*.py' -type f | sort | xargs -I{} uv run python {}

dataset-validate:
    uv run articraft-dataset --repo-root . validate

dataset-manifest:
    uv run articraft-dataset --repo-root . build-manifest

viewer:
    #!/usr/bin/env bash
    set -euo pipefail
    if ! command -v npm >/dev/null 2>&1; then
      echo "npm is required for viewer/web. Install Node.js and npm first."
      exit 1
    fi
    if [ ! -d viewer/web/node_modules ]; then
      npm --prefix viewer/web install
    fi
    npm --prefix viewer/web run build
    uv run articraft-dataset --repo-root . validate
    uv run articraft-dataset --repo-root . build-manifest
    (
      for _ in {1..60}; do
        if curl -fsS http://{{host}}:{{port}}/health >/dev/null; then
          open http://{{host}}:{{port}}/ >/dev/null 2>&1 || uv run python -m webbrowser http://{{host}}:{{port}}/ >/dev/null 2>&1 || true
          exit 0
        fi
        sleep 0.25
      done
    ) >/dev/null 2>&1 &
    exec uv run uvicorn viewer.api.app:app --reload --host {{host}} --port {{port}}

viewer-web-install:
    npm --prefix viewer/web install

viewer-web-dev:
    npm --prefix viewer/web run dev

viewer-web-build:
    npm --prefix viewer/web run build

viewer-web-typecheck:
    npm --prefix viewer/web run typecheck
