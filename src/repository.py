import json
import subprocess
from datetime import datetime, timezone


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def read_json(path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def checkpoint(root, ref):
    subprocess.run(["git", "add", "docs"], cwd=root, check=True)
    changed = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=root)
    if changed.returncode == 1:
        subprocess.run(["git", "commit", "-m", "Save card task checkpoint [skip ci]"], cwd=root, check=True)
        # Webhook request files may have arrived while Chrome was running.
        subprocess.run(["git", "pull", "--rebase", "origin", ref], cwd=root, check=True)
        subprocess.run(["git", "push", "origin", f"HEAD:{ref}"], cwd=root, check=True)
    elif changed.returncode != 0:
        raise RuntimeError("无法检查制卡记录改动")
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
