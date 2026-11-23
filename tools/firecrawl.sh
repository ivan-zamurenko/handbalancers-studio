#!/bin/sh
# Project-local, pinned CLI. Keep automatic updates and feedback disabled.
set -eu
project_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cli="$project_root/.local-tools/firecrawl-cli/node_modules/firecrawl-cli/dist/index.js"
if [ ! -f "$cli" ]; then
  echo 'Firecrawl CLI is missing; see docs/agent-integrations.md.' >&2
  exit 1
fi
export FIRECRAWL_NO_TELEMETRY=1
export FIRECRAWL_NO_AUTO_UPDATE=1
export FIRECRAWL_NO_UPDATE_CHECK=1
export FIRECRAWL_NO_SEARCH_FEEDBACK=1
export FIRECRAWL_NO_ENDPOINT_FEEDBACK=1
node_bin="$project_root/.local-tools/node-v24.21.0-darwin-arm64/bin/node"
if [ ! -x "$node_bin" ]; then node_bin=$(command -v node); fi
exec "$node_bin" "$cli" "$@"
