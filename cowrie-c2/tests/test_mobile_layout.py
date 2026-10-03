import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


class MobileLayoutRegressionTests(unittest.TestCase):
    def test_global_wrapping_rules_are_present(self):
        css_files = [
            ROOT / "static/css/style.css",
            ROOT / "static/css/mobile.css",
        ]

        for css_file in css_files:
            css = css_file.read_text()
            self.assertIn("overflow-x: hidden", css)
            self.assertIn("overflow-wrap: anywhere", css)
            self.assertIn("word-break: break-word", css)

    def test_table_layout_disallows_side_scroll(self):
        style_css = (ROOT / "static/css/style.css").read_text()
        mobile_css = (ROOT / "static/css/mobile.css").read_text()

        self.assertIn("table-layout: fixed", style_css)
        self.assertIn("overflow-x: hidden !important", mobile_css)


if __name__ == "__main__":
    unittest.main()
