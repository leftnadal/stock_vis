import unittest
from unittest import mock

import execute_or_stop


class PublisherScopeTests(unittest.TestCase):
    def test_tuple_prefixes_are_expanded_before_startswith(self):
        root = str(execute_or_stop.ROOT.relative_to(execute_or_stop.REPO)) + "/"
        staged = [root + "preflight_result.json"]
        with mock.patch.object(execute_or_stop, "git", return_value="\n".join(staged)):
            execute_or_stop.verify_staged(("preflight_result.json",))

    def test_out_of_scope_stage_is_rejected(self):
        root = str(execute_or_stop.ROOT.relative_to(execute_or_stop.REPO)) + "/"
        staged = [root + "preflight_result.json", "research_lab/unrelated.json"]
        with mock.patch.object(execute_or_stop, "git", return_value="\n".join(staged)):
            with self.assertRaisesRegex(RuntimeError, "staged_scope_violation"):
                execute_or_stop.verify_staged(("preflight_result.json",))


if __name__ == "__main__":
    unittest.main()
