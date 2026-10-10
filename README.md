# PKT-Train

สคริปต์เทรนโมเดลตรวจจับวัตถุ (รถ/คน) ของ **PK Transport (PKT)** — ส่วน **PKT Train**
สายงาน: PKT Data (เตรียมชุดข้อมูล) → **PKT Train (เทรนโมเดล)** → PKT Analyze (วิเคราะห์ความปลอดภัย)

## ไฟล์

| ไฟล์ | โมเดล | รุ่นที่เลือกได้ (`MODEL_SIZE` ใน Cell 2) |
|---|---|---|
| `Train YOLO26L Augmentation.py` | YOLO26 (Ultralytics) | n / s / m / l / x |
| `Train RTDETR-L Augmentation.py` | RT-DETR (Ultralytics) | l / x |
| `Train RT-DETRv2 PyTorch Augmentation.py` | RT-DETRv2 (repo ทางการ lyuwenyu/RT-DETR) | s / m* / m / l / x |

ทุกไฟล์รันได้ 2 ที่ ตรวจเองอัตโนมัติ (`RUN_ENV = "auto"` ใน Cell 1):

- **Google Colab:** คัดลอกทีละ Cell (`# %%`) ไปวางตามลำดับ Cell 1 → Cell 9 (ทำงานเหมือนเดิม: Drive + zip ชุดข้อมูล)
- **ในเครื่อง (Windows/Linux):** รันทั้งไฟล์ เช่น `python "Train YOLO26L Augmentation.py"`

## รันในเครื่อง

- ต้องมี Python + torch (CUDA) + `ultralytics` (ไฟล์ RT-DETRv2 ต้องมี `git` ด้วย เพื่อโคลน repo ทางการครั้งแรก)
- สคริปต์ติดตั้ง `albumentations` (และของ RT-DETRv2) ให้เองถ้าขาด โดยไม่อัปเกรด ultralytics/torch ของคุณ
- ชุดข้อมูล: ใช้โฟลเดอร์ปกติ (มี `data.yaml` + `train/valid/test`) โดยตรง ไม่ต้องแตก zip — ไม่มีโฟลเดอร์จะใช้ zip แทน
- ผลเทรนอยู่ที่ `Runs/<ชื่อโมเดล>/models_<รุ่น>/runN/` ข้างไฟล์สคริปต์ (พื้นที่ทำงานที่ `_workspace/`) — ทั้งสองโฟลเดอร์ไม่ถูกเก็บใน git
- ระบบเดิมครบ: augmentation แบบ Roboflow, resume อัตโนมัติ (`IN_PROGRESS.flag`), `STOP.flag`, backup ทุก epoch, `BEST_EPOCH_<epoch>.txt`
- ในเครื่อง `cache="disk"` ถูกปิด (เพื่อไม่เขียนไฟล์ลงโฟลเดอร์ชุดข้อมูล) และ `workers` จำกัดตามจำนวน CPU

### ปรับ path / รุ่น ด้วยตัวแปรแวดล้อม

| ตัวแปร | ความหมาย |
|---|---|
| `PKT_MODEL_SIZE` | รุ่นโมเดล (เช่น `m`, `x`) แทนค่า `MODEL_SIZE` |
| `PKT_DATASET_DIR` | โฟลเดอร์ชุดข้อมูล (มี data.yaml) |
| `PKT_DATASET_ZIP` | zip ชุดข้อมูล (ใช้เมื่อไม่มีโฟลเดอร์) |
| `PKT_STORE_DIR` | ที่เก็บ run ถาวร (ตั้งเป็นโฟลเดอร์ Google Drive for Desktop ถ้าอยากซิงก์กับ Colab) |
| `PKT_WORKSPACE_DIR` | พื้นที่ทำงานชั่วคราว |

ค่าตั้งต้นของ path ชุดข้อมูลในเครื่องอยู่ใน Cell 2 ของแต่ละไฟล์ (ปรับให้ตรงกับเครื่องของคุณ)

## สถานะการทดสอบ

- YOLO26 และ RT-DETR (Ultralytics): ทดสอบในเครื่อง (Windows, GTX 1650) กับชุดข้อมูลจิ๋ว — เทรนได้ทั้ง CPU/GPU (หลาย worker), resume ได้, backup/BEST_EPOCH/ทำนายครบ
- RT-DETRv2: แก้ให้รันบน Windows แล้ว (git/urllib/ปิด process แบบ Windows) แต่ **ยังไม่ได้ทดสอบรันจริง**
- ฝั่ง Colab: ตรรกะเดิมไม่เปลี่ยน (ยังไม่ได้รันซ้ำบน Colab หลังแก้)
- รุ่นใหญ่บน GPU 4 GB (เช่น YOLO26l/x, RT-DETR l/x) ไม่ได้ลอง

## เลขเวอร์ชัน

`PKT-Train x.y.z` (tag `vx.y.z`) — 0.1.0 = สคริปต์ Colab เดิม, 0.2.0 = เพิ่มโหมดรันในเครื่อง + เลือกรุ่นโมเดล
