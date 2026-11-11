"""Verify both policy branches before opening the Doubao browser."""
import ipaddress
import json
import os
import socket
import subprocess
from pathlib import Path
from urllib.parse import urlsplit

import requests

from scripts.tailscale_split import STATE, domain_names, nft_element, route_device
from src.config import load_config, required_env
from src.network import curl_trace, tailscale_status, verify_exit_trace, verify_runner_trace


def main():
    load_config()
    try:
        verify_tailscale()
        verify_runner_trace(curl_trace(4))
        print('普通 IPv4 请求保持 Runner 原始公网出口。', flush=True)
        verify_ipv6()
        verify_target_exit()
        verify_domain_routes()
        verify_direct_services()
        with requests.Session() as session:
            session.trust_env = False
            response = session.get('https://www.doubao.com/', timeout=(10, 30))
        restricted = any(term in response.text for term in ('受区域限制', '当前地区暂不支持'))
        print(f'豆包 HTTP {response.status_code}，区域限制提示：{restricted}', flush=True)
        if not response.ok or restricted:
            raise RuntimeError('豆包网页检查未通过；出口 CN 不代表网站一定可用')
        print('分流预检通过；登录和真实对话仍由浏览器 Probe 验证。', flush=True)
    except Exception:
        diagnostics()
        raise


def verify_tailscale():
    status = tailscale_status()
    if status.get('BackendState') != 'Running' or not Path('/sys/class/net/tailscale0').exists():
        raise RuntimeError('Tailscale 未连接或缺少内核 tailscale0')
    node = required_env('TS_EXIT_NODE')
    peer = next((peer for peer in status.get('Peer', {}).values() if node in peer.get('TailscaleIPs', [])), None)
    if not peer or not peer.get('Online') or not peer.get('ExitNode'):
        raise RuntimeError('大陆 Exit Node 不在线或未选中，请检查出口批准和访问规则')
    result = subprocess.run(['tailscale', 'ping', '--c=1', '--until-direct=false', '--timeout=20s', node],
                            capture_output=True, text=True)
    print(result.stdout + result.stderr, flush=True)
    if result.returncode:
        print('节点 ping 未确认；继续用实际 HTTPS 出口验证。', flush=True)


def verify_ipv6():
    try:
        trace = curl_trace(6)
    except RuntimeError:
        if os.getenv('RUNNER_PUBLIC_IPV6'):
            raise
        print('Runner 没有原生 IPv6 出口，非目标 IPv6 不会回落到 Exit Node。', flush=True)
        return
    verify_runner_trace(trace)
    print('普通 IPv6 请求保持 Runner 原始出口。', flush=True)


def verify_target_exit():
    address = socket.getaddrinfo('www.cloudflare.com', 443, socket.AF_INET, socket.SOCK_STREAM)[0][4][0]
    # A short-lived validation IP exercises the exact target mark/NAT path before Chrome starts.
    nft_element('add', address)
    try:
        trace = curl_trace(4, resolved_ipv4=address)
        verify_exit_trace(trace)
        print('目标 TUN 路径实际出口：' + trace['ip'] + '，CN，与大陆服务器一致。', flush=True)
    finally:
        nft_element('delete', address)
    verify_runner_trace(curl_trace(4))
    print('已删除临时验证 IP，普通请求重新确认 Runner 出口。', flush=True)


def verify_domain_routes():
    for domain in domain_names():
        addresses = sorted({item[4][0] for item in socket.getaddrinfo(domain, 443)})
        for address in addresses:
            nft_element('get', address)
            if route_device(address, marked=True) != 'tailscale0':
                raise RuntimeError('豆包目标 IP 未指向 Tailscale：' + domain)
        print('目标 DNS 已进入分流集合：' + domain + ' ' + json.dumps(addresses), flush=True)


def verify_direct_services():
    interface = json.loads(STATE.read_text())['interface']
    domains = ['api.github.com', 'pypi.org', 'files.pythonhosted.org']
    if os.getenv('SUPABASE_URL'):
        domains.append(urlsplit(os.environ['SUPABASE_URL']).hostname)
    sets = json.loads(subprocess.check_output(['sudo', 'nft', '-j', 'list', 'table', 'inet', 'learnwords'], text=True))
    targets = {element for item in sets['nftables'] if 'set' in item
               for element in item['set'].get('elem', []) if isinstance(element, str)}
    for domain in domains:
        addresses = {item[4][0] for item in socket.getaddrinfo(domain, 443, socket.AF_INET)}
        if targets.intersection(addresses) or any(route_device(address) != interface for address in addresses):
            raise RuntimeError('非目标服务与分流 IP 重叠或没有走 Runner：' + domain)
        print('已确认使用 Runner 出口：' + domain, flush=True)


def diagnostics():
    commands = [['ip', '-4', 'rule'], ['ip', '-6', 'rule'], ['ip', '-4', 'route', 'show', 'table', '52'],
                ['sudo', 'nft', 'list', 'table', 'inet', 'learnwords'], ['resolvectl', 'status'], ['tailscale', 'netcheck']]
    for command in commands:
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=25)
            print(' '.join(command) + '\n' + result.stdout + result.stderr, flush=True)
        except (OSError, subprocess.TimeoutExpired) as error:
            print(' '.join(command) + ': ' + type(error).__name__, flush=True)


if __name__ == '__main__':
    main()
