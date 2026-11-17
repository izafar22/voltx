#!/usr/bin/env bash
# Run as root on staging from a reviewed checkout.
set -euo pipefail
[[ "$(hostname)" == rushx-staging-vnic && "$EUID" == 0 ]] || {
    echo "Run as root on rushx-staging-vnic" >&2
    exit 1
}
public_key_file="${1:?Path to the dedicated deployment public key required}"
grep -Eq '^ssh-ed25519 [A-Za-z0-9+/=]+( .*)?$' "$public_key_file"
[[ "$(wc -l < "$public_key_file")" -eq 1 ]]
[[ -L /var/www/rushx-staging/staging ]]
systemctl is-active --quiet rushx-staging.service
python3 -c 'import sys; assert sys.version_info[:2] == (3, 12), "Staging requires Python 3.12 to match CI"'
python3 -m venv --help >/dev/null
backend_user="$(systemctl show rushx-staging.service --property=User --value)"
[[ -n "$backend_user" && "$backend_user" != root ]]
source_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if ! id rushx-staging-deploy >/dev/null 2>&1; then
    useradd --system --user-group --no-create-home \
      --home-dir /var/lib/rushx-staging-deploy --shell /bin/sh rushx-staging-deploy
fi
install -d -o root -g root -m 0755 /var/lib/rushx-staging-deploy/.ssh /opt/rushx-staging/cd /etc/rushx
install -o root -g root -m 0755 "$source_dir/deploy-staging.py" /usr/local/sbin/deploy-staging.py
install -o root -g root -m 0755 "$source_dir/staging-deploy-dispatch.sh" /usr/local/bin/staging-deploy-dispatch
printf 'restrict,command="/usr/local/bin/staging-deploy-dispatch" %s\n' "$(cat "$public_key_file")" \
  > /var/lib/rushx-staging-deploy/.ssh/authorized_keys
chmod 0644 /var/lib/rushx-staging-deploy/.ssh/authorized_keys
printf 'rushx-staging-deploy ALL=(root) NOPASSWD: /usr/local/sbin/deploy-staging.py *\n' \
  > /etc/sudoers.d/rushx-staging-cd
chmod 0440 /etc/sudoers.d/rushx-staging-cd
visudo -cf /etc/sudoers.d/rushx-staging-cd
printf 'APP_ENV=staging\nFRONTEND_INDEX_HTML=/var/www/rushx-staging/staging/index.html\n' \
  > /etc/rushx/staging-cd.env
chmod 0600 /etc/rushx/staging-cd.env
echo "Staging deployment account installed. The first CI deployment will select the new backend release."
