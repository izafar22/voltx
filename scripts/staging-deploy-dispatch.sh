#!/usr/bin/env bash
set -euo pipefail
read -r sha sequence extra <<< "${SSH_ORIGINAL_COMMAND:-}"
[[ "$sha" =~ ^[0-9a-f]{40}$ && "$sequence" =~ ^[1-9][0-9]*$ && -z "$extra" ]] || {
    echo "Expected a commit SHA and CI run number" >&2
    exit 1
}
exec sudo -n /usr/local/sbin/deploy-staging.py "$sha" "$sequence"
