# CHANGELOG — PK Transport

เลขเวอร์ชัน `x.y.z` (tag `vx.y.z`): `y` = ฟีเจอร์ใหม่ (ขั้นงาน), `z` = แก้/ปรับเรื่องเดิม

| เวอร์ชัน | commit | ชื่อ | ทำอะไร |
|---|---|---|---|
| **0.1.0** | `1605ae4` | PK Transport 0.1.0: Launcher_Home_OpenModules_Status_TwoLanguages | หน้าเปิดหลัก: การ์ด PKT Data / PKT Train / PKT Analyze (สถานะ เวอร์ชัน สาขา), เปิดโมดูลเป็นโปรแกรมแยก, ตั้งค่าโฟลเดอร์/Python, สลับไทย/อังกฤษ (ศัพท์เฉพาะไม่แปล), log ของโมดูล |
| **0.2.0** | `1444289` | PK Transport 0.2.0: TrainPage_ModelSizeChoice_LocalRun_ColabCopy | หน้า PKT Train: เลือกโมเดล YOLO26/RT-DETR/RT-DETRv2 และรุ่น, ตั้งค่าเทรน (ค่าตั้งต้นอ่านจากสคริปต์), เทรนในเครื่อง (log สด, epoch, หยุดหลังจบ epoch/หยุดทันที), ปุ่มคัดลอกโค้ด Colab (ทั้งหมด/ทั้งไฟล์/ทีละ Cell); แก้คำสั่ง Python ที่มีเครื่องหมายคำพูดบน Windows |

| **0.3.0** | `0d7c8f1` | PK Transport 0.3.0: TrainedRunsList_SendModelToAnalyze | หน้า PKT Train มีรายการ run ที่เทรนแล้ว (mAP ของ epoch ที่ดีที่สุด) + ปุ่มใช้กับ PKT Analyze; ตั้ง/ล้างโมเดลได้ที่ตั้งค่า; เปิด PKT Analyze ด้วย `PKT_MODEL_PATH`; การ์ด Analyze แสดงโมเดลที่เลือก |

| **0.4.0** | `64aa118` | PK-Transport 0.4.0: ModuleUpdateCheck_DesktopShortcut_CommitNaming | ตรวจ/อัปเดตเวอร์ชันของโมดูลและของแอปจาก GitHub (fetch + pull --ff-only พร้อมยืนยัน), ตรวจตอนเปิดแอป (ปิดได้), ทางลัดเดสก์ท็อป; รูปแบบชื่อ commit ใหม่ `<ชื่อ repo> <x.y.z>: <คำอธิบาย>` ทุก repo |

| **0.5.0** | `1bcb61b` | PK-Transport 0.5.0: SingleWindowApp_MonochromeTheme_LiveLanguageSwitch | แอปหน้าต่างเดียว (`pkt/ui/`): แถบเมนูซ้าย + หน้า Home / PKT Data / PKT Train / PKT Analyze / ตั้งค่า, ธีมขาว-ดำ-เทาและโลโก้/ไอคอนของ PKT Data, สลับไทย/อังกฤษทันทีทุกหน้า, PKT Train เป็นหน้าในแอป, ปิดหน้าต่างระหว่างเทรนจะถามก่อนหยุด; แทน `launcher.py`/`train_page.py`; เพิ่ม `shared.find_analysis_outputs` |
| **0.5.1** | `6e04ffa` | PK-Transport 0.5.1: TrainAdvancedSettings_AllColabFormFields | หน้า PKT Train มีการ์ด ตั้งค่าขั้นสูง: ทุกช่อง `# @param` ของสคริปต์ที่เลือก (cache, device, optimizer, lr0, close_mosaic, amp, aug_* ฯลฯ) เป็นช่องกรอก/ลิสต์/ติ๊ก เหมือนฟอร์ม Colab; ค่าลงในสำเนาที่รันและโค้ด Colab ที่คัดลอก (`train_core.parse_params/patch_params`) |
| **0.6.0** | (commit นี้) | PK-Transport 0.6.0: PKTDataEmbeddedAsTabs | PKT Data ฝังเป็นหน้าในแอป (`pkt/ui/pages/data.py`): 6 แท็บย่อย Data / Label / Curate / Analytics / Zone / Other โหลดตอนเปิดหน้าครั้งแรกจากโค้ดใน repo PKT-Data (ไม่คัดลอกโค้ด); ปุ่ม Open ที่การ์ด PKT Data เปิดแท็บแทนหน้าต่างแยก; หน้าที่ซ่อนอยู่ถูก unmap จริง (ปุ่มลัดของ PKT Data ไม่ทำงานข้ามหน้า); UI ภายในของ PKT Data ยังเป็นอังกฤษ |

เวอร์ชันถัดไป: งานต่อเรื่องเดิม = `0.6.1`; เรื่องใหม่ = `0.6.0` (ฝัง PKT Data เป็นแท็บ)
