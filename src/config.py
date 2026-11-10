import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent


def load_config():
    load_dotenv(ROOT / ".env", override=False)
    config = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    config["max_cards"] = int(os.getenv("MAX_CARDS", config["max_cards"]))
    if not 1 <= config["max_cards"] <= 100 or not 1 <= config["attempts"] <= 3:
        raise ValueError("max_cards 必须在 1–100，attempts 必须在 1–3")
    return config


def required_env(name):
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"请配置 {name}")
    return value
