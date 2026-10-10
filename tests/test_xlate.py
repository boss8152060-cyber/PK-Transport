"""Unit test of pkt.ui.xlate (the language switch of PKT Data / PKT Analyze) and of its catalogs.

Tk is used hidden. The catalog checks read the real sources of PKT-Data and PKT-Analyze and make sure the texts of their windows
are translated, so a new label that nobody translated is noticed."""
import ast
import glob
import os
import re
import sys
import tkinter as tk
import unittest
from tkinter import messagebox, ttk

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from pkt.ui import xlate  # noqa: E402
from pkt.ui.lang import analyze_en, data_th  # noqa: E402

THAI = re.compile(r"[\u0E00-\u0E7F]")


class CatalogTest(unittest.TestCase):
    def test_exact_templates_and_spaces(self):
        c = xlate.Catalog("th", {"Cancel": "ยกเลิก"}, {"Saved {0} zone(s) to: {1}": "บันทึก {0} โซนไปที่: {1}"})
        self.assertEqual(c.translate("Cancel"), "ยกเลิก")
        self.assertEqual(c.translate("  Cancel "), "  ยกเลิก ")                      # spaces the program added are kept
        self.assertEqual(c.translate("Saved 3 zone(s) to: C:\\a b.json"), "บันทึก 3 โซนไปที่: C:\\a b.json")
        self.assertIsNone(c.translate("Something else"))
        self.assertIsNone(c.translate("Saved zones"))

    def test_fragments_translate_the_known_pieces_of_a_built_text(self):
        c = xlate.Catalog("en", {"บันทึก": "Saved", " คลิป": " clips", "ผลลัพธ์": "results"}, fragments=True)
        self.assertEqual(c.translate("บันทึก 5 คลิป ผลลัพธ์ x"), "Saved 5 clips results x")
        self.assertIsNone(c.translate("no thai here"))

    def test_catalogs_have_no_empty_or_identical_entries(self):
        for mod in (data_th, analyze_en):
            for src, dst in mod.EXACT.items():
                self.assertTrue(dst.strip(), src)
                self.assertNotEqual(src, dst)
            for src, dst in mod.TEMPLATES.items():
                self.assertEqual(sorted(re.findall(r"\{\d+\}", src)), sorted(re.findall(r"\{\d+\}", dst)), src)     # same values on both sides

    def test_the_target_text_is_in_the_target_language(self):
        for src, dst in analyze_en.EXACT.items():
            if len(src) > 12:
                self.assertFalse(THAI.search(dst), src)                                 # English catalog: no Thai left in a full text
        for src, dst in data_th.EXACT.items():
            if len(src) > 25:
                self.assertTrue(THAI.search(dst), src)


class WidgetTest(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.lang = "th"
        cat = xlate.Catalog("th", {"Save": "บันทึก", "Name": "ชื่อ", "Ready": "พร้อม", "Dialog": "หน้าต่าง", "Are you sure?": "แน่ใจไหม"})
        self.tr = xlate.Translator(self.root, lambda: self.lang, [cat])
        self.frame = ttk.Frame(self.root)
        self.frame.pack()
        self.tr.areas = [self.frame]
        self.root.deiconify()

    def tearDown(self):
        self.root.destroy()

    def test_widgets_are_swapped_and_restored(self):
        btn = ttk.Button(self.frame, text="Save")
        btn.pack()
        lab = tk.Label(self.frame, text="Name")
        lab.pack()
        var = tk.StringVar(value="Ready")
        status = ttk.Label(self.frame, textvariable=var)
        status.pack()
        entry_var = tk.StringVar(value="Save")                                           # what the user typed is never touched
        ttk.Entry(self.frame, textvariable=entry_var).pack()
        combo = ttk.Combobox(self.frame, values=["Save", "Name"])
        combo.set("Save")
        combo.pack()
        nb = ttk.Notebook(self.frame)
        nb.add(ttk.Frame(nb), text="Name")
        nb.pack()
        tree = ttk.Treeview(self.frame, columns=("a", "b"), show="headings")
        tree.heading("a", text="Save")
        tree.insert("", "end", values=("Name", "keep me"))
        tree.pack()
        self.root.update()
        self.tr.sweep()
        self.assertEqual((str(btn.cget("text")), str(lab.cget("text")), var.get()), ("บันทึก", "ชื่อ", "พร้อม"))
        self.assertEqual(entry_var.get(), "Save")
        self.assertEqual((combo.get(), list(combo.cget("values"))), ("Save", ["Save", "Name"]))
        self.assertEqual(nb.tab(nb.tabs()[0], "text"), "ชื่อ")
        self.assertEqual(tree.heading("a", "text"), "บันทึก")
        self.assertEqual(tuple(tree.item(tree.get_children()[0], "values")), ("ชื่อ", "keep me"))
        # back to the original language: the remembered originals return
        self.lang = "en"
        self.tr.sweep()
        self.assertEqual((str(btn.cget("text")), str(lab.cget("text")), var.get()), ("Save", "Name", "Ready"))
        self.assertEqual(tree.heading("a", "text"), "Save")
        self.assertEqual(tuple(tree.item(tree.get_children()[0], "values")), ("Name", "keep me"))
        # text the program sets later is translated on the next sweep (and a text that is not in the catalog stays)
        self.lang = "th"
        lab.configure(text="Save")
        var.set("something else")
        self.tr.sweep()
        self.assertEqual((str(lab.cget("text")), var.get()), ("บันทึก", "something else"))

    def test_hidden_pages_wait_until_they_are_shown(self):
        other = ttk.Frame(self.root)
        lab = tk.Label(other, text="Save")
        lab.pack()
        self.tr.areas = [other]
        self.root.update()
        self.tr.sweep()
        self.assertEqual(str(lab.cget("text")), "Save")                                  # not mapped: untouched
        other.pack()
        self.root.update()
        self.tr.sweep()
        self.assertEqual(str(lab.cget("text")), "บันทึก")

    def test_windows_and_message_boxes(self):
        top = tk.Toplevel(self.root)
        top.title("Dialog")
        tk.Label(top, text="Name").pack()
        self.root.update()
        self.tr.sweep()
        self.assertEqual(top.title(), "หน้าต่าง")
        shown = []
        real = messagebox.askyesno
        messagebox.askyesno = lambda *a, **k: shown.append((a, k)) or True                 # stands in for the real dialog
        try:
            self.tr.install()
            self.assertTrue(messagebox.askyesno("Dialog", "Are you sure?", parent=self.root))
        finally:
            messagebox.askyesno = real
            xlate.Translator.active = None
        self.assertEqual(shown[0][0], ("หน้าต่าง", "แน่ใจไหม"))                           # title and message arrive translated


def _ui_strings(paths):
    """Text constants in the calls that make labels / buttons / titles / messages (what a user reads)."""
    kw_names = {"text", "title", "message", "prompt", "description", "detail"}
    out = set()
    for path in paths:
        tree = ast.parse(open(path, encoding="utf-8").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                fn = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", "")
                vals = [kw.value for kw in node.keywords if kw.arg in kw_names]
                if fn.startswith(("show", "ask")) or fn in ("title", "heading", "Label", "Button", "Checkbutton", "Radiobutton", "LabelFrame"):
                    vals += list(node.args)
                for v in vals:
                    if isinstance(v, ast.Constant) and isinstance(v.value, str):
                        out.add(v.value)
    return out


@unittest.skipUnless(os.path.isdir(os.path.join(ROOT, "PKT-Data", "src", "pk_studio")), "PKT-Data is not there")
class DataCoverage(unittest.TestCase):
    # English that stays English on purpose (names, file masks, fonts, code of the exported zone file)
    KEEP = {"PK Studio", "DATASET STUDIO", "Auto-Label", "Batch Auto-Label", "⚡ Auto-Label", "🚀 Batch", "Segoe UI", "PK", "Label",
            "train:", "valid:", "test:"}

    def test_every_label_and_message_of_pkt_data_is_in_the_catalog(self):
        cat = xlate.Catalog("th", data_th.EXACT, data_th.TEMPLATES)
        paths = [p for p in glob.glob(os.path.join(ROOT, "PKT-Data", "src", "pk_studio", "**", "*.py"), recursive=True)
                 if not p.endswith(("main.py", "theme.py"))]                    # main.py / theme.py of PKT Data are not used when it is embedded
        missing = []
        for s in sorted(_ui_strings(paths)):
            if not re.search(r"[A-Za-z]{3}", s) or THAI.search(s) or s in self.KEEP:
                continue
            if re.fullmatch(r"[A-Za-z_.\-*# ]+", s) and " " not in s.strip() and s[:1].islower():
                continue                                                         # identifiers / file masks
            if re.search(r"def |import |return |\"\"\"|^\s{2,}", s) or s.startswith(("*.", "T", "Zone definitions")) and " " not in s:
                continue
            if cat.translate(s) is None:
                missing.append(s)
        self.assertEqual(missing, [], "texts of PKT Data without a Thai translation (add them to pkt/ui/lang/data_th.py)")


@unittest.skipUnless(os.path.isfile(os.path.join(ROOT, "PKT-Analyze", "PKStudio.py")), "PKT-Analyze is not there")
class AnalyzeCoverage(unittest.TestCase):
    def test_every_thai_text_of_pkt_analyze_is_in_the_catalog(self):
        cat = xlate.Catalog("en", analyze_en.EXACT, analyze_en.TEMPLATES, fragments=True)
        tree = ast.parse(open(os.path.join(ROOT, "PKT-Analyze", "PKStudio.py"), encoding="utf-8").read())
        docstrings = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.Module)) and node.body and isinstance(node.body[0], ast.Expr) \
                    and isinstance(getattr(node.body[0], "value", None), ast.Constant):
                docstrings.add(id(node.body[0].value))
        missing = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docstrings and THAI.search(node.value) \
                    and len(node.value) < 600:
                out = cat.translate(node.value)
                if out is None or THAI.search(out):
                    missing.append(node.value)
        # a few texts are logic keys (combo-box values / settings) and are never translated
        missing = [m for m in missing if m not in analyze_en.EXACT]
        self.assertLessEqual(len(set(missing)), 2, "Thai texts of PKT Analyze without an English translation (add them to pkt/ui/lang/analyze_en.py): " + repr(sorted(set(missing))[:5]))


if __name__ == "__main__":
    unittest.main()
