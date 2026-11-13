#!/usr/bin/env bash
set -euo pipefail
target="${1:?Expected deployment environment}"
[[ "$GITHUB_REPOSITORY" == izafar22/voltx && "$RELEASE_SHA" == "$GITHUB_SHA" ]] ||
  { echo "Repository or release SHA mismatch" >&2; exit 1; }
[[ "$RELEASE_SHA" =~ ^[0-9a-f]{40}$ && "$RELEASE_SEQUENCE" =~ ^[1-9][0-9]*$ ]] ||
  { echo "Invalid release SHA or sequence" >&2; exit 1; }
[[ "$ORACLE_HOST" =~ ^[a-zA-Z0-9][a-zA-Z0-9.-]*$ && "$ORACLE_USER" =~ ^[a-z_][a-z0-9_-]*$ ]] ||
  { echo "Invalid SSH destination" >&2; exit 1; }
if [[ "$target" == production ]]; then
  bash scripts/verify-oracle-production.sh approval
else
  [[ "$target" == staging && "$GITHUB_REF" == refs/heads/repair-mvp && "$GITHUB_EVENT_NAME" == push ]]
fi

# Check integrity on the runner, then send the same digest via pinned SSH for host verification.
[[ -s oracle-release/SHA256SUMS && -s oracle-release/rushx.tar.gz ]] ||
  { echo "Missing release artifact or checksum" >&2; exit 1; }
digest="$(awk 'NR == 1 && $2 == "rushx.tar.gz" {print $1}' oracle-release/SHA256SUMS)"
[[ "$digest" =~ ^[0-9a-f]{64}$ ]]
printf '%s  oracle-release/rushx.tar.gz\n' "$digest" | sha256sum -c
umask 077
identity="$(mktemp -d)"
trap 'rm -rf -- "$identity"' EXIT
printf '%s\n' "${SSH_KEY:?Missing environment SSH key}" > "$identity/key"
printf '%s\n' "${SSH_KNOWN_HOSTS:?Missing pinned environment host key}" > "$identity/known"
unset SSH_KEY SSH_KNOWN_HOSTS

gh api "repos/$GITHUB_REPOSITORY/branches/$GITHUB_REF_NAME" |
  jq -e --arg sha "$RELEASE_SHA" '.protected and .commit.sha == $sha' >/dev/null ||
  { echo 'Release is superseded or its branch lacks protection'; exit 1; }

# The installed host-side command independently checks its provisioned environment.
ssh -F /dev/null -i "$identity/key" -o IdentitiesOnly=yes -o BatchMode=yes \
  -o StrictHostKeyChecking=yes -o UserKnownHostsFile="$identity/known" -o GlobalKnownHostsFile=/dev/null \
  -o ConnectTimeout=15 -o ServerAliveInterval=15 -o ServerAliveCountMax=3 \
  "$ORACLE_USER@$ORACLE_HOST" "/usr/local/bin/rushx-oracle-release deploy $target $RELEASE_SHA $RELEASE_SEQUENCE $digest" \
  < oracle-release/rushx.tar.gz
