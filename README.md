# PK Transport (PKT)

**PK** = Pongsakorn Klaywun · **T** = Transportation

ชุดโปรแกรมวิเคราะห์ความปลอดภัยจราจร (เน้นมอเตอร์ไซค์) ตั้งแต่ชุดข้อมูล โมเดลตรวจจับ จนถึงตัวชี้วัดความปลอดภัย
A toolkit for traffic-safety analysis, from the dataset to the safety indicators.

```
PKT Data  →  PKT Train  →  PKT Analyze
ชุดข้อมูล     โมเดลตรวจจับ     วิเคราะห์ความปลอดภัย
```

**PK Transport** คือแอปหลัก (หน้าต่างเดียว สลับไทย/อังกฤษ ธีมขาว-ดำ-เทา) ส่วนแต่ละโปรแกรมเป็น **โมดูล** ที่ติดตั้งแยก มี repo และเวอร์ชันของตัวเอง:

| โมดูล | ทำอะไร | repo |
|---|---|---|
| **PKT Data** | เตรียมชุดข้อมูล: เก็บเฟรม ติดป้าย คัดกรอง แบ่งและส่งออก | [PKT-Data](https://github.com/boss8152060-cyber/PKT-Data) |
| **PKT Train** | เทรนโมเดลตรวจจับ (YOLO26, RT-DETR, RT-DETRv2) ในเครื่องหรือบน Colab | [PKT-Train](https://github.com/boss8152060-cyber/PKT-Train) |
| **PKT Analyze** | วิเคราะห์ LDP, Lateral Clearance, Gap Acceptance, TTC, PET, Speed จากวิดีโอ | [PKT-Analyze](https://github.com/boss8152060-cyber/PKT-Analyze) |

## ติดตั้ง / Install

1. เปิด https://github.com/boss8152060-cyber/PK-Transport → **Code → Download ZIP** (หรือ `git clone https://github.com/boss8152060-cyber/PK-Transport.git`) → แตกไฟล์
2. ดับเบิลคลิก **`install.bat`** ครั้งเดียว (ต้องมีอินเทอร์เน็ต ไม่ต้องใช้สิทธิ์ admin) — ลง Python 3.12 ถ้ายังไม่มี, สร้าง `.venv`, สร้างทางลัด **PK Transport** บน Desktop แล้วเปิดแอป ใช้เวลาไม่กี่นาที เพราะตัวแอปไม่ต้องใช้ไลบรารีใหญ่
3. ในแอปไปที่หน้า **โมดูล / Modules** แล้วกด **ติดตั้ง** เฉพาะตัวที่ต้องใช้ (เช่น แค่ PKT Data กับ PKT Train) — แอปโหลดโมดูลจาก GitHub พร้อมไลบรารีที่ต้องใช้ (PyTorch รุ่น GPU ถ้ามี NVIDIA ไม่งั้นรุ่น CPU) ใช้เวลาหลายนาทีสำหรับครั้งแรก
   - อยากติดตั้งโมดูลพร้อมตัวแอปเลย: `install.bat -Modules all` (หรือ `-Modules data,train`)

ครั้งต่อไปเปิดจากทางลัด (หรือ `run_pk_transport.bat`)

## จัดการโมดูล / Modules

หน้า **โมดูล** ในแอป (ผูกกับ GitHub ตลอด):

- **ติดตั้ง / ถอนการติดตั้ง** แต่ละโมดูลแยกกัน หรือ **ติดตั้งที่ยังไม่มีทั้งหมด / อัปเดตทั้งหมด**
- **เลือกเวอร์ชัน**: ลิสต์ของแต่ละโมดูลมีทุกเวอร์ชันที่ปล่อย (git tag) — เลือกรุ่นเก่าเพื่อย้อนกลับได้ ไม่ต้องกลัวพัง ค่าตั้ง โมเดลที่เทรนแล้ว และผลลัพธ์ไม่ถูกแตะ (เก็บใน `user_data/` นอกโฟลเดอร์โมดูล)
- **แจ้งเตือนเวอร์ชันใหม่**: แอปตรวจ GitHub ตอนเปิด (ปิดได้ในตั้งค่า) ถ้ามีรุ่นใหม่ที่การ์ดบน Home และหน้าโมดูลจะขึ้นปุ่ม อัปเดต
- ถ้าเปลี่ยนเวอร์ชัน/ถอนโมดูลที่กำลังเปิดอยู่ แอปจะขอให้รีสตาร์ท; โมดูลที่ยังไม่เคยเปิดเปลี่ยนได้ทันที

**อัปเดตตัวแอปหลัก**: ตั้งค่า → อัปเดตแอปนี้ (โฟลเดอร์ git ใช้ `git pull`; โฟลเดอร์จาก Download ZIP เทียบเลขเวอร์ชันกับ GitHub แล้วดาวน์โหลดไฟล์ใหม่มาทับ ไม่แตะ `.venv` ค่าตั้ง `modules/` `user_data/`)

## ส่งให้คนอื่น / Share

- ส่งลิงก์ GitHub ด้านบน (ทำตามหัวข้อติดตั้ง)
- หรือ `py -3.12 make_portable.py` ได้ ZIP พกพาใน `dist/` (เล็ก ~1 MB); เติม `--with-modules` ถ้าอยากให้ไฟล์ของโมดูลติดไปด้วย (ไลบรารียังโหลดตอน `install.bat`)
- ไฟล์โมเดล `.pt` วิดีโอ และข้อมูลทดสอบไม่อยู่ใน GitHub/ZIP ต้องส่งแยก

## โครงสร้าง / Layout

```text
PK-Transport/
├─ main.py, install.bat, setup.ps1, make_portable.py, modules.json (ทะเบียนโมดูล)
├─ pkt/            ← โค้ดของแอปหลัก (หน้าต่าง ภาษา ตัวจัดการโมดูล modman.py ตัวโหลดปลั๊กอิน plugin.py ตัวลงไลบรารี envsetup.py ...)
├─ modules/        ← โมดูลที่ติดตั้งแล้ว (modules/data, modules/train, modules/analyze) — ไม่ขึ้น git
├─ user_data/      ← ข้อมูลของผู้ใช้ (ผลเทรน ผลวิเคราะห์ แคช) — ไม่ขึ้น git
└─ pkt_settings.json, logs/   ← ค่าตั้งของผู้ใช้ — ไม่ขึ้น git
```

โมดูลคือ repo ที่มี `pkt_module.json` (บอกว่าโมดูลคืออะไร เวอร์ชัน รุ่นแอปหลักต่ำสุด ไลบรารี) กับ `pkt_plugin.py` (วิธีที่โมดูลปรากฏในหน้าต่าง) — รายละเอียดและกฎการปล่อยเวอร์ชันใน `pkt/plugin.py` และ CLAUDE.md ของแต่ละ repo

## สำหรับนักพัฒนา / Developing

- ใช้เฉพาะไลบรารีมาตรฐานของ Python ในแอปหลัก
- ทดสอบโมดูลกับแอปหลักโดยไม่ต้องปล่อยเวอร์ชัน: ตั้งโฟลเดอร์ของโมดูลเป็น "โฟลเดอร์ที่เชื่อมไว้" ในหน้าตั้งค่า (หรือ `PKT_MODULES_SRC` ตอนรันเทสต์)
- เทสต์: `python -m unittest discover -s tests` และ `py -3.12 tests/gui_modules.py`, `gui_app.py`, `gui_updates.py`; ชุดที่ใช้โมดูลจริง (`gui_real_modules.py`, `gui_train_module.py`, `test_lang_coverage.py`) ต้องตั้ง `PKT_MODULES_SRC=<โฟลเดอร์ที่มี clone ของ PKT-Data / PKT-Train / PKT-Analyze>`
- ประวัติเวอร์ชันของแอปหลัก: [CHANGELOG.md](CHANGELOG.md)
