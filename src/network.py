import ipaddress
import json
import os
import subprocess

from src.config import required_env

TRACE_URL = "https://www.cloudflare.com/cdn-cgi/trace"


def restore_runner_route():
    if os.getenv("GITHUB_ACTIONS") == "true" and os.getenv("TS_EXIT_NODE"):
        subprocess.run(["sudo", "tailscale", "set", "--exit-node="], check=True, timeout=30)
        print("浏览器阶段结束，已恢复 Runner 默认路由，后续仅传输加密归档。", flush=True)


def verify_browser_exit(page):
    page.get(TRACE_URL)
    trace = parse_trace(page.ele("tag:body").text)
    verify_exit_trace(trace)
    print("Chrome 出口与大陆服务器一致，地区 CN；未使用浏览器代理。", flush=True)


def parse_trace(text):
    return dict(line.split("=", 1) for line in text.splitlines() if "=" in line)


def verify_exit_trace(trace):
    address = ipaddress.ip_address(trace.get("ip", ""))
    expected = required_env("TS_EXPECTED_IPV4" if address.version == 4 else "TS_EXPECTED_IPV6")
    if address != ipaddress.ip_address(expected):
        raise RuntimeError("公网出口与大陆服务器不一致，停止访问豆包；请核对出口节点及服务器动态 IP")
    if trace.get("loc") != "CN":
        raise RuntimeError("出口地区未确认为 CN，停止访问豆包")


def curl_trace(family):
    result = subprocess.run(["curl", f"-{family}", "--noproxy", "*", "--fail", "--silent",
                             "--show-error", "--connect-timeout", "10", "--max-time", "30", TRACE_URL],
                            capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(f"IPv{family} 出口检查失败（curl {result.returncode}）")
    return parse_trace(result.stdout)


def tailscale_status():
    result = subprocess.run(["tailscale", "status", "--json"], capture_output=True, text=True, check=True)
    return json.loads(result.stdout)
