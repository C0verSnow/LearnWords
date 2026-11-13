import json
import os
import tempfile
import threading
import unittest
from email.parser import BytesParser
from email.policy import default
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from src.main import notify_delivery
from src.telegram import send_document


class TelegramServer(BaseHTTPRequestHandler):
    def do_POST(self):
        raw = self.rfile.read(int(self.headers["Content-Length"]))
        if self.path == "/bottest/sendDocument":
            message = BytesParser(policy=default).parsebytes(
                f"Content-Type: {self.headers['Content-Type']}\r\n\r\n".encode() + raw)
            parts = {part.get_param("name", header="content-disposition"): part
                     for part in message.iter_parts()}
            document = parts["document"]
            self.server.documents.append({"chat_id": parts["chat_id"].get_payload(decode=True).decode(),
                                          "name": document.get_filename(),
                                          "content": document.get_payload(decode=True)})
            status, body = self.server.document_responses.get(document.get_filename(), (200, {"ok": True}))
        elif self.path == "/bottest/sendMessage":
            self.server.messages.append(json.loads(raw))
            status, body = self.server.message_response
        else:
            status, body = 404, {"ok": False}
        self.send_response(status)
        self.end_headers()
        self.wfile.write(body if isinstance(body, bytes) else json.dumps(body).encode())

    def log_message(self, *args):
        pass


class TelegramTests(unittest.TestCase):
    def setUp(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), TelegramServer)
        self.server.documents = []
        self.server.messages = []
        self.server.document_responses = {}
        self.server.message_response = (200, {"ok": True})
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = patch("src.telegram.API_URL", f"http://127.0.0.1:{self.server.server_port}")
        self.url.start()
        self.addCleanup(self.url.stop)

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def test_uploads_both_file_types_as_multipart_with_original_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            for suffix in ("apkg", "zip"):
                path = Path(directory) / f"cards.{suffix}"
                content = b"PK\x03\x04\x00\xff\r\n" + suffix.encode()
                path.write_bytes(content)
                send_document("test", "9", path)
                self.assertEqual(self.server.documents[-1],
                                 {"chat_id": "9", "name": path.name, "content": content})

    def test_api_http_and_invalid_json_errors_are_sanitized(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cards.apkg"
            path.write_bytes(b"apkg")
            for response in ((200, {"ok": False}), (403, {"ok": False}), (200, b"invalid json")):
                with self.subTest(response=response):
                    self.server.document_responses[path.name] = response
                    with self.assertRaisesRegex(RuntimeError, "^Telegram 文件发送失败$"):
                        send_document("test", "9", path)

    def test_file_limit_and_missing_file_do_not_make_http_requests(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cards.zip"
            with path.open("wb") as stream:
                stream.truncate(50_000_001)
            with self.assertRaisesRegex(RuntimeError, "50 MB"):
                send_document("test", "9", path)
            path.unlink()
            with self.assertRaisesRegex(RuntimeError, "Telegram 文件发送失败"):
                send_document("test", "9", path)
            self.assertEqual(self.server.documents, [])

    def test_delivery_continues_after_summary_and_first_document_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            files = [output / "cards.apkg", output / "cards.zip"]
            for path in files:
                path.write_bytes(path.suffix.encode())
            self.server.message_response = (500, {"ok": False})
            self.server.document_responses[files[0].name] = (200, {"ok": False})
            manifest = {"task_id": "tg-7", "stage": "published", "succeeded": ["approach"],
                        "failed": {}, "shortfall": 0, "requested": 1,
                        "release_url": "https://example.test/release"}
            with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "test"}):
                notify_delivery("9", manifest, None, output, files)
            self.assertEqual([d["name"] for d in self.server.documents], [p.name for p in files])
            self.assertIn("Release 下载", self.server.messages[-1]["text"])
            self.assertIn(manifest["release_url"], self.server.messages[-1]["text"])
            self.assertEqual(manifest["stage"], "published")

    def test_manual_run_without_token_or_chat_skips_file_delivery(self):
        manifest = {"task_id": "tg-7", "stage": "published", "succeeded": [], "failed": {},
                    "shortfall": 0, "requested": 1, "release_url": "https://example.test/release"}
        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": ""}):
            notify_delivery("9", manifest, None, None)
        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "test"}):
            notify_delivery("", manifest, None, None)
        self.assertEqual(self.server.documents, [])
        self.assertEqual(self.server.messages, [])
