#!/usr/bin/env bash
set -euo pipefail
scanner="$(mktemp -d)"
trap 'rm -rf -- "$scanner"' EXIT
curl -fsSL --retry 3 -o "$scanner/gitleaks.tar.gz" https://github.com/gitleaks/gitleaks/releases/download/v8.30.1/gitleaks_8.30.1_linux_x64.tar.gz
(cd "$scanner" && echo '551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb  gitleaks.tar.gz' | sha256sum -c && tar -xzf gitleaks.tar.gz gitleaks)
# Scan the introduced history and final diff, without printing matched values.
base="${BASE_SHA:?Expected PR base or push before SHA}"
if [[ "$base" =~ ^0{40}$ ]]; then base="$(git merge-base origin/repair-mvp HEAD)"; fi
git cat-file -e "$base^{commit}"
"$scanner/gitleaks" git --redact=100 --log-opts="$base..HEAD" --exit-code=1
git diff --no-ext-diff "$base" HEAD | "$scanner/gitleaks" stdin --redact=100 --exit-code=1
