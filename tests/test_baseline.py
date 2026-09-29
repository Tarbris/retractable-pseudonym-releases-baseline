import csv
import hashlib
import hmac
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from pseudonym.export import FIELDS, export_directory, read_tables, token


class BaselineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "in"
        self.source.mkdir()
        self.target = self.root / "out"
        self.rows = {
            "subjects": [
                {"row_id": "s2", "tenant": "beta", "local_id": "42", "name": "Synthetic B"},
                {"row_id": "s1", "tenant": "alpha", "local_id": "42", "name": "Synthetic A"},
            ],
            "visits": [{"row_id": "v1", "tenant": "alpha", "subject_id": "42", "category": "demo"}],
            "referrals": [{"row_id": "r1", "from_tenant": "alpha", "from_id": "42",
                           "to_tenant": "beta", "to_id": "42", "note": "fictional"}],
        }

    def write(self):
        for table, fields in FIELDS.items():
            with (self.source / (table + ".csv")).open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=fields)
                writer.writeheader()
                writer.writerows(self.rows[table])

    def exported(self):
        result = {}
        for table in FIELDS:
            with (self.target / (table + ".csv")).open(encoding="utf-8", newline="") as stream:
                result[table] = list(csv.DictReader(stream))
        return result

    def test_token_message_encoding(self):
        expected = "ps_" + hmac.new(b"demo", b'person\x00["alpha","42"]', hashlib.sha256).hexdigest()
        self.assertEqual(token("demo", ("alpha", "42")), expected)

    def test_cross_file_references_and_tenant_scope(self):
        self.write()
        export_directory(self.source, self.target, "demo")
        result = self.exported()
        b, a = result["subjects"]
        self.assertNotEqual(a["local_id"], b["local_id"])
        self.assertEqual(result["visits"][0]["subject_id"], a["local_id"])
        self.assertEqual(result["referrals"][0]["from_id"], a["local_id"])
        self.assertEqual(result["referrals"][0]["to_id"], b["local_id"])

    def test_row_order_headers_and_redactions(self):
        self.rows["subjects"][0]["name"] = "合成,姓名\n第二行"
        self.write()
        export_directory(self.source, self.target, "demo")
        result = self.exported()
        self.assertEqual([r["row_id"] for r in result["subjects"]], ["s2", "s1"])
        self.assertTrue(all(r["name"] == "" for r in result["subjects"]))
        self.assertEqual(result["referrals"][0]["note"], "")
        self.assertEqual(result["visits"][0]["category"], "demo")
        for table, fields in FIELDS.items():
            with (self.target / (table + ".csv")).open(encoding="utf-8", newline="") as stream:
                self.assertEqual(next(csv.reader(stream)), list(fields))

    def test_seed_repeatability_and_variation(self):
        self.write()
        export_directory(self.source, self.target, "first")
        old = {p.name: p.read_bytes() for p in self.target.iterdir()}
        export_directory(self.source, self.target, "first")
        self.assertEqual(old, {p.name: p.read_bytes() for p in self.target.iterdir()})
        export_directory(self.source, self.target, "second")
        self.assertNotEqual(old["subjects.csv"], (self.target / "subjects.csv").read_bytes())

    def test_invalid_reference_does_not_touch_output(self):
        self.rows["visits"][0]["subject_id"] = "missing"
        self.write()
        self.target.mkdir()
        marker = self.target / "subjects.csv"
        marker.write_text("old output", encoding="utf-8")
        with self.assertRaises(ValueError):
            export_directory(self.source, self.target, "demo")
        self.assertEqual(marker.read_text(encoding="utf-8"), "old output")
        self.assertEqual(len(list(self.target.iterdir())), 1)

    def test_duplicate_subject_identity_rejected(self):
        self.rows["subjects"][0]["tenant"] = "alpha"
        self.write()
        with self.assertRaisesRegex(ValueError, "duplicate subject identity"):
            read_tables(self.source)

    def test_duplicate_row_id_rejected(self):
        self.rows["subjects"][0]["row_id"] = "s1"
        self.write()
        with self.assertRaisesRegex(ValueError, "duplicate row_id"):
            read_tables(self.source)

    def test_cli_success_and_no_serve_in_v1(self):
        self.write()
        completed = subprocess.run([sys.executable, "-m", "pseudonym", "export",
                                    "--input", str(self.source), "--output", str(self.target),
                                    "--seed", "demo"], capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        absent = subprocess.run([sys.executable, "-m", "pseudonym", "serve", "--db", "unused"],
                                capture_output=True, text=True)
        self.assertNotEqual(absent.returncode, 0)


if __name__ == "__main__":
    unittest.main()
