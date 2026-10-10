"""
=============================================================================
RUN 9.5 เพิ่ม ROBOFLOW-STYLE DYNAMIC AUGMENTATION:
    - Flip: Horizontal + Vertical
    - 90° Rotate: CW / CCW / 180° ผ่าน RandomRotate90
    - Rotation ±15°, Shear ±10°
    - Crop 0-20%, Cutout สูงสุด 3 holes ขนาดสูงสุด 10%
    - Saturation ±25%, Hue ±15°, Brightness ±15%, Exposure ±10%
    - Grayscale 15%, Blur ≤2.5px, Noise ≤0.1%, Motion Blur, Camera Gain
    - Mosaic=1.0 และ close_mosaic=10

    หมายเหตุ: Bounding Box Level Augmentations ของ Roboflow ที่แก้เฉพาะ
    ภายในกล่องวัตถุ ไม่ได้ทำ 1:1 ใน Run 9.3 นี้; Run นี้ใช้ Image-Level
    transforms ที่ปรับ bounding boxes ตาม spatial transforms ที่รองรับแทน

=============================================================================
สคริปต์นี้รันได้ 2 ที่ (ต้องการ GPU): GOOGLE COLAB (คัดลอกทีละ cell เหมือนเดิม) และ
ในเครื่อง Windows/Linux (รันทั้งไฟล์: python "<ชื่อไฟล์นี้>")  — ตรวจเองอัตโนมัติ (RUN_ENV)
    ในเครื่อง: ใช้ชุดข้อมูลแบบโฟลเดอร์โดยตรง (หรือแตก zip), เก็บ run ไว้ในโฟลเดอร์ Runs ข้างไฟล์นี้
    เลือกรุ่นโมเดลที่ MODEL_SIZE ใน Cell 2: n / s / m / l / x  (yolo26n.pt ... yolo26x.pt)

วิธีใช้:
    1. เปิด https://colab.research.google.com -> New Notebook
    2. Runtime > Change runtime type > เลือก T4 GPU
    3. คัดลอกโค้ดแต่ละ "cell" (คั่นด้วย # %%) ไปแปะทีละ cell ใน Colab
       แล้วรันตามลำดับ Cell 1 -> Cell 9
    4. ทุกครั้งที่จะเทรนรอบใหม่ ให้รันตั้งแต่ Cell 1 ใหม่ทั้งหมด

โมเดล: ใช้ YOLO26 (yolo26m.pt, Ultralytics) — ไฟล์นี้แยกไว้เฉพาะ YOLO26
        เท่านั้น ถ้าต้องการเทรน RT-DETR ให้ใช้ train_rtdetr.py แทน
        กำหนดน้ำหนักตั้งต้นผ่านตัวแปร `PRETRAINED_WEIGHTS` ใน Cell 2
        โฟลเดอร์ models บน Drive จะตั้งชื่อตามโมเดลนี้อัตโนมัติ
        (เช่น models_yolo26l)

ระบบ:
    - Training บน Local VM
    - Google Drive ใช้เก็บ checkpoint/ผลลัพธ์
    - Resume อัตโนมัติ
    - STOP.flag
    - Backup ทุก epoch (log สรุปแค่บรรทัด [backup] เท่านั้น)
    - BEST_EPOCH_<epoch>.txt: ไฟล์เปล่า ชื่อไฟล์บอกเลข epoch ที่ดีที่สุด
      (เช่น BEST_EPOCH_51.txt) ตัดสินจาก Fitness สูงสุดของ Ultralytics
=============================================================================
"""

# %% [Cell 1] ติดตั้ง/อัปเดตไลบรารี + ตรวจว่ารันที่ไหน
import os
import sys
import subprocess

RUN_ENV = "auto"  # @param ["auto", "colab", "local"]
try:
    import google.colab  # noqa: F401
    _colab_available = True
except ImportError:
    _colab_available = False
IN_COLAB = (RUN_ENV == "colab") or (RUN_ENV == "auto" and _colab_available)

# ในเครื่อง Windows ตัวโหลดข้อมูลแบบหลายโปรเซส (spawn) นำไฟล์นี้กลับไปอ่านใหม่ในแต่ละ worker
# ส่วนที่มีผลข้างเคียง (แตก zip, เริ่มเทรน, ...) ต้องรันเฉพาะโปรเซสหลัก -> IS_MAIN
IS_MAIN = (__name__ == "__main__")
if not IS_MAIN:
    import builtins
    builtins.print = lambda *args, **kwargs: None      # ตัวโหลดข้อมูล (worker) นำไฟล์นี้ไปอ่านใหม่ — ไม่ต้องพิมพ์ซ้ำ
HAS_ALARM = hasattr(__import__("signal"), "SIGALRM")   # Windows ไม่มี SIGALRM (ใช้ timeout ต่อรูปใน Cell 9 ไม่ได้)

if not IN_COLAB:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")   # คอนโซล Windows พิมพ์ภาษาไทยได้
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

if IS_MAIN:
    if IN_COLAB:
        subprocess.run([sys.executable, "-m", "pip", "install", "-U", "ultralytics", "albumentations", "-q"], check=False)
    else:
        # ในเครื่อง: ไม่อัปเกรด ultralytics/torch ของคุณเอง ติดตั้งเฉพาะที่ขาด
        try:
            import albumentations  # noqa: F401
        except ImportError:
            print("ไม่พบ albumentations -> ติดตั้ง ...")
            subprocess.run([sys.executable, "-m", "pip", "install", "albumentations", "-q"], check=False)


# %% [Cell 2] เชื่อมต่อ Google Drive (Colab) หรือโฟลเดอร์ในเครื่อง + ตั้ง path
import os
from pathlib import Path

# --- เลือกรุ่นโมเดล: n / s / m / l / x  (yolo26n.pt ... yolo26x.pt) ---
MODEL_SIZE = "l"  # @param ["n", "s", "m", "l", "x"]
MODEL_SIZE = os.environ.get("PKT_MODEL_SIZE", MODEL_SIZE)
PRETRAINED_WEIGHTS = f'yolo26{MODEL_SIZE}.pt'
MODEL_NAME_TAG = os.path.splitext(PRETRAINED_WEIGHTS)[0]  # โฟลเดอร์ models ตั้งชื่อตามรุ่นอัตโนมัติ

if IN_COLAB:
    from google.colab import drive
    drive.mount('/content/drive')

    # --- Google Drive: ใช้เก็บ zip ต้นทาง + ผลลัพธ์สุดท้าย ---
    DRIVE_PROJECT_DIR = '/content/drive/MyDrive/PK Studio/PK Object Detection: Vehicles/YOLO26'
    DRIVE_ZIP_PATH = '/content/drive/MyDrive/PSU Transport Project 2026.zip'
    LOCAL_DATASET_SOURCE = ''     # Colab: ใช้ zip เสมอ
    # --- ดิสก์เครื่อง Colab: ใช้ทำงานจริงทั้งหมด ---
    LOCAL_DIR = '/content/local_workspace'
else:
    # ============ รันในเครื่อง (ปรับ path ตรงนี้ หรือกำหนดตัวแปรแวดล้อม PKT_*) ============
    _here = Path(os.path.abspath(__file__)).parent if '__file__' in globals() else Path.cwd()
    # ชุดข้อมูลแบบโฟลเดอร์ปกติ (มี data.yaml + train/valid/test) ใช้ตรง ๆ ไม่ต้องคัดลอก/แตก zip
    # ถ้าโฟลเดอร์นี้ไม่มี จะไปใช้ zip ด้านล่างแทน (แตกไว้ใน _workspace)
    LOCAL_DATASET_SOURCE = os.environ.get(
        "PKT_DATASET_DIR", r"F:\motorcycle group project\PSU Transport Project 2026\Dataset\PSU Transport Project 2026")
    DRIVE_ZIP_PATH = os.environ.get(
        "PKT_DATASET_ZIP", r"F:\motorcycle group project\PSU Transport Project 2026\Dataset\PSU Transport Project 2026.zip")
    # ที่เก็บ run ถาวร (บทบาทเดียวกับ Google Drive ตอนอยู่บน Colab) — ถ้าอยากให้ซิงก์กับ Colab ใช้โฟลเดอร์ Google Drive for Desktop เช่น
    #   r"G:\My Drive\PK Studio\PK Object Detection  Vehicles\YOLO26"
    DRIVE_PROJECT_DIR = os.environ.get("PKT_STORE_DIR", str(_here / "Runs" / "YOLO26"))
    LOCAL_DIR = os.environ.get("PKT_WORKSPACE_DIR", str(_here / "_workspace" / "YOLO26"))

DRIVE_MODELS_DIR = f'{DRIVE_PROJECT_DIR}/models_{MODEL_NAME_TAG}'

# ย้ายโฟลเดอร์ models เดิม (ก่อนมีชื่อต่อท้ายตามโมเดล) มาไว้ที่ path ใหม่
# เพื่อให้ run เก่า (เช่น run9) ยังถูก resume/continue_from_run เจอเหมือนเดิม
_old_models_dir = f'{DRIVE_PROJECT_DIR}/models'
if os.path.isdir(_old_models_dir) and not os.path.isdir(DRIVE_MODELS_DIR):
    print(f"พบโฟลเดอร์ models เดิม -> ย้ายไปเป็น {DRIVE_MODELS_DIR} เพื่อให้ run เก่ายังใช้ต่อได้")
    os.rename(_old_models_dir, DRIVE_MODELS_DIR)

os.makedirs(DRIVE_MODELS_DIR, exist_ok=True)

LOCAL_DATASET_DIR = f'{LOCAL_DIR}/dataset'
LOCAL_MODELS_DIR = f'{LOCAL_DIR}/models'
os.makedirs(LOCAL_DATASET_DIR, exist_ok=True)
os.makedirs(LOCAL_MODELS_DIR, exist_ok=True)

print(f"รันที่: {'Google Colab' if IN_COLAB else 'ในเครื่อง'}  |  รุ่นโมเดล: {PRETRAINED_WEIGHTS}")
print(f"ไฟล์ถาวร ({'Drive' if IN_COLAB else 'โฟลเดอร์ Runs'}): {DRIVE_PROJECT_DIR}")
print(f"โฟลเดอร์ models ({MODEL_NAME_TAG}): {DRIVE_MODELS_DIR}")
print(f"พื้นที่ทำงาน: {LOCAL_DIR}")


# %% [Cell 3] ตรวจสอบ GPU
if IS_MAIN:
    try:
        subprocess.run(["nvidia-smi"], check=False)
    except FileNotFoundError:
        print("(ไม่พบคำสั่ง nvidia-smi)")

import torch

if torch.cuda.is_available():
    print(f"\nพร้อมเทรน: พบ GPU {torch.cuda.get_device_name(0)}")
else:
    print("\n!! ไม่พบ GPU !!")
    print("ไปที่ Runtime > Change runtime type > เลือก T4 GPU")
    print("แล้วกด Restart runtime ก่อนรันเซลล์ถัดไป")


# %% [Cell 4] คัดลอก zip จาก Drive มา local ครั้งเดียว แล้วแตกไฟล์
import json
import shutil
import zipfile
from pathlib import Path

if IS_MAIN:
    drive_zip_path = DRIVE_ZIP_PATH
    local_zip_path = f'{LOCAL_DIR}/dataset.zip'
    fingerprint_path = f'{LOCAL_DATASET_DIR}/.zip_fingerprint.json'

    if not IN_COLAB and LOCAL_DATASET_SOURCE and os.path.isdir(LOCAL_DATASET_SOURCE):
        LOCAL_DATASET_DIR = LOCAL_DATASET_SOURCE      # ชุดข้อมูลแบบโฟลเดอร์ ใช้ตรง ๆ ไม่ต้องคัดลอก/แตก zip
        print(f"ใช้ชุดข้อมูลแบบโฟลเดอร์ในเครื่องโดยตรง: {LOCAL_DATASET_DIR}")
    elif not os.path.exists(drive_zip_path):
        print(f"ยังไม่พบไฟล์ที่: {drive_zip_path}")
        print("ตรวจสอบ path/ชื่อไฟล์จริงด้วย !ls -la")
    else:
        zip_stat = os.stat(drive_zip_path)
        current_fingerprint = {'size': zip_stat.st_size, 'mtime': zip_stat.st_mtime}
        saved_fingerprint = None

        if os.path.exists(fingerprint_path):
            with open(fingerprint_path, encoding='utf-8') as f:
                saved_fingerprint = json.load(f)

        if saved_fingerprint == current_fingerprint:
            print("ไฟล์ zip เหมือนเดิมทุกประการ -> ใช้ dataset ที่แตกไว้แล้วบนเครื่อง")
        else:
            print("คัดลอกไฟล์ zip จาก Drive มาดิสก์เครื่อง...")
            shutil.copy2(drive_zip_path, local_zip_path)

            if os.path.exists(LOCAL_DATASET_DIR):
                shutil.rmtree(LOCAL_DATASET_DIR)
            os.makedirs(LOCAL_DATASET_DIR, exist_ok=True)

            with zipfile.ZipFile(local_zip_path, 'r') as z:
                z.extractall(LOCAL_DATASET_DIR)

            with open(fingerprint_path, 'w', encoding='utf-8') as f:
                json.dump(current_fingerprint, f)

            print("แตกไฟล์ dataset บนดิสก์เครื่องเรียบร้อย")


# %% [Cell 5] ตรวจสอบโครงสร้างโฟลเดอร์ + หา data.yaml
if IS_MAIN:
    print("โครงสร้างโฟลเดอร์ที่พบ:")
    for _root, _dirs, _files in os.walk(LOCAL_DATASET_DIR):
        _depth = os.path.relpath(_root, LOCAL_DATASET_DIR).count(os.sep) + (0 if _root == LOCAL_DATASET_DIR else 1)
        if _depth >= 2:
            _dirs[:] = []
        print(f"  {_root}  ({len(_files)} ไฟล์)")

    yaml_candidates = list(Path(LOCAL_DATASET_DIR).rglob('data.yaml'))
    if not yaml_candidates:
        raise FileNotFoundError(f"ไม่พบ data.yaml ใน {LOCAL_DATASET_DIR}")

    DATA_YAML = str(yaml_candidates[0])
    print(f"\n--- ใช้ data.yaml จาก: {DATA_YAML} ---")
    print(open(DATA_YAML, encoding='utf-8').read())


# %% [Cell 6] เทรนโมเดล YOLO26
from ultralytics import YOLO
import albumentations as A

DRIVE_MODELS_PATH = Path(DRIVE_MODELS_DIR)
STOP_FLAG_PATH = Path(DRIVE_PROJECT_DIR) / 'STOP.flag'

# น้ำหนักตั้งต้นเมื่อเริ่ม run ใหม่ (ใช้ทั้งโหมด "new" และ "auto")
# กำหนดไว้แล้วที่ Cell 2 ในตัวแปร PRETRAINED_WEIGHTS (มีผลกับชื่อโฟลเดอร์ Drive ด้วย)


# ============================================================================
# TRAINING MODE
# ============================================================================
training_mode = "auto"  # @param ["auto", "new", "continue_from_run"]

# auto:
#     ถ้ามี run ที่ค้างอยู่ -> resume
#     ถ้าไม่มี -> สร้าง run ใหม่
#
# new:
#     เริ่ม run ใหม่จาก PRETRAINED_WEIGHTS (yolo26m.pt)
#
# continue_from_run:
#     ใช้ best.pt จาก run เก่ามาเป็นจุดตั้งต้น

source_run_name = "run9"  # @param {type:"string"}


# ============================================================================
# TRAINING CONFIGURATION
# ============================================================================
epochs = 300      # @param {type:"integer"}
imgsz = 640        # @param {type:"integer"}
batch = 48         # @param {type:"integer"}
workers = 24       # @param {type:"integer"}
cache = "disk"     # @param ["disk", "False"]
device = 0         # @param {type:"integer"}
cache = False if cache == "False" else cache
if not IN_COLAB:
    workers = min(workers, os.cpu_count() or 1)         # ในเครื่องมีแกน CPU น้อยกว่า Colab/เครื่องใหญ่
    if cache == "disk":
        cache = False                                   # "disk" เขียนไฟล์ .npy ลงโฟลเดอร์ชุดข้อมูลของคุณเอง -> ไม่ใช้ในเครื่อง
    if not torch.cuda.is_available():
        device = "cpu"
patience = 15      # @param {type:"integer"}
close_mosaic = 10  # @param {type:"integer"}


# ============================================================================
# ROBOFLOW-STYLE AUGMENTATION
# ============================================================================
use_roboflow_style_aug = True  # @param {type:"boolean"}

# ---- Geometry ----
aug_horizontal_flip = True     # @param {type:"boolean"}
aug_vertical_flip = True       # @param {type:"boolean"}
aug_rotate_90 = True           # @param {type:"boolean"}
aug_rotation_degrees = 15      # @param {type:"number"}
aug_shear_degrees = 10         # @param {type:"number"}
aug_crop_max_percent = 20      # @param {type:"integer"}
aug_cutout_holes = 3           # @param {type:"integer"}
aug_cutout_percent = 10        # @param {type:"integer"}

# ---- Color / Lighting ----
aug_saturation_percent = 25    # @param {type:"integer"}
aug_hue_degrees = 15           # @param {type:"integer"}
aug_brightness_percent = 15    # @param {type:"integer"}
aug_exposure_percent = 10      # @param {type:"integer"}
aug_grayscale_percent = 15     # @param {type:"integer"}
aug_camera_gain_sigma = 0.05   # @param {type:"number"}

# ---- Image Quality ----
aug_blur_max_px = 2.5          # @param {type:"number"}
aug_noise_percent = 0.1        # @param {type:"number"}
aug_motion_blur_max_px = 100   # @param {type:"integer"}

# ---- Dynamic probabilities ----
aug_p_rotate_90 = 0.50     # @param {type:"number"}
aug_p_crop = 0.30          # @param {type:"number"}
aug_p_cutout = 0.30        # @param {type:"number"}
aug_p_color = 0.30         # @param {type:"number"}
aug_p_grayscale = 0.15     # @param {type:"number"}
aug_p_blur = 0.20          # @param {type:"number"}
aug_p_noise = 0.15         # @param {type:"number"}
aug_p_motion_blur = 0.20   # @param {type:"number"}
aug_p_camera_gain = 0.20   # @param {type:"number"}


# ============================================================================
# BUILD CUSTOM AUGMENTATIONS
# ============================================================================
def build_roboflow_style_augmentations():
    if not use_roboflow_style_aug:
        return None

    transforms = []

    if aug_rotate_90:
        transforms.append(A.RandomRotate90(p=aug_p_rotate_90))

    if aug_crop_max_percent > 0:
        crop_scale_min = max(0.08, 1.0 - (aug_crop_max_percent / 100.0))
        transforms.append(A.RandomResizedCrop(
            size=(imgsz, imgsz), scale=(crop_scale_min, 1.0), ratio=(0.90, 1.10), p=aug_p_crop,
        ))

    if aug_cutout_holes > 0 and aug_cutout_percent > 0:
        hole_fraction = min(1.0, aug_cutout_percent / 100.0)
        transforms.append(A.CoarseDropout(
            num_holes_range=(1, aug_cutout_holes),
            hole_height_range=(0.03, hole_fraction),
            hole_width_range=(0.03, hole_fraction),
            fill=0, p=aug_p_cutout,
        ))

    if aug_saturation_percent > 0 or aug_hue_degrees > 0:
        sat_shift = int(round(255 * aug_saturation_percent / 100.0))
        transforms.append(A.HueSaturationValue(
            hue_shift_limit=aug_hue_degrees, sat_shift_limit=sat_shift, val_shift_limit=0, p=aug_p_color,
        ))

    if aug_brightness_percent > 0:
        transforms.append(A.RandomBrightnessContrast(
            brightness_limit=(aug_brightness_percent / 100.0), contrast_limit=0.0, p=aug_p_color,
        ))

    if aug_exposure_percent > 0:
        # ชื่ออาร์กิวเมนต์ต่างกันตามเวอร์ชัน albumentations (ใหม่: gamma_range, เก่า: gamma_limit)
        import inspect
        _gamma_key = "gamma_range" if "gamma_range" in inspect.signature(A.RandomGamma.__init__).parameters else "gamma_limit"
        transforms.append(A.RandomGamma(
            **{_gamma_key: (100 - aug_exposure_percent, 100 + aug_exposure_percent)}, p=aug_p_color,
        ))

    if aug_grayscale_percent > 0:
        transforms.append(A.ToGray(p=aug_p_grayscale))

    if aug_blur_max_px > 0:
        transforms.append(A.GaussianBlur(
            blur_limit=(3, 5), sigma_limit=(0.1, aug_blur_max_px), p=aug_p_blur,
        ))

    if aug_noise_percent > 0:
        noise_std = aug_noise_percent / 100.0
        transforms.append(A.GaussNoise(
            std_range=(0.0, noise_std), mean_range=(0.0, 0.0), p=aug_p_noise,
        ))

    if aug_motion_blur_max_px > 0:
        motion_kernel = int(min(99, aug_motion_blur_max_px))
        if motion_kernel % 2 == 0:
            motion_kernel -= 1
        motion_kernel = max(3, motion_kernel)
        transforms.append(A.MotionBlur(blur_limit=(3, motion_kernel), p=aug_p_motion_blur))

    if aug_camera_gain_sigma > 0:
        transforms.append(A.MultiplicativeNoise(
            multiplier=(max(0.0, 1.0 - aug_camera_gain_sigma), 1.0 + aug_camera_gain_sigma),
            per_channel=False, elementwise=False, p=aug_p_camera_gain,
        ))

    return transforms


ROBOFLOW_STYLE_TRANSFORMS = build_roboflow_style_augmentations()

if use_roboflow_style_aug:
    TRAIN_AUGMENTATION_ARGS = dict(
        degrees=float(aug_rotation_degrees),
        shear=float(aug_shear_degrees),
        translate=0.0,
        scale=0.0,
        perspective=0.0,
        fliplr=0.5 if aug_horizontal_flip else 0.0,
        flipud=0.5 if aug_vertical_flip else 0.0,
        hsv_h=0.0, hsv_s=0.0, hsv_v=0.0,
        mosaic=1.0,
        mixup=0.0,
        cutmix=0.0,
        augmentations=ROBOFLOW_STYLE_TRANSFORMS,
    )
else:
    TRAIN_AUGMENTATION_ARGS = dict()

print("\n========== AUGMENTATION CONFIG ==========")
print(f"Roboflow-style augmentation: {use_roboflow_style_aug}")

if use_roboflow_style_aug:
    print(f"Custom Albumentations transforms: {len(ROBOFLOW_STYLE_TRANSFORMS)}")
    for t in ROBOFLOW_STYLE_TRANSFORMS:
        print(f"  - {t}")
    print(
        "Ultralytics Geometry Args: "
        f"degrees=±{aug_rotation_degrees}, shear=±{aug_shear_degrees}, "
        f"fliplr={TRAIN_AUGMENTATION_ARGS['fliplr']}, flipud={TRAIN_AUGMENTATION_ARGS['flipud']}, "
        "mosaic=1.0"
    )
else:
    print("ใช้ Ultralytics default augmentation")

print("========================================\n")


# ============================================================================
# CHECK RESUMABLE CHECKPOINT
# ============================================================================
def is_resumable_checkpoint(pt_path) -> bool:
    try:
        ckpt = torch.load(str(pt_path), map_location='cpu', weights_only=False)
        return ckpt.get('optimizer') is not None and ckpt.get('epoch', -1) >= 0
    except Exception as e:
        print(f"  [WARNING] เช็ค checkpoint ไม่สำเร็จ ({e}) ถือว่า resume ไม่ได้ไว้ก่อน")
        return False


# ============================================================================
# FIND RESUMABLE RUN
# ============================================================================
def find_resumable_run():
    candidates = []

    for run_dir in DRIVE_MODELS_PATH.glob('run*'):
        if not run_dir.is_dir() or not run_dir.name[3:].isdigit():
            continue

        in_progress_flag = run_dir / 'IN_PROGRESS.flag'
        last_pt = run_dir / 'weights' / 'last.pt'

        if in_progress_flag.exists() and last_pt.exists():
            candidates.append(run_dir)

    if not candidates:
        return None

    return sorted(candidates, key=lambda p: int(p.name[3:]))[-1]


# ============================================================================
# SAVE PER-CLASS METRICS
# ============================================================================
def save_per_class_metrics(validator):
    try:
        import csv as _csv

        metrics = validator.metrics
        rows = [[
            "all", validator.seen, int(metrics.nt_per_class.sum()),
            *[round(float(x), 5) for x in metrics.mean_results()],
        ]]

        for i, c in enumerate(metrics.ap_class_index):
            p, r, ap50, ap = metrics.class_result(i)
            rows.append([
                validator.names[c],
                int(metrics.nt_per_image[c]),
                int(metrics.nt_per_class[c]),
                round(float(p), 5), round(float(r), 5), round(float(ap50), 5), round(float(ap), 5),
            ])

        csv_path = Path(validator.save_dir) / "per_class_metrics.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = _csv.writer(f)
            writer.writerow(["Class", "Images", "Instances", "P", "R", "mAP50", "mAP50-95"])
            writer.writerows(rows)

    except Exception as e:
        print(f"  [WARNING] เขียน per_class_metrics.csv ไม่สำเร็จ (ไม่กระทบการเทรน): {e}")


# ============================================================================
# BEST_EPOCH_<epoch>.txt
#
# สำคัญ:
# - ไฟล์นี้เป็น "ไฟล์เปล่า" (ไม่มีเนื้อหาข้างใน) ใช้แค่ชื่อไฟล์บอก epoch ที่ดีที่สุด
#   เช่น BEST_EPOCH_51.txt, BEST_EPOCH_100.txt
# - ไม่แก้ results.csv
# - ใช้ trainer.fitness ซึ่งเป็นค่า Fitness ที่ Ultralytics คำนวณให้
# - ถ้า Fitness ปัจจุบันสูงกว่า Best เดิม -> ลบไฟล์ BEST_EPOCH_*.txt อันเก่าทิ้ง
#   แล้วสร้างไฟล์เปล่าอันใหม่ตามเลข epoch ปัจจุบัน
# - เก็บ Fitness ล่าสุดไว้ในไฟล์ state ภายใน (.best_epoch_state.json) เพื่อใช้
#   เทียบรอบถัดไปเท่านั้น ไม่ใช่ไฟล์ที่ต้องดูผลลัพธ์
# - ทำงานเงียบ ๆ (ไม่ print) เพื่อให้ log เห็นแค่บรรทัด [backup]
# ============================================================================
def update_best_epoch_file(trainer, drive_weights_dir):
    try:
        import csv
        import json
        import math

        results_path = Path(trainer.save_dir) / "results.csv"
        if not results_path.exists():
            return  # ยังไม่มี results.csv ให้อ่าน -> ข้ามเงียบ ๆ

        # trainer.fitness คือ Fitness ที่ Ultralytics ใช้ตัดสิน best model
        # (ไม่คำนวณสูตรขึ้นมาเอง)
        current_fitness = getattr(trainer, "fitness", None)
        if current_fitness is None:
            return

        try:
            current_fitness = float(current_fitness)
        except Exception:
            return

        if not math.isfinite(current_fitness):
            return

        # อ่าน results.csv แบบ raw text เพื่อหาเลข epoch ของ row ล่าสุด
        with open(results_path, "r", encoding="utf-8") as f:
            raw_lines = f.readlines()

        non_empty_lines = [line for line in raw_lines if line.strip()]
        if len(non_empty_lines) < 2:
            return  # ยังไม่มี data row

        current_data_line = non_empty_lines[-1].rstrip("\r\n")

        # หา epoch จาก row ล่าสุด (fallback เป็น trainer.epoch ถ้า parse ไม่ได้)
        try:
            parsed_last_row = next(csv.reader([current_data_line]))
            epoch_from_csv = parsed_last_row[0].strip() if parsed_last_row else str(trainer.epoch + 1)
        except Exception:
            epoch_from_csv = str(trainer.epoch + 1)

        drive_weights_dir = Path(drive_weights_dir)
        drive_weights_dir.mkdir(parents=True, exist_ok=True)

        # state ภายใน ใช้เก็บ Best Fitness ล่าสุดไว้เทียบเท่านั้น
        # (ตัวไฟล์ BEST_EPOCH_<epoch>.txt ที่โชว์ผู้ใช้เป็นไฟล์เปล่า ไม่มี Fitness อยู่ข้างใน)
        state_file = drive_weights_dir / ".best_epoch_state.json"

        previous_fitness = None
        if state_file.exists():
            try:
                state = json.loads(state_file.read_text(encoding="utf-8"))
                previous_fitness = float(state.get("fitness"))
            except Exception:
                previous_fitness = None

        is_new_best = previous_fitness is None or current_fitness > previous_fitness
        if not is_new_best:
            return  # ไม่ดีกว่าเดิม -> ไม่เปลี่ยนอะไร (เงียบ)

        def _replace_best_marker(weights_dir: Path):
            weights_dir.mkdir(parents=True, exist_ok=True)
            for old_file in weights_dir.glob("BEST_EPOCH_*.txt"):
                old_file.unlink(missing_ok=True)
            (weights_dir / f"BEST_EPOCH_{epoch_from_csv}.txt").write_text("", encoding="utf-8")

        # อัปเดตไฟล์ marker เปล่าบน Drive
        _replace_best_marker(drive_weights_dir)
        state_file.write_text(
            json.dumps({"epoch": epoch_from_csv, "fitness": current_fitness}),
            encoding="utf-8",
        )

        # เก็บสำเนาไว้บน local ด้วย เผื่อ Cell 7 bulk copy ลง Drive ซ้ำตอนจบ
        local_weights_dir = Path(trainer.save_dir) / "weights"
        _replace_best_marker(local_weights_dir)
        (local_weights_dir / ".best_epoch_state.json").write_text(
            json.dumps({"epoch": epoch_from_csv, "fitness": current_fitness}),
            encoding="utf-8",
        )

    except Exception as e:
        print(f"  [WARNING] อัปเดต BEST_EPOCH_<epoch>.txt ไม่สำเร็จ (ไม่กระทบการเทรน): {e}")


# ============================================================================
# BACKUP WEIGHTS + RESULTS
# ============================================================================
def backup_weights_to_drive(trainer):
    """
    Callback:
        - ทำงานทุกครั้งที่ Ultralytics save checkpoint
        - + ทำงานอีกครั้งตอน train จบ

    Backup:
        best.pt, last.pt, results.csv, args.yaml, results.png,
        per_class_metrics.csv, confusion matrices, PR/F1 curves,
        validation images, BEST_EPOCH_<epoch>.txt

    BEST_EPOCH_<epoch>.txt:
        - ไฟล์เปล่า ชื่อไฟล์บอกเลข epoch ที่ดีที่สุด (เช่น BEST_EPOCH_51.txt)
        - ใช้ trainer.fitness, Fitness สูงสุดเท่านั้น
        - ไม่แก้ results.csv
        - อัปเดตแบบเงียบ (log สรุปอยู่ที่บรรทัด [backup] ด้านล่างเท่านั้น)
    """
    try:
        drive_backup_dir = DRIVE_MODELS_PATH / run_name
        drive_backup_dir.mkdir(parents=True, exist_ok=True)

        local_weights_dir = Path(trainer.save_dir) / 'weights'
        drive_weights_dir = drive_backup_dir / 'weights'
        drive_weights_dir.mkdir(parents=True, exist_ok=True)

        # 1. Backup weights
        for fname in ('best.pt', 'last.pt'):
            src = local_weights_dir / fname
            if src.exists():
                shutil.copy2(src, drive_weights_dir / fname)

        # 2. Update BEST_EPOCH_<epoch>.txt (เงียบ ไม่ print)
        update_best_epoch_file(trainer, drive_weights_dir)

        # 3. Backup ไฟล์วิเคราะห์ขนาดเล็ก
        small_files_to_backup = (
            'results.csv', 'args.yaml', 'results.png', 'per_class_metrics.csv',
            'confusion_matrix.png', 'confusion_matrix_normalized.png',
            'BoxPR_curve.png', 'BoxF1_curve.png',
            'val_batch0_pred.jpg', 'val_batch0_labels.jpg',
        )
        for fname in small_files_to_backup:
            src = Path(trainer.save_dir) / fname
            if src.exists():
                shutil.copy2(src, drive_backup_dir / fname)

        print(
            "  [backup] เซฟ weights + metrics + BEST_EPOCH_<epoch>.txt + กราฟ/ตาราง "
            f"กลับ Drive แล้ว (epoch {trainer.epoch + 1})"
        )

    except Exception as e:
        print(f"  [WARNING] backup รอบนี้ไม่สำเร็จ (ไม่กระทบการเทรน จะลองใหม่ epoch ถัดไป): {e}")


# ============================================================================
# STOP FLAG
# ============================================================================
def check_stop_signal(trainer):
    try:
        if STOP_FLAG_PATH.exists():
            print("  [STOP] พบไฟล์ STOP.flag บน Drive -> สั่งจบการเทรนแบบสมบูรณ์หลัง epoch นี้")
            trainer.stop = True
    except Exception as e:
        print(f"  [WARNING] เช็ค STOP.flag ไม่สำเร็จ (ไม่กระทบการเทรน): {e}")


# ============================================================================
# START FRESH RUN
# ============================================================================
def start_fresh_run(pretrained_weights):
    global run_name

    existing_numbers = [
        int(p.name[3:]) for p in DRIVE_MODELS_PATH.glob('run*')
        if p.is_dir() and p.name[3:].isdigit()
    ]
    next_run_number = max(existing_numbers, default=0) + 1
    run_name = f'run{next_run_number}'

    print(f"รอบนี้คือ: {run_name}")
    print(f"เริ่มจากจุดตั้งต้น: {pretrained_weights}")

    # IN_PROGRESS.flag
    in_progress_flag_path = DRIVE_MODELS_PATH / run_name / 'IN_PROGRESS.flag'
    in_progress_flag_path.parent.mkdir(parents=True, exist_ok=True)
    in_progress_flag_path.write_text('training started, not yet finished')

    # Model
    model = YOLO(pretrained_weights)
    model.add_callback('on_model_save', backup_weights_to_drive)
    model.add_callback('on_val_end', save_per_class_metrics)
    model.add_callback('on_fit_epoch_end', check_stop_signal)
    model.add_callback('on_train_end', backup_weights_to_drive)

    # Train
    model.train(
        data=DATA_YAML,
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        workers=workers,
        cache=cache,
        device=device,
        patience=patience,
        close_mosaic=close_mosaic,
        **TRAIN_AUGMENTATION_ARGS,
        project=LOCAL_MODELS_DIR,
        name=run_name,
        exist_ok=False,
    )


# ============================================================================
# RESUME STUCK RUN
# ============================================================================
def resume_stuck_run(resumable_drive_run):
    global run_name
    run_name = resumable_drive_run.name

    print(f"พบ {run_name} ที่มี IN_PROGRESS.flag ค้างอยู่")
    print("กำลังตรวจสอบว่า resume ได้จริงไหม...")

    local_run_dir = f'{LOCAL_MODELS_DIR}/{run_name}'
    if os.path.exists(local_run_dir):
        shutil.rmtree(local_run_dir)
    shutil.copytree(resumable_drive_run, local_run_dir)

    last_pt_path = f'{local_run_dir}/weights/last.pt'

    # Check checkpoint
    if not is_resumable_checkpoint(last_pt_path):
        print("  [WARNING] checkpoint นี้ resume ต่อไม่ได้จริง")
        print(f"  แปลว่า {run_name} เทรนจบสมบูรณ์ไปแล้วจริง ๆ แต่ IN_PROGRESS.flag ยังอยู่")

        old_flag = resumable_drive_run / 'IN_PROGRESS.flag'
        if old_flag.exists():
            old_flag.unlink()

        best_pt_path = f'{local_run_dir}/weights/best.pt'
        start_fresh_run(pretrained_weights=best_pt_path)
        return

    # Resume
    print("-> ยืนยันว่า resume ได้จริง")
    print(f"กำลังเทรนต่อจาก: {last_pt_path}")

    model = YOLO(last_pt_path)
    model.add_callback('on_model_save', backup_weights_to_drive)
    model.add_callback('on_val_end', save_per_class_metrics)
    model.add_callback('on_fit_epoch_end', check_stop_signal)
    model.add_callback('on_train_end', backup_weights_to_drive)

    # Patch check_resume เพื่อให้ epochs จาก Form มีผล
    from ultralytics.engine.trainer import BaseTrainer

    original_check_resume = BaseTrainer.check_resume

    def check_resume_with_form_epochs(self, overrides):
        original_check_resume(self, overrides)
        if getattr(self, "resume", False) and "epochs" in overrides:
            self.args.epochs = overrides["epochs"]

    BaseTrainer.check_resume = check_resume_with_form_epochs

    try:
        model.train(
            resume=True,
            epochs=epochs,
            imgsz=imgsz,
            batch=batch,
            workers=workers,
            cache=cache,
            device=device,
            patience=patience,
            close_mosaic=close_mosaic,
            **TRAIN_AUGMENTATION_ARGS,
        )
    finally:
        BaseTrainer.check_resume = original_check_resume


if IS_MAIN:
    # ============================================================================
    # SELECT TRAINING MODE
    # ============================================================================
    if training_mode == "continue_from_run":
        source_best_pt = DRIVE_MODELS_PATH / source_run_name / 'weights' / 'best.pt'
        if not source_best_pt.exists():
            raise FileNotFoundError(
                f"ไม่พบ {source_best_pt}\nเช็คว่า source_run_name = '{source_run_name}' ถูกต้องไหม"
            )

        print(f"โหมด: ต่อยอดจาก run ({source_run_name})")
        start_fresh_run(pretrained_weights=str(source_best_pt))

    elif training_mode == "new":
        print("โหมด: บังคับเริ่ม run ใหม่เสมอ")
        start_fresh_run(pretrained_weights=PRETRAINED_WEIGHTS)

    else:
        # AUTO
        resumable_drive_run = find_resumable_run()

        if resumable_drive_run is not None:
            print("โหมด: auto -> พบ run ค้างอยู่")
            resume_stuck_run(resumable_drive_run)
        else:
            print("โหมด: auto -> ไม่พบ run ค้าง จะเริ่ม run ใหม่")
            start_fresh_run(pretrained_weights=PRETRAINED_WEIGHTS)


    # ============================================================================
    # TRAIN COMPLETE
    # ============================================================================
    in_progress_flag_path = DRIVE_MODELS_PATH / run_name / 'IN_PROGRESS.flag'
    if in_progress_flag_path.exists():
        in_progress_flag_path.unlink()

    print(f"เทรน {run_name} เสร็จสมบูรณ์แล้ว (ปิดสถานะ resume)")

    if STOP_FLAG_PATH.exists():
        print("\nพบว่าหยุดเพราะ STOP.flag")
        print("อย่าลืมลบไฟล์นี้ทิ้งก่อนเริ่ม run ถัดไป!")
        print(f"({STOP_FLAG_PATH})")


# %% [Cell 7] คัดลอกผลลัพธ์กลับ Google Drive
if IS_MAIN:
    local_run_dir = f'{LOCAL_MODELS_DIR}/{run_name}'
    drive_run_dir = f'{DRIVE_MODELS_DIR}/{run_name}'

    print("กำลังคัดลอกผลลัพธ์จาก local ไป Drive...")
    shutil.copytree(local_run_dir, drive_run_dir, dirs_exist_ok=True)

    best_pt_path = f'{drive_run_dir}/weights/best.pt'

    # BEST_EPOCH_<epoch>.txt เป็นไฟล์เปล่า ชื่อไฟล์เปลี่ยนไปตาม epoch ที่ดีที่สุด
    # จึงต้องหาไฟล์ด้วย glob แทนการเดาชื่อไฟล์ตรง ๆ
    best_epoch_marker_files = sorted(Path(f'{drive_run_dir}/weights').glob('BEST_EPOCH_*.txt'))
    best_epoch_path = str(best_epoch_marker_files[-1]) if best_epoch_marker_files else "(ไม่พบไฟล์ BEST_EPOCH_<epoch>.txt)"

    print("\nโมเดลที่เทรนเสร็จอยู่ที่ Drive:")
    print(best_pt_path)
    print("\nEpoch ที่ดีที่สุด (จากชื่อไฟล์เปล่า) อยู่ที่:")
    print(best_epoch_path)
    print("\nดาวน์โหลด best.pt นี้มาใช้กับ 2_auto_label.py หรือ 3_auto_label_gui.py")


# %% [Cell 8] ดูผลการเทรน
if IS_MAIN:
    print("เปิดดูกราฟและผลลัพธ์ทั้งหมดได้ที่:")
    print(drive_run_dir)
    print("\nBEST_EPOCH_<epoch>.txt (ไฟล์เปล่า บอกเลข epoch ที่ดีที่สุด):")
    print(best_epoch_path)


# %% [Cell 9] ทดสอบโมเดลกับรูปตัวอย่าง
if IS_MAIN:
    import signal
    try:
        from IPython.display import Image as IPyImage
        from IPython.display import display
    except ImportError:                       # ในเครื่องที่ไม่มี IPython: แค่พิมพ์ที่อยู่ไฟล์ภาพ
        def IPyImage(filename=None, width=None):
            return filename

        def display(obj):
            print(f"  (ไฟล์ภาพ: {obj})")

    test_model = YOLO(best_pt_path)

    valid_images_dir = Path(DATA_YAML).parent / 'valid' / 'images'
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp'}
    all_valid_images = sorted(
        p for p in valid_images_dir.iterdir() if p.suffix.lower() in image_extensions
    )

    local_predict_dir = Path(LOCAL_MODELS_DIR) / f'{run_name}_test_predictions'
    local_predict_dir.mkdir(parents=True, exist_ok=True)

    PREDICT_TIMEOUT_SECONDS = 15
    skipped_images = []
    succeeded_count = 0


    def _alarm(seconds):
        if HAS_ALARM:
            signal.alarm(seconds)


    class _PredictTimeout(Exception):
        pass


    def _timeout_handler(signum, frame):
        raise _PredictTimeout()


    print(f"กำลังทดสอบกับ {len(all_valid_images)} รูป (timeout {PREDICT_TIMEOUT_SECONDS} วินาที/รูป)...")

    _old_signal_handler = signal.signal(signal.SIGALRM, _timeout_handler) if HAS_ALARM else None

    for idx, img_path in enumerate(all_valid_images, start=1):
        _alarm(PREDICT_TIMEOUT_SECONDS)

        try:
            test_model.predict(
                source=str(img_path),
                save=True,
                conf=0.3,
                project=str(local_predict_dir.parent),
                name=local_predict_dir.name,
                exist_ok=True,
                verbose=False,
            )
            _alarm(0)
            succeeded_count += 1

        except _PredictTimeout:
            skipped_images.append(img_path.name)
            print(f"  [ข้าม] {img_path.name} ใช้เวลาเกิน {PREDICT_TIMEOUT_SECONDS} วินาที")

        except Exception as e:
            _alarm(0)
            skipped_images.append(img_path.name)
            print(f"  [ข้าม] {img_path.name} เกิดข้อผิดพลาด: {e}")

        if idx % 50 == 0:
            print(f"  ความคืบหน้า: {idx}/{len(all_valid_images)} รูป")

    if HAS_ALARM:
        signal.signal(signal.SIGALRM, _old_signal_handler)

    print(f"\nเสร็จสิ้น: ทำนายสำเร็จ {succeeded_count}/{len(all_valid_images)} รูป")

    if skipped_images:
        print(
            f"ข้ามไป {len(skipped_images)} รูป (ใช้เวลานานผิดปกติ/error): "
            f"{skipped_images[:10]}" + (" ..." if len(skipped_images) > 10 else "")
        )

    drive_predict_dir = f'{DRIVE_MODELS_DIR}/{run_name}_test_predictions'
    shutil.copytree(local_predict_dir, drive_predict_dir, dirs_exist_ok=True)

    print("\nผลลัพธ์ถูกเซฟถาวรไว้ที่ Google Drive:")
    print(drive_predict_dir)

    result_images = sorted(local_predict_dir.glob('*.jpg'))[:5]

    if not result_images:
        print("ไม่พบรูปผลลัพธ์ ตรวจสอบว่า predict รันสำเร็จหรือไม่")
    else:
        print(f"ตัวอย่าง {len(result_images)} รูปแรก:")
        for img_path in result_images:
            display(IPyImage(filename=str(img_path), width=600))
