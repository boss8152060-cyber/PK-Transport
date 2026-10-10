"""
=============================================================================
RT-DETR-L (Ultralytics) — แปลงจากสคริปต์ YOLO26 Run 9.5
    ใช้ Roboflow-style dynamic augmentation ชุดเดียวกับ YOLO26:
    - Flip: Horizontal + Vertical
    - 90° Rotate: CW / CCW / 180° ผ่าน RandomRotate90
    - Rotation ±15°, Shear ±10°
    - Crop 0-20%, Cutout สูงสุด 3 holes ขนาดสูงสุด 10%
    - Saturation ±25%, Hue ±15°, Brightness ±15%, Exposure ±10%
    - Grayscale 15%, Blur ≤2.5px, Noise ≤0.1%, Motion Blur, Camera Gain
    - Mosaic=1.0 และ close_mosaic=10

สิ่งที่ต่างจากเวอร์ชัน YOLO26:
    - ใช้คลาส RTDETR แทน YOLO และน้ำหนัก rtdetr-l.pt
    - โฟลเดอร์ Drive แยกเป็น .../RT-DETR/models_rtdetr-l
    - batch เริ่มต้น 16 (RT-DETR-L กิน VRAM มากกว่า YOLO26m มาก, T4 16GB
      ถ้า OOM ให้ลดเหลือ 8)
    - optimizer AdamW, lr0=1e-4 (ค่าที่เหมาะกับ transformer detector)
    - patience 50 (DETR converge ช้ากว่า YOLO)
    - deterministic=False (grid_sample ใน RT-DETR ไม่รองรับโหมด deterministic)

=============================================================================
สคริปต์นี้รันได้ 2 ที่ (ต้องการ GPU): GOOGLE COLAB (คัดลอกทีละ cell เหมือนเดิม) และ
ในเครื่อง Windows/Linux (รันทั้งไฟล์: python "<ชื่อไฟล์นี้>")  — ตรวจเองอัตโนมัติ (RUN_ENV)
    ในเครื่อง: ใช้ชุดข้อมูลแบบโฟลเดอร์โดยตรง (หรือแตก zip), เก็บ run ไว้ในโฟลเดอร์ Runs ข้างไฟล์นี้
    เลือกรุ่นโมเดลที่ MODEL_SIZE ใน Cell 2: l / x  (rtdetr-l.pt, rtdetr-x.pt — Ultralytics มีน้ำหนักทางการเฉพาะสองรุ่นนี้)
    1. Runtime > Change runtime type > T4 GPU (แนะนำ L4/A100 ถ้ามี)
    2. คัดลอกแต่ละ cell (คั่นด้วย # %%) ไปรันตามลำดับ Cell 1 -> Cell 9
    3. ทุกครั้งที่จะเทรนรอบใหม่ ให้รันตั้งแต่ Cell 1 ใหม่ทั้งหมด

ระบบ: Local VM training, backup Drive ทุก epoch, resume อัตโนมัติ,
      STOP.flag, BEST_EPOCH_<epoch>.txt (ไฟล์เปล่า)
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

# --- เลือกรุ่นโมเดล: l / x  (rtdetr-l.pt, rtdetr-x.pt — Ultralytics มีน้ำหนักทางการเฉพาะสองรุ่นนี้) ---
MODEL_SIZE = "l"  # @param ["l", "x"]
MODEL_SIZE = os.environ.get("PKT_MODEL_SIZE", MODEL_SIZE)
PRETRAINED_WEIGHTS = f'rtdetr-{MODEL_SIZE}.pt'
MODEL_NAME_TAG = os.path.splitext(PRETRAINED_WEIGHTS)[0]  # โฟลเดอร์ models ตั้งชื่อตามรุ่นอัตโนมัติ

if IN_COLAB:
    from google.colab import drive
    drive.mount('/content/drive')

    # --- Google Drive: ใช้เก็บ zip ต้นทาง + ผลลัพธ์สุดท้าย ---
    DRIVE_PROJECT_DIR = '/content/drive/MyDrive/PK Studio/PK Object Detection: Vehicles/RT-DETR'
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
    #   r"G:\My Drive\PK Studio\PK Object Detection  Vehicles\RT-DETR"
    DRIVE_PROJECT_DIR = os.environ.get("PKT_STORE_DIR", str(_here / "Runs" / "RT-DETR"))
    LOCAL_DIR = os.environ.get("PKT_WORKSPACE_DIR", str(_here / "_workspace" / "RT-DETR"))

DRIVE_MODELS_DIR = f'{DRIVE_PROJECT_DIR}/models_{MODEL_NAME_TAG}'

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
    vram_gb = torch.cuda.get_device_properties(0).total_memory / 1024**3
    print(f"VRAM: {vram_gb:.1f} GB")
    if vram_gb < 20:
        print("หมายเหตุ: RT-DETR-L บน GPU <20GB แนะนำ batch 8-16")
else:
    print("\n!! ไม่พบ GPU !! ไปที่ Runtime > Change runtime type > T4 GPU แล้ว Restart")


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
    else:
        zip_stat = os.stat(drive_zip_path)
        current_fingerprint = {'size': zip_stat.st_size, 'mtime': zip_stat.st_mtime}
        saved_fingerprint = None
        if os.path.exists(fingerprint_path):
            with open(fingerprint_path, encoding='utf-8') as f:
                saved_fingerprint = json.load(f)

        if saved_fingerprint == current_fingerprint:
            print("ไฟล์ zip เหมือนเดิม -> ใช้ dataset ที่แตกไว้แล้ว")
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
            print("แตกไฟล์ dataset เรียบร้อย")


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


# %% [Cell 6] เทรนโมเดล RT-DETR-L
from ultralytics import RTDETR
import albumentations as A

DRIVE_MODELS_PATH = Path(DRIVE_MODELS_DIR)
STOP_FLAG_PATH = Path(DRIVE_PROJECT_DIR) / 'STOP.flag'

# ============================================================================
# TRAINING MODE
# ============================================================================
training_mode = "auto"  # @param ["auto", "new", "continue_from_run"]
source_run_name = "run1"  # @param {type:"string"}

# ============================================================================
# TRAINING CONFIGURATION (ปรับให้เหมาะกับ RT-DETR)
# ============================================================================
epochs = 150       # @param {type:"integer"}
imgsz = 640        # @param {type:"integer"}
batch = 16         # @param {type:"integer"}
workers = 8        # @param {type:"integer"}
cache = "disk"     # @param ["disk", "False"]
device = 0         # @param {type:"integer"}
cache = False if cache == "False" else cache
if not IN_COLAB:
    workers = min(workers, os.cpu_count() or 1)         # ในเครื่องมีแกน CPU น้อยกว่า Colab/เครื่องใหญ่
    if cache == "disk":
        cache = False                                   # "disk" เขียนไฟล์ .npy ลงโฟลเดอร์ชุดข้อมูลของคุณเอง -> ไม่ใช้ในเครื่อง
    if not torch.cuda.is_available():
        device = "cpu"
patience = 50      # @param {type:"integer"}
close_mosaic = 10  # @param {type:"integer"}

optimizer = "AdamW"    # @param ["AdamW", "SGD", "auto"]
lr0 = 0.0001           # @param {type:"number"}
lrf = 0.01             # @param {type:"number"}
weight_decay = 0.0001  # @param {type:"number"}
warmup_epochs = 3      # @param {type:"number"}
amp = True             # @param {type:"boolean"}

RTDETR_TRAIN_ARGS = dict(
    optimizer=optimizer,
    lr0=lr0,
    lrf=lrf,
    weight_decay=weight_decay,
    warmup_epochs=warmup_epochs,
    amp=amp,
    deterministic=False,  # จำเป็นสำหรับ RT-DETR (grid_sample)
)

# ============================================================================
# ROBOFLOW-STYLE AUGMENTATION (เหมือน YOLO26 Run 9.5)
# ============================================================================
use_roboflow_style_aug = True  # @param {type:"boolean"}

aug_horizontal_flip = True     # @param {type:"boolean"}
aug_vertical_flip = True       # @param {type:"boolean"}
aug_rotate_90 = True           # @param {type:"boolean"}
aug_rotation_degrees = 15      # @param {type:"number"}
aug_shear_degrees = 10         # @param {type:"number"}
aug_crop_max_percent = 20      # @param {type:"integer"}
aug_cutout_holes = 3           # @param {type:"integer"}
aug_cutout_percent = 10        # @param {type:"integer"}

aug_saturation_percent = 25    # @param {type:"integer"}
aug_hue_degrees = 15           # @param {type:"integer"}
aug_brightness_percent = 15    # @param {type:"integer"}
aug_exposure_percent = 10      # @param {type:"integer"}
aug_grayscale_percent = 15     # @param {type:"integer"}
aug_camera_gain_sigma = 0.05   # @param {type:"number"}

aug_blur_max_px = 2.5          # @param {type:"number"}
aug_noise_percent = 0.1        # @param {type:"number"}
aug_motion_blur_max_px = 100   # @param {type:"integer"}

aug_p_rotate_90 = 0.50     # @param {type:"number"}
aug_p_crop = 0.30          # @param {type:"number"}
aug_p_cutout = 0.30        # @param {type:"number"}
aug_p_color = 0.30         # @param {type:"number"}
aug_p_grayscale = 0.15     # @param {type:"number"}
aug_p_blur = 0.20          # @param {type:"number"}
aug_p_noise = 0.15         # @param {type:"number"}
aug_p_motion_blur = 0.20   # @param {type:"number"}
aug_p_camera_gain = 0.20   # @param {type:"number"}


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
        transforms.append(A.GaussNoise(
            std_range=(0.0, aug_noise_percent / 100.0), mean_range=(0.0, 0.0), p=aug_p_noise,
        ))

    if aug_motion_blur_max_px > 0:
        k = int(min(99, aug_motion_blur_max_px))
        k = max(3, k - 1 if k % 2 == 0 else k)
        transforms.append(A.MotionBlur(blur_limit=(3, k), p=aug_p_motion_blur))

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

print("\n========== CONFIG ==========")
print(f"Model: {PRETRAINED_WEIGHTS} | batch={batch} | optimizer={optimizer} | lr0={lr0}")
print(f"Roboflow-style augmentation: {use_roboflow_style_aug}")
if use_roboflow_style_aug:
    print(f"Custom Albumentations transforms: {len(ROBOFLOW_STYLE_TRANSFORMS)}")
    for t in ROBOFLOW_STYLE_TRANSFORMS:
        print(f"  - {t}")
print("============================\n")


# ============================================================================
# HELPERS: checkpoint / resumable run
# ============================================================================
def is_resumable_checkpoint(pt_path) -> bool:
    try:
        ckpt = torch.load(str(pt_path), map_location='cpu', weights_only=False)
        return ckpt.get('optimizer') is not None and ckpt.get('epoch', -1) >= 0
    except Exception as e:
        print(f"  [WARNING] เช็ค checkpoint ไม่สำเร็จ ({e}) ถือว่า resume ไม่ได้ไว้ก่อน")
        return False


def find_resumable_run():
    candidates = [
        d for d in DRIVE_MODELS_PATH.glob('run*')
        if d.is_dir() and d.name[3:].isdigit()
        and (d / 'IN_PROGRESS.flag').exists() and (d / 'weights' / 'last.pt').exists()
    ]
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
# BEST_EPOCH_<epoch>.txt (ไฟล์เปล่า ตัดสินจาก trainer.fitness)
# ============================================================================
def update_best_epoch_file(trainer, drive_weights_dir):
    try:
        import csv
        import math

        results_path = Path(trainer.save_dir) / "results.csv"
        if not results_path.exists():
            return

        current_fitness = getattr(trainer, "fitness", None)
        if current_fitness is None:
            return
        try:
            current_fitness = float(current_fitness)
        except Exception:
            return
        if not math.isfinite(current_fitness):
            return

        with open(results_path, "r", encoding="utf-8") as f:
            non_empty_lines = [line for line in f if line.strip()]
        if len(non_empty_lines) < 2:
            return

        try:
            parsed = next(csv.reader([non_empty_lines[-1].rstrip("\r\n")]))
            epoch_from_csv = parsed[0].strip() if parsed else str(trainer.epoch + 1)
        except Exception:
            epoch_from_csv = str(trainer.epoch + 1)

        drive_weights_dir = Path(drive_weights_dir)
        drive_weights_dir.mkdir(parents=True, exist_ok=True)
        state_file = drive_weights_dir / ".best_epoch_state.json"

        previous_fitness = None
        if state_file.exists():
            try:
                previous_fitness = float(json.loads(state_file.read_text(encoding="utf-8")).get("fitness"))
            except Exception:
                previous_fitness = None

        if previous_fitness is not None and current_fitness <= previous_fitness:
            return

        state_json = json.dumps({"epoch": epoch_from_csv, "fitness": current_fitness})

        def _replace_best_marker(weights_dir: Path):
            weights_dir.mkdir(parents=True, exist_ok=True)
            for old_file in weights_dir.glob("BEST_EPOCH_*.txt"):
                old_file.unlink(missing_ok=True)
            (weights_dir / f"BEST_EPOCH_{epoch_from_csv}.txt").write_text("", encoding="utf-8")
            (weights_dir / ".best_epoch_state.json").write_text(state_json, encoding="utf-8")

        _replace_best_marker(drive_weights_dir)
        _replace_best_marker(Path(trainer.save_dir) / "weights")

    except Exception as e:
        print(f"  [WARNING] อัปเดต BEST_EPOCH_<epoch>.txt ไม่สำเร็จ (ไม่กระทบการเทรน): {e}")


# ============================================================================
# CREATE RESULTS.PNG
# ============================================================================
def ensure_results_png(trainer):
    """
    สร้าง results.png แบบ 3x3 จาก results.csv ของ RT-DETR โดยตรง

    CSV ของ RT-DETR Run นี้มีคอลัมน์จริงดังนี้:
      train/giou_loss
      train/cls_loss
      train/l1_loss
      val/giou_loss
      val/cls_loss
      val/l1_loss
      metrics/precision(B)
      metrics/recall(B)
      metrics/mAP50(B)
      metrics/mAP50-95(B)
      validation_fitness

    ดังนั้นไม่ใช้ชื่อแบบ YOLO เช่น train/box_loss หรือ val/box_loss
    """
    try:
        import csv as _csv
        import math
        import matplotlib.pyplot as plt

        results_csv = Path(trainer.save_dir) / "results.csv"
        results_png = Path(trainer.save_dir) / "results.png"

        if not results_csv.exists():
            print(f"  [WARNING] ไม่พบ results.csv: {results_csv}")
            return False

        with open(results_csv, "r", encoding="utf-8-sig", newline="") as f:
            reader = _csv.DictReader(f)
            raw_rows = list(reader)

            if not reader.fieldnames:
                print("  [WARNING] results.csv ไม่มี header")
                return False

            headers = [str(h).strip() for h in reader.fieldnames if h is not None]

        if not raw_rows:
            print("  [WARNING] results.csv ไม่มีข้อมูล")
            return False

        # Normalize header/value เพื่อให้รองรับ CSV ที่มี space หรือ BOM
        rows = []
        for raw in raw_rows:
            row = {}
            for k, v in raw.items():
                if k is not None:
                    key = str(k).strip()
                    value = v.strip() if isinstance(v, str) else v
                    row[key] = value
            rows.append(row)

        def series(col):
            """อ่านตัวเลขจากคอลัมน์จริงของ CSV"""
            if col not in headers:
                return None

            values = []
            for row in rows:
                try:
                    value = float(row.get(col, ""))
                    values.append(value if math.isfinite(value) else float("nan"))
                except (TypeError, ValueError):
                    values.append(float("nan"))
            return values

        # ================================================================
        # ใช้ชื่อคอลัมน์ "จริง" จาก results.csv ของ RT-DETR Run นี้
        # ================================================================
        epoch = series("epoch")

        train_box = series("train/giou_loss")
        train_cls = series("train/cls_loss")

        val_cls = series("val/cls_loss")
        val_box = series("val/giou_loss")

        precision = series("metrics/precision(B)")
        recall = series("metrics/recall(B)")
        map50 = series("metrics/mAP50(B)")
        map5095 = series("metrics/mAP50-95(B)")
        fitness = series("validation_fitness")

        if epoch is None:
            print(f"  [WARNING] ไม่พบคอลัมน์ epoch")
            print(f"  columns = {headers}")
            return False

        # ตรวจว่ามีข้อมูลจริงอย่างน้อยในแต่ละชุด
        def has_data(values):
            return values is not None and any(math.isfinite(v) for v in values)

        # ================================================================
        # 3 x 3 ตามรูปตัวอย่างของผู้ใช้
        # ================================================================
        panels = [
            ("Train Box Loss", train_box),
            ("Train Class Loss", train_cls),
            ("Validation Class Loss", val_cls),
            ("Validation Box Loss", val_box),
            ("Precision", precision),
            ("Recall", recall),
            ("mAP@50", map50),
            ("mAP@50-95", map5095),
            ("Validation Fitness", fitness),
        ]

        fig, axes = plt.subplots(3, 3, figsize=(14, 9.2))
        axes = axes.ravel()

        for ax, (title, y) in zip(axes, panels):
            if has_data(y):
                # ใช้เฉพาะจุดที่ epoch และค่าของ metric เป็นตัวเลข
                xx = []
                yy = []
                for x_val, y_val in zip(epoch, y):
                    if math.isfinite(x_val) and math.isfinite(y_val):
                        xx.append(x_val)
                        yy.append(y_val)

                ax.plot(
                    xx,
                    yy,
                    marker=".",
                    markersize=3,
                    linewidth=1.0,
                )
                ax.set_title(title)
            else:
                ax.set_title(f"{title} (no data)")

            ax.set_xlabel("Epoch")
            ax.grid(True, alpha=0.25)

        fig.tight_layout(pad=1.0)
        fig.savefig(results_png, dpi=160, bbox_inches="tight")
        plt.close(fig)

        # ไม่แสดงรายละเอียดคอลัมน์/สถานะย่อยในหน้าจอ
        return results_png.exists()

    except Exception as e:
        print(f"  [WARNING] สร้าง results.png ไม่สำเร็จ: {e}")
        import traceback
        traceback.print_exc()
        return False


# ============================================================================
# BACKUP WEIGHTS + RESULTS
# ============================================================================
def backup_weights_to_drive(trainer):
    try:
        # RT-DETR บางเวอร์ชันไม่สร้าง results.png อัตโนมัติ
        # จึงสร้างก่อนทุกครั้งที่ backup เพื่อให้ไฟล์พร้อมคัดลอกไป Drive
        ensure_results_png(trainer)

        drive_backup_dir = DRIVE_MODELS_PATH / run_name
        drive_weights_dir = drive_backup_dir / 'weights'
        drive_weights_dir.mkdir(parents=True, exist_ok=True)
        local_weights_dir = Path(trainer.save_dir) / 'weights'

        for fname in ('best.pt', 'last.pt'):
            src = local_weights_dir / fname
            if src.exists():
                shutil.copy2(src, drive_weights_dir / fname)

        update_best_epoch_file(trainer, drive_weights_dir)

        for fname in (
            'results.csv', 'args.yaml', 'results.png', 'per_class_metrics.csv',
            'confusion_matrix.png', 'confusion_matrix_normalized.png',
            'BoxPR_curve.png', 'BoxF1_curve.png',
            'val_batch0_pred.jpg', 'val_batch0_labels.jpg',
        ):
            src = Path(trainer.save_dir) / fname
            if src.exists():
                shutil.copy2(src, drive_backup_dir / fname)

        print("  [backup] Backup แล้ว")
    except Exception as e:
        print(f"  [WARNING] backup รอบนี้ไม่สำเร็จ (จะลองใหม่ epoch ถัดไป): {e}")


def check_stop_signal(trainer):
    try:
        if STOP_FLAG_PATH.exists():
            print("  [STOP] พบ STOP.flag บน Drive -> จบการเทรนหลัง epoch นี้")
            trainer.stop = True
    except Exception as e:
        print(f"  [WARNING] เช็ค STOP.flag ไม่สำเร็จ: {e}")


def attach_callbacks(model):
    model.add_callback('on_model_save', backup_weights_to_drive)
    model.add_callback('on_val_end', save_per_class_metrics)
    model.add_callback('on_fit_epoch_end', check_stop_signal)
    model.add_callback('on_train_end', backup_weights_to_drive)


# ============================================================================
# START FRESH RUN
# ============================================================================
def start_fresh_run(pretrained_weights):
    global run_name

    existing_numbers = [
        int(p.name[3:]) for p in DRIVE_MODELS_PATH.glob('run*')
        if p.is_dir() and p.name[3:].isdigit()
    ]
    run_name = f'run{max(existing_numbers, default=0) + 1}'

    print(f"รอบนี้คือ: {run_name}")
    print(f"เริ่มจากจุดตั้งต้น: {pretrained_weights}")

    flag = DRIVE_MODELS_PATH / run_name / 'IN_PROGRESS.flag'
    flag.parent.mkdir(parents=True, exist_ok=True)
    flag.write_text('training started, not yet finished')

    model = RTDETR(pretrained_weights)
    attach_callbacks(model)

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
        **RTDETR_TRAIN_ARGS,
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

    print(f"พบ {run_name} ที่มี IN_PROGRESS.flag ค้างอยู่ -> ตรวจสอบ checkpoint...")

    local_run_dir = f'{LOCAL_MODELS_DIR}/{run_name}'
    if os.path.exists(local_run_dir):
        shutil.rmtree(local_run_dir)
    shutil.copytree(resumable_drive_run, local_run_dir)

    last_pt_path = f'{local_run_dir}/weights/last.pt'

    if not is_resumable_checkpoint(last_pt_path):
        print(f"  [WARNING] {run_name} resume ไม่ได้ (น่าจะเทรนจบแล้ว) -> เริ่ม run ใหม่จาก best.pt")
        old_flag = resumable_drive_run / 'IN_PROGRESS.flag'
        if old_flag.exists():
            old_flag.unlink()
        start_fresh_run(pretrained_weights=f'{local_run_dir}/weights/best.pt')
        return

    print(f"-> resume ได้จริง กำลังเทรนต่อจาก: {last_pt_path}")

    model = RTDETR(last_pt_path)
    attach_callbacks(model)

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
            **RTDETR_TRAIN_ARGS,
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
            raise FileNotFoundError(f"ไม่พบ {source_best_pt}\nเช็ค source_run_name = '{source_run_name}'")
        print(f"โหมด: ต่อยอดจาก run ({source_run_name})")
        start_fresh_run(pretrained_weights=str(source_best_pt))

    elif training_mode == "new":
        print("โหมด: บังคับเริ่ม run ใหม่เสมอ")
        start_fresh_run(pretrained_weights=PRETRAINED_WEIGHTS)

    else:
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
        print(f"\nพบว่าหยุดเพราะ STOP.flag — อย่าลืมลบก่อนเริ่ม run ถัดไป!\n({STOP_FLAG_PATH})")


# %% [Cell 7] คัดลอกผลลัพธ์กลับ Google Drive
if IS_MAIN:
    local_run_dir = f'{LOCAL_MODELS_DIR}/{run_name}'
    drive_run_dir = f'{DRIVE_MODELS_DIR}/{run_name}'

    print("กำลังคัดลอกผลลัพธ์จาก local ไป Drive...")
    shutil.copytree(local_run_dir, drive_run_dir, dirs_exist_ok=True)

    best_pt_path = f'{drive_run_dir}/weights/best.pt'
    best_epoch_marker_files = sorted(Path(f'{drive_run_dir}/weights').glob('BEST_EPOCH_*.txt'))
    best_epoch_path = str(best_epoch_marker_files[-1]) if best_epoch_marker_files else "(ไม่พบไฟล์ BEST_EPOCH_<epoch>.txt)"

    print(f"\nโมเดลที่เทรนเสร็จ: {best_pt_path}")
    print(f"Epoch ที่ดีที่สุด: {best_epoch_path}")
    print("\nหมายเหตุ: best.pt นี้ต้องโหลดด้วย RTDETR(...) ไม่ใช่ YOLO(...)")


# %% [Cell 8] ดูผลการเทรน + แสดง results.png
if IS_MAIN:
    try:
        from IPython.display import Image as IPyImage
        from IPython.display import display
    except ImportError:                       # ในเครื่องที่ไม่มี IPython: แค่พิมพ์ที่อยู่ไฟล์ภาพ
        def IPyImage(filename=None, width=None):
            return filename

        def display(obj):
            print(f"  (ไฟล์ภาพ: {obj})")

    # สร้าง/ตรวจสอบ results.png อีกครั้งหลังเทรนเสร็จ เพื่อให้แน่ใจว่ามีไฟล์
    try:
        # trainer object อาจไม่อยู่ใน scope หลัง resume/new ดังนั้นใช้ local results.csv โดยตรง
        results_csv_path = Path(local_run_dir) / "results.csv"
        results_png_path = Path(local_run_dir) / "results.png"

        if results_csv_path.exists():
            # สร้างใหม่ทุกครั้งจาก results.csv ปัจจุบัน
            # เพื่อไม่ให้ results.png เก่าที่เคยเป็น "(no data)" ค้างอยู่
            class _ResultHolder:
                save_dir = local_run_dir
            ensure_results_png(_ResultHolder())
    except Exception as e:
        print(f"[WARNING] ตรวจสอบ/สร้าง results.png หลังเทรนไม่สำเร็จ: {e}")

    print("เปิดดูกราฟและผลลัพธ์ทั้งหมดได้ที่:")
    print(drive_run_dir)
    print(f"\nBEST_EPOCH_<epoch>.txt: {best_epoch_path}")

    results_png = Path(local_run_dir) / "results.png"
    if results_png.exists():
        print("\nกราฟผลการเทรน (results.png):")
        display(IPyImage(filename=str(results_png), width=1000))
    else:
        print("\nไม่พบ results.png — ตรวจสอบ results.csv และ log ด้านบน")


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

    test_model = RTDETR(best_pt_path)

    valid_images_dir = Path(DATA_YAML).parent / 'valid' / 'images'
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp'}
    all_valid_images = sorted(p for p in valid_images_dir.iterdir() if p.suffix.lower() in image_extensions)

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
                imgsz=imgsz,
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
        print(f"ข้ามไป {len(skipped_images)} รูป: {skipped_images[:10]}" + (" ..." if len(skipped_images) > 10 else ""))

    drive_predict_dir = f'{DRIVE_MODELS_DIR}/{run_name}_test_predictions'
    shutil.copytree(local_predict_dir, drive_predict_dir, dirs_exist_ok=True)
    print(f"\nผลลัพธ์ถูกเซฟไว้ที่: {drive_predict_dir}")

    result_images = sorted(local_predict_dir.glob('*.jpg'))[:5]
    if not result_images:
        print("ไม่พบรูปผลลัพธ์ ตรวจสอบว่า predict รันสำเร็จหรือไม่")
    else:
        print(f"ตัวอย่าง {len(result_images)} รูปแรก:")
        for img_path in result_images:
            display(IPyImage(filename=str(img_path), width=600))
