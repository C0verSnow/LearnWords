import unittest

from src.commands import parse_command, parse_update
from src.session import validate_session


class CommandTests(unittest.TestCase):
    def test_commands(self):
        self.assertEqual(parse_command("/make 20", 100).mode, "next")
        self.assertEqual(parse_command("/make@MyBot 5 random", 100).count, 5)
        for text in ("/make 0", "/make -1", "/make 101", "/make 1.5", "/make 2 unknown",
                     "/make", "/make 1 next extra", "/status extra", "/make 999999999999999999"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_command(text, 100)
        for name in ("status", "release", "help"):
            self.assertEqual(parse_command(f"/{name}", 100).name, name)

    def test_update_authorization_and_unsupported_updates(self):
        update = {"update_id": 11, "message": {"from": {"id": 9}, "chat": {"id": 9, "type": "private"},
                                               "text": "/make 2"}}
        self.assertEqual(parse_update(update, {"9"}), (11, 9, "/make 2"))
        with self.assertRaises(PermissionError):
            parse_update(update, {"10"})
        update["message"]["chat"]["type"] = "group"
        with self.assertRaises(PermissionError):
            parse_update(update, {"9"})
        self.assertIsNone(parse_update({"update_id": 12, "edited_message": {}}, {"9"}))
        with self.assertRaises(ValueError):
            parse_update({"update_id": True}, {"9"})

    def test_session_is_an_explicit_versioned_experiment(self):
        valid = {"version": 1, "cookies": [{"name": "a", "value": "b", "domain": ".deepseek.com"}],
                 "local_storage": {}, "session_storage": {}}
        validate_session(valid)
        for invalid in ({}, {**valid, "cookies": "cookie"}, {**valid, "local_storage": {"x": 1}}):
            with self.assertRaises(ValueError):
                validate_session(invalid)
