# CLAUDE.md — PK Transport (แอปหลัก)

**PK Transport (PKT)** = แอปหลักของ 3 โมดูล: **PKT Data**, **PKT Train**, **PKT Analyze** (PKT = Pongsakorn Klaywun Transportation)
ผู้ใช้เป็นคนไทย ไม่ชำนาญ git — **ตอบและอธิบายเป็นภาษาไทย**

## โครงสร้าง (ตั้งแต่ 2.0.0: แอปหลัก + โมดูลที่ติดตั้งแยก)

- repo นี้ https://github.com/boss8152060-cyber/PK-Transport (branch `main`) มี **เฉพาะแอปหลัก**; แต่ละโมดูลเป็น **repo ของตัวเอง** (เวอร์ชัน/tag/CHANGELOG ของตัวเอง):
  - https://github.com/boss8152060-cyber/PKT-Data (tag `vX.Y.Z`), https://github.com/boss8152060-cyber/PKT-Train (tag `vX.Y.Z`), https://github.com/boss8152060-cyber/PKT-Analyze (tag `PKT-X.Y.Z`)
  - ประวัติเดิมของทั้งสามอยู่ครบในแต่ละ repo (ช่วง 1.0.0–1.2.0 เคยรวมเป็น repo เดียวชั่วคราว ประวัติของช่วงนั้นอยู่ใน tag `v1.0.0`–`v1.2.0` ของ repo นี้)
- แอปหลักโหลดโมดูลเวอร์ชันที่ผู้ใช้เลือก (ตาม git tag) มาไว้ใน `modules/<id>/` ผ่านหน้า **โมดูล**; ข้อมูลของผู้ใช้อยู่ใน `user_data/` (ไม่ถูกแตะตอนอัปเดต/ถอน/ย้อนเวอร์ชันโมดูล)
- ไฟล์สำคัญ:
  - `modules.json` — ทะเบียนโมดูล: `id`, `name`, `repo`, `tag_regex` (กลุ่ม 1 = เลขเวอร์ชัน), `min_version` (เวอร์ชันแรกที่เป็นโมดูลของ 2.0.0 ขึ้นไป), `desc_key`
  - `pkt/modman.py` ตัวจัดการโมดูล (ไม่ผูก GUI; ใช้จากบรรทัดคำสั่งได้: `python -m pkt.modman list|install|update|uninstall|prepare`) — ดึง tag จาก GitHub API, ดาวน์โหลด ZIP ของ tag, ตรวจ manifest, สลับโฟลเดอร์แบบปลอดภัย (ของเก่าอยู่จนของใหม่เสร็จ), เก็บ `user_files`
  - `pkt/plugin.py` — รูปแบบ `pkt_module.json` + API ปลั๊กอิน `pkt_plugin.py` (`PLUGIN_API = 1`) และการโหลด/ล้างโมดูลที่ import แล้ว
  - `pkt/envsetup.py` — ลง PyTorch (CUDA ตาม nvidia-smi / CPU) + ไลบรารีของโมดูล (`pip` ในโปรแกรมที่รันอยู่ = `.venv`)
  - `pkt/ui/app.py` — หน้าต่างหลัก + API ที่โมดูลเรียกใช้: `t`, `tr.add_texts`, `b` (TextBinder), `settings`, `save_settings`, `set_status`, `user_data_dir`, `open_path`, `python_for`, `set_analyze_model/get_analyze_model`, `show`, `notify`, `refreshers`, `status_var`, `root`, `project_root`
  - `pkt/ui/pages/` — `home.py`, `host.py` (หน้าของโมดูลหนึ่งตัว: หน้าจริงถ้าติดตั้ง ไม่งั้นข้อความ+ปุ่มติดตั้ง), `modules.py` (หน้าจัดการ), `settings.py`
  - `pkt/ui/xlate.py` — ตัวแปลข้อความของโมดูลที่เขียนไว้ภาษาเดียวตามปุ่มภาษา (พจนานุกรมอยู่ **ในโมดูล**: `pkt_data_lang.py`, `pkt_analyze_lang.py`)
  - `pkt/updates.py` — อัปเดตตัวแอปหลัก: โฟลเดอร์ git ใช้ `pull --ff-only`; โฟลเดอร์จาก Download ZIP เทียบเลข `__version__` กับ GitHub แล้ว `apply_zip` (ลบไฟล์ที่เวอร์ชันใหม่ไม่มีแล้วด้วย โดยดูจาก `.pkt_files.json`) — **ต้อง bump `pkt/__init__.py` ทุกครั้งที่ปล่อย ไม่งั้นคนใช้ ZIP จะไม่เห็นอัปเดต**
  - `install.bat` + `setup.ps1` (ตัวติดตั้งแอปหลัก เบา ไม่ลง torch; `-Modules` ลงโมดูลทันที; ไฟล์ .ps1 ต้องเป็น ASCII ล้วน), `make_portable.py` (ZIP พกพา, `--with-modules`)
- ใช้เฉพาะไลบรารีมาตรฐานของ Python ในแอปหลัก (ไลบรารีหนักเป็นของโมดูล ลงตอนติดตั้งโมดูล)
- ไฟล์ของผู้ใช้ที่ไม่ขึ้น git: `pkt_settings.json`, `logs/`, `modules/`, `user_data/`

## กฎของแอป

- **ห้ามใส่โค้ดของโมดูลใน repo นี้** — แก้ในโมดูลนั้น ๆ (repo ของมัน) แล้วปล่อยเวอร์ชันใหม่ (tag); การเปลี่ยน API ที่โมดูลเรียกใช้ต้องคงความเข้ากันได้ย้อนหลัง หรือเพิ่ม `PLUGIN_API`/`min_shell`
- ข้อความของแอปหลักอยู่ใน `pkt/i18n.py` ทั้งไทยและอังกฤษ (key ต้องครบทั้งสองภาษา — มีเทสต์ตรวจ); ข้อความของโมดูลอยู่ในโมดูล (`texts()` ใน `pkt_plugin.py` → `app.tr.add_texts`); **ศัพท์เฉพาะไม่แปล** (TTC, PET, LDP, Lateral Clearance, Gap Acceptance, Speed, ชื่อโมเดล YOLO26/RT-DETR/RT-DETRv2, Colab, ชื่อโมดูล) ดู `KEEP_TERMS`
- ธีม: ขาว-ดำ-เทาโทนเข้มเหมือน PKT Data (สีใน `pkt/ui/theme.py`), โลโก้ = ของ PKT Data (`assets/icon.ico`) — ห้ามเปลี่ยนเป็นสีฉูดฉาด; ใช้ `TextBinder` ผูกข้อความให้สลับภาษาสด
- เรียกตัวชี้วัดด้วยชื่อ ห้ามใช้รหัส Y1–Y7
- เปลี่ยนเลย์เอาต์ต้องถ่ายภาพหน้าจอตรวจ (PIL `ImageGrab`; ตั้ง `PKT_SHOT_DIR` ตอนรัน `tests/gui_modules.py` ได้ภาพหน้าหลัก ๆ; Tk บนเครื่องนี้ไม่ DPI-aware ภาพอาจถูกตัด)

## ตรวจก่อน commit ทุกครั้ง (รันจากโฟลเดอร์นี้)

1. `python -m compileall -q pkt main.py`
2. `python -m unittest discover -s tests -v` (modman/plugin/envsetup กับ GitHub ปลอม, i18n, updates กับ repo git ชั่วคราว, zip update, portable, shortcut, xlate)
3. `py -3.12 tests/gui_modules.py` (ติดตั้ง/อัปเดต/ย้อน/ถอนโมดูลในหน้าต่างจริง กับ GitHub ปลอมในเครื่อง ไม่ใช้เน็ต/pip)
4. `py -3.12 tests/gui_app.py`, `py -3.12 tests/gui_updates.py`
5. ชุดที่ใช้โมดูลจริง ตั้ง `PKT_MODULES_SRC=<โฟลเดอร์ที่มี clone PKT-Data / PKT-Train / PKT-Analyze>`: `tests/gui_real_modules.py` (Data/Analyze จริง + ภาษา), `tests/gui_train_module.py` (หน้าเทรน), `python -m unittest tests.test_lang_coverage` (ทุกข้อความของโมดูลมีคำแปล)
- แก้ `setup.ps1` แล้วลอง `powershell -File setup.ps1 -DryRun`; ก่อนแจก `py -3.12 make_portable.py`

## กฎการใช้ git

หลังทำงานเสร็จและตรวจแล้ว commit + push ให้เอง (remote `origin` ของ repo นั้นเท่านั้น) — **แต่ละ repo ใช้ชื่อ repo ของตัวเองนำหน้า**:

```
PK-Transport <x.y.z>: <คำอธิบายสั้น ๆ_แบบ_CamelCase> [(PASS)]      (แอปหลัก, tag v<x.y.z>)
PKT-Data <x.y.z>: ...   PKT-Train <x.y.z>: ...   PKT-Analyze <x.y.z>: ...      (โมดูล; ดู CLAUDE.md ของแต่ละ repo)
```

- เพิ่มบรรทัดใน `CHANGELOG.md` + ติด tag + `git push` พร้อม `git push origin <tag>`; อัปเดต `plan.md`; bump `pkt/__init__.py` (แอปหลัก)
- `(PASS)` เฉพาะเมื่อผู้ใช้ยืนยันแล้วว่าผ่าน; บรรทัดสุดท้ายของ message ใส่ trailer `Co-Authored-By: ...` ตามที่ระบบกำหนด
- **ห้าม** `git push --force`, `git reset --hard`, `git rebase`, `git commit --amend` กับ commit ที่ push แล้ว, ลบ branch/tag/ประวัติ โดยไม่ขออนุญาต; ห้าม push ไป remote อื่น
- ช่องคอมมิตใน CHANGELOG ที่ยังเป็น "(commit นี้)" ให้ใส่ hash จริงใน commit ถัดไป

## ข้อมูลอ้างอิง

- Python 3.12 (`py -3.12`); แอปนี้รันในโปรแกรมของ `.venv` (หลัง `install.bat`) โมดูลใช้ Python ตัวเดียวกัน (ตั้งคำสั่ง Python ต่อโมดูลได้ที่ตั้งค่า)
- หน้า PKT Train อยู่ใน repo PKT-Train (`pkt_train/`): ใส่ค่าลงใน **สำเนา** ของสคริปต์ (`user_data/PKT-Train/_gui_runs/`) แล้วรัน + ตัวแปร `PKT_*`; ผลเทรนเริ่มต้นที่ `user_data/PKT-Train/Runs/<โมเดล>`
- ตัวแปร `PKT_USER_DATA` (แอปตั้งก่อนโหลดโมดูล = `user_data/<ชื่อโมดูล>`) ให้โมดูลเก็บไฟล์ของผู้ใช้นอกโฟลเดอร์โมดูล; `PKT_MODEL_PATH` = โมเดลที่ส่งให้ PKT Analyze; `PKT_FORCE_CPU=1` = ลง PyTorch รุ่น CPU
- โมดูลที่ผู้ใช้ชี้ "โฟลเดอร์ที่เชื่อมไว้" (สำหรับนักพัฒนา) ในตั้งค่า จะถูกใช้แทน `modules/<id>` และไม่ถูกติดตั้งทับ/ลบ
