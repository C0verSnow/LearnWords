#!/usr/bin/env bash
set -euo pipefail

if ! timeout 10 getent ahostsv4 archive.ubuntu.com > /dev/null; then
    echo 'Runner 原始 DNS 无法解析 Ubuntu 软件源，改用公共 DNS。'
    resolvectl status
    runner_interface=$(ip -4 route get 1.1.1.1 | awk '{for(i=1;i<=NF;i++) if($i=="dev") print $(i+1)}')
    sudo resolvectl dns "$runner_interface" 1.1.1.1 8.8.8.8
    sudo resolvectl domain "$runner_interface" '~.'
    sudo resolvectl flush-caches
fi
timeout 10 getent ahostsv4 archive.ubuntu.com
timeout 10 sudo -u _apt getent ahostsv4 archive.ubuntu.com

sudo sed -i '/azure\.archive\.ubuntu\.com/d' /etc/apt/apt-mirrors.txt
apt_network_args=(-o Acquire::Retries=1 -o Acquire::http::Timeout=15 -o Acquire::https::Timeout=15)
sudo apt-get "${apt_network_args[@]}" update
sudo apt-get "${apt_network_args[@]}" install -y "$@"
