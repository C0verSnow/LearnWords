import re
from dataclasses import dataclass

from src.github import GitHubError
from src.telegram import HELP


@dataclass(frozen=True)
class Command:
    name: str
    count: int = 0
    mode: str = "next"


def handle_command(command, update_id, chat_id, github):
    if command.name == "help":
        return HELP
    if command.name == "status":
        return github.latest_status(chat_id)
    if command.name == "release":
        return github.latest_release()
    request_id = f"tg-{update_id}"
    payload = {"count": str(command.count), "mode": command.mode,
               "request_id": request_id, "chat_id": str(chat_id)}
    if not github.claim(request_id, payload):
        return "这条指令已经受理，不会重复创建任务。用 /status 查看进度。"
    try:
        github.dispatch(payload)
    except GitHubError:
        # Preserve the ID so a transport timeout cannot silently enqueue a second job.
        return (f"GitHub 未确认受理，任务号：{request_id}。请先用 /status 检查；"
                "若没有任务，可在 Actions 手动填写这个任务号重试。")
    return (f"已接收制卡任务。\n请求数量：{command.count}\n选词方式：{command.mode}"
            f"\n任务号：{request_id}\n当前状态：等待 GitHub Actions 执行")


def parse_command(text, max_cards):
    parts = text.strip().split()
    if not parts:
        raise ValueError(HELP)
    name = parts[0].split("@", 1)[0]
    if name in ("/help", "/start", "/status", "/release") and len(parts) == 1:
        return Command("help" if name == "/start" else name[1:])
    if name != "/make" or len(parts) not in (2, 3):
        raise ValueError(HELP)
    if not re.fullmatch(r"[0-9]{1,3}", parts[1]) or not 1 <= int(parts[1]) <= max_cards:
        raise ValueError(f"数量请填 1–{max_cards} 的整数。")
    mode = parts[2] if len(parts) == 3 else "next"
    if mode not in ("next", "random"):
        raise ValueError("选词方式只能填 next 或 random。")
    return Command("make", int(parts[1]), mode)


def parse_update(update, allowed_ids):
    if not isinstance(update, dict) or type(update.get("update_id")) is not int:
        raise ValueError("Telegram 更新格式错误")
    message = update.get("message")
    if not isinstance(message, dict):
        return None
    user = message.get("from", {})
    chat = message.get("chat", {})
    if not isinstance(user, dict) or not isinstance(chat, dict):
        raise ValueError("Telegram 消息格式错误")
    if str(user.get("id")) not in allowed_ids or chat.get("type") != "private":
        raise PermissionError("仅允许授权用户私聊")
    if type(chat.get("id")) is not int:
        raise ValueError("Telegram 聊天格式错误")
    if not isinstance(message.get("text"), str):
        return None
    return update["update_id"], chat["id"], message["text"]
