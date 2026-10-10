"""Live language switching: widgets are created through a TextBinder, which remembers (widget, option, key, values) so that every
visible text can be redrawn in the other language at once (no restart, nothing rebuilt, what the user typed stays)."""
import tkinter as tk
from tkinter import ttk


class TextBinder:
    def __init__(self, translator):
        self.tr = translator
        self.items = []             # [widget, option, key, kwargs]
        self.callbacks = []         # functions that redraw what is not a plain text option (table headings, combobox lists, status lines)

    def t(self, key, **kw):
        return self.tr.t(key, **kw)

    def bind(self, widget, key, option="text", **kw):
        """Show `key` in `widget[option]` now and after every language change."""
        widget[option] = self.tr.t(key, **kw)
        self.items.append([widget, option, key, kw])
        return widget

    def rebind(self, widget, key, option="text", **kw):
        """Change which key a bound widget shows (e.g. a status label that moves between 'found' and 'missing')."""
        for it in self.items:
            if it[0] is widget and it[1] == option:
                it[2], it[3] = key, kw
                break
        else:
            return self.bind(widget, key, option, **kw)
        widget[option] = self.tr.t(key, **kw)
        return widget

    def on_change(self, fn):
        self.callbacks.append(fn)

    def refresh(self):
        alive = []
        for it in self.items:
            widget, option, key, kw = it
            try:
                widget[option] = self.tr.t(key, **kw)
            except tk.TclError:
                continue                       # the widget was destroyed
            alive.append(it)
        self.items = alive
        for fn in list(self.callbacks):
            try:
                fn()
            except tk.TclError:
                pass

    # ---- shortcuts that create a bound widget
    def label(self, parent, key, style="TLabel", **kw):
        values = kw.pop("values", {})
        return self.bind(ttk.Label(parent, style=style, **kw), key, **values)

    def button(self, parent, key, command, style="TButton", **kw):
        values = kw.pop("values", {})
        return self.bind(ttk.Button(parent, style=style, command=command, **kw), key, **values)

    def check(self, parent, key, variable, style="Card.TCheckbutton", **kw):
        return self.bind(ttk.Checkbutton(parent, style=style, variable=variable, **kw), key)

    def radio(self, parent, key, variable, value, style="Card.TRadiobutton", **kw):
        return self.bind(ttk.Radiobutton(parent, style=style, variable=variable, value=value, **kw), key)
