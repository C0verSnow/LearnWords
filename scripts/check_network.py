"""Verify the kernel TUN and actual exit before opening a browser."""
import json
import os
import socket
import subprocess
from pathlib import Path

import requests

from src.config import load_config, required_env
from src.network import curl_trace, tailscale_status, verify_exit_trace


def main():
    load_config()
    try:
        verify_tailscale()
        ipv4 = curl_trace(4)
        verify_exit_trace(ipv4)
        print("IPv4 出口：" + ipv4["ip"] + "，CN，与大陆服务器一致。", flush=True)
        verify_ipv6()
        addresses = sorted({item[4][0] for item in socket.getaddrinfo("www.doubao.com", 443)})
        print("豆包 DNS：" + json.dumps(addresses), flush=True)
        with requests.Session() as session:
            session.trust_env = False
            response = session.get("https://www.doubao.com/", timeout=(10, 30))
        restricted = any(term in response.text for term in ("受区域限制", "当前地区暂不支持"))
        print(f"豆包 HTTP {response.status_code}，区域限制提示：{restricted}", flush=True)
        if not response.ok or restricted:
            raise RuntimeError("豆包网页检查未通过；出口 CN 不代表网站一定可用")
        print("网络预检通过；登录和真实对话仍由浏览器 Probe 验证。", flush=True)
    except Exception:
        diagnostics()
        raise


def verify_tailscale():
    status = tailscale_status()
    if status.get("BackendState") != "Running":
        raise RuntimeError("Tailscale 未连接，请检查授权信息")
    if not Path("/sys/class/net/tailscale0").exists():
        raise RuntimeError("缺少 tailscale0，必须使用内核 TUN，不能使用 userspace-networking")
    node = required_env("TS_EXIT_NODE")
    peer = next((peer for peer in status.get("Peer", {}).values() if node in peer.get("TailscaleIPs", [])), None)
    if not peer or not peer.get("Online") or not peer.get("ExitNode"):
        raise RuntimeError("指定 Exit Node 不在线或未选中，请检查出口批准和访问规则")
    result = subprocess.run(["tailscale", "ping", "--c=1", "--timeout=20s", node],
                            capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError("Exit Node 连接探测失败，直连或中继均未确认")
    print("Tailscale 已连接，内核 TUN 存在，指定 Exit Node 在线且已选中。", flush=True)


def verify_ipv6():
    try:
        trace = curl_trace(6)
    except RuntimeError:
        if os.getenv("TS_EXPECTED_IPV6"):
            raise
        print("IPv6 没有公网连通性；继续使用已确认的 IPv4。", flush=True)
        return
    verify_exit_trace(trace)
    print("IPv6 出口：" + trace["ip"] + "，CN，与大陆服务器一致。", flush=True)


def diagnostics():
    for command in (["ip", "-4", "rule"], ["ip", "-6", "rule"],
                    ["ip", "-4", "route", "show", "table", "52"],
                    ["ip", "-6", "route", "show", "table", "52"],
                    ["resolvectl", "status"], ["tailscale", "netcheck"]):
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=25)
            print(" ".join(command) + "\n" + result.stdout + result.stderr, flush=True)
        except (OSError, subprocess.TimeoutExpired) as error:
            print(" ".join(command) + ": " + type(error).__name__, flush=True)


if __name__ == "__main__":
    main()
