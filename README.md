# PK Transport (PKT)

**PK** = Pongsakorn Klaywun · **T** = Transportation

ชุดโปรแกรมวิเคราะห์ความปลอดภัยจราจร (เน้นมอเตอร์ไซค์) ตั้งแต่ชุดข้อมูลถึงตัวชี้วัด
A toolkit for traffic-safety analysis, from the dataset to the safety indicators.

```
PKT Data  →  PKT Train  →  PKT Analyze
ชุดข้อมูล     โมเดลตรวจจับ     วิเคราะห์ความปลอดภัย
```

| โมดูล | ทำอะไร | repo |
|---|---|---|
| **PKT Data** | เตรียมชุดข้อมูล: เก็บเฟรม ติดป้าย คัดกรอง แบ่งและส่งออก | [PKT-Data](https://github.com/boss8152060-cyber/PKT-Data) |
| **PKT Train** | เทรนโมเดลตรวจจับ (YOLO26, RT-DETR, RT-DETRv2) ในเครื่องหรือบน Colab | [PKT-Train](https://github.com/boss8152060-cyber/PKT-Train) |
| **PKT Analyze** | วิเคราะห์ LDP, Lateral Clearance, Gap Acceptance, TTC, PET, Speed จากวิดีโอ | [PKT-Analyze](https://github.com/boss8152060-cyber/PKT-Analyze) |

repo นี้ (**PK-Transport**) คือหน้าเปิดหลักของทั้งสามโมดูล — ไม่มีโค้ดของโมดูลอยู่ในนี้
This repo is the launcher; the three modules live in their own repos next to it.

## ติดตั้ง / Setup

โคลนทั้ง 4 repo ไว้ในโฟลเดอร์เดียวกัน (โมดูลอยู่ข้างไฟล์ `main.py`):

```text
PK-Transport/          ← repo นี้
├─ main.py, pkt/, modules.json ...
├─ PKT-Data/           ← git clone .../PKT-Data.git
├─ PKT-Train/          ← git clone .../PKT-Train.git
└─ PKT-Analyze/        ← PKT Analyze (PKStudio.py)
```

ถ้าวางที่อื่น ตั้งโฟลเดอร์ของแต่ละโมดูลได้ที่ปุ่ม **ตั้งค่า / Settings** ในแอป

## เปิดแอป / Run

```
py -3.12 main.py        (หรือดับเบิลคลิก run_pk_transport.bat)
```

หน้าต่างหลักใช้แค่ไลบรารีมาตรฐานของ Python (Tkinter) แต่ละโมดูลมี requirements ของตัวเอง
(PKT Data: `PKT-Data/requirements.txt`; PKT Analyze: Python 3.12 + torch (CUDA) + ultralytics)

- การ์ดของแต่ละโมดูลแสดงสถานะ (พบ/ไม่พบ), เวอร์ชัน (จากเลขเวอร์ชันหรือ git tag), สาขา/commit และมีปุ่ม **เปิด** / **เปิดโฟลเดอร์**
- สลับภาษา ไทย / English ได้ที่มุมขวาบน (ศัพท์เฉพาะ เช่น TTC, PET, LDP, ชื่อโมเดล คงเป็นภาษาอังกฤษทั้งสองภาษา)
- โมดูลที่เปิดจะรันเป็นโปรแกรมแยก; ข้อความที่พิมพ์ออกมาเก็บไว้ที่ `logs/<โมดูล>.log` และถ้าปิดทันทีหลังเริ่มจะแจ้งพร้อมที่อยู่ log

## PKT Train

กดปุ่ม **เปิด** ที่การ์ด PKT Train จะเปิดหน้าเทรน (เป็นหน้าต่างของแอปนี้ ใช้สคริปต์ใน `PKT-Train/` โดยไม่แก้ไฟล์ต้นฉบับ):

- เลือกโมเดล **YOLO26** (n/s/m/l/x), **RT-DETR** (l/x) หรือ **RT-DETRv2** (s/m*/m/l/x) แล้วตั้งค่า Epochs / ขนาดภาพ / Batch / Workers / Patience และการรัน (auto = ต่อ run ที่ค้าง, เริ่มใหม่, ต่อยอดจาก run เก่า) — ค่าตั้งต้นอ่านจากสคริปต์
- **เทรนในเครื่อง:** เลือกโฟลเดอร์ชุดข้อมูล (มี `data.yaml`; เว้นว่าง = ค่าตั้งต้นของสคริปต์) และโฟลเดอร์เก็บผล แล้วกด **เริ่มเทรน** — เห็น log สด และ epoch ปัจจุบัน; **หยุดหลังจบ epoch นี้** (เขียน `STOP.flag`) หรือ **หยุดทันที** (เทรนต่อได้ภายหลังเพราะสคริปต์ resume เอง)
- **เทรนบน Colab:** เลือก "บน Colab" แล้วกด **คัดลอกไปคลิปบอร์ด** (ทั้งหมด Cell 1→9 / ทั้งไฟล์ / ทีละ Cell) — โมเดลและค่าที่เลือกถูกเขียนลงในโค้ดที่คัดลอก ไปวางใน Colab ได้เลย (ปุ่มเปิด Colab ด้วย)
- ด้านบนแสดง Python ที่ใช้เทรน (ตรวจ torch / GPU / ultralytics) — ตั้งค่า Python ได้ที่ปุ่ม ตั้งค่า ของหน้าหลัก

### ส่งโมเดลที่เทรนแล้วไป PKT Analyze

- ในหน้า PKT Train มีรายการ **run ที่เทรนแล้ว** (ค้นหาในโฟลเดอร์ Runs: ชื่อ run, โมเดล, epoch ที่ดีที่สุด, mAP50 และ mAP50-95 ของ epoch นั้น) — เลือก run แล้วกด **ใช้กับ PKT Analyze**
- แอปจำโมเดลนั้นไว้ (`pkt_settings.json`, ตั้ง/ล้างเองได้ที่ **ตั้งค่า**) และเมื่อกดเปิด PKT Analyze จะส่งตัวแปร `PKT_MODEL_PATH` ให้ → ช่อง Model ของ PKT Analyze เริ่มต้นด้วยโมเดลนั้น (ต้องใช้ PKT-Analyze รุ่น PKT 1.46.0 ขึ้นไป); การ์ด PKT Analyze แสดงชื่อโมเดลที่เลือก
- run ที่มีแต่ไฟล์ `.pth` (RT-DETRv2 ทางการ) แสดงในรายการแต่ใช้กับ PKT Analyze ไม่ได้ (ต้องเป็น `.pt` จาก YOLO26 / RT-DETR)

### ตรวจและอัปเดตเวอร์ชัน

- ตอนเปิดแอป (ปิดได้ที่ **ตั้งค่า**) และเมื่อกด **ตรวจอัปเดต** แอปดึงข้อมูลจาก GitHub (`git fetch` อย่างเดียว ไม่แตะไฟล์ของคุณ) แล้วแต่ละการ์ดบอกว่า เป็นรุ่นล่าสุด / มีของใหม่ N commit / มี commit ในเครื่องที่ยังไม่ push / ต่างกัน (diverged) / ตรวจไม่ได้ (ไม่ใช่ repo git หรือไม่ได้ผูก GitHub) ถ้าต่อ GitHub ไม่ได้จะแสดงสถานะล่าสุดที่รู้พร้อมบอกว่าออฟไลน์
- กด **อัปเดต** ที่การ์ดที่มีของใหม่: แอปแสดงรายการ commit ใหม่และขอยืนยัน แล้วทำ `git pull --ff-only` (เฉพาะ fast-forward ที่ปลอดภัย — ไฟล์ที่คุณแก้เองจะไม่ถูกเขียนทับ ถ้า git ปฏิเสธจะแจ้งเหตุผลและไม่เปลี่ยนอะไร)
- ตรวจ/อัปเดตตัวแอปนี้เองได้ที่มุมขวาบน (ต้องเปิดแอปใหม่หลังอัปเดต)

### ทางลัดบนเดสก์ท็อป

**ตั้งค่า → สร้างทางลัดบนเดสก์ท็อป** สร้างไฟล์ `PK Transport.lnk` ที่เปิดแอปโดยไม่เปิดหน้าต่างคอนโซล (ใช้ Python 3.12 ถ้ามี) — สร้างเมื่อกดปุ่มเท่านั้น

## สถานะ / Status

- **0.1.0:** หน้าเปิดหลัก + เปิด PKT Data / PKT Analyze + สถานะ/เวอร์ชัน + ตั้งค่า + สองภาษา
- **0.2.0:** หน้า **PKT Train** (ดูหัวข้อด้านล่าง)
- **0.3.0:** ส่งโมเดลที่เทรนแล้ว (`best.pt`) ไปเป็นโมเดลตั้งต้นของ PKT Analyze (ดูหัวข้อด้านล่าง)
- **0.4.0:** ตรวจ/อัปเดตเวอร์ชันของโมดูลและของแอปนี้ผ่าน GitHub + ทางลัดบนเดสก์ท็อป (ดูหัวข้อด้านล่าง)
- **0.5.0:** แอปหน้าต่างเดียว: แถบเมนูซ้าย (Home / PKT Data / PKT Train / PKT Analyze / ตั้งค่า), ธีมขาว-ดำ-เทาแบบเดียวกับ PKT Data + โลโก้ PKT Data, สลับไทย/อังกฤษทันที, PKT Train เป็นหน้าในแอป (PKT Data / PKT Analyze ยังเปิดเป็นหน้าต่างแยกจากหน้าโมดูล — ขั้นต่อไปฝังเป็นแท็บ)
- **0.6.0:** PKT Data ฝังเป็นแท็บในแอป (Data / Label / Curate / Analytics / Zone / Other)
- **0.7.0:** PKT Analyze ฝังเป็นหน้าในแอป (โหลดครั้งแรกใช้เวลาไม่กี่วินาที)
- **0.8.0:** ตัวติดตั้งคลิกเดียว `install.bat` + ZIP พกพา `make_portable.py`
- **1.0.0:** รวม repo ทั้ง 4 เป็นหนึ่งเดียว (เก็บประวัติเดิมครบ); ปุ่มอัปเดตครั้งเดียวครอบคลุมทุกโมดูล
- ถัดไป: ตามความต้องการ (เช่น ส่งโฟลเดอร์ชุดข้อมูลจาก PKT Data ไป PKT Train)

## ติดตั้งบนเครื่องใหม่ / Install on another PC

1. สร้างไฟล์ ZIP พกพา: `py -3.12 make_portable.py` → `dist/PK-Transport-<เวอร์ชัน>-portable.zip` (แอป + PKT Data + PKT Train + PKT Analyze ไม่มีโมเดล/วิดีโอ/ประวัติ git)
2. ส่ง ZIP ให้ปลายทาง แตกไฟล์ แล้ว **ดับเบิลคลิก `install.bat` ครั้งเดียว** (ต้องมีอินเทอร์เน็ต ไม่ต้องใช้สิทธิ์ admin): ลง Python 3.12 ถ้ายังไม่มี, สร้าง `.venv`, ลง PyTorch (รุ่น GPU ถ้ามี NVIDIA ไม่งั้นรุ่น CPU) + ไลบรารีอื่น, สร้างทางลัด **PK Transport** บน Desktop/Start Menu, แล้วเปิดแอป
3. ครั้งต่อไปเปิดจากทางลัด (หรือ `run_pk_transport.bat`)
- ได้โค้ดมาจาก GitHub ก็ได้: **Code → Download ZIP** (หรือ `git clone https://github.com/boss8152060-cyber/PK-Transport.git`) แล้วรัน `install.bat` — ทุกโมดูลอยู่ใน repo เดียว (repo ต้องเป็น public ถึงจะโหลดได้โดยไม่ล็อกอิน)
- เครื่องที่ได้ ZIP ไม่มี `.git` → ปุ่มอัปเดตในแอปใช้ไม่ได้ ให้โหลด ZIP ใหม่แทน (ถ้า `git clone` ไว้ ปุ่มอัปเดตใช้ได้)
- สวิตช์ของ `setup.ps1`: `-DryRun` `-ForceCpu` `-NoLaunch` `-NoShortcuts`

## ทดสอบ / Tests

```
python -m unittest discover -s tests
py -3.12 tests/gui_app.py
py -3.12 tests/gui_train.py
py -3.12 tests/gui_updates.py
py -3.12 tests/gui_data.py
py -3.12 tests/gui_analyze.py
```
