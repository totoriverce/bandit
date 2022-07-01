#
# Copyright 2014 Hewlett-Packard Development Company, L.P.
#
# SPDX-License-Identifier: Apache-2.0
import os
import sys

import testtools

from bandit.core import config as b_config
from bandit.core import constants as C
from bandit.core import manager as b_manager
from bandit.core import metrics
from bandit.core import test_set as b_test_set


class FunctionalTests(testtools.TestCase):

    """Functional tests for bandit test plugins.

    This set of tests runs bandit against each example file in turn
    and records the score returned. This is compared to a known good value.
    When new tests are added to an example the expected result should be
    adjusted to match.
    """

    def setUp(self):
        super().setUp()
        # NOTE(tkelsey): bandit is very sensitive to paths, so stitch
        # them up here for the testing environment.
        #
        path = os.path.join(os.getcwd(), "bandit", "plugins")
        b_conf = b_config.BanditConfig()
        self.b_mgr = b_manager.BanditManager(b_conf, "file")
        self.b_mgr.b_conf._settings["plugins_dir"] = path
        self.b_mgr.b_ts = b_test_set.BanditTestSet(config=b_conf)

    def run_example(self, example_script, ignore_nosec=False):
        """A helper method to run the specified test

        This method runs the test, which populates the self.b_mgr.scores
        value. Call this directly if you need to run a test, but do not
        need to test the resulting scores against specified values.
        :param example_script: Filename of an example script to test
        """
        path = os.path.join(os.getcwd(), "examples", example_script)
        self.b_mgr.ignore_nosec = ignore_nosec
        self.b_mgr.discover_files([path], True)
        self.b_mgr.run_tests()

    def check_example(self, example_script, expect, ignore_nosec=False):
        """A helper method to test the scores for example scripts.

        :param example_script: Filename of an example script to test
        :param expect: dict with expected counts of issue types
        """
        # reset scores for subsequent calls to check_example
        self.b_mgr.scores = []
        self.run_example(example_script, ignore_nosec=ignore_nosec)

        result = {
            "SEVERITY": {"UNDEFINED": 0, "LOW": 0, "MEDIUM": 0, "HIGH": 0},
            "CONFIDENCE": {"UNDEFINED": 0, "LOW": 0, "MEDIUM": 0, "HIGH": 0},
        }

        for test_scores in self.b_mgr.scores:
            for score_type in test_scores:
                self.assertIn(score_type, expect)
                for idx, rank in enumerate(C.RANKING):
                    result[score_type][rank] = (
                        test_scores[score_type][idx] // C.RANKING_VALUES[rank]
                    )

        self.assertDictEqual(expect, result)

    def check_metrics(self, example_script, expect):
        """A helper method to test the metrics being returned.

        :param example_script: Filename of an example script to test
        :param expect: dict with expected values of metrics
        """
        self.b_mgr.metrics = metrics.Metrics()
        self.b_mgr.scores = []
        self.run_example(example_script)

        # test general metrics (excludes issue counts)
        m = self.b_mgr.metrics.data
        for k in expect:
            if k != "issues":
                self.assertEqual(expect[k], m["_totals"][k])
        # test issue counts
        if "issues" in expect:
            for (criteria, default) in C.CRITERIA:
                for rank in C.RANKING:
                    label = f"{criteria}.{rank}"
                    expected = 0
                    if expect["issues"].get(criteria).get(rank):
                        expected = expect["issues"][criteria][rank]
                    self.assertEqual(expected, m["_totals"][label])

    def test_imports_aliases(self):
        """Test the `import X as Y` syntax."""
        if sys.version_info >= (3, 9):
            expect = {
                "SEVERITY": {"UNDEFINED": 0, "LOW": 4, "MEDIUM": 1, "HIGH": 4},
                "CONFIDENCE": {
                    "UNDEFINED": 0,
                    "LOW": 0,
                    "MEDIUM": 0,
                    "HIGH": 9,
                },
            }
        else:
            expect = {
                "SEVERITY": {"UNDEFINED": 0, "LOW": 4, "MEDIUM": 5, "HIGH": 0},
                "CONFIDENCE": {
                    "UNDEFINED": 0,
                    "LOW": 0,
                    "MEDIUM": 0,
                    "HIGH": 9,
                },
            }
        self.check_example("imports-aliases.py", expect)

    def test_imports_from(self):
        """Test the `from X import Y` syntax."""
        expect = {
            "SEVERITY": {"UNDEFINED": 0, "LOW": 3, "MEDIUM": 0, "HIGH": 0},
            "CONFIDENCE": {"UNDEFINED": 0, "LOW": 0, "MEDIUM": 0, "HIGH": 3},
        }
        self.check_example("imports-from.py", expect)

    def test_imports_function(self):
        """Test the `__import__` function."""
        expect = {
            "SEVERITY": {"UNDEFINED": 0, "LOW": 2, "MEDIUM": 0, "HIGH": 0},
            "CONFIDENCE": {"UNDEFINED": 0, "LOW": 0, "MEDIUM": 0, "HIGH": 2},
        }
        self.check_example("imports-function.py", expect)

    def test_imports(self):
        """Test for dangerous imports."""
        expect = {
            "SEVERITY": {"UNDEFINED": 0, "LOW": 2, "MEDIUM": 0, "HIGH": 0},
            "CONFIDENCE": {"UNDEFINED": 0, "LOW": 0, "MEDIUM": 0, "HIGH": 2},
        }
        self.check_example("imports.py", expect)

    def test_imports_using_importlib(self):
        """Test for dangerous imports using importlib."""
        expect = {
            "SEVERITY": {"UNDEFINED": 0, "LOW": 4, "MEDIUM": 0, "HIGH": 0},
            "CONFIDENCE": {"UNDEFINED": 0, "LOW": 0, "MEDIUM": 0, "HIGH": 4},
        }
        self.check_example("imports-with-importlib.py", expect)

    def test_nonsense(self):
        """Test that a syntactically invalid module is skipped."""
        self.run_example("nonsense.py")
        self.assertEqual(1, len(self.b_mgr.skipped))

    def test_okay(self):
        """Test a vulnerability-free file."""
        expect = {
            "SEVERITY": {"UNDEFINED": 0, "LOW": 0, "MEDIUM": 0, "HIGH": 0},
            "CONFIDENCE": {"UNDEFINED": 0, "LOW": 0, "MEDIUM": 0, "HIGH": 0},
        }
        self.check_example("okay.py", expect)

    def test_subdirectory_okay(self):
        """Test a vulnerability-free file under a subdirectory."""
        expect = {
            "SEVERITY": {"UNDEFINED": 0, "LOW": 0, "MEDIUM": 0, "HIGH": 0},
            "CONFIDENCE": {"UNDEFINED": 0, "LOW": 0, "MEDIUM": 0, "HIGH": 0},
        }
        self.check_example("init-py-test/subdirectory-okay.py", expect)

    def test_skip(self):
        """Test `#nosec` and `#noqa` comments."""
        expect = {
            "SEVERITY": {"UNDEFINED": 0, "LOW": 5, "MEDIUM": 0, "HIGH": 0},
            "CONFIDENCE": {"UNDEFINED": 0, "LOW": 0, "MEDIUM": 0, "HIGH": 5},
        }
        self.check_example("skip.py", expect)

    def test_ignore_skip(self):
        """Test --ignore-nosec flag."""
        expect = {
            "SEVERITY": {"UNDEFINED": 0, "LOW": 7, "MEDIUM": 0, "HIGH": 0},
            "CONFIDENCE": {"UNDEFINED": 0, "LOW": 0, "MEDIUM": 0, "HIGH": 7},
        }
        self.check_example("skip.py", expect, ignore_nosec=True)

    def test_multiline_sql_statements(self):
        """
        Test for SQL injection through string building using
        multi-line strings.
        """
        example_file = "sql_multiline_statements.py"
        confidence_low_tests = 13
        severity_medium_tests = 26
        nosec_tests = 7
        skipped_tests = 8
        if sys.version_info[:2] <= (3, 7):
            # In the case of implicit concatenation in python 3.7,
            # we know only the first line of multi-line string.
            # Thus, cases like:
            # query = ("SELECT * "
            #          "FROM foo "  # nosec
            #          f"WHERE id = {identifier}")
            # are not skipped but reported as errors.
            confidence_low_tests = 17
            severity_medium_tests = 30
            nosec_tests = 5
            skipped_tests = 6
        expect = {
            "SEVERITY": {
                "UNDEFINED": 0,
                "LOW": 0,
                "MEDIUM": severity_medium_tests,
                "HIGH": 0,
            },
            "CONFIDENCE": {
                "UNDEFINED": 0,
                "LOW": confidence_low_tests,
                "MEDIUM": 13,
                "HIGH": 0,
            },
        }
        expect_stats = {
            "nosec": nosec_tests,
            "skipped_tests": skipped_tests,
        }
        self.check_example(example_file, expect)
        self.check_metrics(example_file, expect_stats)

    def test_xml(self):
        """Test xml vulnerabilities."""
        expect = {
            "SEVERITY": {"UNDEFINED": 0, "LOW": 1, "MEDIUM": 4, "HIGH": 0},
            "CONFIDENCE": {"UNDEFINED": 0, "LOW": 0, "MEDIUM": 0, "HIGH": 5},
        }
        self.check_example("xml_etree_celementtree.py", expect)

        expect = {
            "SEVERITY": {"UNDEFINED": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 0},
            "CONFIDENCE": {"UNDEFINED": 0, "LOW": 0, "MEDIUM": 0, "HIGH": 3},
        }
        self.check_example("xml_expatbuilder.py", expect)

        expect = {
            "SEVERITY": {"UNDEFINED": 0, "LOW": 3, "MEDIUM": 1, "HIGH": 0},
            "CONFIDENCE": {"UNDEFINED": 0, "LOW": 0, "MEDIUM": 0, "HIGH": 4},
        }
        self.check_example("xml_lxml.py", expect)

        expect = {
            "SEVERITY": {"UNDEFINED": 0, "LOW": 2, "MEDIUM": 2, "HIGH": 0},
            "CONFIDENCE": {"UNDEFINED": 0, "LOW": 0, "MEDIUM": 0, "HIGH": 4},
        }
        self.check_example("xml_pulldom.py", expect)

        expect = {
            "SEVERITY": {"UNDEFINED": 0, "LOW": 0, "MEDIUM": 0, "HIGH": 1},
            "CONFIDENCE": {"UNDEFINED": 0, "LOW": 0, "MEDIUM": 0, "HIGH": 1},
        }
        self.check_example("xml_xmlrpc.py", expect)

        expect = {
            "SEVERITY": {"UNDEFINED": 0, "LOW": 1, "MEDIUM": 4, "HIGH": 0},
            "CONFIDENCE": {"UNDEFINED": 0, "LOW": 0, "MEDIUM": 0, "HIGH": 5},
        }
        self.check_example("xml_etree_elementtree.py", expect)

        expect = {
            "SEVERITY": {"UNDEFINED": 0, "LOW": 1, "MEDIUM": 1, "HIGH": 0},
            "CONFIDENCE": {"UNDEFINED": 0, "LOW": 0, "MEDIUM": 0, "HIGH": 2},
        }
        self.check_example("xml_expatreader.py", expect)

        expect = {
            "SEVERITY": {"UNDEFINED": 0, "LOW": 2, "MEDIUM": 2, "HIGH": 0},
            "CONFIDENCE": {"UNDEFINED": 0, "LOW": 0, "MEDIUM": 0, "HIGH": 4},
        }
        self.check_example("xml_minidom.py", expect)

        expect = {
            "SEVERITY": {"UNDEFINED": 0, "LOW": 2, "MEDIUM": 6, "HIGH": 0},
            "CONFIDENCE": {"UNDEFINED": 0, "LOW": 0, "MEDIUM": 0, "HIGH": 8},
        }
        self.check_example("xml_sax.py", expect)

    def test_skips(self):
        """Test catching the use of assert."""
        test = next(
            x
            for x in self.b_mgr.b_ts.tests["Assert"]
            if x.__name__ == "assert_used"
        )

        test._config = {"skips": []}
        expect = {
            "SEVERITY": {"UNDEFINED": 0, "LOW": 1, "MEDIUM": 0, "HIGH": 0},
            "CONFIDENCE": {"UNDEFINED": 0, "LOW": 0, "MEDIUM": 0, "HIGH": 1},
        }
        self.check_example("assert.py", expect)

        test._config = {"skips": ["*assert.py"]}
        expect = {
            "SEVERITY": {"UNDEFINED": 0, "LOW": 0, "MEDIUM": 0, "HIGH": 0},
            "CONFIDENCE": {"UNDEFINED": 0, "LOW": 0, "MEDIUM": 0, "HIGH": 0},
        }
        self.check_example("assert.py", expect)

        test._config = {}
        expect = {
            "SEVERITY": {"UNDEFINED": 0, "LOW": 1, "MEDIUM": 0, "HIGH": 0},
            "CONFIDENCE": {"UNDEFINED": 0, "LOW": 0, "MEDIUM": 0, "HIGH": 1},
        }
        self.check_example("assert.py", expect)

    def test_metric_gathering(self):
        expect = {
            "nosec": 2,
            "loc": 7,
            "issues": {"CONFIDENCE": {"HIGH": 5}, "SEVERITY": {"LOW": 5}},
        }
        self.check_metrics("skip.py", expect)
        expect = {
            "nosec": 0,
            "loc": 4,
            "issues": {"CONFIDENCE": {"HIGH": 2}, "SEVERITY": {"LOW": 2}},
        }
        self.check_metrics("imports.py", expect)

    def test_multiline_code(self):
        """Test issues in multiline statements return code as expected."""
        self.run_example("multiline_statement.py")
        self.assertEqual(0, len(self.b_mgr.skipped))
        self.assertEqual(1, len(self.b_mgr.files_list))
        self.assertTrue(
            self.b_mgr.files_list[0].endswith("multiline_statement.py")
        )

        issues = self.b_mgr.get_issue_list()
        self.assertEqual(3, len(issues))
        self.assertTrue(
            issues[0].fname.endswith("examples/multiline_statement.py")
        )
        self.assertEqual(1, issues[0].lineno)
        if sys.version_info >= (3, 8):
            self.assertEqual(list(range(1, 2)), issues[0].linerange)
        else:
            self.assertEqual(list(range(1, 3)), issues[0].linerange)
        self.assertIn("subprocess", issues[0].get_code())
        self.assertEqual(5, issues[1].lineno)
        self.assertEqual(list(range(3, 6 + 1)), issues[1].linerange)
        self.assertIn("shell=True", issues[1].get_code())
        self.assertEqual(11, issues[2].lineno)
        if sys.version_info >= (3, 8):
            self.assertEqual(list(range(8, 13 + 1)), issues[2].linerange)
        else:
            self.assertEqual(list(range(8, 12 + 1)), issues[2].linerange)
        self.assertIn("shell=True", issues[2].get_code())

    def test_code_line_numbers(self):
        self.run_example("binding.py")
        issues = self.b_mgr.get_issue_list()

        code_lines = issues[0].get_code().splitlines()
        lineno = issues[0].lineno
        self.assertEqual("%i " % (lineno - 1), code_lines[0][:2])
        self.assertEqual("%i " % (lineno), code_lines[1][:2])
        self.assertEqual("%i " % (lineno + 1), code_lines[2][:2])

    def test_nosec(self):
        expect = {
            "SEVERITY": {"UNDEFINED": 0, "LOW": 5, "MEDIUM": 0, "HIGH": 0},
            "CONFIDENCE": {"UNDEFINED": 0, "LOW": 0, "MEDIUM": 0, "HIGH": 5},
        }
        self.check_example("nosec.py", expect)

    def test_baseline_filter(self):
        issue_text = (
            "A Flask app appears to be run with debug=True, which "
            "exposes the Werkzeug debugger and allows the execution "
            "of arbitrary code."
        )
        json = f"""{{
          "results": [
            {{
              "code": "...",
              "filename": "{os.getcwd()}/examples/flask_debug.py",
              "issue_confidence": "MEDIUM",
              "issue_severity": "HIGH",
              "issue_cwe": {{
                "id": 94,
                "link": "https://cwe.mitre.org/data/definitions/94.html"
              }},
              "issue_text": "{issue_text}",
              "line_number": 10,
              "col_offset": 0,
              "line_range": [
                10
              ],
              "test_name": "flask_debug_true",
              "test_id": "B201"
            }}
          ]
        }}
        """

        self.b_mgr.populate_baseline(json)
        self.run_example("flask_debug.py")
        self.assertEqual(1, len(self.b_mgr.baseline))
        self.assertEqual({}, self.b_mgr.get_issue_list())
