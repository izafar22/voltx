#!/usr/bin/env bash
# Atomic, frontend-only release deployment. Requires a pre-migrated symlink webroot.
set -Eeuo pipefail
SHA="${1:?Release SHA required}"
ARCHIVE="${2:?Artifact path required}"
[[ "$SHA" =~ ^[0-9a-f]{40}$ ]] || { echo "Invalid SHA"; exit 1; }
[[ -s "$ARCHIVE" ]] || { echo "Missing artifact"; exit 1; }

ROOT="${RUSHX_DEPLOY_ROOT:-/var/www/rushx}"
LIVE="$ROOT/frontend"
RELEASES="$ROOT/releases"
STAGING="$ROOT/staging/$SHA"
LOCK="${HOME}/rushx-deploy/frontend-deploy.lock"
MARKER="${HOME}/rushx-deploy/frontend-deployed-sha"
mkdir -p "${HOME}/rushx-deploy"
exec 9>"$LOCK"
flock -n 9 || { echo "Deployment already running"; exit 1; }
command -v python3 >/dev/null
command -v curl >/dev/null
# Never replace a real directory or a symlink pointing outside managed releases.
[[ -L "$LIVE" ]] || { echo "Atomic deployment requires frontend symlink; migrate webroot separately"; exit 1; }
PREVIOUS="$(readlink -f "$LIVE")"
[[ -d "$PREVIOUS" && -s "$PREVIOUS/index.html" ]] || { echo "Invalid previous release"; exit 1; }
case "$PREVIOUS" in "$RELEASES"/*) ;; *) echo "Live target outside managed releases"; exit 1;; esac
[[ ! -L "$STAGING" ]] || { echo "Unsafe release symlink"; exit 1; }
command -v sudo >/dev/null || { echo "sudo required for restricted switch helper"; exit 1; }
mkdir -p "$ROOT/staging"
if [[ -e "$RELEASES/$SHA" ]]; then
    echo "Release already exists; refusing overwrite"; exit 1
fi
if [[ -e "$STAGING" ]]; then
    [[ -d "$STAGING" && ! -L "$STAGING" ]] || { echo "Unsafe staging"; exit 1; }
    rm -rf -- "$STAGING"
fi
mkdir -p "$STAGING"
SWITCHED=0
PROMOTED=0
SUCCESS=0
CHECK_FILE=""
cleanup() {
    code=$?
    trap - ERR INT TERM HUP
    trap '' INT TERM HUP
    [[ -z "$CHECK_FILE" ]] || rm -f -- "$CHECK_FILE"
    if [[ "$SUCCESS" != 1 ]]; then
        if [[ "$SWITCHED" == 1 ]]; then
            echo "Deployment failed; restoring $PREVIOUS"
            sudo -n /usr/local/sbin/rushx-release-switch switch "$(basename "$PREVIOUS")" || echo "CRITICAL: rollback failed"
        fi
        if [[ "$PROMOTED" == 1 ]]; then sudo -n /usr/local/sbin/rushx-release-switch discard "$SHA" || echo "WARNING: promoted release cleanup failed"; fi
        if [[ -d "$STAGING" && ! -L "$STAGING" ]]; then rm -rf -- "$STAGING"; fi
    fi
    exit "$code"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
trap 'exit 129' HUP

# Validate every archive member before extraction.
python3 - "$ARCHIVE" <<'PY'
import pathlib, sys, tarfile
with tarfile.open(sys.argv[1], "r:gz") as archive:
    for member in archive:
        p = pathlib.PurePosixPath(member.name)
        if p.is_absolute() or ".." in p.parts or not (member.isfile() or member.isdir()):
            raise SystemExit("Unsafe archive entry: " + member.name)
PY
tar -xzf "$ARCHIVE" -C "$STAGING" --no-same-owner --no-same-permissions
chmod -R a+rX "$STAGING"
[[ -s "$STAGING/index.html" ]]
[[ -n "$(find "$STAGING/static/js" -type f -name '*.js' -size +0c -print -quit)" ]]
[[ -n "$(find "$STAGING/static/css" -type f -name '*.css' -size +0c -print -quit)" ]]
# Atomic rename on the same filesystem. Nginx must serve via $LIVE.
sudo -n /usr/local/sbin/rushx-release-switch promote "$SHA"
PROMOTED=1
sudo -n /usr/local/sbin/rushx-release-switch switch "$SHA"
SWITCHED=1
rm -rf -- "$STAGING"
CHECK_FILE="$(mktemp "${HOME}/rushx-deploy/health.XXXXXXXX")"
curl --fail --silent --show-error --max-time 15 -H 'Host: evchargerrepair.in' http://127.0.0.1/ -o "$CHECK_FILE"
grep -qi '<html' "$CHECK_FILE"
curl --fail --silent --show-error --location --max-time 30 https://evchargerrepair.in/ -o "$CHECK_FILE"
grep -qi '<html' "$CHECK_FILE"
printf '%s\n' "$SHA" > "$MARKER"
SUCCESS=1
echo "Deployed $SHA; previous stable release: $PREVIOUS"
