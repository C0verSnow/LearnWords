import json
import os
import tarfile
import tempfile
from pathlib import Path

import requests

from src.config import required_env


def read_session():
    path = Path(os.getenv("SESSION_FILE", ".session/doubao.json"))
    if os.getenv("SUPABASE_URL"):
        url = (required_env("SUPABASE_URL").rstrip("/") + "/storage/v1/object/authenticated/"
               + os.getenv("SUPABASE_SESSION_BUCKET", "browser-sessions") + "/"
               + os.getenv("SUPABASE_SESSION_OBJECT", "doubao.json"))
        try:
            response = requests.get(url, headers={
                "Authorization": f"Bearer {required_env('SUPABASE_SERVICE_ROLE_KEY')}",
                "apikey": required_env("SUPABASE_SERVICE_ROLE_KEY"),
            }, timeout=20)
            if not response.ok:
                raise RuntimeError(f"会话下载失败（HTTP {response.status_code}）")
            data = response.json()
        except requests.RequestException:
            raise RuntimeError("会话下载失败") from None
    else:
        if not path.exists():
            raise RuntimeError("没有会话文件，请先按 docs/session-research.md 完成登录实验")
        data = json.loads(path.read_text(encoding="utf-8"))
    validate_session(data)
    return data


def restore_session(page, data, mode):
    page.set.cookies(data["cookies"])
    if mode == "web_storage":
        for key, value in data["local_storage"].items():
            page.set.local_storage(key, value)
        for key, value in data["session_storage"].items():
            page.set.session_storage(key, value)
    page.refresh()


def export_session(page, path):
    data = {"version": 1, "cookies": page.cookies(all_domains=True, all_info=True),
            "local_storage": page.local_storage(), "session_storage": page.session_storage()}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    path.chmod(0o600)


def save_profile(directory):
    with tempfile.TemporaryFile() as stream:
        with tarfile.open(fileobj=stream, mode="w:gz") as archive:
            archive.add(directory, arcname=".", filter=profile_archive_entry)
        stream.seek(0)
        print(f"[DEBUG-profile] archive bytes: {os.fstat(stream.fileno()).st_size}", flush=True)
        try:
            response = requests.post(profile_url(), data=stream, headers={
                "Authorization": f"Bearer {required_env('SUPABASE_SERVICE_ROLE_KEY')}",
                "apikey": required_env("SUPABASE_SERVICE_ROLE_KEY"),
                "Content-Type": "application/gzip", "x-upsert": "true",
            }, timeout=120)
        except requests.RequestException:
            raise RuntimeError("浏览器目录上传失败") from None
        if not response.ok:
            print(f"[DEBUG-profile] upload HTTP {response.status_code}", flush=True)
            print("[DEBUG-profile] size limit: " + str("maximum allowed size" in response.text), flush=True)
            raise RuntimeError(f"浏览器目录上传失败（HTTP {response.status_code}）")


def restore_profile(directory):
    try:
        response = requests.get(profile_url(authenticated=True), headers={
            "Authorization": f"Bearer {required_env('SUPABASE_SERVICE_ROLE_KEY')}",
            "apikey": required_env("SUPABASE_SERVICE_ROLE_KEY"),
        }, timeout=120)
    except requests.RequestException:
        raise RuntimeError("浏览器目录下载失败") from None
    if not response.ok:
        raise RuntimeError(f"浏览器目录下载失败（HTTP {response.status_code}）")
    with tempfile.TemporaryFile() as stream:
        stream.write(response.content)
        stream.seek(0)
        with tarfile.open(fileobj=stream, mode="r:gz") as archive:
            archive.extractall(directory, filter="data")


def profile_url(authenticated=False):
    return (required_env("SUPABASE_URL").rstrip("/") + "/storage/v1/object/"
            + ("authenticated/" if authenticated else "")
            + os.getenv("SUPABASE_SESSION_BUCKET", "browser-sessions") + "/"
            + os.getenv("SUPABASE_PROFILE_OBJECT", "doubao-profile.tar.gz"))


def profile_archive_entry(entry):
    # Cached assets can exceed the storage upload limit; retain the actual browser databases.
    caches = {"Cache", "Code Cache", "GPUCache", "ShaderCache", "GrShaderCache", "component_crx_cache"}
    if (entry.isfile() or entry.isdir()) and not caches.intersection(Path(entry.name).parts):
        return entry


def validate_session(data):
    if not isinstance(data, dict) or data.get("version") != 1:
        raise ValueError("会话文件版本错误")
    if not isinstance(data.get("cookies"), list):
        raise ValueError("会话文件缺少 cookies 列表")
    for cookie in data["cookies"]:
        if not isinstance(cookie, dict) or not all(isinstance(cookie.get(k), str)
                                                  for k in ("name", "value", "domain")):
            raise ValueError("Cookie 格式错误")
    for key in ("local_storage", "session_storage"):
        storage = data.get(key)
        if not isinstance(storage, dict) or any(not isinstance(k, str) or not isinstance(v, str)
                                                for k, v in storage.items()):
            raise ValueError("网页存储格式错误")
