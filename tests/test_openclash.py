import json
import shlex
import subprocess
import unittest
from pathlib import Path


class OpenClashTests(unittest.TestCase):
    def test_js_generates_only_scoped_rules_and_dns_overrides(self):
        root = Path(__file__).resolve().parent.parent
        domains_path = root / "configs/doubao-domains.txt"
        original = domains_path.read_bytes()
        result = subprocess.run(["node", str(root / "scripts/generate_openclash_override.js")],
                                capture_output=True, text=True, check=True)
        subprocess.run(["sh", "-n"], input=result.stdout, text=True, check=True)
        calls = [shlex.split(line) for line in result.stdout.splitlines()
                 if line and not line.startswith("#")]
        self.assertEqual([call[0] for call in calls],
                         ["ruby_arr_insert_arr", "ruby_uniq", "ruby_arr_insert_arr", "ruby_uniq"])
        self.assertTrue(all(call[1] == "$CONFIG_FILE" for call in calls))
        self.assertEqual(calls[0][2:4], ["['rules']", "0"])
        self.assertEqual(calls[2][2:4], ["['dns']['fake-ip-filter']", "0"])
        rules = json.loads(calls[0][4])
        self.assertEqual(len(rules), 15)
        self.assertTrue(all(rule.startswith("AND,((SRC-IP-CIDR,192.168.1.245/32),(")
                            and rule.endswith(")),DIRECT") for rule in rules))
        self.assertIn("AND,((SRC-IP-CIDR,192.168.1.245/32),(DOMAIN-SUFFIX,doubao.com)),DIRECT", rules)
        self.assertIn("AND,((SRC-IP-CIDR,192.168.1.245/32),(DOMAIN,www.cloudflare.com)),DIRECT", rules)
        filters = json.loads(calls[2][4])
        self.assertEqual(len(filters), 15)
        self.assertIn("+.doubao.com", filters)
        self.assertIn("+.www.cloudflare.com", filters)
        self.assertEqual(domains_path.read_bytes(), original)
