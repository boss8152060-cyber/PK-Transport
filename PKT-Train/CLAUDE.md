# CLAUDE.md — PKT-Train

โมดูล **PKT Train** ของ PK Transport (PKT = Pongsakorn Klaywun Transportation): สคริปต์เทรนโมเดลตรวจจับวัตถุ (รถ/คน)
ผู้ใช้เป็นคนไทย ไม่ชำนาญ git — **ตอบและอธิบายเป็นภาษาไทย**

## โครงสร้าง

- **git repo นี้อยู่ที่:** `F:\motorcycle group project\PSU Transport Project 2026\PK-Transport\PKT-Train` (branch `main`, remote `origin` = https://github.com/boss8152060-cyber/PKT-Train.git)
- สคริปต์ 3 ตัว (แต่ละตัวเขียนเป็น Cell `# %% [Cell N]` ใช้บน Google Colab และรันทั้งไฟล์ในเครื่องได้ — ตรวจเองอัตโนมัติ `RUN_ENV`):
  `Train YOLO26L Augmentation.py`, `Train RTDETR-L Augmentation.py`, `Train RT-DETRv2 PyTorch Augmentation.py` (ดู `README.md`)
- แอป **PK-Transport** (หน้า PKT Train) อ่านและแพตช์ข้อความของสคริปต์เหล่านี้ด้วย regex (`epochs = ...`, `imgsz`, `batch`, `workers`, `patience`, `training_mode`, `source_run_name`, `MODEL_SIZE = "..."`) —
  **ถ้าเปลี่ยนรูปแบบบรรทัดเหล่านี้ ต้องแก้ `pkt/train_core.py` ใน PK-Transport ด้วย** (`test_train_core.RealScripts` ตรวจให้) และ Cell ต้องมี 1–9 ครบ
- โฟลเดอร์ที่ไม่ขึ้น git (ดู `.gitignore`): `Runs/`, `_workspace/`, `_original_colab_versions/`, ไฟล์น้ำหนัก (`.pt`, `.pth`, `.engine`)

## กฎของสคริปต์

- **ห้ามทำให้ Colab พัง:** พฤติกรรมบน Colab ต้องเหมือนเดิม (path ของ Drive, `# @param`, การคัดลอกทีละ Cell); ส่วนที่มีผลข้างเคียงต้องอยู่ใต้ `if IS_MAIN:` (Windows ตัวโหลดข้อมูลแบบหลายโปรเซสนำไฟล์ไปอ่านใหม่)
- ไม่มีคำสั่งแบบ notebook (`!pip`, `!ls`) ในไฟล์ — ใช้ `subprocess` แทน เพื่อให้รันเป็นไฟล์ `.py` ได้
- ก่อน commit: ตรวจ syntax ทุกไฟล์ (`python -c "import ast,sys;ast.parse(open(sys.argv[1],encoding='utf-8').read())" <ไฟล์>`); ถ้าแก้ตรรกะเทรน ให้ทดสอบจริงด้วยชุดข้อมูลจิ๋ว/โมเดลจาก yaml (ไม่ต้องดาวน์โหลดน้ำหนัก) ตามที่ทำใน 0.2.0 — RT-DETRv2 ยังไม่เคยทดสอบรันจริง

## กฎการใช้ git

หลังทำงานเสร็จและตรวจแล้ว commit + push ให้เอง (remote `origin` ของ repo นี้เท่านั้น):

```
PKT-Train <x.y.z>: <คำอธิบายสั้น ๆ_แบบ_CamelCase> [(PASS)]
```

- **ชื่อ repo นำหน้าเลขเวอร์ชัน เหมือนกันทุก repo ของ PK Transport** (`PK-Transport` / `PKT-Analyze` / `PKT-Data` / `PKT-Train`); commit เก่าไม่แก้
- `y` ขึ้นเมื่อมีความสามารถใหม่ (เช่นรองรับรุ่น/โมเดลใหม่), `z` เมื่อแก้/ปรับเรื่องเดิมหรือเอกสาร
- ทุก commit: เพิ่มบรรทัดใน `CHANGELOG.md` + ติด tag `v<x.y.z>` + `git push` พร้อม `git push origin v<x.y.z>`
- `(PASS)` เฉพาะเมื่อผู้ใช้ยืนยันแล้วว่าผ่าน; บรรทัดสุดท้ายของ message ใส่ trailer `Co-Authored-By: ...` ตามที่ระบบกำหนด
- **ห้าม** `git push --force`, `git reset --hard`, `git rebase`, `git commit --amend` กับ commit ที่ push แล้ว, ลบ branch/tag/ประวัติ โดยไม่ขออนุญาต; ห้าม push ไป remote อื่น
