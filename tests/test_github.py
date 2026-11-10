import base64
import json
import os
import subprocess
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import requests

from api.telegram import handler

from src.commands import handle_command, parse_command
from src.github import GitHub, GitHubError
from src.content import FIELDS
from src.main import run


class GitHubServer(BaseHTTPRequestHandler):
    def do_GET(self):
        if "/contents/" in self.path:
            if self.server.request_file:
                self.reply(200, {"content": base64.b64encode(b"{}").decode(), "sha": "abc"})
            else:
                self.reply(404, {})
        elif "/releases/tags/" in self.path:
            self.reply(200, self.server.release) if self.server.release else self.reply(404, {})
        elif self.path.endswith("/releases/latest"):
            self.reply(404, {})
        else:
            self.reply(200, {"workflow_runs": [{"display_title": "make-tg-7 chat-9", "status": "completed",
                                               "conclusion": "success", "html_url": "https://example.test/run"}]})

    def do_PUT(self):
        self.server.last_write = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if self.server.request_file:
            self.reply(422, {})
        else:
            self.server.request_file = True
            self.reply(201, {})

    def do_POST(self):
        raw = self.rfile.read(int(self.headers["Content-Length"]))
        if self.path.endswith("/dispatches"):
            self.server.dispatches.append(json.loads(raw))
            self.reply(self.server.dispatch_status, {})
        elif self.path.endswith("/releases"):
            self.server.release = {"id": 1, "draft": True, "assets": [], "html_url": "https://example.test/release",
                                   "upload_url": f"http://127.0.0.1:{self.server.server_port}/upload{{?name}}"}
            self.reply(201, self.server.release)
        else:
            self.server.uploads.append((self.path, raw))
            self.reply(self.server.upload_status, {})

    def do_PATCH(self):
        self.rfile.read(int(self.headers["Content-Length"]))
        self.server.release["draft"] = False
        self.reply(200, self.server.release)

    def reply(self, status, payload):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        if status != 204:
            self.wfile.write(json.dumps(payload).encode())

    def log_message(self, *args):
        pass


class GitHubTests(unittest.TestCase):
    def setUp(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), GitHubServer)
        self.server.request_file = False
        self.server.dispatches = []
        self.server.dispatch_status = 204
        self.server.release = None
        self.server.uploads = []
        self.server.upload_status = 201
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.github = GitHub("test", "owner/repo", "feature/test",
                             api_url=f"http://127.0.0.1:{self.server.server_port}")

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def test_duplicate_update_dispatches_once_with_validated_inputs(self):
        command = parse_command("/make 5 random", 100)
        self.assertIn("已接收", handle_command(command, 7, 9, self.github))
        self.assertIn("不会重复", handle_command(command, 7, 9, self.github))
        self.assertEqual(len(self.server.dispatches), 1)
        self.assertEqual(self.server.dispatches[0], {"ref": "feature/test", "inputs": {
            "count": "5", "mode": "random", "request_id": "tg-7", "chat_id": "9"}})
        self.assertIn("success", self.github.latest_status(9))
        self.assertIn("还没有", self.github.latest_status(10))
        self.assertIn("还没有", self.github.latest_release())

    def test_dispatch_failure_never_claims_success(self):
        self.server.dispatch_status = 403
        self.assertIn("未确认", handle_command(parse_command("/make 1", 100), 7, 9, self.github))

    def test_webhook_secret_authorization_and_command_over_http(self):
        webhook = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=webhook.serve_forever, daemon=True)
        thread.start()
        update = {"update_id": 7, "message": {"from": {"id": 9}, "chat": {"id": 9, "type": "private"},
                                              "text": "/make 5"}}
        url = f"http://127.0.0.1:{webhook.server_port}/api/telegram"
        env = {"TELEGRAM_WEBHOOK_SECRET": "secret", "TELEGRAM_ALLOWED_USER_IDS": "9",
               "TELEGRAM_BOT_TOKEN": "test", "GITHUB_TOKEN": "test", "GITHUB_REPOSITORY": "owner/repo",
               "GITHUB_REF": "feature/test"}
        try:
            with patch.dict(os.environ, env), patch("api.telegram.GitHub", return_value=self.github), \
                    patch("api.telegram.send_message") as messages:
                self.assertEqual(requests.post(url, json=update, timeout=10).status_code, 403)
                headers = {"X-Telegram-Bot-Api-Secret-Token": "secret"}
                self.assertEqual(requests.post(url, json=update, headers=headers, timeout=10).status_code, 200)
                self.assertIn("已接收", messages.call_args.args[2])
                update["message"]["text"] = "/make 0"
                self.assertEqual(requests.post(url, json=update, headers=headers, timeout=10).status_code, 200)
                self.assertIn("数量", messages.call_args.args[2])
                update["message"]["from"]["id"] = 10
                self.assertEqual(requests.post(url, json=update, headers=headers, timeout=10).status_code, 403)
                self.assertEqual(len(self.server.dispatches), 1)
        finally:
            webhook.shutdown()
            webhook.server_close()
            thread.join()

    def test_release_only_becomes_public_after_all_uploads(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cards.apkg"
            path.write_bytes(b"apkg")
            self.server.upload_status = 500
            with self.assertRaises(GitHubError):
                self.github.publish("tg-7", [path], "result", "abc")
            self.assertTrue(self.server.release["draft"])
            self.server.upload_status = 201
            url = self.github.publish("tg-7", [path], "result", "abc")
            self.assertFalse(self.server.release["draft"])
            self.assertEqual(url, "https://example.test/release")
            uploads = len(self.server.uploads)
            self.github.publish("tg-7", [path], "result", "abc")
            self.assertEqual(len(self.server.uploads), uploads)

    def test_runner_real_cached_content_to_release_checkpoint_and_resume(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "work"
            origin = Path(directory) / "origin.git"
            root.mkdir()
            def git(*args, cwd=root):
                return subprocess.check_output(["git", *args], cwd=cwd, stderr=subprocess.STDOUT, text=True)
            git("init", "--bare", str(origin))
            git("init", "-b", "feature/test")
            git("config", "user.name", "CI")
            git("config", "user.email", "ci@example.test")
            git("remote", "add", "origin", str(origin))
            (root / "docs/words").mkdir(parents=True)
            (root / "docs/explanations").mkdir()
            (root / "docs/words/vocabulary.txt").write_text("approach\ncontext\n")
            valid = {"Word": "approach", **dict.fromkeys(FIELDS, "English example. 中文翻译。")}
            (root / "docs/explanations/approach.json").write_text(json.dumps(valid))
            # An invalid persisted answer must fail this word rather than be counted as delivered.
            (root / "docs/explanations/context.json").write_text('{}')
            git("add", ".")
            git("commit", "-m", "fixture")
            git("push", "-u", "origin", "feature/test")
            args = SimpleNamespace(request_id="tg-7", count=3, mode="next", chat_id="")
            config = {"attempts": 2, "doubao": {}}
            with patch("src.main.ROOT", root), patch("src.main.GitHub", return_value=self.github), \
                    patch.dict(os.environ, {"GITHUB_TOKEN": "test", "GITHUB_REPOSITORY": "owner/repo"}):
                self.server.upload_status = 500
                self.assertEqual(run(args, config), 1)
                self.assertFalse((root / "docs/records/generated.json").exists())
                self.server.upload_status = 201
                self.assertEqual(run(args, config), 0)
                records = json.loads((root / "docs/records/generated.json").read_text())
                self.assertEqual(set(records), {"approach"})
                manifest = json.loads((root / "docs/manifests/tg-7.json").read_text())
                self.assertEqual(manifest["stage"], "published")
                self.assertEqual(manifest["shortfall"], 1)
                self.assertEqual(set(manifest["failed"]), {"context"})
                uploads = len(self.server.uploads)
                self.assertEqual(run(args, config), 0)
                self.assertEqual(len(self.server.uploads), uploads)
            self.assertEqual(git("status", "--porcelain").strip(), "?? output/")
            self.assertEqual(git("rev-parse", "HEAD").strip(),
                             git("rev-parse", "refs/heads/feature/test", cwd=origin).strip())
