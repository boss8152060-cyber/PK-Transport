# CHANGELOG — PK Transport

เลขเวอร์ชัน `x.y.z` (tag `vx.y.z`): `y` = ฟีเจอร์ใหม่ (ขั้นงาน), `z` = แก้/ปรับเรื่องเดิม

| เวอร์ชัน | commit | ชื่อ | ทำอะไร |
|---|---|---|---|
| **0.1.0** | `7863152` | PK Transport 0.1.0: Launcher_Home_OpenModules_Status_TwoLanguages | หน้าเปิดหลัก: การ์ด PKT Data / PKT Train / PKT Analyze (สถานะ เวอร์ชัน สาขา), เปิดโมดูลเป็นโปรแกรมแยก, ตั้งค่าโฟลเดอร์/Python, สลับไทย/อังกฤษ (ศัพท์เฉพาะไม่แปล), log ของโมดูล |
| **0.2.0** | (commit นี้) | PK Transport 0.2.0: TrainPage_ModelSizeChoice_LocalRun_ColabCopy | หน้า PKT Train: เลือกโมเดล YOLO26/RT-DETR/RT-DETRv2 และรุ่น, ตั้งค่าเทรน (ค่าตั้งต้นอ่านจากสคริปต์), เทรนในเครื่อง (log สด, epoch, หยุดหลังจบ epoch/หยุดทันที), ปุ่มคัดลอกโค้ด Colab (ทั้งหมด/ทั้งไฟล์/ทีละ Cell); แก้คำสั่ง Python ที่มีเครื่องหมายคำพูดบน Windows |

เวอร์ชันถัดไป: งานต่อเรื่องเดิม = `0.2.1`; เรื่องใหม่ (ส่ง best.pt ไป PKT Analyze / ตั้งค่าร่วม) = `0.3.0`
