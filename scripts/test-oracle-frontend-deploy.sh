#!/usr/bin/env bash
# Isolated deployment regression tests: never touch /var/www or the public site.
set -Eeuo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf -- "$TMP"' EXIT
mkdir -p "$TMP/home/rushx-deploy" "$TMP/www/frontend" "$TMP/bin" "$TMP/package/static/js" "$TMP/package/static/css"
export HOME="$TMP/home"
printf 'old site\n' > "$TMP/www/frontend/index.html"
printf '<html>new site</html>\n' > "$TMP/package/index.html"
printf 'console.log(1)\n' > "$TMP/package/static/js/main.js"
printf 'body{}\n' > "$TMP/package/static/css/main.css"
tar -C "$TMP/package" -czf "$TMP/site.tar.gz" .
SHA=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
# Use an isolated copy with the production root rewritten; leave repo script unchanged.
sed "s|^ROOT=/var/www/rushx$|ROOT=$TMP/www|" "$REPO_ROOT/scripts/deploy-oracle-frontend.sh" > "$TMP/deploy.sh"
bash -n "$TMP/deploy.sh"
cat > "$TMP/bin/curl" <<'MOCK'
#!/usr/bin/env bash
if [[ "${FAIL_SMOKE:-0}" == 1 ]]; then exit 22; fi
while (( $# )); do
    if [[ "$1" == "-o" ]]; then
        shift
        if [[ "$1" != "/dev/null" ]]; then printf '<html>OK</html>\n' > "$1"; fi
    fi
    shift
done
MOCK
chmod +x "$TMP/bin/curl"
export PATH="$TMP/bin:$PATH"
run() { bash "$TMP/deploy.sh" "$SHA" "$TMP/site.tar.gz"; }
assert_no_stage() { [[ ! -e "$TMP/www/releases/$SHA" ]]; }
assert_old() { grep -q 'old site' "$TMP/www/frontend/index.html"; }
assert_new() { grep -q 'new site' "$TMP/www/frontend/index.html"; }
# Preflight failure after staging creation must clean up.
mkdir -p "$TMP/www/releases/$SHA"
printf 'stale\n' > "$TMP/www/releases/$SHA/leftover"
# Failed smoke must roll back and clear staging.
if FAIL_SMOKE=1 run; then echo "FAIL: smoke failure was accepted"; exit 1; fi
assert_old
assert_no_stage
# Retry identical SHA must work; no leftover files should survive.
run
assert_new
[[ -d "$TMP/www/releases/$SHA" ]]
[[ ! -e "$TMP/www/releases/$SHA/leftover" ]]
python3 - "$HOME/rushx-deploy/frontend-deployed-sha" "$SHA" <<'PY'
import pathlib, sys
assert pathlib.Path(sys.argv[1]).read_bytes() == (sys.argv[2] + "\n").encode()
PY
# Subsequent failed retry must restore currently live content and clean staging.
if FAIL_SMOKE=1 run; then echo "FAIL: retry smoke failure was accepted"; exit 1; fi
assert_new
assert_no_stage
# Reject a malformed archive and clean staging before any live modification.
mkdir -p "$TMP/invalid"
printf 'not a frontend' > "$TMP/invalid/README"
tar -C "$TMP/invalid" -czf "$TMP/bad.tar.gz" .
if bash "$TMP/deploy.sh" "$SHA" "$TMP/bad.tar.gz"; then echo "FAIL: bad artifact accepted"; exit 1; fi
assert_new
assert_no_stage
echo "PASS: rollback, retry, stale cleanup, SHA marker, invalid artifact"
