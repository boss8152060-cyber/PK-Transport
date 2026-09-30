"""
=========================================================================
PK Studio - Main Application Shell

รวมเครื่องมือทั้งหมดที่ทดสอบผ่านแล้วแยกกันมาก่อนหน้านี้ (Auto Label Tool,
Dataset Curator, Dataset Splitter, Multi Video Tool) เข้าไว้ในโปรแกรมเดียว
มีแถบเมนูไอคอนด้านซ้าย (สไตล์ Roboflow) — logic การทำงานภายในของแต่ละ
เครื่องมือไม่ได้ถูกแก้ไขจากของเดิมที่ทดสอบผ่านแล้ว

ธีมสี: ปรับใหม่ทั้งแอพให้เป็นธีมสว่างสไตล์ Roboflow (พื้นหลังขาว/ม่วงอ่อน,
แถบเมนูซ้ายสีเข้ม, ปุ่ม/จุดเน้นสีม่วง) — ดูค่าสีทั้งหมดได้จาก theme.py

หมายเหตุการติดตั้ง: เนื่องจากรวม Auto Label Tool + Dataset Curator +
Dataset Splitter ไว้ในโปรแกรมเดียว จำเป็นต้องติดตั้ง PyTorch/CUDA (ที่ 2
เครื่องมือแรกใช้) แม้ Dataset Splitter เองจะไม่ได้ใช้ก็ตาม

รัน:
    python main.py
=========================================================================
"""

import tkinter as tk
from pathlib import Path
from tkinter import ttk

from theme import COLORS, apply_global_theme
from tabs.tab_data import DataTab
from tabs.tab_autolabeler import AutoLabelerTab
from tabs.tab_curator_splitter import CuratorSplitterTab
from tabs.tab_analytics import AnalyticsTab


class PKStudioApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("PK Studio - All-in-One Computer Vision Suite")
        self.root.geometry("1440x900")

        # ตั้งไอคอนของหน้าต่าง (title bar/taskbar) เป็นโลโก้ PK ถ้ามีไฟล์ icon.ico
        # อยู่ข้าง main.py — ใช้ try/except เพราะ iconbitmap ใช้ได้เฉพาะบน Windows
        # เท่านั้น (บน Linux/Mac จะ error แต่ไม่ควรทำให้แอพทั้งหมดรันไม่ได้)
        try:
            icon_path = Path(__file__).resolve().parent / "icon.ico"
            if icon_path.exists():
                self.root.iconbitmap(str(icon_path))
        except Exception:
            pass

        self.style = apply_global_theme(self.root)
        self._build_ui()

    def _build_ui(self) -> None:
        # ----- แถบเมนูไอคอนด้านซ้าย (สไตล์ Roboflow) -----
        sidebar = tk.Frame(self.root, bg=COLORS["sidebar_bg"], width=76)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        # เส้นแบ่งระหว่างแถบเมนูกับเนื้อหา — จำเป็นเพราะทั้งคู่เป็นสีขาวเหมือนกัน
        # ไม่มีเส้นนี้จะแยกไม่ออกเลยว่าแถบเมนูจบตรงไหน
        tk.Frame(self.root, bg=COLORS["sidebar_border"], width=1).pack(side="left", fill="y")

        tk.Label(
            sidebar, text="PK", font=("Segoe UI", 16, "bold"),
            bg=COLORS["sidebar_bg"], fg=COLORS["text_dark"], pady=18,
        ).pack()

        # ----- พื้นที่แสดงเนื้อหาหลัก (ขวาของ sidebar) -----
        self.workspace_container = tk.Frame(self.root, bg=COLORS["main_bg"])
        self.workspace_container.pack(side="left", fill="both", expand=True)

        self.tabs = {
            "data": DataTab(self.workspace_container),
            "autolabeler": AutoLabelerTab(self.workspace_container),
            "curator_splitter": CuratorSplitterTab(self.workspace_container),
            "analytics": AnalyticsTab(self.workspace_container),
        }

        btn_configs = [
            ("data", "🎬", "Data"),
            ("autolabeler", "🏷️", "Label"),
            ("curator_splitter", "✂️", "Curate"),
            ("analytics", "📊", "Analytics"),
        ]

        self.nav_buttons = {}
        for tab_id, icon, label in btn_configs:
            btn_frame = tk.Frame(sidebar, bg=COLORS["sidebar_bg"], cursor="hand2")
            btn_frame.pack(fill="x", pady=2)

            # แถบสีบอกสถานะ active อยู่ซ้ายสุด (แยกออกมาต่างหาก ไม่ปนกับตัวไอคอน/
            # ตัวหนังสือ)
            accent_bar = tk.Frame(btn_frame, bg=COLORS["sidebar_bg"], width=4)
            accent_bar.place(x=0, y=0, relheight=1)

            # สำคัญ: ไอคอน/ตัวหนังสือต้องเป็นสีเข้ม (ดำ/เทา) เพราะพื้นหลังแถบเมนู
            # เป็นสีขาว — ก่อนหน้านี้เคยเผลอปล่อยเป็นสีขาวค้างมาจากดีไซน์แถบเมนู
            # สีเข้มแบบเดิม กลายเป็นขาวบนขาว มองไม่เห็นเลย (บั๊กที่เพิ่งเจอจริง)
            icon_lbl = tk.Label(
                btn_frame, text=icon, font=("Segoe UI", 18),
                bg=COLORS["sidebar_bg"], fg=COLORS["text_dark"],
            )
            icon_lbl.pack(pady=(10, 0))
            text_lbl = tk.Label(
                btn_frame, text=label, font=("Segoe UI", 8),
                bg=COLORS["sidebar_bg"], fg=COLORS["text_muted"],
            )
            text_lbl.pack(pady=(0, 10))

            for widget in (btn_frame, icon_lbl, text_lbl):
                widget.bind("<Button-1>", lambda e, tid=tab_id: self.switch_tab(tid))

            self.nav_buttons[tab_id] = (btn_frame, icon_lbl, text_lbl, accent_bar)

        self.switch_tab("autolabeler")

    def switch_tab(self, selected_tab_id: str) -> None:
        for tab_id, tab_frame in self.tabs.items():
            tab_frame.pack_forget()

        for tab_id, (frame, icon_lbl, text_lbl, accent_bar) in self.nav_buttons.items():
            is_active = tab_id == selected_tab_id
            # เปลี่ยนแค่สีพื้นหลัง (ขาว <-> เทาอ่อนมาก) ไม่แตะสีตัวอักษร/ไอคอนเลย
            # (ไอคอน/ตัวหนังสือเป็นสีเข้มคงที่เสมอ อ่านออกได้ทั้ง 2 สถานะ)
            bg = COLORS["sidebar_active_bg"] if is_active else COLORS["sidebar_bg"]
            frame.configure(bg=bg)
            icon_lbl.configure(bg=bg)
            text_lbl.configure(bg=bg)
            accent_bar.configure(bg=COLORS["accent"] if is_active else COLORS["sidebar_bg"])

        self.tabs[selected_tab_id].pack(fill="both", expand=True)


if __name__ == "__main__":
    root = tk.Tk()
    app = PKStudioApp(root)
    root.mainloop()
