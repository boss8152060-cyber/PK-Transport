"""
=========================================================================
PK Studio - Theme (สไตล์ Roboflow: พื้นหลังสว่าง, แถบข้างสีเข้ม, จุดเน้นสีม่วง)

ทุกแท็บ import COLORS จากไฟล์นี้ เพื่อให้สีตรงกันทั้งแอพ ไม่ต้อง hardcode
สีซ้ำในแต่ละไฟล์ — ถ้าจะปรับธีมทั้งแอพ แก้ที่นี่ที่เดียวพอ
=========================================================================
"""

from tkinter import ttk

COLORS = {
    "sidebar_bg": "#FFFFFF",      # แถบเมนูซ้าย (ขาวล้วน เหมือนพื้นหลังหลัก)
    "sidebar_active_bg": "#EFEFEF",  # พื้นหลังแท็บที่กำลังเลือกอยู่ (เทาอ่อนมาก ให้เห็นความต่าง)
    "sidebar_border": "#DDDDDD",  # เส้นแบ่งระหว่างแถบเมนูกับเนื้อหา (จำเป็นเพราะทั้งคู่เป็นสีขาว)
    "main_bg": "#FFFFFF",         # พื้นหลังเนื้อหาหลัก (ขาวล้วน)
    "card_bg": "#FFFFFF",         # พื้นหลังการ์ด
    "border": "#DDDDDD",          # เส้นขอบการ์ด/ตาราง
    "accent": "#000000",          # สีเน้นหลัก (ปุ่ม, หัวข้อ, ไอคอน, ตัวอักษร) — ดำล้วน
    "accent_hover": "#333333",    # สีตอน hover/active (เทาเข้ม)
    "text_dark": "#000000",       # ข้อความหลัก — ดำล้วนตามที่ต้องการ
    "text_muted": "#777777",      # ข้อความรอง/คำอธิบาย
    "success": "#222222",         # ใช้เฉดเทาเข้มแทนสีเขียว (ธีมขาวดำล้วน ไม่มีสี)
    "warning": "#555555",         # ใช้เฉดเทากลางแทนสีส้ม
    "danger": "#000000",          # ใช้ดำล้วนแทนสีแดง (เน้นด้วยตัวหนา/underline แทนสี)
}


def apply_global_theme(root) -> ttk.Style:
    """ตั้งค่า ttk.Style ทั้งแอพให้เป็นธีมสว่างสไตล์ Roboflow เรียกครั้งเดียวใน
    main.py ตอนเริ่มโปรแกรม — คืนค่า Style object เผื่อ main.py อยากปรับเพิ่มเอง"""
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except Exception:
        pass  # ถ้าไม่มีธีม clam ในเครื่องนั้น ใช้ธีม default ของระบบแทน

    root.configure(bg=COLORS["main_bg"])

    style.configure(".", background=COLORS["main_bg"], foreground=COLORS["text_dark"], font=("Segoe UI", 9))
    style.configure("TFrame", background=COLORS["main_bg"])
    style.configure("TLabel", background=COLORS["main_bg"], foreground=COLORS["text_dark"])

    style.configure(
        "TLabelframe", background=COLORS["main_bg"], foreground=COLORS["text_dark"],
        bordercolor=COLORS["border"], relief="solid", borderwidth=1,
    )
    style.configure(
        "TLabelframe.Label", background=COLORS["main_bg"], foreground=COLORS["accent"],
        font=("Segoe UI", 10, "bold"),
    )

    style.configure(
        "TButton", background=COLORS["accent"], foreground="#ffffff",
        borderwidth=0, relief="flat", padding=(12, 6), font=("Segoe UI", 9),
    )
    style.map(
        "TButton",
        background=[("active", COLORS["accent_hover"]), ("pressed", COLORS["accent_hover"]),
                    ("disabled", "#C9C9D9")],
    )

    style.configure("TEntry", fieldbackground="#ffffff", bordercolor=COLORS["border"])
    style.configure("TCombobox", fieldbackground="#ffffff")

    style.configure(
        "TNotebook", background=COLORS["main_bg"], bordercolor=COLORS["border"],
    )
    style.configure(
        "TNotebook.Tab", background=COLORS["main_bg"], foreground=COLORS["text_muted"],
        padding=(14, 8), font=("Segoe UI", 9),
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", COLORS["card_bg"])],
        foreground=[("selected", COLORS["accent"])],
    )

    style.configure(
        "Treeview", background="#ffffff", fieldbackground="#ffffff",
        foreground=COLORS["text_dark"], bordercolor=COLORS["border"], rowheight=26,
    )
    style.configure(
        "Treeview.Heading", background=COLORS["main_bg"], foreground=COLORS["text_muted"],
        font=("Segoe UI", 9, "bold"), relief="flat",
    )
    style.map("Treeview", background=[("selected", COLORS["accent"])], foreground=[("selected", "#ffffff")])

    style.configure(
        "TPanedwindow", background=COLORS["main_bg"],
    )

    style.configure(
        "TProgressbar", background=COLORS["accent"], troughcolor=COLORS["border"],
        borderwidth=0, thickness=8,
    )

    style.configure("TCheckbutton", background=COLORS["main_bg"], foreground=COLORS["text_dark"])
    style.configure("TRadiobutton", background=COLORS["main_bg"], foreground=COLORS["text_dark"])
    style.configure("TSeparator", background=COLORS["border"])

    return style
