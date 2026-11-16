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

    def test_a_text_the_program_sets_is_translated_at_once_not_at_the_next_sweep(self):
        xlate._patch_tk()
        xlate.Translator.active = self.tr
        try:
            lab = ttk.Label(self.frame, text="Save")                      # created with the original text: shown translated at once
            lab.pack()
            self.assertEqual(str(lab.cget("text")), "บันทึก")
            lab.configure(text="Name")                                    # the program changes it again and again: never the other language
            self.assertEqual(str(lab.cget("text")), "ชื่อ")
            lab["text"] = "Ready"
            self.assertEqual(str(lab.cget("text")), "พร้อม")
            var = tk.StringVar(value="Save")
            status = ttk.Label(self.frame, textvariable=var)               # a label of a text variable: what it shows now and later
            status.pack()
            self.assertEqual(var.get(), "บันทึก")
            var.set("Name")
            self.assertEqual(var.get(), "ชื่อ")
            var.set("typed by the user")
            self.assertEqual(var.get(), "typed by the user")
            entry_var = tk.StringVar(value="Save")                         # an entry's variable is never touched
            ttk.Entry(self.frame, textvariable=entry_var).pack()
            entry_var.set("Name")
            self.assertEqual(entry_var.get(), "Name")
            outside = tk.Label(self.root, text="Save")                     # a widget outside the watched pages is left alone
            self.assertEqual(str(outside.cget("text")), "Save")
            # switching back restores the original wording
            self.lang = "en"
            self.tr.sweep(full=True)
            self.assertEqual((str(lab.cget("text")), var.get()), ("Ready", "typed by the user"))
        finally:
            xlate.Translator.active = None

    def test_a_full_sweep_reaches_the_tabs_that_are_not_shown(self):
        nb = ttk.Notebook(self.frame)
        nb.pack()
        page1, page2 = ttk.Frame(nb), ttk.Frame(nb)
        nb.add(page1, text="Name")
        nb.add(page2, text="Save")
        hidden = ttk.Label(page2, text="Save")
        hidden.pack()
        self.root.update()
        self.tr.sweep()                                                   # the normal sweep leaves the hidden tab alone ...
        self.assertEqual(str(hidden.cget("text")), "Save")
        self.tr.sweep(full=True)                                          # ... the full one (language change) does not
        self.assertEqual(str(hidden.cget("text")), "บันทึก")

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


if __name__ == "__main__":
    unittest.main()
