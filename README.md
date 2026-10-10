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
└─ PKT-Analyze/        ← โฟลเดอร์แม่; repo อยู่ที่ PKT-Analyze/Run (git clone .../PKT-Analyze.git Run)
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

## สถานะ / Status

- **0.1.0:** หน้าเปิดหลัก + เปิด PKT Data / PKT Analyze + สถานะ/เวอร์ชัน + ตั้งค่า + สองภาษา
- ถัดไป: หน้า PKT Train (เลือกรุ่น เทรนในเครื่อง ปุ่มคัดลอกโค้ด Colab), ส่งโมเดลที่เทรนแล้วไปเป็นโมเดลตั้งต้นของ PKT Analyze

## ทดสอบ / Tests

```
python -m unittest discover -s tests
py -3.12 tests/gui_launcher.py
```
