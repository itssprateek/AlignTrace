import hashlib
from pathlib import Path
import sqlite3
import tempfile
import unittest
from alignment.records import Finding, SourceSpan
from alignment.store import save_finding


class EvidenceSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "step.py"
        self.source.write_text("assert result == 3\n", encoding="utf-8")
        self.span = SourceSpan("step.py", "fixture-v1", hashlib.sha256(self.source.read_bytes()).hexdigest(),
                               1, 1, "assert result == 3")

    def record(self, **changes):
        values = dict(case_id="c1", condition_id="r1", collection_version="fixture-v1",
                      completeness="uncertain", evidence_route="unknown", conflict="uncertain",
                      origin="artificial_demo", search_complete=False, reason="Fixture",
                      uncertainty_reason="Incomplete context", evidence=[self.span])
        values.update(changes)
        return Finding(**values)

    def test_modified_source_is_rejected(self):
        self.source.write_text("assert result == 4\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            self.span.verify(self.root)

    def test_fabricated_span_text_is_rejected(self):
        self.span.text = "assert result == 5"
        with self.assertRaisesRegex(ValueError, "text mismatch"):
            self.span.verify(self.root)

    def test_path_escape_is_rejected(self):
        self.span.path = "../outside.py"
        with self.assertRaisesRegex(ValueError, "source root"):
            self.span.verify(self.root)

    def test_absence_requires_full_review(self):
        for label in ("partial", "no_support_found"):
            with self.subTest(label=label), self.assertRaisesRegex(ValueError, "completed collection"):
                self.record(completeness=label).validate(self.root)

    def test_uncertainty_requires_reason(self):
        with self.assertRaisesRegex(ValueError, "explanation"):
            self.record(uncertainty_reason="").validate(self.root)

    def test_support_requires_real_evidence(self):
        with self.assertRaisesRegex(ValueError, "require evidence"):
            self.record(completeness="sufficient", evidence_route="direct", evidence=[]).validate(self.root)

    def test_support_and_conflict_can_coexist(self):
        # Contract permits both; semantic sufficiency is a separate research assessment.
        self.record(completeness="sufficient", evidence_route="direct", conflict="present").validate(self.root)

    def test_storage_validates_before_writing_and_is_idempotent(self):
        db = self.root / "records.sqlite"
        with self.assertRaises(ValueError):
            save_finding(db, self.record(completeness="no_support_found"), self.root)
        self.assertFalse(db.exists())
        save_finding(db, self.record(), self.root)
        save_finding(db, self.record(), self.root)
        with sqlite3.connect(str(db)) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM findings").fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()
