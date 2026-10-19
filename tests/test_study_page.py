"""Checks for full outline and original visual coverage."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skill/scripts"))
from render_study_page import render  # noqa: E402


class StudyPageTests(unittest.TestCase):
    def setUp(self):
        self.root = ROOT / "examples"
        self.data = json.loads((self.root / "study-page-input.json").read_text(encoding="utf-8"))

    def page(self):
        return render(self.data, self.root)

    def test_nested_original_outline_and_images_are_embedded(self):
        page = self.page()
        self.assertIn("2.1.1 整体结果", page)
        self.assertIn("2.1.2 分项结果", page)
        self.assertLess(page.index("2.1.1 整体结果"), page.index("2.1.2 分项结果"))
        self.assertIn("原图 1 · 原文原貌", page)
        self.assertIn("原表 1 · 原文原貌", page)
        self.assertEqual(page.count("data:image/png;base64,"), 2)
        self.assertIn('id="image-viewer"', page)
        self.assertEqual(page.count('class="zoom-open"'), 2)
        self.assertIn("内容单元 7 / 7", page)
        self.assertIn('id="text-size"', page)

    def test_skipped_subsection_fails(self):
        self.data["sections"].pop(3)
        with self.assertRaisesRegex(ValueError, "no subsection may be skipped"):
            self.page()

    def test_skipped_body_unit_fails(self):
        self.data["sections"][3]["blocks"].pop(0)
        with self.assertRaisesRegex(ValueError, "source-unit coverage/order mismatch"):
            self.page()

    def test_skipped_figure_fails(self):
        self.data["sections"][3]["blocks"].pop(1)
        with self.assertRaisesRegex(ValueError, "figure/table coverage/order mismatch"):
            self.page()

    def test_reordered_subsections_fail(self):
        self.data["sections"][3], self.data["sections"][4] = self.data["sections"][4], self.data["sections"][3]
        with self.assertRaisesRegex(ValueError, "must match original inventory and order"):
            self.page()

    def test_duplicate_visual_fails(self):
        self.data["sections"][3]["blocks"].append(self.data["sections"][3]["blocks"][1].copy())
        with self.assertRaisesRegex(ValueError, "figure/table coverage/order mismatch"):
            self.page()

    def test_missing_original_image_fails(self):
        self.data["sections"][3]["blocks"][1]["asset"] = "assets/not-here.png"
        with self.assertRaises(FileNotFoundError):
            self.page()

    def test_paper_text_cannot_inject_html(self):
        self.data["sections"][0]["blocks"][0]["text"] = '<script>alert("x")</script>'
        page = self.page()
        self.assertIn('&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;', page)
        self.assertNotIn('<script>alert("x")</script>', page)

    def test_path_cannot_escape_input_directory(self):
        self.data["sections"][3]["blocks"][1]["asset"] = "../secret.png"
        with self.assertRaisesRegex(ValueError, "relative path"):
            self.page()


if __name__ == "__main__":
    unittest.main()
