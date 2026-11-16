"""Unit tests of pkt.i18n: both languages complete, technical terms kept in English."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pkt import i18n  # noqa: E402


class Texts(unittest.TestCase):
    def test_both_languages_have_the_same_keys(self):
        self.assertEqual(set(i18n.TEXT["th"]), set(i18n.TEXT["en"]))

    def test_no_empty_text(self):
        for lang in i18n.LANGS:
            for key, text in i18n.TEXT[lang].items():
                self.assertTrue(text.strip(), (lang, key))

    def test_indicator_and_model_names_stay_in_english_in_thai(self):
        th = i18n.TEXT["th"]
        for term in ("LDP", "Lateral Clearance", "Gap Acceptance", "TTC", "PET", "Speed"):
            self.assertIn(term, th["analyze_desc"])
            self.assertIn(term, i18n.TEXT["en"]["analyze_desc"])
        for term in ("YOLO26", "RT-DETR", "RT-DETRv2", "Colab"):
            self.assertIn(term, th["train_desc"])

    def test_module_names_are_not_translated(self):
        for lang in i18n.LANGS:
            self.assertIn("PKT Data", i18n.TEXT[lang]["pipeline_hint"])
            self.assertIn("PKT Analyze", i18n.TEXT[lang]["pipeline_hint"])

    def test_thai_texts_are_thai(self):
        self.assertTrue(any("฀" <= ch <= "๿" for ch in i18n.TEXT["th"]["open"]))
        self.assertFalse(any("฀" <= ch <= "๿" for ch in i18n.TEXT["en"]["open"]))


class TranslatorTests(unittest.TestCase):
    def test_switch_and_fallbacks(self):
        t = i18n.Translator("en")
        self.assertEqual(t.t("open"), "Open")
        t.set_lang("th")
        self.assertEqual(t.t("open"), "เปิด")
        t.set_lang("xx")                                   # an unknown language is ignored
        self.assertEqual(t.lang, "th")
        self.assertEqual(i18n.Translator("zz").lang, "th")
        self.assertEqual(t.t("no_such_key"), "no_such_key")

    def test_formatting_and_bad_placeholders(self):
        t = i18n.Translator("en")
        self.assertEqual(t.t("mod_installed_ok", name="PKT Data", version="1.4.0"), "PKT Data 1.4.0 installed")
        self.assertIn("{name}", t.t("mod_installed_ok", other=1))     # a missing value leaves the text readable

    def test_modules_add_their_own_texts(self):
        t = i18n.Translator("th")
        t.add_texts({"th": {"zz_key": "ทดสอบ", "open": "no"}, "en": {"zz_key": "test"}})
        self.assertEqual(t.t("zz_key"), "ทดสอบ")
        self.assertEqual(t.t("open"), "เปิด")                 # a module can never replace a text of the shell
        t.set_lang("en")
        self.assertEqual(t.t("zz_key"), "test")
        self.assertEqual(i18n.Translator("th").t("zz_key"), "zz_key")      # other translators are not affected


if __name__ == "__main__":
    unittest.main()
