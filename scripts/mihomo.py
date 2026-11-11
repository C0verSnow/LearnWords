"""Start the runner's private Hong Kong proxy before opening Chrome."""
import gzip
import hashlib
import os
import re
import subprocess
import time
from pathlib import Path

import requests
import yaml

from scripts.remote_login import storage
from src.config import load_config

VERSION = "v1.19.33"
SHA256 = "386508bfb1c72c43b6a0eda73708ecdce82546581b0ebcb16366c53757c622b6"
PROXY = "http://127.0.0.1:7890"
CONTROLLER = "http://127.0.0.1:9090"


def main():
    load_config()
    directory = Path(".session/mihomo").resolve()
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    nodes = subscription_nodes()
    binary = install_binary(directory)
    config = {
        "mixed-port": 7890, "bind-address": "127.0.0.1", "allow-lan": False,
        "external-controller": "127.0.0.1:9090", "mode": "rule", "log-level": "silent",
        "proxies": nodes,
        "proxy-groups": [{"name": "HongKong", "type": "select",
                          "proxies": [node["name"] for node in nodes]}],
        "rules": ["MATCH,HongKong"],
    }
    path = directory / "config.yaml"
    path.write_text(yaml.safe_dump(config, allow_unicode=True), encoding="utf-8")
    path.chmod(0o600)
    process = subprocess.Popen([str(binary), "-d", str(directory), "-f", str(path)],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               start_new_session=True)
    try:
        wait_for_controller(process)
        select_hong_kong(nodes)
        with open(os.environ["GITHUB_ENV"], "a", encoding="utf-8") as stream:
            stream.write(f"BROWSER_PROXY={PROXY}\n")
        print("mihomo ready: verified Hong Kong exit; Chrome proxy configured.", flush=True)
    except Exception:
        process.terminate()
        raise


def subscription_nodes():
    subscription = os.getenv("MIHOMO_SUBSCRIPTION_URL")
    if not subscription:
        private = storage("GET", "proxy/subscription.json")
        if not isinstance(private, dict) or not isinstance(private.get("url"), str):
            raise ValueError("请配置私有 MIHOMO_SUBSCRIPTION_URL")
        subscription = private["url"]
    try:
        response = requests.get(subscription, headers={"User-Agent": "clash.meta"}, timeout=30)
        if not response.ok:
            raise RuntimeError(f"订阅下载失败（HTTP {response.status_code}）")
        data = yaml.safe_load(response.text)
    except (requests.RequestException, yaml.YAMLError):
        raise RuntimeError("订阅下载或解析失败，请使用 Clash/mihomo YAML 订阅") from None
    if not isinstance(data, dict) or not isinstance(data.get("proxies"), list):
        raise ValueError("订阅必须包含 proxies 节点列表")
    nodes = data["proxies"]
    if any(not isinstance(node, dict) or not isinstance(node.get("name"), str) for node in nodes):
        raise ValueError("订阅节点缺少名称")
    selected = [node for node in nodes
                if re.search(r"香港|🇭🇰|\bHK\b|Hong\s*Kong", node["name"], re.I)]
    if not selected:
        raise ValueError("订阅中没有香港节点")
    print(f"Private subscription loaded: {len(selected)} Hong Kong candidates.", flush=True)
    return selected


def install_binary(directory):
    asset = f"mihomo-linux-amd64-compatible-{VERSION}.gz"
    response = requests.get(f"https://github.com/MetaCubeX/mihomo/releases/download/{VERSION}/{asset}",
                            timeout=90)
    response.raise_for_status()
    if hashlib.sha256(response.content).hexdigest() != SHA256:
        raise RuntimeError("mihomo 下载校验失败")
    binary = directory / "mihomo"
    binary.write_bytes(gzip.decompress(response.content))
    binary.chmod(0o700)
    return binary


def wait_for_controller(process):
    for _ in range(30):
        if process.poll() is not None:
            raise RuntimeError("mihomo 启动失败，请检查订阅节点配置")
        try:
            if requests.get(CONTROLLER + "/version", timeout=1).ok:
                return
        except requests.RequestException:
            pass
        time.sleep(1)
    raise TimeoutError("mihomo 控制接口未就绪")


def select_hong_kong(nodes):
    for index, node in enumerate(nodes, 1):
        response = requests.put(CONTROLLER + "/proxies/HongKong",
                                json={"name": node["name"]}, timeout=5)
        response.raise_for_status()
        try:
            response = requests.get("https://www.cloudflare.com/cdn-cgi/trace",
                                    proxies={"http": PROXY, "https": PROXY}, timeout=15)
            if response.ok and "loc=HK" in response.text.splitlines():
                print(f"Hong Kong candidate {index}: exit country HK confirmed.", flush=True)
                return
        except requests.RequestException:
            pass
    raise RuntimeError("香港节点均未通过真实出口检查，停止浏览器任务")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        # Subscription/parser/network exceptions can contain private URLs or node credentials.
        print("mihomo setup failed: " + type(error).__name__, flush=True)
        raise SystemExit(1) from None
