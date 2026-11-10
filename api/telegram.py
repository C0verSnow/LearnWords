import hmac
import json
from http.server import BaseHTTPRequestHandler

from src.commands import handle_command, parse_command, parse_update
from src.config import load_config, required_env
from src.github import GitHub, GitHubError
from src.telegram import send_message


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            config = load_config()
            expected = required_env("TELEGRAM_WEBHOOK_SECRET")
            supplied = self.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
            if not hmac.compare_digest(expected.encode(), supplied.encode()):
                self.respond(403)
                return
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 65536:
                self.respond(400)
                return
            update = json.loads(self.rfile.read(length))
            parsed = parse_update(update, {value.strip() for value in required_env("TELEGRAM_ALLOWED_USER_IDS").split(",")})
            if parsed:
                update_id, chat_id, text = parsed
                github = GitHub(required_env("GITHUB_TOKEN"), required_env("GITHUB_REPOSITORY"),
                                required_env("GITHUB_REF"))
                try:
                    command = parse_command(text, config["max_cards"])
                    reply = handle_command(command, update_id, chat_id, github)
                except ValueError as error:
                    reply = str(error)
                except GitHubError as error:
                    reply = f"{error}，请稍后重试。"
                send_message(required_env("TELEGRAM_BOT_TOKEN"), chat_id, reply)
            self.respond(200)
        except PermissionError:
            self.respond(403)
        except (ValueError, TypeError):
            self.respond(400)
        except Exception as error:
            print(f"Webhook 处理失败：{type(error).__name__}", flush=True)
            self.respond(503)

    def respond(self, status):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"ok": status == 200}).encode())
