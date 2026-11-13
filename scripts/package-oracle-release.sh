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
COPYFILE_DISABLE=1 tar -czf oracle-release/rushx.tar.gz -C "$stage" backend frontend wheels release-sha.txt
(cd oracle-release && sha256sum rushx.tar.gz > SHA256SUMS)
# Exercise the VM extractor against the actual CI output before publishing it.
python - <<'PYTHON'
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, "scripts")
from oracle_release import frontend_assets, unpack

with tempfile.TemporaryDirectory() as temporary:
    release = Path(temporary)
    unpack(Path("oracle-release/rushx.tar.gz"), release)
    assert (release / "release-sha.txt").read_bytes() == (release / "frontend/rushx-release.txt").read_bytes()
    assert (release / "backend/server.py").is_file() and (release / "backend/release_environment.py").is_file()
    assert any((release / "wheels").glob("*.whl"))
    list(frontend_assets(release / "frontend"))
PYTHON
