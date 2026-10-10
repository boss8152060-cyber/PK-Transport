"""Thai / English texts of the launcher.

Technical terms stay in English in BOTH languages (they are the names of the indicators and models, not words to translate):
see KEEP_TERMS. Add a key to both languages; `Translator.t` falls back to English and then to the key itself.
"""

LANGS = ("th", "en")
LANG_NAMES = {"th": "ไทย", "en": "English"}

# never translated, in either language (tests check that the texts that mention them keep them as written)
KEEP_TERMS = (
    "TTC", "PET", "LDP", "Lateral Clearance", "Gap Acceptance", "Speed", "Headway",
    "YOLO26", "RT-DETR", "RT-DETRv2", "Colab", "PKT Data", "PKT Train", "PKT Analyze", "PK Transport",
)

TEXT = {
    "en": {
        "app_title": "PK Transport",
        "subtitle": "Dataset → Detection model → Traffic safety analysis",
        "language": "Language",
        "settings": "Settings",
        "open": "Open",
        "open_folder": "Open folder",
        "found": "Found",
        "missing": "Not found",
        "version": "Version",
        "branch": "Branch",
        "changes": "uncommitted changes",
        "data_desc": "Prepare datasets: collect frames, label, curate, split and export.",
        "train_desc": "Train detection models (YOLO26, RT-DETR, RT-DETRv2) on this PC or on Colab.",
        "analyze_desc": "Analyze traffic safety and driver behavior from video: LDP, Lateral Clearance, Gap Acceptance, TTC, PET, Speed.",
        "train_soon": "The training page comes in the next step. Meanwhile the scripts are in the folder.",
        "opened": "Opened {name}",
        "launch_failed": "Could not open {name}",
        "exited_early": "{name} closed right after starting (exit code {code}). See the log:\n{log}",
        "module_missing": "{name} was not found at:\n{path}\n\nClone it next to this app or set its folder in Settings.",
        "entry_missing": "The start file of {name} was not found:\n{path}",
        "python_missing": "No Python was found to start {name}. Set one in Settings.",
        "settings_title": "Settings",
        "module_folder": "Folder",
        "python_command": "Python command (blank = automatic)",
        "browse": "Browse…",
        "save": "Save",
        "cancel": "Cancel",
        "saved": "Settings saved",
        "pick_folder": "Choose the folder of {name}",
        "pipeline_hint": "Order of work: PKT Data → PKT Train → PKT Analyze",
        "git_missing": "git not found (version info limited)",
    },
    "th": {
        "app_title": "PK Transport",
        "subtitle": "ชุดข้อมูล → โมเดลตรวจจับ → วิเคราะห์ความปลอดภัยจราจร",
        "language": "ภาษา",
        "settings": "ตั้งค่า",
        "open": "เปิด",
        "open_folder": "เปิดโฟลเดอร์",
        "found": "พบ",
        "missing": "ไม่พบ",
        "version": "เวอร์ชัน",
        "branch": "สาขา",
        "changes": "มีการแก้ที่ยังไม่ commit",
        "data_desc": "เตรียมชุดข้อมูล: เก็บเฟรม ติดป้าย คัดกรอง แบ่งและส่งออก",
        "train_desc": "เทรนโมเดลตรวจจับ (YOLO26, RT-DETR, RT-DETRv2) ในเครื่องหรือบน Colab",
        "analyze_desc": "วิเคราะห์ความปลอดภัยและพฤติกรรมผู้ขับขี่จากวิดีโอ: LDP, Lateral Clearance, Gap Acceptance, TTC, PET, Speed",
        "train_soon": "หน้าเทรนจะมาในขั้นถัดไป ตอนนี้สคริปต์อยู่ในโฟลเดอร์",
        "opened": "เปิด {name} แล้ว",
        "launch_failed": "เปิด {name} ไม่ได้",
        "exited_early": "{name} ปิดทันทีหลังเริ่ม (exit code {code}) ดู log ที่:\n{log}",
        "module_missing": "ไม่พบ {name} ที่:\n{path}\n\nโคลนไว้ข้างแอปนี้ หรือตั้งโฟลเดอร์ในหน้าตั้งค่า",
        "entry_missing": "ไม่พบไฟล์เริ่มต้นของ {name}:\n{path}",
        "python_missing": "ไม่พบ Python สำหรับเปิด {name} ตั้งค่าได้ในหน้าตั้งค่า",
        "settings_title": "ตั้งค่า",
        "module_folder": "โฟลเดอร์",
        "python_command": "คำสั่ง Python (ว่าง = อัตโนมัติ)",
        "browse": "เลือก…",
        "save": "บันทึก",
        "cancel": "ยกเลิก",
        "saved": "บันทึกการตั้งค่าแล้ว",
        "pick_folder": "เลือกโฟลเดอร์ของ {name}",
        "pipeline_hint": "ลำดับงาน: PKT Data → PKT Train → PKT Analyze",
        "git_missing": "ไม่พบ git (ข้อมูลเวอร์ชันจำกัด)",
    },
}


class Translator:
    def __init__(self, lang="th"):
        self.lang = lang if lang in LANGS else "th"

    def set_lang(self, lang):
        if lang in LANGS:
            self.lang = lang

    def t(self, key, **kwargs):
        text = TEXT.get(self.lang, {}).get(key)
        if text is None:
            text = TEXT["en"].get(key, key)
        try:
            return text.format(**kwargs) if kwargs else text
        except (KeyError, IndexError):
            return text
