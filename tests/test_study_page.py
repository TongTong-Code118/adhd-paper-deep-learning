"""Behavior checks for the self-contained study-page renderer."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skill" / "scripts"))
from render_study_page import render  # noqa: E402


class StudyPageTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / "examples" / "study-page-input.json").read_text(encoding="utf-8"))

    def test_single_file_page_contains_focus_controls_and_sources(self):
        page = render(self.data)
        self.assertIn('data-panel="0"', page)
        self.assertIn('data-panel="2"', page)
        self.assertIn('id="text-size"', page)
        self.assertIn('id="next"', page)
        self.assertIn("教学模拟 §2–3", page)
        self.assertIn("想好后查看答案", page)
        self.assertNotIn("https://", page)
        self.assertNotIn("<link rel=", page)

    def test_paper_text_cannot_inject_html(self):
        self.data["sections"][0]["takeaway"] = '<script>alert("x")</script>'
        page = render(self.data)
        self.assertIn('&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;', page)
        self.assertNotIn('<script>alert("x")</script>', page)

    def test_missing_source_fails_before_output(self):
        del self.data["sections"][0]["source"]
        with self.assertRaisesRegex(ValueError, "source"):
            render(self.data)


if __name__ == "__main__":
    unittest.main()
