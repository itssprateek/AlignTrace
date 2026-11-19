import copy
import unittest
from alignment.ingest import join_records


class JoinTests(unittest.TestCase):
    def setUp(self):
        self.main = {"s1": {"gt_test_files": ["steps/a.py"], "base_commit": "rev"}}
        self.sidecar = {"s1": {"files": [{"path": "steps/a.py", "content": "assert True\n"}]}}

    def test_shared_sources_are_deduplicated_without_labelling(self):
        self.main["s2"] = copy.deepcopy(self.main["s1"])
        self.sidecar["s2"] = copy.deepcopy(self.sidecar["s1"])
        records, sources = join_records(self.main, self.sidecar)
        self.assertEqual(len(records), 2)
        self.assertEqual(len(sources), 1)
        self.assertEqual(records[0]["annotation_status"], "not_labelled")

    def test_missing_sidecar_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "IDs do not match"):
            join_records(self.main, {})

    def test_missing_test_file_is_rejected(self):
        self.sidecar["s1"]["files"] = []
        with self.assertRaisesRegex(ValueError, "paths do not match"):
            join_records(self.main, self.sidecar)

    def test_conflicting_shared_source_is_rejected(self):
        self.main["s2"] = copy.deepcopy(self.main["s1"])
        self.sidecar["s2"] = copy.deepcopy(self.sidecar["s1"])
        self.sidecar["s2"]["files"][0]["content"] = "assert False\n"
        with self.assertRaisesRegex(ValueError, "Conflicting content"):
            join_records(self.main, self.sidecar)

    def test_unsafe_source_path_is_rejected(self):
        self.main["s1"]["gt_test_files"] = ["../outside.py"]
        self.sidecar["s1"]["files"][0]["path"] = "../outside.py"
        with self.assertRaisesRegex(ValueError, "Unsafe source"):
            join_records(self.main, self.sidecar)
