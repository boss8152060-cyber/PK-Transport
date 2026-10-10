"""The PK Transport look: colours, fonts, icons and the ttk styles every page uses (one place, so the whole app stays consistent)."""
import tkinter.font as tkfont
from tkinter import ttk

COLORS = {
    # shell (the same dark rail as PKT Data)
    "sidebar": "#111111", "sidebar_hover": "#262626", "sidebar_active": "#333333", "sidebar_text": "#FFFFFF",
    "sidebar_muted": "#A3A3A3", "sidebar_icon": "#D4D4D4", "sidebar_line": "#3A3A3A", "highlight": "#FFFFFF",
    # workspace
    "bg": "#F5F5F5", "card": "#FFFFFF", "border": "#D8D8D8", "border_strong": "#BDBDBD", "field": "#FFFFFF", "surface_alt": "#EBEBEB",
    # text
    "text": "#111111", "muted": "#666666", "subtle": "#909090",
    # roles: black / white / grey only; state is shown by the icon and the weight (an inverted black chip = needs attention)
    "primary": "#202020", "primary_hover": "#000000", "accent": "#202020", "accent_soft": "#E5E5E5",
    "ok": "#303030", "ok_soft": "#EAEAEA", "warn": "#111111", "warn_soft": "#D9D9D9", "bad": "#FFFFFF", "bad_soft": "#111111",
    "info": "#444444", "info_soft": "#EBEBEB", "select": "#E2E2E2",
}

FONT = "Segoe UI"
ICON_FONT = "Segoe MDL2 Assets"

# Segoe MDL2 Assets code points (Windows 10/11); ICON_FALLBACK is used when that font is missing
ICONS = {
    "home": "", "data": "", "train": "", "analyze": "", "settings": "", "language": "",
    "refresh": "", "folder": "", "play": "", "stop": "", "check": "", "warning": "",
    "info": "", "clock": "", "update": "", "arrow": "", "copy": "", "link": "",
    "model": "", "shortcut": "", "open": "",
}
ICON_FALLBACK = {
    "home": "⌂", "data": "▦", "train": "◈", "analyze": "▲", "settings": "⚙", "language": "◎",
    "refresh": "↻", "folder": "▣", "play": "▶", "stop": "■", "check": "✓", "warning": "⚠",
    "info": "ⓘ", "clock": "◷", "update": "⬇", "arrow": "›", "copy": "❐", "link": "↗",
    "model": "◆", "shortcut": "↗", "open": "↗",
}

_icon_font_ok = None


def icon_font_available(root=None):
    global _icon_font_ok
    if _icon_font_ok is None:
        try:
            _icon_font_ok = ICON_FONT in set(tkfont.families(root))
        except Exception:
            _icon_font_ok = False
    return _icon_font_ok


def icon(name, root=None):
    """The glyph of an icon (a Segoe MDL2 code point, or a plain Unicode symbol when that font is not installed)."""
    return (ICONS if icon_font_available(root) else ICON_FALLBACK).get(name, "")


def icon_font(size=12):
    return (ICON_FONT if _icon_font_ok else FONT, size)


def F(size=10, weight="normal"):
    """A font tuple of the app font."""
    return (FONT, size, weight)


def apply_theme(root):
    """Style every ttk widget the pages use. Names: TLabel / Muted.TLabel / Title.TLabel (on the workspace colour) and Card.* (on a white card)."""
    c = COLORS
    icon_font_available(root)
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except Exception:
        pass
    root.configure(bg=c["bg"])
    for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont", "TkCaptionFont", "TkSmallCaptionFont", "TkIconFont", "TkTooltipFont"):
        try:
            tkfont.nametofont(name).configure(family=FONT, size=10)
        except Exception:
            pass
    style.configure(".", background=c["bg"], foreground=c["text"], font=F(10), bordercolor=c["border"], focuscolor=c["bg"],
                    lightcolor=c["bg"], darkcolor=c["bg"], troughcolor=c["border"])
    style.configure("TFrame", background=c["bg"])
    style.configure("Card.TFrame", background=c["card"])
    style.configure("Sidebar.TFrame", background=c["sidebar"])

    # labels
    style.configure("TLabel", background=c["bg"], foreground=c["text"])
    style.configure("Muted.TLabel", background=c["bg"], foreground=c["muted"])
    style.configure("Title.TLabel", background=c["bg"], foreground=c["text"], font=F(19, "bold"))
    style.configure("Subtitle.TLabel", background=c["bg"], foreground=c["muted"], font=F(10))
    style.configure("Section.TLabel", background=c["bg"], foreground=c["text"], font=F(11, "bold"))
    style.configure("Card.TLabel", background=c["card"], foreground=c["text"])
    style.configure("CardTitle.TLabel", background=c["card"], foreground=c["text"], font=F(12, "bold"))
    style.configure("CardMuted.TLabel", background=c["card"], foreground=c["muted"])
    style.configure("CardSubtle.TLabel", background=c["card"], foreground=c["subtle"], font=F(9))
    style.configure("CardOk.TLabel", background=c["card"], foreground=c["ok"], font=F(10, "bold"))
    style.configure("CardWarn.TLabel", background=c["card"], foreground=c["warn"], font=F(10, "bold"))
    style.configure("CardBad.TLabel", background=c["card"], foreground=c["text"], font=F(10, "bold"))
    style.configure("CardMetric.TLabel", background=c["card"], foreground=c["text"], font=F(16, "bold"))
    style.configure("Status.TLabel", background=c["card"], foreground=c["muted"], font=F(9))

    # buttons
    base = dict(relief="solid", borderwidth=1, padding=(14, 7), focusthickness=0, font=F(10))
    style.configure("TButton", background=c["card"], foreground=c["text"], bordercolor=c["border_strong"], lightcolor=c["card"], darkcolor=c["card"], **base)
    style.map("TButton", background=[("disabled", c["bg"]), ("pressed", c["bg"]), ("active", "#EEF1F6")], foreground=[("disabled", c["subtle"])],
              bordercolor=[("active", c["primary"])])
    style.configure("Primary.TButton", background=c["primary"], foreground="#FFFFFF", bordercolor=c["primary"], lightcolor=c["primary"], darkcolor=c["primary"], **base)
    style.map("Primary.TButton", background=[("disabled", "#C5CCD8"), ("pressed", c["primary_hover"]), ("active", c["primary_hover"])],
              foreground=[("disabled", "#FFFFFF")], bordercolor=[("disabled", "#C5CCD8"), ("active", c["primary_hover"])])
    style.configure("Compact.TButton", padding=(9, 6))
    style.map("Compact.TButton", background=[("disabled", c["bg"]), ("pressed", c["bg"]), ("active", "#EEF1F6")], foreground=[("disabled", c["subtle"])],
              bordercolor=[("active", c["primary"])])
    style.configure("CompactPrimary.TButton", padding=(9, 6), background=c["primary"], foreground="#FFFFFF", bordercolor=c["primary"], lightcolor=c["primary"], darkcolor=c["primary"])
    style.map("CompactPrimary.TButton", background=[("disabled", "#C5CCD8"), ("pressed", c["primary_hover"]), ("active", c["primary_hover"])],
              foreground=[("disabled", "#FFFFFF")], bordercolor=[("disabled", "#C5CCD8"), ("active", c["primary_hover"])])
    style.configure("Accent.TButton", background=c["accent"], foreground="#FFFFFF", bordercolor=c["accent"], lightcolor=c["accent"], darkcolor=c["accent"], **base)
    style.map("Accent.TButton", background=[("disabled", "#C5CCD8"), ("active", "#000000")], foreground=[("disabled", "#FFFFFF")])
    style.configure("Danger.TButton", background=c["card"], foreground=c["text"], bordercolor=c["text"], lightcolor=c["card"], darkcolor=c["card"], **base)
    style.map("Danger.TButton", background=[("disabled", c["bg"]), ("active", "#E5E5E5")], foreground=[("disabled", c["subtle"])],
              bordercolor=[("disabled", c["border_strong"])])
    style.configure("Link.TButton", background=c["card"], foreground=c["text"], bordercolor=c["card"], lightcolor=c["card"], darkcolor=c["card"],
                    relief="flat", borderwidth=0, padding=(4, 2), font=F(10, "bold"))
    style.map("Link.TButton", foreground=[("disabled", c["subtle"]), ("active", c["primary"])], background=[("active", c["card"])])

    # inputs
    style.configure("TEntry", fieldbackground=c["field"], foreground=c["text"], bordercolor=c["border_strong"], lightcolor=c["field"], darkcolor=c["field"],
                    padding=(8, 6), insertcolor=c["text"])
    style.map("TEntry", bordercolor=[("focus", c["accent"])], lightcolor=[("focus", c["accent"])], darkcolor=[("focus", c["accent"])])
    style.configure("TCombobox", fieldbackground=c["field"], background=c["card"], foreground=c["text"], bordercolor=c["border_strong"],
                    lightcolor=c["field"], darkcolor=c["field"], arrowcolor=c["muted"], padding=(8, 5))
    style.map("TCombobox", fieldbackground=[("readonly", c["field"])], bordercolor=[("focus", c["accent"])], arrowcolor=[("disabled", c["subtle"])])
    root.option_add("*TCombobox*Listbox.background", c["card"])
    root.option_add("*TCombobox*Listbox.foreground", c["text"])
    root.option_add("*TCombobox*Listbox.selectBackground", c["primary"])
    root.option_add("*TCombobox*Listbox.selectForeground", "#FFFFFF")
    style.configure("Card.TCheckbutton", background=c["card"], foreground=c["text"], focuscolor=c["card"], indicatorcolor=c["field"])
    style.map("Card.TCheckbutton", indicatorcolor=[("selected", c["accent"])], background=[("active", c["card"])])
    style.configure("Card.TRadiobutton", background=c["card"], foreground=c["text"], focuscolor=c["card"], indicatorcolor=c["field"])
    style.map("Card.TRadiobutton", indicatorcolor=[("selected", c["accent"])], background=[("active", c["card"])])
    style.configure("TCheckbutton", background=c["bg"])
    style.configure("TRadiobutton", background=c["bg"])

    # table, scrollbar, separator, progress
    style.configure("Treeview", background=c["card"], fieldbackground=c["card"], foreground=c["text"], rowheight=28, bordercolor=c["border"],
                    lightcolor=c["card"], darkcolor=c["card"], borderwidth=0)
    style.map("Treeview", background=[("selected", c["select"])], foreground=[("selected", c["text"])])
    style.configure("Treeview.Heading", background="#EEF1F6", foreground=c["muted"], font=F(9, "bold"), relief="flat", padding=(8, 6), bordercolor=c["border"])
    style.map("Treeview.Heading", background=[("active", "#E3E8F0")])
    style.configure("Vertical.TScrollbar", background="#C5CCD8", troughcolor=c["bg"], bordercolor=c["bg"], arrowsize=12, relief="flat", gripcount=0)
    style.map("Vertical.TScrollbar", background=[("active", c["border_strong"])])
    style.configure("TSeparator", background=c["border"])
    style.configure("Horizontal.TProgressbar", background=c["accent"], troughcolor=c["border"], bordercolor=c["border"], lightcolor=c["accent"], darkcolor=c["accent"])
    return style
