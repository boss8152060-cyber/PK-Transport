"""Language switch for the embedded programs (PKT Data, PKT Analyze) without touching their widget code.

Each program was written in one language (PKT Data: English, PKT Analyze: Thai). A catalog lists, for one target language, the
exact texts and the "{0}"-style templates of its messages with their translation. The translator walks the widgets of the visible
pages and windows and swaps the text of labels, buttons, check/radio buttons, group boxes, notebook tabs and table headings;
message boxes and dialogs are translated when they are opened. What the user can type, combo-box values and file names are never
touched (the programs compare some of those values in their logic). The original text of every widget is remembered, so switching
back restores it, and text the program sets later is translated on the next sweep."""
import re
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

TEXT_WIDGETS = (tk.Label, tk.Button, tk.Checkbutton, tk.Radiobutton, tk.LabelFrame, ttk.Label, ttk.Button, ttk.Checkbutton, ttk.Radiobutton,
                ttk.LabelFrame, ttk.Menubutton)
LABELS = (tk.Label, ttk.Label)                     # only these get their text variable translated (a status line, a progress text)
SWEEP_MS = 500
THAI = re.compile(r"[\u0E00-\u0E7F]")


class Catalog:
    """Translations into ONE language: exact texts and templates ("Saved {0} zone(s) to: {1}")."""

    def __init__(self, lang, exact=None, templates=None, fragments=False):
        self.lang = lang
        self.exact = dict(exact or {})
        self.fragments = None                        # texts the program builds from pieces: translate the known pieces inside them
        self._cache = {}
        if fragments:
            self.fragments = sorted((k for k in self.exact if THAI.search(k) and len(k.strip()) >= 2), key=len, reverse=True)
        self.templates = []                          # (compiled regex, target template)
        for src, dst in (templates or {}).items():
            pattern = re.escape(src)
            pattern = re.sub(r"\\\{(\d+)\\\}", lambda m: f"(?P<g{m.group(1)}>.*?)", pattern)
            self.templates.append((re.compile(pattern, re.S), dst))

    def translate(self, text):
        """The translation of `text`, or None when the catalog has none."""
        hit = self.exact.get(text)
        if hit is not None:
            return hit
        stripped = text.strip()
        if stripped != text and stripped in self.exact:                # the program added spaces around a known text
            lead, trail = text[:len(text) - len(text.lstrip())], text[len(text.rstrip()):]
            return lead + self.exact[stripped] + trail
        for rx, dst in self.templates:
            m = rx.fullmatch(text)
            if m:
                groups = {k[1:]: v for k, v in m.groupdict().items()}
                try:
                    return re.sub(r"\{(\d+)\}", lambda g: groups.get(g.group(1), g.group(0)), dst)
                except (KeyError, IndexError):
                    return None
        if self.fragments is not None and THAI.search(text):
            if text not in self._cache:
                out = text
                for frag in self.fragments:
                    if frag in out:
                        out = out.replace(frag, self.exact[frag])
                self._cache[text] = out if out != text else None
                if len(self._cache) > 4000:
                    self._cache.clear()
            return self._cache.get(text)
        return None


class Translator:
    active = None                                   # the message-box wrappers translate with the last installed translator

    def __init__(self, root, get_lang, catalogs):
        self.root = root
        self.get_lang = get_lang
        self.catalogs = list(catalogs)
        self.memo = {}                               # (widget path, what) -> (original text, text now shown)
        self.areas = []                              # widgets whose subtree is swept while they are mapped (the program pages)
        self._pending = False
        self.installed = False

    # ------------------------------------------------------------------ text
    def tr(self, text, lang=None):
        if not isinstance(text, str) or not text.strip():
            return text
        lang = lang or self.get_lang()
        for cat in self.catalogs:
            if cat.lang == lang:
                hit = cat.translate(text)
                if hit is not None:
                    return hit
        return text

    def _swap(self, key, current, setter):
        """Show the translation of the text the program put there; remember the original so switching back restores it."""
        orig, shown = self.memo.get(key, (None, None))
        if orig is None or current != shown:             # first time, or the program changed the text since
            orig = current
        want = self.tr(orig)
        if want != current or key not in self.memo:
            setter(want)
        self.memo[key] = (orig, want)

    # ------------------------------------------------------------------ widgets
    def _one(self, w):
        try:
            if isinstance(w, TEXT_WIDGETS):
                var = str(w.cget("textvariable")) if isinstance(w, LABELS) else ""
                if var:
                    self._swap((str(w), "var"), str(w.getvar(var)), lambda v, w=w, var=var: w.setvar(var, v))
                else:
                    self._swap((str(w), "text"), str(w.cget("text")), lambda v, w=w: w.configure(text=v))
            elif isinstance(w, ttk.Notebook):
                for tab in w.tabs():
                    self._swap((str(w), tab), str(w.tab(tab, "text")), lambda v, w=w, tab=tab: w.tab(tab, text=v))
            elif isinstance(w, ttk.Treeview):
                for col in w["columns"]:
                    self._swap((str(w), "col" + str(col)), str(w.heading(col, "text")), lambda v, w=w, col=col: w.heading(col, text=v))
                kids = w.get_children()
                if len(kids) <= 60:                                       # a small table (shortcut list ...), not a list of files
                    for item in kids:
                        for i, cell in enumerate(w.item(item, "values")):
                            if isinstance(cell, str):
                                self._swap((str(w), item, i), cell, lambda v, w=w, item=item, i=i: self._set_cell(w, item, i, v))
            elif isinstance(w, (tk.Toplevel,)) and w is not self.root:
                self._swap((str(w), "title"), w.title(), lambda v, w=w: w.title(v))
        except tk.TclError:
            pass                                                         # the widget is gone / has no such option

    @staticmethod
    def _set_cell(tree, item, index, value):
        values = list(tree.item(item, "values"))
        values[index] = value
        tree.item(item, values=values)

    def sweep(self, widget=None):
        """Translate `widget` and everything below it that is visible (default: every registered area and every extra window)."""
        if widget is not None:
            self._walk(widget)
            return
        for area in self.areas:
            try:
                if area.winfo_exists() and area.winfo_ismapped():
                    self._walk(area)
            except tk.TclError:
                pass
        for child in self.root.winfo_children():
            if isinstance(child, tk.Toplevel):
                self._walk(child)

    def _walk(self, widget):
        stack = [widget]
        while stack:
            w = stack.pop()
            try:
                if w is not widget and not isinstance(w, tk.Toplevel) and not w.winfo_ismapped():
                    continue                                              # a hidden page: translated when it is shown
            except tk.TclError:
                continue
            self._one(w)
            try:
                stack.extend(w.winfo_children())
            except tk.TclError:
                pass

    def _soon(self, _event=None):
        if not self._pending:
            self._pending = True
            self.root.after_idle(self._run_soon)

    def _run_soon(self):
        self._pending = False
        self.sweep()

    def _tick(self):
        try:
            self.sweep()
            self.root.after(SWEEP_MS, self._tick)
        except tk.TclError:
            pass

    # ------------------------------------------------------------------ install
    def install(self):
        """Start sweeping, translate the dialogs of tkinter (message boxes, simple dialogs) and react to new windows / tab changes at once."""
        Translator.active = self
        if self.installed:
            return
        self.installed = True
        Translator.active = self
        for name in ("showinfo", "showwarning", "showerror", "askquestion", "askokcancel", "askyesno", "askyesnocancel", "askretrycancel"):
            self._wrap(messagebox, name)
        for name in ("askstring", "askinteger", "askfloat"):
            self._wrap(simpledialog, name)
        self.root.bind_all("<<NotebookTabChanged>>", self._soon, add="+")
        self.root.bind_all("<Map>", self._soon, add="+")
        self.root.after(SWEEP_MS, self._tick)

    def _wrap(self, module, name):
        original = getattr(module, name, None)
        if original is None or getattr(original, "_pkt_wrapped", False):
            return

        def wrapper(*args, **kw):
            me = Translator.active
            if me is not None:
                args = [me.tr(a) if i < 2 else a for i, a in enumerate(args)]
                for key in ("title", "message", "prompt", "detail"):
                    if isinstance(kw.get(key), str):
                        kw[key] = me.tr(kw[key])
            return original(*args, **kw)
        wrapper._pkt_wrapped = True
        wrapper.__doc__ = original.__doc__
        setattr(module, name, wrapper)
