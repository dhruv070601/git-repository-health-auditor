import unittest
from git_health.auditor import render_markdown
class AuditorTests(unittest.TestCase):
    def test_markdown_contains_findings_and_recommendations(self):
        report = {"repository": "C:/demo", "branch": "main", "finding_count": 1, "findings": [{"severity": "HIGH", "title": "Possible hard-coded secrets", "detail": "sample.py:3", "recommendation": "Rotate exposed credentials."}]}
        output = render_markdown(report)
        self.assertIn("# Git Repository Health Report", output)
        self.assertIn("[HIGH] Possible hard-coded secrets", output)
        self.assertIn("Rotate exposed credentials.", output)
    def test_empty_report(self):
        report = {"repository": ".", "branch": "main", "finding_count": 0, "findings": []}
        self.assertIn("**Findings:** 0", render_markdown(report))
if __name__ == "__main__": unittest.main()
