# plan.md — PK Transport

## สถานะ

- **เวอร์ชันล่าสุด:** 0.7.0 (แอปหน้าต่างเดียว ธีมเดียวกับ PKT Data สลับภาษาไทย/อังกฤษ) — ดู `CHANGELOG.md`
- **Remote:** `origin` = https://github.com/boss8152060-cyber/PK-Transport.git (push แล้ว: main + tag v0.1.0, v0.2.0)

## งาน

- [x] ขั้น 1: หน้าเปิดหลัก (การ์ด 3 โมดูล, สถานะ/เวอร์ชัน/สาขา, ปุ่มเปิด/เปิดโฟลเดอร์, ตั้งค่า, ภาษาไทย/อังกฤษ, log + แจ้งเมื่อโมดูลปิดทันที) + test
- [x] ขั้น 2: หน้า PKT Train — เลือกกลุ่มโมเดล/รุ่น (YOLO26 n/s/m/l/x, RT-DETR l/x, RT-DETRv2 s/m*/m/l/x), เทรนในเครื่อง (สำเนาสคริปต์ที่ใส่ค่าแล้ว + ตัวแปร `PKT_*`, log สด, epoch, ปุ่มหยุดผ่าน `STOP.flag`/หยุดทันที, เปิดโฟลเดอร์ผล) และปุ่ม **คัดลอกโค้ด Colab** (ทั้งหมด/ทั้งไฟล์/ทีละ Cell) — เสร็จ 2026-10-10
- [x] ขั้น 3: รายการ run ที่เทรนแล้วในหน้า PKT Train + ปุ่ม **ใช้กับ PKT Analyze** + ช่อง **โมเดลสำหรับ PKT Analyze** ในตั้งค่า; แอปส่ง `PKT_MODEL_PATH` ตอนเปิด PKT Analyze (PKT-Analyze รับตัวแปรนี้แล้วใน PKT 1.46.0) — เสร็จ 2026-10-10 (ตั้งค่าร่วมอื่น ๆ เช่นโฟลเดอร์ชุดข้อมูลยังเก็บในหน้า PKT Train)
- [x] ขั้น 4: ตรวจอัปเดตของโมดูลและของแอป (`git fetch` + ปุ่มอัปเดตแบบ `pull --ff-only` พร้อมยืนยัน), ตรวจตอนเปิดแอป (ปิดได้), ทางลัดเดสก์ท็อป (ปุ่มใน ตั้งค่า) — เสร็จ 2026-10-10
- [x] ขั้น 5 (0.5.0): แอปหน้าต่างเดียว — เปลือกแอป/ธีม/Home/ตั้งค่า/PKT Train ในแอป; ขั้นต่อไปตามแผน: ฝัง PKT Data เป็นแท็บ → ฝัง PKT Analyze → ตัวติดตั้งคลิกเดียว/ZIP พกพา → รวม repo
- [ ] ถัดไป (ยังไม่ได้ขอ): ส่งโฟลเดอร์ชุดข้อมูลจาก PKT Data ไป PKT Train; ตัวเปิดที่ติดตั้ง/แพ็กเป็นโปรแกรม

## ที่ตัดสินใจแล้ว

- แอปรวม = หน้าเปิดหลัก + หน้า PKT Train ใหม่ **ไม่รวมโค้ดโมดูลเดิมเป็นไฟล์เดียว** (PKStudio.py ใหญ่ ~13,000 บรรทัด; แต่ละโมดูลรันแยกอยู่แล้ว)
- ไม่ใช้ git submodule ตอนนี้ (repo ของ PKT-Analyze อยู่ที่ `PKT-Analyze/Run` ไม่ใช่รากของโฟลเดอร์) ใช้ `modules.json` + ตั้งค่าที่อยู่แทน
- ภาษา: ไทย/อังกฤษ สลับได้ ศัพท์เฉพาะ (TTC, PET, LDP, ชื่อโมเดล ฯลฯ) ไม่แปล

## บันทึกความคืบหน้า

| วันที่ | สิ่งที่ทำ | ไฟล์ |
|---|---|---|
| 2026-10-10 | **0.7.0** ขั้น 3: ฝัง PKT Analyze เป็นแท็บ (`pages/analyze.py`; `modules.json` analyze มี `page: analyze`); ทดสอบ `tests/gui_analyze.py` (โหลดของจริง ต้องมี torch) + ถ่ายภาพหน้าจอจริง; **ยังไม่ได้วิเคราะห์วิดีโอจริงจากในแท็บ, ข้อความใน PKT Analyze ยังเป็นไทยล้วน (ยังไม่มีอังกฤษ), ปุ่มรีสตาร์ทด้วย Python CUDA ของ PKStudio.py ยังไม่ได้ลอง** | `pkt/ui/pages/analyze.py`, `pkt/ui/app.py`, `pkt/ui/kit.py`, `pkt/ui/theme.py`, `modules.json`, `tests/` |
| 2026-10-10 | **0.6.0** ขั้น 2: ฝัง PKT Data เป็นแท็บ (`pages/data.py`; `modules.json` data มี `page: data`); `show()` ซ่อนหน้าอื่นจริง; ทดสอบ `tests/gui_data.py` (โหลดของจริง 6 แท็บ สลับ ซ่อน/แสดง ภาษา) + `gui_app.py` ปรับ, ถ่ายภาพหน้าจอจริง; **ยังไม่ได้ลองใช้งานจริงทีละฟีเจอร์ (ดึงเฟรม ตีกรอบ ฯลฯ) ในแท็บ และข้อความใน PKT Data ยังไม่แปลไทย** | `pkt/ui/pages/data.py`, `pkt/ui/app.py`, `modules.json`, `tests/` |
| 2026-10-10 | **0.5.1** PKT Train: การ์ดตั้งค่าขั้นสูง = ทุกช่อง `# @param` ของสคริปต์ (อ่านด้วย `parse_params`, เขียนกลับด้วย `patch_params` คงคอมเมนต์/รูปแบบตัวเลขเดิม); unit test 54 ตัว + gui_train ตรวจว่าค่าไปถึงสคริปต์จริง; ถ่ายภาพหน้าจอตรวจเลย์เอาต์ | `pkt/train_core.py`, `pkt/ui/pages/train.py`, `pkt/i18n.py`, `tests/` |
| 2026-10-10 | **0.5.0** แอปหน้าต่างเดียว: แพ็กเกจ `pkt/ui/` (theme โทน PKT Data, bind = สลับภาษาสด, kit, app, pages home/module/settings/train), `assets/icon.ico` จาก PKT Data, ลบ `launcher.py`/`train_page.py`; ทดสอบ unit 50 ตัว + `gui_app.py`/`gui_train.py`/`gui_updates.py` ผ่านหมด, ถ่ายภาพหน้าจอจริงไทย/อังกฤษทุกหน้า; **PKT Data/Analyze ยังเปิดเป็นหน้าต่างแยก** | `pkt/ui/`, `main.py`, `tests/`, เอกสาร |
| 2026-10-10 | **0.4.0** ขั้น 4: `pkt/updates.py` (`check_repo` = fetch + นับ ahead/behind, `incoming`, `pull_ff` = fast-forward อย่างเดียว), `pkt/shortcut.py` (.lnk ผ่าน PowerShell), ปุ่ม ตรวจอัปเดต/อัปเดตบนการ์ดและมุมหัวหน้าต่าง, ตัวเลือกตรวจตอนเปิดแอป, ปุ่มสร้างทางลัดใน ตั้งค่า; **รูปแบบชื่อ commit ใหม่ทุก repo:** `<ชื่อ repo> <x.y.z>: <คำอธิบาย>` (กฎใน CLAUDE.md ของ PK-Transport / PKT-Analyze 1.46.1 / PKT-Data 1.3.9(1) / PKT-Train 0.2.1 ที่เพิ่ม CLAUDE.md+CHANGELOG ด้วย); ทดสอบ: unit test 49 ตัว (`test_updates.py` ใช้ repo git จริงชั่วคราว: behind/ahead/diverged/ออฟไลน์/pull ปลอดภัย; `test_shortcut.py` สร้าง .lnk จริงในโฟลเดอร์ชั่วคราวแล้วอ่านกลับ) + `gui_updates.py` (หน้าต่างจริงกับ repo ชั่วคราว) ผ่านหมด; ตรวจ `check_repo` กับ repo จริงทั้ง 4 ตัวบนเครื่อง = เป็นรุ่นล่าสุดทั้งหมด; **ยังไม่ได้กดปุ่ม อัปเดต กับ repo จริง และไม่ได้สร้างทางลัดบนเดสก์ท็อปจริง** | `pkt/updates.py`, `pkt/shortcut.py`, `pkt/launcher.py`, `pkt/i18n.py`, `tests/`, เอกสาร |
| 2026-10-10 | **0.3.0** ขั้น 3: `pkt/shared.py` (หา run ที่เทรนแล้ว + mAP ของ epoch ที่ดีที่สุดจาก results.csv/BEST_EPOCH, จำโมเดลของ PKT Analyze, สร้าง environment ที่มี `PKT_MODEL_PATH`), รายการ run + ปุ่มในหน้า PKT Train, ช่องโมเดลในตั้งค่า, โน้ตบนการ์ด PKT Analyze; ฝั่ง PKT-Analyze เพิ่ม `PKT_MODEL_PATH` (PKT 1.46.0 `0290a9b`); ทดสอบ unit test 38 ตัว (`test_shared.py` ใหม่ 9 ตัว) + `gui_train.py`/`gui_launcher.py` ขยายแล้วผ่านหมด; **ยังไม่ได้ลองเปิด PKT Analyze จริงแล้วดูช่อง Model ด้วยตา** (ทดสอบตัวแปรส่งต่อด้วยโมดูลปลอมและนำเข้า PKStudio.py จริงพร้อมตัวแปร) | `pkt/shared.py`, `pkt/launcher.py`, `pkt/train_page.py`, `pkt/i18n.py`, `tests/` |
| 2026-10-10 | **0.2.0** ขั้น 2: หน้า PKT Train — `pkt/train_core.py` (ตารางโมเดล/รุ่น, อ่านค่าตั้งต้นและใส่ค่าลงสำเนาสคริปต์ด้วย regex โดยไม่แก้ไฟล์ต้นฉบับ, ตัด Cell สำหรับ Colab, อ่านความคืบหน้าจาก log, ตรวจ Python/GPU) + `pkt/train_page.py` (หน้าต่าง); การ์ด Train เปิดหน้านี้; แก้บั๊กคำสั่ง Python ที่มีเครื่องหมายคำพูด (path มีช่องว่าง) บน Windows; ทดสอบ: unit test 29 ตัว (รวมสคริปต์จริงของ PKT-Train ทั้ง 3 ตัว: แพตช์แล้วยังเป็น Python ถูกต้อง Cell 1–9 ครบ) + `gui_train.py` (โฟลเดอร์ PKT-Train ปลอม: เลือกโมเดล/รุ่น, รันจริงด้วยสคริปต์ปลอม, log/epoch, STOP.flag, หยุดทันที, คัดลอก Colab, สลับภาษา) ผ่านหมด — **ยังไม่ได้เทรนจริงผ่านหน้านี้** (เทรนจริงของสคริปต์ทดสอบแยกแล้วใน PKT-Train 0.2.0) | `pkt/train_core.py`, `pkt/train_page.py`, `pkt/launcher.py`, `pkt/modules.py`, `modules.json`, `pkt/i18n.py`, `tests/` |
| 2026-10-10 | **0.1.0** ขั้น 1: หน้าเปิดหลัก + `pkt/modules.py` (หาโมดูล/เวอร์ชัน/คำสั่งเปิด) + `pkt/i18n.py` (ไทย/อังกฤษ) + ตั้งค่า + log; ทดสอบ 19 unit test + `gui_launcher.py` (โมดูลปลอม) ผ่าน; ตรวจกับโมดูลจริงบนเครื่อง: PKT Data 1.3.9, PKT Train v0.2.0, PKT Analyze PKT-1.45.1 พบครบ | `main.py`, `pkt/`, `modules.json`, `tests/`, เอกสาร |
