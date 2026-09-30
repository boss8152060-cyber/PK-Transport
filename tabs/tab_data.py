"""
=========================================================================
PK Studio - Tab: Data (Multi Video Tool — ฝังโดยตรง)

เดิมเปิดเป็นหน้าต่างแยกผ่าน subprocess เพื่อความปลอดภัย แต่ตอนนี้แก้ไข
extract_frames.py ให้ launch_gui() รับพารามิเตอร์ parent ได้แล้ว (ทดสอบ
ยืนยันทั้ง 2 โหมด — standalone เดิม กับ embedded ใหม่ — ทำงานถูกต้องแยกจาก
กันสมบูรณ์ ไม่กระทบกัน) จึงฝังเข้ามาในแท็บนี้ได้โดยตรง โค้ดภายใน 2500+
บรรทัดของ Multi Video Tool ไม่ถูกแก้ไขเลยนอกจากส่วนหัว-ท้ายของฟังก์ชัน
launch_gui() เท่านั้น
=========================================================================
"""

import importlib.util
from pathlib import Path
from tkinter import messagebox, ttk

TOOLS_DIR = Path(__file__).resolve().parent.parent / "tools"
EXTRACT_FRAMES_SCRIPT = TOOLS_DIR / "extract_frames.py"


def _load_extract_frames_module():
    """โหลด extract_frames.py แบบไดนามิก (ไม่ใช้ import ปกติ เพราะไฟล์อยู่นอก
    โครงสร้าง package ของ tabs/) คืนค่า module ที่โหลดแล้ว"""
    spec = importlib.util.spec_from_file_location("mvt_extract_frames", str(EXTRACT_FRAMES_SCRIPT))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DataTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding=0)

        if not EXTRACT_FRAMES_SCRIPT.exists():
            ttk.Label(
                self,
                text=f"ไม่พบไฟล์ {EXTRACT_FRAMES_SCRIPT}\nตรวจสอบว่าวางไฟล์ extract_frames.py ไว้ในโฟลเดอร์ tools/ แล้วหรือยัง",
                foreground="red",
                padding=20,
            ).pack()
            return

        try:
            mvt_module = _load_extract_frames_module()
            # ส่ง self (ttk.Frame ของแท็บนี้) เป็น parent -> launch_gui() จะสร้าง
            # Multi Video Tool เป็น ttk.Frame ฝังอยู่ข้างในแทนที่จะเปิดหน้าต่างใหม่
            # (โหมด standalone เดิม ยังใช้งานได้ปกติถ้าใครรัน extract_frames.py ตรง ๆ)
            mvt_frame = mvt_module.launch_gui(parent=self)
            mvt_frame.pack(fill="both", expand=True)
        except Exception as exc:
            messagebox.showerror("โหลด Multi Video Tool ไม่สำเร็จ", f"เกิดข้อผิดพลาด: {exc}")
            ttk.Label(self, text=f"โหลดไม่สำเร็จ: {exc}", foreground="red", padding=20).pack()
