#!/usr/bin/env bash
# Runs as dedicated, non-root deployment user after environment approval.
set -Eeuo pipefail

SHA="${1:?Release SHA required}"
ARCHIVE="${2:?Artifact path required}"
[[ "$SHA" =~ ^[0-9a-f]{40}$ ]] || { echo "Invalid SHA"; exit 1; }
[[ -f "$ARCHIVE" && -s "$ARCHIVE" ]] || { echo "Missing artifact"; exit 1; }

ROOT=/var/www/rushx
LIVE="$ROOT/frontend"
RELEASES="$ROOT/releases"
BACKUPS="$ROOT/backups"
STAGING="$RELEASES/$SHA"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP="$BACKUPS/frontend-$STAMP"
LOCK=${HOME}/rushx-deploy/frontend-deploy.lock

exec 9>"$LOCK"
flock -n 9 || { echo "Another deployment is in progress"; exit 1; }
command -v rsync >/dev/null || { echo "rsync is required on Oracle"; exit 1; }
[[ -d "$LIVE" && ! -L "$LIVE" ]] || { echo "Expected existing frontend directory at $LIVE"; exit 1; }
[[ ! -e "$STAGING" ]] || { echo "Release directory already exists: $STAGING"; exit 1; }

mkdir -p "$RELEASES" "$BACKUPS" "$STAGING"
# Reject symlinks, device nodes, and path traversal in the archive.
python3 - "$ARCHIVE" <<'PY'
import sys, tarfile, pathlib
with tarfile.open(sys.argv[1], "r:gz") as archive:
    for member in archive.getmembers():
        path = pathlib.PurePosixPath(member.name)
        if path.is_absolute() or ".." in path.parts or not (member.isfile() or member.isdir()):
            raise SystemExit("Unsafe archive entry: " + member.name)
PY
tar -xzf "$ARCHIVE" -C "$STAGING" --no-same-owner --no-same-permissions
# Ensure Nginx can traverse directories and read static assets.
chmod -R a+rX "$STAGING"
[[ -s "$STAGING/index.html" ]] || { echo "index.html missing"; exit 1; }
find "$STAGING/static/js" -type f -name '*.js' -size +0c | grep -q . || { echo "JS missing"; exit 1; }
find "$STAGING/static/css" -type f -name '*.css' -size +0c | grep -q . || { echo "CSS missing"; exit 1; }

mkdir -p "$BACKUP"
rsync -a --delete "$LIVE/" "$BACKUP/"
[[ -s "$BACKUP/index.html" ]] || { echo "Backup validation failed"; exit 1; }
echo "Backup: $BACKUP"
echo "Deploying: $SHA"

# Keep the temporary response private and remove it on every exit path.
PUBLIC_CHECK="$(mktemp "${HOME}/rushx-deploy/public-check.XXXXXXXX")"
cleanup() {
    rm -f -- "$PUBLIC_CHECK"
}
trap cleanup EXIT

rollback() {
    code="$1"
    trap - ERR INT TERM HUP
    echo "Deployment failed (exit $code); restoring $BACKUP"
    rsync -a --delete "$BACKUP/" "$LIVE/" || echo "CRITICAL: automatic rollback failed"
    exit "$code"
}
trap 'rollback "$?"' ERR
trap 'rollback 130' INT
trap 'rollback 143' TERM
trap 'rollback 129' HUP

rsync -a --delete "$STAGING/" "$LIVE/"
[[ -s "$LIVE/index.html" ]]
curl --fail --silent --show-error --max-time 15 -H 'Host: evchargerrepair.in' http://127.0.0.1/ -o /dev/null
# Check the public TLS endpoint while the rollback trap remains armed.
curl --fail --silent --show-error --location --max-time 30 https://evchargerrepair.in/ -o /tmp/rushx-deploy-public-$.html
grep -qi '<html' /tmp/rushx-deploy-public-$.html
rm -f /tmp/rushx-deploy-public-$.html
printf '%s\n' "$SHA" > "$ROOT/frontend-deployed-sha"
trap - ERR
echo "Deployed $SHA; rollback snapshot: $BACKUP"
