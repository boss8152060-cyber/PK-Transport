"""Small widgets the pages are built from: Card, SidebarItem, Chip, ScrollFrame, page header."""
import tkinter as tk
from tkinter import ttk

from pkt.ui.theme import COLORS, F, icon, icon_font


class Card(tk.Frame):
    """A white panel with a hairline border. Put children in `card.inner` (a ttk.Frame styled Card.TFrame)."""

    def __init__(self, parent, padding=16, **kw):
        super().__init__(parent, bg=COLORS["card"], highlightbackground=COLORS["border"], highlightcolor=COLORS["border"], highlightthickness=1, bd=0, **kw)
        self.inner = ttk.Frame(self, style="Card.TFrame", padding=padding)
        self.inner.pack(fill="both", expand=True)


class Chip(tk.Label):
    """A small coloured status pill."""
    KINDS = {"ok": ("ok_soft", "ok"), "warn": ("warn_soft", "warn"), "bad": ("bad_soft", "bad"), "info": ("info_soft", "info"),
             "neutral": ("surface_alt", "muted"), "accent": ("accent_soft", "accent")}

    def __init__(self, parent, text="", kind="neutral", **kw):
        bg, fg = self.KINDS[kind]
        super().__init__(parent, text=text, bg=COLORS[bg], fg=COLORS[fg], font=F(9, "bold"), padx=9, pady=2, bd=0, **kw)
        self.kind = kind

    def set_kind(self, kind):
        bg, fg = self.KINDS[kind]
        self.kind = kind
        self.configure(bg=COLORS[bg], fg=COLORS[fg])


class SidebarItem(tk.Frame):
    """One entry of the navigation rail (the look of PKT Data): a glyph, a bold title and a small hint; a bar at the left when selected."""

    def __init__(self, parent, glyph, command, binder=None, key=None, text="", hint_key=None, height=58):
        super().__init__(parent, bg=COLORS["sidebar"], height=height, cursor="hand2")
        self.pack_propagate(False)
        self.command = command
        self.active = False
        self.bar = tk.Frame(self, width=3, bg=COLORS["sidebar"])
        self.bar.pack(side="left", fill="y")
        box = tk.Frame(self, bg=COLORS["sidebar"], width=40)
        box.pack(side="left", fill="y")
        box.pack_propagate(False)
        self.box = box
        self.icon = tk.Label(box, text=glyph, bg=COLORS["sidebar"], fg=COLORS["sidebar_icon"], font=("Segoe UI Symbol", 17))
        self.icon.place(relx=.5, rely=.5, anchor="center")
        tb = tk.Frame(self, bg=COLORS["sidebar"])
        tb.pack(side="left", fill="both", expand=True, padx=(5, 6))
        self.tb = tb
        self.text = tk.Label(tb, text=text, bg=COLORS["sidebar"], fg=COLORS["sidebar_text"], font=F(10, "bold"), anchor="w")
        self.text.pack(anchor="w", pady=(10, 0))
        self.hint = tk.Label(tb, text="", bg=COLORS["sidebar"], fg=COLORS["sidebar_muted"], font=F(8), anchor="w")
        self.hint.pack(anchor="w", pady=(1, 0))
        if binder is not None and key:
            binder.bind(self.text, key)
        if binder is not None and hint_key:
            binder.bind(self.hint, hint_key)
        self.parts = (self, self.bar, box, self.icon, tb, self.text, self.hint)
        for w in self.parts:
            w.bind("<Button-1>", lambda e: self.command())
            w.bind("<Enter>", lambda e: self._paint(hover=True))
            w.bind("<Leave>", lambda e: self._paint(hover=False))

    def set_active(self, active):
        self.active = active
        self._paint()

    def _paint(self, hover=False):
        if self.active:
            bg, bar = COLORS["sidebar_active"], COLORS["highlight"]
        elif hover:
            bg, bar = COLORS["sidebar_hover"], COLORS["sidebar_hover"]
        else:
            bg, bar = COLORS["sidebar"], COLORS["sidebar"]
        for w in (self, self.box, self.icon, self.tb, self.text, self.hint):
            w.configure(bg=bg)
        self.bar.configure(bg=bar)
        self.icon.configure(fg=COLORS["highlight"] if self.active else COLORS["sidebar_icon"])


class ScrollFrame(ttk.Frame):
    """A vertically scrollable area: put children in `.body`. The mouse wheel scrolls while the pointer is over it."""

    def __init__(self, parent, **kw):
        super().__init__(parent, **kw)
        self.canvas = tk.Canvas(self, bg=COLORS["bg"], highlightthickness=0, bd=0)
        self.scroll = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self._on_scroll)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scroll.pack(side="right", fill="y")
        self.body = ttk.Frame(self.canvas)
        self._win = self.canvas.create_window(0, 0, window=self.body, anchor="nw")
        self.body.bind("<Configure>", lambda e: self._sync())
        self.canvas.bind("<Configure>", lambda e: self._sync())
        for w in (self.canvas, self.body):
            w.bind("<Enter>", self._bind_wheel)
            w.bind("<Leave>", self._unbind_wheel)

    def _on_scroll(self, first, last):
        self.scroll.set(first, last)

    def _sync(self):
        self.canvas.itemconfigure(self._win, width=self.canvas.winfo_width())
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        need = self.body.winfo_reqheight() > self.canvas.winfo_height()
        if need and not self.scroll.winfo_ismapped():
            self.scroll.pack(side="right", fill="y")
        elif not need and self.scroll.winfo_ismapped():
            self.scroll.pack_forget()

    _wheel_installed = False
    _under_pointer = None

    def _bind_wheel(self, _e=None):
        ScrollFrame._under_pointer = self
        if not ScrollFrame._wheel_installed:                 # one binding for all pages, added to what other code (embedded PKT Analyze) binds
            ScrollFrame._wheel_installed = True
            self.canvas.bind_all("<MouseWheel>", ScrollFrame._on_wheel, add="+")

    def _unbind_wheel(self, _e=None):
        if ScrollFrame._under_pointer is self:
            ScrollFrame._under_pointer = None

    @staticmethod
    def _on_wheel(e):
        sf = ScrollFrame._under_pointer
        try:
            if sf is not None and sf.winfo_ismapped() and sf.body.winfo_reqheight() > sf.canvas.winfo_height():
                sf.canvas.yview_scroll(int(-e.delta / 120), "units")
        except tk.TclError:
            ScrollFrame._under_pointer = None


def autowrap(label, container, pad=0, minimum=140):
    """Keep `label` wrapped to the width of `container` (minus pad) as the window is resized."""
    try:
        if str(container.cget("style")) == "Card.TFrame":
            pad += 34                                  # the padding of a card
    except tk.TclError:
        pass

    def fit(_e=None):
        width = container.winfo_width() - pad
        if width > 20:
            label.configure(wraplength=max(minimum, width))
    label.configure(wraplength=minimum)           # a small start, so the label never makes its column wider than the window
    container.bind("<Configure>", fit, add="+")
    return label


def page_header(parent, binder, title_key, subtitle_key=None, right=None):
    """The title block at the top of every page: big title, grey subtitle, optional widget factory on the right."""
    head = ttk.Frame(parent)
    left = ttk.Frame(head)
    left.pack(side="left", fill="x", expand=True)
    binder.label(left, title_key, style="Title.TLabel").pack(anchor="w")
    if subtitle_key:
        binder.label(left, subtitle_key, style="Subtitle.TLabel").pack(anchor="w", pady=(2, 0))
    if right is not None:
        holder = ttk.Frame(head)
        holder.pack(side="right")
        right(holder)
    return head
