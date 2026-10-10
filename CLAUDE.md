# CLAUDE.md — PK Transport (หน้าเปิดหลัก)

แอปรวม **PK Transport (PKT)** = หน้าเปิดหลักของ 3 โมดูล: **PKT Data**, **PKT Train**, **PKT Analyze**
(PKT = Pongsakorn Klaywun Transportation) ผู้ใช้เป็นคนไทย ไม่ชำนาญ git — **ตอบและอธิบายเป็นภาษาไทย**

## โครงสร้าง

- **git repo นี้อยู่ที่:** `F:\motorcycle group project\PSU Transport Project 2026\PK-Transport` (branch `main`)
- โมดูลเป็น **repo แยก** วางข้างกันใต้โฟลเดอร์นี้ (อยู่ใน `.gitignore` ของ repo นี้ ห้าม commit โค้ดโมดูลที่นี่):
  - `PKT-Data/` (repo root) — remote https://github.com/boss8152060-cyber/PKT-Data.git
  - `PKT-Train/` (repo root) — remote https://github.com/boss8152060-cyber/PKT-Train.git
  - `PKT-Analyze/` โฟลเดอร์แม่ (`Run/` = repo, `Input/ Output/ Other/` = ข้อมูลทดสอบนอก git) — remote https://github.com/boss8152060-cyber/PKT-Analyze.git
  - `_backups/` สำรองเก่า
- โค้ดของแอปนี้: `main.py` (ตัวเปิด), `pkt/` (`modules.py` ตรรกะหาโมดูล/เวอร์ชัน/คำสั่งเปิด ไม่ผูก GUI, `launcher.py` หน้าต่างหลัก Tk, `train_core.py` ตรรกะ PKT Train ไม่ผูก GUI, `shared.py` สิ่งที่ใช้ร่วมกันระหว่างโมดูล (หา run ที่เทรนแล้ว, โมเดลของ PKT Analyze, `PKT_MODEL_PATH`), `train_page.py` หน้าเทรน, `i18n.py` ข้อความไทย/อังกฤษ), `modules.json` (ที่อยู่ตั้งต้นของโมดูล), `tests/`
- ใช้เฉพาะไลบรารีมาตรฐานของ Python (ไม่เพิ่ม dependency ภายนอกโดยไม่จำเป็น)
- ไฟล์ของผู้ใช้ที่ไม่ขึ้น git: `pkt_settings.json` (ภาษา, โฟลเดอร์/Python ที่ผู้ใช้ตั้ง), `logs/`

## กฎของแอป

- **ไม่แก้โค้ดของโมดูลจากที่นี่** — แต่ละโมดูลแก้และ commit ใน repo ของตัวเอง (ดู CLAUDE.md ของโมดูลนั้น) การเรียกโมดูลทำเป็นโปรแกรมแยก (subprocess) เท่านั้น
- ข้อความบนหน้าจอใส่ใน `pkt/i18n.py` ทั้งไทยและอังกฤษ (key ต้องครบทั้งสองภาษา — มีเทสต์ตรวจ); **ศัพท์เฉพาะไม่แปล** (TTC, PET, LDP, Lateral Clearance, Gap Acceptance, Speed, ชื่อโมเดล YOLO26/RT-DETR/RT-DETRv2, Colab, ชื่อโมดูล) ดู `KEEP_TERMS`
- เรียกตัวชี้วัดด้วยชื่อ ห้ามใช้รหัส Y1–Y7
- เปลี่ยนเลย์เอาต์ต้องถ่ายภาพหน้าจอตรวจ (PIL `ImageGrab` ได้ แต่ Tk บนเครื่องนี้ไม่ DPI-aware ภาพจับอาจถูกตัด)

## ตรวจก่อน commit ทุกครั้ง (รันจากโฟลเดอร์นี้)

1. `python -m py_compile main.py pkt/*.py`
2. `python -m unittest discover -s tests -v` (test_modules, test_i18n, test_train_core — อ่าน/แพตช์สคริปต์จริงใน `PKT-Train` ถ้ามีอยู่ข้างกัน, test_shared)
3. `py -3.12 tests/gui_launcher.py` (หน้าต่างจริงแบบซ่อน + โมดูลปลอมในโฟลเดอร์ชั่วคราว)
4. `py -3.12 tests/gui_train.py` (หน้า PKT Train + โฟลเดอร์ PKT-Train ปลอม + สคริปต์เทรนปลอมที่รันจริงเป็น subprocess)

## กฎการใช้ git

หลังทำงานเสร็จและตรวจแล้ว commit + push ให้เอง (remote `origin` ของ repo นี้เท่านั้น):

```
PK Transport <x.y.z>: <คำอธิบายสั้น ๆ_แบบ_CamelCase> [(PASS)]
```
- เพิ่มบรรทัดใน `CHANGELOG.md` + ติด tag `v<x.y.z>` + `git push` พร้อม `git push origin v<x.y.z>`
- `(PASS)` เฉพาะเมื่อผู้ใช้ยืนยันแล้วว่าผ่าน; บรรทัดสุดท้ายของ message ใส่ trailer `Co-Authored-By: ...` ตามที่ระบบกำหนด
- อัปเดต `plan.md` เมื่อทำงานเสร็จ
- **ห้าม** `git push --force`, `git reset --hard`, `git rebase`, `git commit --amend` กับ commit ที่ push แล้ว, ลบ branch/tag/ประวัติ โดยไม่ขออนุญาต; ห้าม push ไป remote อื่น

## ข้อมูลอ้างอิง

- Python 3.12 (`py -3.12`) มี torch+CUDA ใช้กับโมดูลที่ต้องใช้ GPU; แอปนี้เปิดโมดูลด้วย `py -3.12` ถ้ามี ไม่งั้นใช้ Python ปัจจุบัน (ตั้งเองได้ที่ตั้งค่า)
- PKT Train = หน้าต่างของแอปนี้ (modules.json `page: "train"`) ไม่ใช่โปรแกรมแยก: ใส่ค่าที่เลือกลงใน **สำเนา** ของสคริปต์ (`PKT-Train/_workspace/_gui_runs/`) แล้วรันด้วย Python ที่ตั้งไว้ + ตัวแปร `PKT_*`; ห้ามแก้สคริปต์ต้นฉบับใน PKT-Train จากแอปนี้ (แก้และ commit ใน repo PKT-Train)
- ถ้าเปลี่ยนชื่อ/รูปแบบบรรทัดค่าตั้งต้นในสคริปต์ PKT-Train (`epochs = ...`, `MODEL_SIZE = "..."`) ต้องปรับ regex ใน `train_core.py` — `test_train_core.RealScripts` จะเตือน
