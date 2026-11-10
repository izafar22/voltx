#!/usr/bin/env bash
# Install as root: /usr/local/sbin/rushx-release-switch (root:root, 0755).
# sudoers: rushx-deploy ALL=(root) NOPASSWD: /usr/local/sbin/rushx-release-switch *
set -Eeuo pipefail
[[ "$EUID" == 0 && "$#" == 2 ]] || exit 2
ACTION="$1"; ID="$2"
[[ "$ID" =~ ^[a-f0-9]{40}$ || "$ID" == initial-stable ]] || exit 2
[[ "$ACTION" == switch || "$ACTION" == discard ]] || exit 2
ROOT=/var/www/rushx
RELEASES="$ROOT/releases"
LIVE="$ROOT/frontend"
TARGET="$RELEASES/$ID"
exec 9>/run/lock/rushx-release-switch.lock
flock -x 9
[[ -d "$RELEASES" && ! -L "$RELEASES" && -d "$ROOT" && ! -L "$ROOT" ]] || exit 3
[[ -d "$TARGET" && ! -L "$TARGET" ]] || exit 3
[[ -L "$LIVE" ]] || { echo "Live frontend must be a symlink"; exit 3; }
CURRENT="$(readlink -f -- "$LIVE")"
case "$CURRENT" in "$RELEASES"/*) ;; *) exit 3;; esac
[[ -d "$CURRENT" && -s "$CURRENT/index.html" ]] || exit 3
[[ "$TARGET" != "$CURRENT" || "$ACTION" == switch ]] || exit 3
# No links inside release tree: prevents a privileged traversal or symlink-based mutation.
if find -P "$TARGET" -type l -print -quit | grep -q .; then echo "Symlinks in release forbidden"; exit 3; fi
if [[ "$ACTION" == discard ]]; then
    [[ "$ID" != initial-stable ]] || exit 3
    rm -rf -- "$TARGET"
    exit 0
fi
[[ -s "$TARGET/index.html" ]] || exit 3
[[ -n "$(find "$TARGET/static/js" -type f -name '*.js' -size +0c -print -quit)" ]] || exit 3
[[ -n "$(find "$TARGET/static/css" -type f -name '*.css' -size +0c -print -quit)" ]] || exit 3
# Ownership protects the active release against writes by the SSH deploy user.
chown -R root:www-data "$TARGET"
find "$TARGET" -type d -exec chmod 755 {} +
find "$TARGET" -type f -exec chmod 644 {} +
TMP="$(mktemp -u "$ROOT/.frontend-switch.XXXXXXXX")"
trap 'rm -f -- "$TMP"' EXIT
ln -s -- "$TARGET" "$TMP"
mv -Tf -- "$TMP" "$LIVE"
echo "Switched $CURRENT -> $TARGET"
