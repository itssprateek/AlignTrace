import hashlib
import unittest
from alignment.packet import build_packet


class PacketTests(unittest.TestCase):
    def source(self, path, content):
        return {"source_id": "rev:" + path, "revision": "rev", "path": path,
                "content": content, "sha256": hashlib.sha256(content.encode()).hexdigest()}

    def build(self, code, other=None, text="Then output is correct"):
        source = self.source("features/steps/api.py", code)
        sources = {source["source_id"]: source}
        if other:
            sources[other["source_id"]] = other
        record = {"instance_id": "scenario-1", "dataset_revision": "dataset-rev",
                  "test_source_ids": list(sources),
                  "source_record": {"base_commit": "rev", "feature_commit": "rev",
                                    "feature": {"file_path": "features/test.feature", "background": None},
                                    "scenario": {"kind": "scenario", "line": 3, "gherkin": text}}}
        return build_packet(record, sources)

    def test_exact_step_assertion_and_blank_labels(self):
        packet = self.build('@then("output is correct")\ndef check(context):\n    assert context.value == 3\n')
        candidate = packet["steps"][0]["candidates"][0]
        self.assertEqual(candidate["assertions"][0]["start_line"], 3)
        self.assertIsNone(packet["human_review"]["completeness"])
        self.assertFalse(packet["collection_review_complete"])

    def test_no_borrowing_neighbouring_assertion_or_unused_helper(self):
        helper = self.source("features/steps/helpers.py", 'def helper():\n    assert True\n')
        packet = self.build('from helpers import helper\n@then("output is correct")\ndef check(context):\n    pass\ndef other(context):\n    helper()\n    assert False\n', helper)
        candidate = packet["steps"][0]["candidates"][0]
        self.assertEqual(candidate["assertions"], [])
        self.assertEqual(candidate["helper_candidates"], [])
        self.assertTrue(candidate["body_is_pass"])

    def test_one_hop_helper_evidence(self):
        helper = self.source("features/steps/helpers.py", 'def helper(value):\n    deeper(value)\n    assert value == 3\n')
        packet = self.build('from helpers import helper\n@then("output is correct")\ndef check(context):\n    helper(context.value)\n', helper)
        candidate = packet["steps"][0]["candidates"][0]
        self.assertEqual(len(candidate["helper_candidates"]), 1)
        self.assertEqual(len(candidate["helper_candidates"][0]["assertions"]), 1)
        self.assertTrue(candidate["helper_candidates"][0]["deeper_calls_not_expanded"])

    def test_duplicate_literal_binding_is_ambiguous(self):
        packet = self.build('@then("output is correct")\ndef first(c):\n    pass\n@then("output is correct")\ndef second(c):\n    pass\n')
        self.assertEqual(packet["steps"][0]["match_status"], "ambiguous")

    def test_parameterised_step_remains_unresolved(self):
        packet = self.build('@then("value is {number}")\ndef check(c, number):\n    assert c.value == number\n', text="Then value is 3")
        self.assertEqual(packet["steps"][0]["match_status"], "unresolved")

    def test_nested_assertions_not_assigned_to_outer_step(self):
        packet = self.build('@then("output is correct")\ndef check(c):\n    def inner():\n        assert False\n    pass\n')
        self.assertEqual(packet["steps"][0]["candidates"][0]["assertions"], [])
