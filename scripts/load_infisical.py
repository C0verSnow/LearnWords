import json
import os
from pathlib import Path
import subprocess
import sys
import uuid


def main():
    env = authentication_environment()
    domain = env["INFISICAL_API_URL"]
    env["INFISICAL_TOKEN"] = capture([
        "infisical", "login", "--method=universal-auth", "--silent", "--plain", "--domain=" + domain,
    ], env).strip()
    mask(env["INFISICAL_TOKEN"])
    raw = capture([
        "infisical", "secrets-manager", "secrets", "get", "--silent", "--output=json",
        "--expand=false", "--include-imports=false", "--domain=" + domain,
        "--projectId=" + env["INFISICAL_PROJECT_ID"], "--env=" + env["INFISICAL_ENVIRONMENT"],
        "--path=" + env["INFISICAL_SECRET_PATH"],
    ], env)
    values = {row["secretKey"]: row["secretValue"] for row in json.loads(raw)}
    required = ["BROWSER_PROFILE_KEY", "SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY",
                "TS_OAUTH_CLIENT_ID", "TS_OAUTH_SECRET", "TS_EXIT_NODE", "TS_EXPECTED_IPV4",
                "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"]
    if any(not values.get(key) for key in required):
        raise RuntimeError("Infisical runner configuration is incomplete")
    # Deployment credentials must never replace the job's short-lived GitHub token.
    allowed = required + ["TS_EXPECTED_IPV6", "SESSION_MODE", "MAX_CARDS", "SUPABASE_SESSION_BUCKET",
                          "SUPABASE_SESSION_OBJECT", "SUPABASE_PROFILE_OBJECT"]
    with Path(os.environ["GITHUB_ENV"]).open("a") as target:
        for key in allowed:
            if key in values:
                value = values[key]
                if value:
                    mask(value)
                delimiter = "infisical_" + uuid.uuid4().hex
                target.write(f"{key}<<{delimiter}\n{value}\n{delimiter}\n")
    print("Infisical runner configuration loaded")


def authentication_environment():
    required = ["INFISICAL_CLIENT_ID", "INFISICAL_CLIENT_SECRET", "INFISICAL_PROJECT_ID",
                "INFISICAL_ENVIRONMENT", "INFISICAL_SECRET_PATH", "INFISICAL_API_URL"]
    if any(not os.getenv(key) for key in required):
        raise RuntimeError("Infisical bootstrap configuration is missing")
    env = os.environ.copy()
    env["INFISICAL_UNIVERSAL_AUTH_CLIENT_ID"] = env.pop("INFISICAL_CLIENT_ID")
    env["INFISICAL_UNIVERSAL_AUTH_CLIENT_SECRET"] = env.pop("INFISICAL_CLIENT_SECRET")
    return env


def capture(command, env):
    result = subprocess.run(command, env=env, capture_output=True, text=True, timeout=60)
    if result.returncode:
        raise RuntimeError("Infisical request failed; sensitive output suppressed")
    return result.stdout


def mask(value):
    escaped = value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    print("::add-mask::" + escaped, flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print("Infisical configuration failed; no application started", file=sys.stderr)
        sys.exit(1)
