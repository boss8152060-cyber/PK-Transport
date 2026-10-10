# plan.md — PK Transport

## สถานะ

- **เวอร์ชันล่าสุด:** 0.3.0 (ส่งโมเดลที่เทรนแล้วไป PKT Analyze) — ดู `CHANGELOG.md`
- **Remote:** `origin` = https://github.com/boss8152060-cyber/PK-Transport.git (push แล้ว: main + tag v0.1.0, v0.2.0)

## งาน

- [x] ขั้น 1: หน้าเปิดหลัก (การ์ด 3 โมดูล, สถานะ/เวอร์ชัน/สาขา, ปุ่มเปิด/เปิดโฟลเดอร์, ตั้งค่า, ภาษาไทย/อังกฤษ, log + แจ้งเมื่อโมดูลปิดทันที) + test
- [x] ขั้น 2: หน้า PKT Train — เลือกกลุ่มโมเดล/รุ่น (YOLO26 n/s/m/l/x, RT-DETR l/x, RT-DETRv2 s/m*/m/l/x), เทรนในเครื่อง (สำเนาสคริปต์ที่ใส่ค่าแล้ว + ตัวแปร `PKT_*`, log สด, epoch, ปุ่มหยุดผ่าน `STOP.flag`/หยุดทันที, เปิดโฟลเดอร์ผล) และปุ่ม **คัดลอกโค้ด Colab** (ทั้งหมด/ทั้งไฟล์/ทีละ Cell) — เสร็จ 2026-10-10
- [x] ขั้น 3: รายการ run ที่เทรนแล้วในหน้า PKT Train + ปุ่ม **ใช้กับ PKT Analyze** + ช่อง **โมเดลสำหรับ PKT Analyze** ในตั้งค่า; แอปส่ง `PKT_MODEL_PATH` ตอนเปิด PKT Analyze (PKT-Analyze รับตัวแปรนี้แล้วใน PKT 1.46.0) — เสร็จ 2026-10-10 (ตั้งค่าร่วมอื่น ๆ เช่นโฟลเดอร์ชุดข้อมูลยังเก็บในหน้า PKT Train)
- [ ] ขั้น 4: ตรวจ/อัปเดตเวอร์ชันของโมดูล (git fetch) และทางลัด/ตัวเปิด

## ที่ตัดสินใจแล้ว

- แอปรวม = หน้าเปิดหลัก + หน้า PKT Train ใหม่ **ไม่รวมโค้ดโมดูลเดิมเป็นไฟล์เดียว** (PKStudio.py ใหญ่ ~13,000 บรรทัด; แต่ละโมดูลรันแยกอยู่แล้ว)
- ไม่ใช้ git submodule ตอนนี้ (repo ของ PKT-Analyze อยู่ที่ `PKT-Analyze/Run` ไม่ใช่รากของโฟลเดอร์) ใช้ `modules.json` + ตั้งค่าที่อยู่แทน
- ภาษา: ไทย/อังกฤษ สลับได้ ศัพท์เฉพาะ (TTC, PET, LDP, ชื่อโมเดล ฯลฯ) ไม่แปล

## บันทึกความคืบหน้า

| วันที่ | สิ่งที่ทำ | ไฟล์ |
|---|---|---|
| 2026-10-10 | **0.3.0** ขั้น 3: `pkt/shared.py` (หา run ที่เทรนแล้ว + mAP ของ epoch ที่ดีที่สุดจาก results.csv/BEST_EPOCH, จำโมเดลของ PKT Analyze, สร้าง environment ที่มี `PKT_MODEL_PATH`), รายการ run + ปุ่มในหน้า PKT Train, ช่องโมเดลในตั้งค่า, โน้ตบนการ์ด PKT Analyze; ฝั่ง PKT-Analyze เพิ่ม `PKT_MODEL_PATH` (PKT 1.46.0 `0290a9b`); ทดสอบ unit test 38 ตัว (`test_shared.py` ใหม่ 9 ตัว) + `gui_train.py`/`gui_launcher.py` ขยายแล้วผ่านหมด; **ยังไม่ได้ลองเปิด PKT Analyze จริงแล้วดูช่อง Model ด้วยตา** (ทดสอบตัวแปรส่งต่อด้วยโมดูลปลอมและนำเข้า PKStudio.py จริงพร้อมตัวแปร) | `pkt/shared.py`, `pkt/launcher.py`, `pkt/train_page.py`, `pkt/i18n.py`, `tests/` |
| 2026-10-10 | **0.2.0** ขั้น 2: หน้า PKT Train — `pkt/train_core.py` (ตารางโมเดล/รุ่น, อ่านค่าตั้งต้นและใส่ค่าลงสำเนาสคริปต์ด้วย regex โดยไม่แก้ไฟล์ต้นฉบับ, ตัด Cell สำหรับ Colab, อ่านความคืบหน้าจาก log, ตรวจ Python/GPU) + `pkt/train_page.py` (หน้าต่าง); การ์ด Train เปิดหน้านี้; แก้บั๊กคำสั่ง Python ที่มีเครื่องหมายคำพูด (path มีช่องว่าง) บน Windows; ทดสอบ: unit test 29 ตัว (รวมสคริปต์จริงของ PKT-Train ทั้ง 3 ตัว: แพตช์แล้วยังเป็น Python ถูกต้อง Cell 1–9 ครบ) + `gui_train.py` (โฟลเดอร์ PKT-Train ปลอม: เลือกโมเดล/รุ่น, รันจริงด้วยสคริปต์ปลอม, log/epoch, STOP.flag, หยุดทันที, คัดลอก Colab, สลับภาษา) ผ่านหมด — **ยังไม่ได้เทรนจริงผ่านหน้านี้** (เทรนจริงของสคริปต์ทดสอบแยกแล้วใน PKT-Train 0.2.0) | `pkt/train_core.py`, `pkt/train_page.py`, `pkt/launcher.py`, `pkt/modules.py`, `modules.json`, `pkt/i18n.py`, `tests/` |
| 2026-10-10 | **0.1.0** ขั้น 1: หน้าเปิดหลัก + `pkt/modules.py` (หาโมดูล/เวอร์ชัน/คำสั่งเปิด) + `pkt/i18n.py` (ไทย/อังกฤษ) + ตั้งค่า + log; ทดสอบ 19 unit test + `gui_launcher.py` (โมดูลปลอม) ผ่าน; ตรวจกับโมดูลจริงบนเครื่อง: PKT Data 1.3.9, PKT Train v0.2.0, PKT Analyze PKT-1.45.1 พบครบ | `main.py`, `pkt/`, `modules.json`, `tests/`, เอกสาร |
