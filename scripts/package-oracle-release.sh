#!/usr/bin/env bash
set -euo pipefail
sha="$(git rev-parse HEAD)"
test -s frontend/build/index.html
stage="$(mktemp -d)"
trap 'rm -rf -- "$stage"' EXIT
mkdir -p "$stage"/{backend,frontend,wheels}
# Explicit runtime files from the tested tree. Never package a local .env or test fixtures.
git archive "$sha" backend/{server.py,auth_service.py,google_oidc.py,demo_chargers.py,whatsapp_otp_provider.py,staging_safety.py,release_environment.py,requirements.txt,services,templates/whatsapp_utility_catalog.json} |
  tar -xf - -C "$stage"
cp -a frontend/build/. "$stage/frontend/"
find "$stage/frontend" -name .DS_Store -type f -delete
printf '%s\n' "$sha" > "$stage/release-sha.txt"
cp "$stage/release-sha.txt" "$stage/frontend/rushx-release.txt"
python -m pip wheel -r "$stage/backend/requirements.txt" --wheel-dir "$stage/wheels"
mkdir -p oracle-release
tar -czf oracle-release/rushx.tar.gz -C "$stage" backend frontend wheels release-sha.txt
(cd oracle-release && sha256sum rushx.tar.gz > SHA256SUMS)
