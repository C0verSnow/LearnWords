import json
import io
import os
import threading
import tempfile
import tarfile
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from src.content import FIELDS
from src.doubao import Doubao
from src.main import generate_cards
from src.session import export_session, save_profile, restore_profile, PROFILE_AAD
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from scripts.remote_login import apply_command


class BrowserPage(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/storage/v1/object/authenticated/"):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(self.server.profile_archive)
            return
        content = {"Word": "approach", **dict.fromkeys(FIELDS, "An example. 中文说明。")}
        page = """<!doctype html><meta charset="utf-8">
        <div id="account">test account</div><button id="new">new chat</button>
        <input id="login-user" type="text"><input id="login-password" type="password">
        <div id="editor" contenteditable="true"><p><br></p></div><button id="send">send</button>
        <pre id="answer"></pre>
        <script>
        document.querySelector('#new').onclick = () => {
          document.querySelector('#answer').textContent = '';
        };
        document.querySelector('#editor').onkeydown = event => {
          if (event.key === 'Enter') {
            event.preventDefault();

          }
        };
        document.querySelector('#send').onclick = () => {
          window.submittedText = document.querySelector('#editor').innerText;
          document.querySelector('#answer').textContent = RESPONSE;
          document.querySelector('#editor').textContent = '';
        };
        </script>""".replace("RESPONSE", json.dumps(json.dumps(content, ensure_ascii=False)))
        if self.path == "/rejected":
            page = page.replace(
                "document.querySelector('#answer').textContent = "
                + json.dumps(json.dumps(content, ensure_ascii=False)) + ";",
                "fetch('/chat/completion', {method: 'POST'}).then(() => {"
                "document.querySelector('#answer').innerHTML = '<span id=failed>发送失败</span>';"
                "});")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(page.encode())

    def do_POST(self):
        if self.path == "/chat/completion":
            self.server.rejections += 1
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            self.wfile.write(b'event: STREAM_ERROR\ndata: {"error_code":710022004,"error_msg":"rate limited"}\n\n')
            return
        self.server.profile_archive = self.rfile.read(int(self.headers["Content-Length"]))
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'{}')

    def log_message(self, *args):
        pass


class BrowserTests(unittest.TestCase):
    def test_rejected_message_stops_remaining_words_without_retry(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), BrowserPage)
        server.rejections = 0
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        config = {"attempts": 2, "doubao": {
            "url": f"http://127.0.0.1:{server.server_port}/rejected", "timeout": 5,
            "input": "css:#editor", "send": "css:#send", "answer": "css:#answer",
            "authenticated": "css:#account", "new_chat": "css:#new",
            "generating": "css:#not-generating", "failed": "css:#failed"}}
        manifest = {"selected": ["approach", "context"], "succeeded": [], "failed": {}}
        try:
            with tempfile.TemporaryDirectory() as directory, \
                    patch("src.main.ROOT", Path(directory)), \
                    patch.dict(os.environ, {"SESSION_MODE": "none", "SUPABASE_URL": "", "BROWSER_DIRECTORY": directory}):
                root = Path(directory)
                self.assertEqual(generate_cards(manifest, config, root, root / "manifest.json"), [])
                self.assertEqual(server.rejections, 1)
                self.assertEqual(set(manifest["failed"]), {"approach", "context"})
                for reason in manifest["failed"].values():
                    self.assertIn("发送失败", reason)
                self.assertFalse((root / "docs/explanations").exists())
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_chrome_query_and_storage_restore_in_fresh_profile(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), BrowserPage)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        config = {"url": f"http://127.0.0.1:{server.server_port}/", "timeout": 20,
                  "input": "css:#editor", "send": "css:#send", "answer": "css:#answer", "authenticated": "css:#account",
                  "new_chat": "css:#new", "generating": "css:#not-generating"}
        try:
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "session.json"
                bundle = Path(directory) / "browser"
                bundle.mkdir()
                with patch.dict(os.environ, {"SESSION_MODE": "none", "SUPABASE_URL": "", "BROWSER_DIRECTORY": directory}):
                    browser = Doubao(config, profile=bundle / "profile", ini_path=bundle / "chrome.ini")
                    try:
                        browser.restore()
                        login_fields = {"login_user": "css:#login-user", "login_password": "css:#login-password"}
                        apply_command(browser.page, login_fields,
                                      {"action": "credentials", "user": "initial-account", "password": "initial-secret"})
                        apply_command(browser.page, login_fields,
                                      {"action": "credentials", "user": "updated-account", "password": "updated-secret"})
                        self.assertEqual(browser.page.ele("css:#login-user").value, "updated-account")
                        self.assertEqual(browser.page.ele("css:#login-password").value, "updated-secret")
                        browser.page.set.local_storage("local-probe", "value")
                        browser.page.set.session_storage("session-probe", "value")
                        browser.page.set.cookies([{"name": "probe", "value": "ok", "domain": "127.0.0.1", "path": "/", "expires": time.time() + 3600}])
                        export_session(browser.page, path)
                    finally:
                        browser.close()
                with patch.dict(os.environ, {"SESSION_MODE": "profile",
                                             "SUPABASE_URL": config["url"].rstrip("/"),
                                             "SUPABASE_SERVICE_ROLE_KEY": "test-key",
                                             "SUPABASE_SESSION_BUCKET": "browser-sessions",
                                             "SUPABASE_PROFILE_OBJECT": "doubao-profile.tar.gz.enc",
                                             "BROWSER_DIRECTORY": str(Path(directory) / "restored"),
                                             "BROWSER_PROFILE_KEY": base64.urlsafe_b64encode(AESGCM.generate_key(bit_length=256)).decode()}):
                    cache = bundle / "profile/Default/Cache"
                    cache.mkdir(exist_ok=True)
                    (cache / "discard-me").write_text("Cached asset")
                    model = bundle / "profile/optimization_guide_model_store/43"
                    model.mkdir(parents=True)
                    (model / "model.bin").write_bytes(b"Downloaded Chrome prediction model")
                    save_profile(bundle)
                    encrypted_archive = server.profile_archive
                    cipher = AESGCM(base64.urlsafe_b64decode(os.environ["BROWSER_PROFILE_KEY"]))
                    self.assertFalse(encrypted_archive.startswith(b"\x1f\x8b"))
                    decrypted = cipher.decrypt(encrypted_archive[:12], encrypted_archive[12:], PROFILE_AAD)
                    self.assertLess(len(encrypted_archive), len(decrypted) + 64)
                    with tarfile.open(fileobj=io.BytesIO(decrypted), mode="r:gz") as archive:
                        self.assertNotIn("./profile/Default/Cache/discard-me", archive.getnames())
                        self.assertIn("./chrome.ini", archive.getnames())
                        self.assertNotIn("./profile/optimization_guide_model_store/43/model.bin", archive.getnames())
                    browser = Doubao(config)
                    try:
                        browser.restore()
                        browser.page.set.local_storage("after-restore", "saved-on-close")
                        self.assertTrue((browser.directory / "chrome.ini").is_file())
                        self.assertEqual(browser.page.local_storage("local-probe"), "value")
                        self.assertIn("probe", [cookie["name"] for cookie in browser.page.cookies()])
                        browser.page.ele(config["input"]).input("旧草稿")
                        self.assertEqual(browser.generate("approach")["Word"], "approach")
                        submitted = browser.page.run_js("return window.submittedText")
                        self.assertNotIn("旧草稿", submitted)
                        self.assertIn("approach", submitted)
                    finally:
                        browser.close()
                    with patch.dict(os.environ, {"BROWSER_DIRECTORY": str(Path(directory) / "second-runner")}):
                        browser = Doubao(config)
                        try:
                            browser.restore()
                            self.assertEqual(browser.page.local_storage("after-restore"), "saved-on-close")
                        finally:
                            browser.close()
                    restored = Path(directory) / "roundtrip"
                    restore_profile(restored)
                    self.assertTrue((restored / "profile/Local State").is_file())
                    server.profile_archive = encrypted_archive[:-1] + bytes([encrypted_archive[-1] ^ 1])
                    rejected = Path(directory) / "tampered"
                    with self.assertRaisesRegex(RuntimeError, "解密失败"):
                        restore_profile(rejected)
                    self.assertFalse(rejected.exists())
                    server.profile_archive = encrypted_archive
                with patch.dict(os.environ, {"SESSION_MODE": "web_storage", "SESSION_FILE": str(path), "SUPABASE_URL": "",
                                             "BROWSER_DIRECTORY": str(Path(directory) / "json-restored")}):
                    enter_config = {key: value for key, value in config.items() if key not in ("send", "new_chat")}
                    browser = Doubao(enter_config)
                    try:
                        browser.restore()
                        self.assertEqual(browser.page.local_storage("local-probe"), "value")
                        self.assertEqual(browser.page.session_storage("session-probe"), "value")
                        self.assertIn("probe", [cookie["name"] for cookie in browser.page.cookies()])
                        self.assertEqual(browser.generate("approach")["Word"], "approach")
                        self.assertEqual(browser.page.session_storage("session-probe"), "value")
                    finally:
                        browser.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join()
import base64
