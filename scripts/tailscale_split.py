"""Learn domain IPs with dnsmasq and steer them through the existing Tailscale TUN."""
import argparse
import ipaddress
import json
import os
import socket
import subprocess
from pathlib import Path

from src.config import ROOT, load_config
from src.network import curl_trace

DIRECTORY = ROOT / '.session/network'
STATE = DIRECTORY / 'runner.json'
DOMAINS = ROOT / 'configs/doubao-domains.txt'
MARK = '0x100/0x100'
POLICY = Path('/etc/opt/chrome/policies/managed/learnwords-dns.json')


def main():
    load_config()
    parser = argparse.ArgumentParser(description='Runner-only Tailscale domain routing')
    parser.add_argument('action', choices=('baseline', 'start', 'stop'))
    args = parser.parse_args()
    if args.action == 'baseline':
        save_baseline()
    elif args.action == 'start':
        start_split()
    else:
        stop_split()


def save_baseline():
    DIRECTORY.mkdir(mode=0o700, parents=True, exist_ok=True)
    route = json.loads(subprocess.check_output(['ip', '-j', '-4', 'route', 'get', '1.1.1.1'], text=True))[0]
    resolvers = [line.split()[1] for line in Path('/run/systemd/resolve/resolv.conf').read_text().splitlines()
                 if line.startswith('nameserver ') and not ipaddress.ip_address(line.split()[1]).is_loopback]
    if not resolvers:
        raise RuntimeError('没有取得 Runner 原始 DNS，停止配置分流')
    ipv4 = curl_trace(4)
    try:
        ipv6 = curl_trace(6)
    except RuntimeError:
        ipv6 = {}
    STATE.write_text(json.dumps({'interface': route['dev'], 'dns': resolvers, 'ipv4': ipv4, 'ipv6': ipv6}))
    STATE.chmod(0o600)
    with open(os.environ['GITHUB_ENV'], 'a', encoding='utf-8') as stream:
        stream.write('RUNNER_PUBLIC_IPV4=' + ipv4['ip'] + '\nRUNNER_PUBLIC_IPV6=' + ipv6.get('ip', '') + '\n')
    print('已保存 Runner 原始出口：' + ipv4['ip'] + '，以及原始 DNS 和网卡。', flush=True)


def start_split():
    state = json.loads(STATE.read_text())
    version = subprocess.check_output(['dnsmasq', '--version'], text=True)
    if 'no-nftset' in version or 'nftset' not in version:
        raise RuntimeError('dnsmasq 缺少 nftset 支持')
    rules = '''table inet learnwords {
      set doubao4 { type ipv4_addr; }
      set doubao6 { type ipv6_addr; }
      chain mark {
        type route hook output priority mangle; policy accept;
        meta mark & 0xff0000 == 0x80000 return
        ip daddr 223.5.5.5 meta l4proto { tcp, udp } th dport 53 meta mark set meta mark | 0x100
        ip daddr @doubao4 counter meta mark set meta mark | 0x100
        ip6 daddr @doubao6 counter meta mark set meta mark | 0x100
      }
      chain source {
        type nat hook postrouting priority srcnat; policy accept;
        oifname "tailscale0" meta mark & 0x100 == 0x100 counter masquerade
      }
    }'''
    # Output marking happens after source selection; SNAT gives Tailscale its own allowed source IP.
    subprocess.run(['sudo', 'nft', '-f', '-'], input=rules, text=True, check=True)
    for family, overlay in (('-4', '100.64.0.0/10'), ('-6', 'fd7a:115c:a1e0::/48')):
        run('ip', family, 'rule', 'add', 'pref', '5260', 'fwmark', MARK, 'lookup', '52')
        run('ip', family, 'rule', 'add', 'pref', '5261', 'to', overlay, 'lookup', '52')
        run('ip', family, 'rule', 'add', 'pref', '5265', 'lookup', 'main')
        # A runner without native IPv6 must not fall through to the exit node for non-target traffic.
        run('ip', family, 'rule', 'add', 'pref', '5266', 'unreachable')
    domains = domain_names()
    lines = ['port=53', 'listen-address=127.0.0.1', 'bind-interfaces', 'no-resolv', 'user=root', 'group=root',
             'cache-size=1000', 'pid-file=' + str(DIRECTORY / 'dnsmasq.pid'),
             'log-facility=' + str(DIRECTORY / 'dnsmasq.log')]
    lines.extend('server=' + resolver for resolver in state['dns'])
    for domain in domains:
        lines.extend(['server=/' + domain + '/223.5.5.5',
                      'nftset=/' + domain + '/4#inet#learnwords#doubao4,6#inet#learnwords#doubao6'])
    config = DIRECTORY / 'dnsmasq.conf'
    config.write_text('\n'.join(lines) + '\n')
    run('dnsmasq', '--conf-file=' + str(config))
    run('resolvectl', 'dns', state['interface'], '127.0.0.1')
    run('resolvectl', 'domain', state['interface'], '~.')
    run('resolvectl', 'flush-caches')
    run('mkdir', '-p', str(POLICY.parent))
    subprocess.run(['sudo', 'tee', str(POLICY)], input='{"DnsOverHttpsMode":"off"}\n', text=True,
                   stdout=subprocess.DEVNULL, check=True)
    print('域名分流已启用：豆包目标和其 DNS 走 Tailscale，其他使用 Runner 原路由。', flush=True)


def stop_split():
    run('tailscale', 'set', '--exit-node=', check=False)
    if STATE.exists():
        state = json.loads(STATE.read_text())
        run('resolvectl', 'revert', state['interface'], check=False)
        run('resolvectl', 'flush-caches', check=False)
    pid = DIRECTORY / 'dnsmasq.pid'
    if pid.exists():
        run('kill', '-TERM', str(int(pid.read_text().strip())), check=False)
    for family in ('-4', '-6'):
        for priority in ('5260', '5261', '5265', '5266'):
            run('ip', family, 'rule', 'del', 'pref', priority, check=False)
    run('nft', 'delete', 'table', 'inet', 'learnwords', check=False)
    run('rm', '-f', str(POLICY), check=False)
    print('已清理本任务的 DNS、分流规则和出口路由。', flush=True)


def domain_names():
    return [line.strip() for line in DOMAINS.read_text().splitlines()
            if line.strip() and not line.lstrip().startswith('#')]


def nft_element(action, address):
    family = 'doubao4' if ipaddress.ip_address(address).version == 4 else 'doubao6'
    run('nft', action, 'element', 'inet', 'learnwords', family, '{', address, '}')


def route_device(address, marked=False):
    family = '-4' if ipaddress.ip_address(address).version == 4 else '-6'
    command = ['ip', '-j', family, 'route', 'get', address]
    if marked:
        command += ['mark', '0x100']
    return json.loads(subprocess.check_output(command, text=True))[0]['dev']


def run(*command, check=True):
    return subprocess.run(['sudo', *command], check=check, text=True,
                          stdout=None if check else subprocess.DEVNULL,
                          stderr=None if check else subprocess.DEVNULL)


if __name__ == '__main__':
    main()
