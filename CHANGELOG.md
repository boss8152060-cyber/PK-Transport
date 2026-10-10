# CHANGELOG — PK Transport

เลขเวอร์ชัน `x.y.z` (tag `vx.y.z`): `y` = ฟีเจอร์ใหม่ (ขั้นงาน), `z` = แก้/ปรับเรื่องเดิม

| เวอร์ชัน | commit | ชื่อ | ทำอะไร |
|---|---|---|---|
| **0.1.0** | `7863152` | PK Transport 0.1.0: Launcher_Home_OpenModules_Status_TwoLanguages | หน้าเปิดหลัก: การ์ด PKT Data / PKT Train / PKT Analyze (สถานะ เวอร์ชัน สาขา), เปิดโมดูลเป็นโปรแกรมแยก, ตั้งค่าโฟลเดอร์/Python, สลับไทย/อังกฤษ (ศัพท์เฉพาะไม่แปล), log ของโมดูล |
| **0.2.0** | (commit นี้) | PK Transport 0.2.0: TrainPage_ModelSizeChoice_LocalRun_ColabCopy | หน้า PKT Train: เลือกโมเดล YOLO26/RT-DETR/RT-DETRv2 และรุ่น, ตั้งค่าเทรน (ค่าตั้งต้นอ่านจากสคริปต์), เทรนในเครื่อง (log สด, epoch, หยุดหลังจบ epoch/หยุดทันที), ปุ่มคัดลอกโค้ด Colab (ทั้งหมด/ทั้งไฟล์/ทีละ Cell); แก้คำสั่ง Python ที่มีเครื่องหมายคำพูดบน Windows |

| **0.3.0** | (commit นี้) | PK Transport 0.3.0: TrainedRunsList_SendModelToAnalyze | หน้า PKT Train มีรายการ run ที่เทรนแล้ว (mAP ของ epoch ที่ดีที่สุด) + ปุ่มใช้กับ PKT Analyze; ตั้ง/ล้างโมเดลได้ที่ตั้งค่า; เปิด PKT Analyze ด้วย `PKT_MODEL_PATH`; การ์ด Analyze แสดงโมเดลที่เลือก |

เวอร์ชันถัดไป: งานต่อเรื่องเดิม = `0.3.1`; เรื่องใหม่ (ตรวจ/อัปเดตเวอร์ชันของโมดูล, ทางลัด) = `0.4.0`
