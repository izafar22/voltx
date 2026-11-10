#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
export HOME="$TMP/home" RUSHX_DEPLOY_ROOT="$TMP/www"
mkdir -p "$HOME/rushx-deploy" "$TMP/www/releases/previous" "$TMP/package/static/js" "$TMP/package/static/css" "$TMP/bin"
printf '<html>old stable</html>\n' > "$TMP/www/releases/previous/index.html"
ln -s "$TMP/www/releases/previous" "$TMP/www/frontend"
printf '<html>new release</html>\n' > "$TMP/package/index.html"
printf 'console.log(1)\n' > "$TMP/package/static/js/main.js"
printf 'body{}\n' > "$TMP/package/static/css/main.css"
tar -C "$TMP/package" -czf "$TMP/site.tar.gz" .
SHA=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
bash -n "$ROOT/scripts/deploy-oracle-frontend.sh"
cat > "$TMP/bin/curl" <<'MOCK'
#!/usr/bin/env bash
[[ "${FAIL_SMOKE:-0}" != 1 ]] || exit 22
while (( $# )); do
  if [[ "$1" == "-o" ]]; then
    shift
    [[ "$1" == "/dev/null" ]] || printf '<html>OK</html>\n' > "$1"
  fi
  shift
done
MOCK
chmod +x "$TMP/bin/curl"
export PATH="$TMP/bin:$PATH"
run() { bash "$ROOT/scripts/deploy-oracle-frontend.sh" "$SHA" "$TMP/site.tar.gz"; }
active() { readlink -f "$TMP/www/frontend"; }
[[ "$(active)" == "$TMP/www/releases/previous" ]]
# Existing stale staging must be cleaned and failed smoke must restore previous.
mkdir -p "$TMP/www/releases/$SHA"
printf stale > "$TMP/www/releases/$SHA/stale"
if FAIL_SMOKE=1 run; then echo 'Expected failed smoke'; exit 1; fi
[[ "$(active)" == "$TMP/www/releases/previous" && ! -e "$TMP/www/releases/$SHA" ]]
run
[[ "$(active)" == "$TMP/www/releases/$SHA" && ! -e "$TMP/www/releases/$SHA/stale" ]]
python3 - "$HOME/rushx-deploy/frontend-deployed-sha" "$SHA" <<'PY'
import pathlib,sys
assert pathlib.Path(sys.argv[1]).read_bytes() == (sys.argv[2] + "\n").encode()
PY
# The current live release must never be deleted by a retry.
if run; then echo 'Expected refusal to overwrite active release'; exit 1; fi
[[ "$(active)" == "$TMP/www/releases/$SHA" && -s "$TMP/www/releases/$SHA/index.html" ]]
# Invalid archive must fail without switching.
mkdir -p "$TMP/bad"
printf bad > "$TMP/bad/README"
tar -C "$TMP/bad" -czf "$TMP/bad.tar.gz" .
if bash "$ROOT/scripts/deploy-oracle-frontend.sh" bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb "$TMP/bad.tar.gz"; then echo 'Expected invalid archive rejection'; exit 1; fi
[[ "$(active)" == "$TMP/www/releases/$SHA" ]]
echo 'PASS: atomic switch, rollback, stale staging, active-release guard, SHA marker, bad artifact'
