#!/usr/bin/env bash
set -euo pipefail

if [[ ${EUID} -ne 0 ]]; then
  echo '请用 sudo bash scripts/setup_exit_node.sh 执行。' >&2
  exit 1
fi

if ! command -v tailscale >/dev/null; then
  installer=$(mktemp)
  curl --fail --silent --show-error --location https://tailscale.com/install.sh -o "$installer"
  sh "$installer"
  rm -f "$installer"
fi

cat > /etc/sysctl.d/99-learnwords-tailscale.conf <<'EOF'
net.ipv4.ip_forward = 1
net.ipv6.conf.all.forwarding = 1
EOF
sysctl -p /etc/sysctl.d/99-learnwords-tailscale.conf
systemctl enable --now tailscaled

if ! tailscale ip -4 >/dev/null 2>&1; then
  echo '请先运行 sudo tailscale up，在官方页面登录，再重跑本脚本。' >&2
  exit 1
fi

tailscale set --advertise-exit-node
echo '已广播出口；还需在 Tailscale Machines 页面批准 armbian 的 Use as exit node。'
echo 'TS_EXIT_NODE：'
tailscale ip -4
echo '以下为当前公网 IPv4 和地区，请据此设置 TS_EXPECTED_IPV4：'
curl -4 --noproxy '*' --fail --silent --show-error --max-time 30 https://www.cloudflare.com/cdn-cgi/trace | sed -n -e '/^ip=/p' -e '/^loc=/p'
echo 'IPv6 检查（不可用时可以不设置 TS_EXPECTED_IPV6）：'
curl -6 --noproxy '*' --fail --silent --show-error --max-time 30 https://www.cloudflare.com/cdn-cgi/trace | sed -n -e '/^ip=/p' -e '/^loc=/p' || true
