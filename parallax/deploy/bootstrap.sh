#!/usr/bin/env bash
# One-shot prep for a fresh Ubuntu 22.04/24.04 VM (Oracle Always-Free ARM works
# great). Installs Docker + the compose plugin and opens the host firewall.
#
#   curl -fsSL <raw-url>/bootstrap.sh | bash      # or: bash deploy/bootstrap.sh
set -euo pipefail

echo "==> Installing Docker…"
if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sh
  sudo usermod -aG docker "$USER" || true
fi

echo "==> Opening host firewall for 80/443…"
# Oracle Ubuntu images ship restrictive iptables; insert ACCEPT rules before the
# default REJECT. (You must ALSO open 80/443 in the Oracle VCN Security List.)
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT 2>/dev/null || true
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT 2>/dev/null || true
sudo netfilter-persistent save 2>/dev/null || sudo bash -c 'iptables-save > /etc/iptables/rules.v4' 2>/dev/null || true

cat <<'EOF'

==> Docker ready. Next:
  1. Open ports 80 and 443 in the Oracle Cloud VCN Security List (ingress).
  2. cp .env.prod.example .env.prod   and fill in the secrets + API_DOMAIN.
  3. docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
  4. curl https://$API_DOMAIN/health

(You may need to log out/in once so your user picks up the docker group.)
EOF
