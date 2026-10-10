"""
=============================================================================
RUN 9.5 (RT-DETRv2-M, Official PyTorch) — เวอร์ชันปรับความเร็ว
=============================================================================
โมเดล: RT-DETRv2-M  (config ทางการ: rtdetrv2_r50vd_m_7x_coco.yml)
Repo : https://github.com/lyuwenyu/RT-DETR  (โฟลเดอร์ rtdetrv2_pytorch)

สคริปต์นี้ใช้บน GOOGLE COLAB (ต้องการ GPU) รันตามลำดับ Cell 1 -> Cell 9
ทุกครั้งที่จะเทรนรอบใหม่ ให้รันตั้งแต่ Cell 1 ใหม่ทั้งหมด (เหมือนเดิม)

สิ่งที่เปลี่ยนเพื่อให้เทรนเร็วขึ้น:
    1. Pre-resize: ย่อรูปทั้ง dataset ให้ด้านยาวสุด = PRERESIZE_MAX_SIDE (640)
       ครั้งเดียวก่อนเทรน (Cell 5) พร้อมปรับพิกัดกล่องใน COCO json
       -> ลดงาน decode JPEG + augmentation ทุก epoch ลงราว 5 เท่า
       (mAP50 / mAP50-95 ไม่เปลี่ยน เพราะ IoU ไม่ขึ้นกับสเกล;
        AP_small/medium/large ของ COCO จะอิงพิกเซลของรูปที่ย่อแล้ว)
    2. AlbuRoboflow ย่อรูป (LongestMaxSize) ก่อนทำ augmentation เสมอ
       กันไว้เผื่อปิด pre-resize
    3. MotionBlur สูงสุด 25 px (เดิม 100 px = kernel 99x99 กิน CPU มาก)
       ** augmentation ต่างจาก Run 9.5 เดิม -> ควรนับเป็น run ใหม่ในเล่ม **

ระบบที่ยังคงไว้เหมือนเดิม:
    - Training บน Local VM, Google Drive ใช้เก็บ checkpoint/ผลลัพธ์
    - training_mode: auto / new / continue_from_run
    - Resume อัตโนมัติ (IN_PROGRESS.flag) + epochs จาก Form มีผลตอน resume
    - STOP.flag บน Drive -> หยุดแบบสมบูรณ์หลังจบ epoch
    - patience (early stopping) ตาม Fitness แบบ Ultralytics
    - Backup ทุก epoch (log สรุปแค่บรรทัด [backup])
    - BEST_EPOCH_<epoch>.txt (ไฟล์เปล่า) ตัดสินจาก
      Fitness = 0.1*mAP50 + 0.9*mAP50-95
    - per_class_metrics.csv, results.csv, results.png
    - Roboflow-style augmentation (Albumentations)
      + close_mosaic -> ปิด augmentation หนักใน N epoch สุดท้าย (stop_epoch)

Dataset: รองรับทั้ง YOLO (data.yaml) และ COCO (_annotations.coco.json)

ข้อต่างจาก Ultralytics (ข้อจำกัดของ repo ทางการ):
    - ไม่มี Mosaic ใน pipeline ทางการของ RT-DETRv2 -> ไม่ได้ใช้
    - ไม่มี confusion matrix / PR curve / val_batch*.jpg อัตโนมัติ
    - P / R คำนวณเองจาก COCOeval (ค่าที่ conf ที่ F1 สูงสุด แบบ Ultralytics)
    - val loss ได้จากแพตช์ det_engine.py (ไม่มีใน repo ทางการ)
=============================================================================
"""

# %% [Cell 1] ติดตั้ง repo ทางการ + ไลบรารี
import os
RTDETR_REPO_DIR = '/content/RT-DETR'
RTDETR_DIR = f'{RTDETR_REPO_DIR}/rtdetrv2_pytorch'

if not os.path.isdir(RTDETR_REPO_DIR):
    !git clone -q https://github.com/lyuwenyu/RT-DETR.git {RTDETR_REPO_DIR}

# ติดตั้ง requirements โดย "ไม่แตะ" torch/torchvision ของ Colab (กันเวอร์ชัน CUDA พัง)
!grep -viE "^(torch|torchvision)([<>=~ ]|$)" {RTDETR_DIR}/requirements.txt > /content/rtdetr_req.txt
!pip install -q -r /content/rtdetr_req.txt
!pip install -q -U albumentations pycocotools pyyaml matplotlib


# %% [Cell 2] เชื่อมต่อ Google Drive + ตั้ง path
import os
from google.colab import drive

drive.mount('/content/drive')

# --- โมเดล RT-DETRv2-M (ทางการ) ---
BASE_CONFIG_NAME = 'rtdetrv2_r50vd_m_7x_coco.yml'   # RT-DETRv2-M
PRETRAINED_WEIGHTS_URL = (
    'https://github.com/lyuwenyu/storage/releases/download/v0.1/'
    'rtdetrv2_r50vd_m_7x_coco_ema.pth'
)
PRETRAINED_WEIGHTS = f'/content/pretrained/{os.path.basename(PRETRAINED_WEIGHTS_URL)}'
MODEL_NAME_TAG = 'rtdetrv2_r50vd_m'

# --- Google Drive ---
DRIVE_PROJECT_DIR = '/content/drive/MyDrive/PK Studio/PK Object Detection: Vehicles/RTDETRv2'
DRIVE_MODELS_DIR = f'{DRIVE_PROJECT_DIR}/models_{MODEL_NAME_TAG}'
os.makedirs(DRIVE_MODELS_DIR, exist_ok=True)

# --- ดิสก์เครื่อง Colab ---
LOCAL_DIR = '/content/local_workspace'
LOCAL_DATASET_DIR = f'{LOCAL_DIR}/dataset'
LOCAL_COCO_DIR = f'{LOCAL_DIR}/coco_ann'
LOCAL_MODELS_DIR = f'{LOCAL_DIR}/models'
for _d in (LOCAL_DATASET_DIR, LOCAL_COCO_DIR, LOCAL_MODELS_DIR, os.path.dirname(PRETRAINED_WEIGHTS)):
    os.makedirs(_d, exist_ok=True)

# ดาวน์โหลด COCO-pretrained weights (ครั้งเดียว)
if not os.path.exists(PRETRAINED_WEIGHTS):
    !wget -q -O "{PRETRAINED_WEIGHTS}" "{PRETRAINED_WEIGHTS_URL}"
if not os.path.exists(PRETRAINED_WEIGHTS) or os.path.getsize(PRETRAINED_WEIGHTS) < 1_000_000:
    print("!! ดาวน์โหลด pretrained weights ไม่สำเร็จ -> ตรวจลิงก์ใน README ของ rtdetrv2_pytorch แล้วแก้ PRETRAINED_WEIGHTS_URL")

print(f"ไฟล์ถาวร (Drive): {DRIVE_PROJECT_DIR}")
print(f"โฟลเดอร์ models: {DRIVE_MODELS_DIR}")
print(f"พื้นที่ทำงาน (Local VM): {LOCAL_DIR}")
print(f"Repo ทางการ: {RTDETR_DIR}")


# %% [Cell 3] ตรวจสอบ GPU / CPU / RAM
!nvidia-smi

import torch

if torch.cuda.is_available():
    print(f"\nพร้อมเทรน: พบ GPU {torch.cuda.get_device_name(0)}")
    print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
else:
    print("\n!! ไม่พบ GPU !!")
    print("ไปที่ Runtime > Change runtime type > เลือก T4 GPU แล้ว Restart runtime")
print(f"CPU cores: {os.cpu_count()}")


# %% [Cell 4] คัดลอก zip จาก Drive มา local ครั้งเดียว แล้วแตกไฟล์ (เหมือนเดิม)
import json
import shutil
import zipfile
from pathlib import Path

drive_zip_path = '/content/drive/MyDrive/PSU Transport Project 2026.zip'
local_zip_path = f'{LOCAL_DIR}/dataset.zip'
fingerprint_path = f'{LOCAL_DATASET_DIR}/.zip_fingerprint.json'

if not os.path.exists(drive_zip_path):
    print(f"ยังไม่พบไฟล์ที่: {drive_zip_path}")
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
        os.remove(local_zip_path)  # คืนพื้นที่ดิสก์
        # dataset เปลี่ยน -> ล้างรูปที่ย่อไว้เดิม
        for _old in Path(LOCAL_DIR).glob('resized_*'):
            shutil.rmtree(_old, ignore_errors=True)
        print("แตกไฟล์ dataset บนดิสก์เครื่องเรียบร้อย")


# %% [Cell 5] ตรวจโครงสร้าง + แปลง dataset -> COCO + ย่อรูปครั้งเดียว
import time
import yaml
from concurrent.futures import ThreadPoolExecutor
from PIL import Image

print("โครงสร้างโฟลเดอร์ที่พบ:")
!find "{LOCAL_DATASET_DIR}" -maxdepth 2

dataset_format = "auto"  # @param ["auto", "yolo", "coco"]
PRERESIZE_MAX_SIDE = 640  # @param {type:"integer"}
# ^ ด้านยาวสุดของรูปหลังย่อ (0 = ไม่ย่อ) ใช้ค่าเดียวกับ imgsz ใน Cell 6

IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.bmp', '.webp'}
TRAIN_SPLIT_NAMES = ('train',)
VAL_SPLIT_NAMES = ('valid', 'val', 'validation')


def _find_split_dir(root: Path, split_names, must_contain=None):
    """หาโฟลเดอร์ split เช่น train/ หรือ valid/ (ลึกได้หลายชั้น)"""
    for name in split_names:
        for d in sorted(root.rglob(name)):
            if not d.is_dir():
                continue
            if must_contain is None or (d / must_contain).exists():
                return d
    return None


def _yolo_names(data_yaml_path):
    cfg = yaml.safe_load(open(data_yaml_path, encoding='utf-8'))
    names = cfg.get('names')
    if isinstance(names, dict):
        names = [names[k] for k in sorted(names, key=lambda x: int(x))]
    return [str(n) for n in names], cfg


def _resolve_yolo_images_dir(data_yaml: Path, cfg: dict, key: str, fallback_names):
    """ลองตาม path ใน data.yaml ก่อน (รองรับ '../train/images' ของ Roboflow) แล้วค่อยค้นหาเอง"""
    value = cfg.get(key)
    if isinstance(value, str):
        base = Path(cfg['path']) if cfg.get('path') else data_yaml.parent
        stripped = value
        while stripped.startswith('../'):
            stripped = stripped[3:]
        for cand in (base / value, data_yaml.parent / value, data_yaml.parent / stripped):
            cand = cand.resolve()
            if cand.is_dir():
                return cand
    split_dir = _find_split_dir(data_yaml.parent, fallback_names, must_contain='images')
    return (split_dir / 'images') if split_dir else None


def yolo_split_to_coco(images_dir: Path, class_names, out_json: Path):
    labels_dir = images_dir.parent / 'labels'
    images, annotations = [], []
    ann_id = 1
    img_paths = sorted(p for p in images_dir.rglob('*') if p.suffix.lower() in IMAGE_EXTS)
    for img_id, img_path in enumerate(img_paths, start=1):
        with Image.open(img_path) as im:
            w, h = im.size
        images.append({'id': img_id, 'file_name': str(img_path.relative_to(images_dir)),
                       'width': w, 'height': h})
        lbl = labels_dir / img_path.relative_to(images_dir).with_suffix('.txt')
        if not lbl.exists():
            continue
        for line in lbl.read_text(encoding='utf-8').splitlines():
            vals = line.split()
            if len(vals) < 5:
                continue
            cls = int(float(vals[0]))
            coords = list(map(float, vals[1:]))
            if len(coords) == 4:                       # bbox
                xc, yc, bw, bh = coords
                x1, y1, x2, y2 = xc - bw / 2, yc - bh / 2, xc + bw / 2, yc + bh / 2
            else:                                      # polygon (segmentation) -> bbox
                xs, ys = coords[0::2], coords[1::2]
                x1, y1, x2, y2 = min(xs), min(ys), max(xs), max(ys)
            x1, x2 = max(0.0, x1) * w, min(1.0, x2) * w
            y1, y2 = max(0.0, y1) * h, min(1.0, y2) * h
            if x2 - x1 < 1 or y2 - y1 < 1 or not (0 <= cls < len(class_names)):
                continue
            annotations.append({'id': ann_id, 'image_id': img_id, 'category_id': cls,
                                'bbox': [x1, y1, x2 - x1, y2 - y1],
                                'area': (x2 - x1) * (y2 - y1), 'iscrowd': 0})
            ann_id += 1
    categories = [{'id': i, 'name': n, 'supercategory': 'object'} for i, n in enumerate(class_names)]
    out_json.write_text(json.dumps({'images': images, 'annotations': annotations,
                                    'categories': categories}), encoding='utf-8')
    return len(images), len(annotations)


def normalize_coco_splits(split_jsons: dict, out_dir: Path):
    """จัด category id ของ COCO (เช่นจาก Roboflow ที่มี superclass id 0) ให้เป็น 0..N-1"""
    loaded = {k: json.load(open(v, encoding='utf-8')) for k, v in split_jsons.items()}
    used_ids = set()
    for d in loaded.values():
        used_ids |= {a['category_id'] for a in d['annotations']}
    all_cats = {c['id']: c for c in loaded['train']['categories']}
    keep_ids = sorted(cid for cid, c in all_cats.items()
                      if cid in used_ids or c.get('supercategory', 'none') != 'none')
    id_map = {old: new for new, old in enumerate(keep_ids)}
    names = [all_cats[cid]['name'] for cid in keep_ids]
    out = {}
    for split, d in loaded.items():
        d['annotations'] = [dict(a, category_id=id_map[a['category_id']])
                            for a in d['annotations'] if a['category_id'] in id_map]
        d['categories'] = [{'id': i, 'name': n, 'supercategory': 'object'} for i, n in enumerate(names)]
        p = out_dir / f'{split}.json'
        p.write_text(json.dumps(d), encoding='utf-8')
        out[split] = p
    return names, out


def preresize_split(img_dir, ann_json, out_img_dir, out_json, max_side):
    """
    ย่อรูปทุกภาพใน split ให้ด้านยาวสุด = max_side (ไม่ขยายรูปที่เล็กกว่า)
    แล้วปรับ bbox/area/width/height ใน COCO json ตามสัดส่วนจริงของแต่ละภาพ
    รูปที่ย่อแล้วจะถูกข้าม (รันซ้ำใน session เดิมเร็วมาก)
    """
    d = json.load(open(ann_json, encoding='utf-8'))
    out_img_dir = Path(out_img_dir)
    sizes = {}

    def _one(im):
        src = Path(img_dir) / im['file_name']
        dst = out_img_dir / im['file_name']
        w, h = im['width'], im['height']
        s = min(1.0, max_side / max(w, h))
        nw, nh = max(1, round(w * s)), max(1, round(h * s))
        if not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            with Image.open(src) as x:
                x = x.convert('RGB')
                if s < 1.0:
                    x = x.resize((nw, nh), Image.BILINEAR)
                x.save(dst, quality=95)
        return im['id'], (nw / w, nh / h, nw, nh)

    with ThreadPoolExecutor(max_workers=8) as ex:
        for iid, v in ex.map(_one, d['images']):
            sizes[iid] = v

    for im in d['images']:
        _, _, nw, nh = sizes[im['id']]
        im['width'], im['height'] = nw, nh
    for a in d['annotations']:
        sx, sy, _, _ = sizes[a['image_id']]
        x, y, bw, bh = a['bbox']
        a['bbox'] = [x * sx, y * sy, bw * sx, bh * sy]
        a['area'] = a['bbox'][2] * a['bbox'][3]
    Path(out_json).write_text(json.dumps(d), encoding='utf-8')
    return len(d['images'])


dataset_root = Path(LOCAL_DATASET_DIR)
yaml_candidates = list(dataset_root.rglob('data.yaml'))
coco_candidates = list(dataset_root.rglob('_annotations.coco.json'))

fmt = dataset_format
if fmt == "auto":
    fmt = "yolo" if yaml_candidates else ("coco" if coco_candidates else None)
if fmt is None:
    raise FileNotFoundError("ไม่พบทั้ง data.yaml (YOLO) และ _annotations.coco.json (COCO)")

coco_out = Path(LOCAL_COCO_DIR)

if fmt == "yolo":
    DATA_YAML = str(yaml_candidates[0])
    print(f"\n--- รูปแบบ YOLO, ใช้ data.yaml จาก: {DATA_YAML} ---")
    print(open(DATA_YAML, encoding='utf-8').read())
    CLASS_NAMES, _cfg = _yolo_names(DATA_YAML)
    TRAIN_IMG_DIR = _resolve_yolo_images_dir(Path(DATA_YAML), _cfg, 'train', TRAIN_SPLIT_NAMES)
    VAL_IMG_DIR = _resolve_yolo_images_dir(Path(DATA_YAML), _cfg, 'val', VAL_SPLIT_NAMES)
    if TRAIN_IMG_DIR is None or VAL_IMG_DIR is None:
        raise FileNotFoundError("หาโฟลเดอร์ train/images หรือ valid/images ไม่เจอ")
    COCO_TRAIN_JSON = coco_out / 'train.json'
    COCO_VAL_JSON = coco_out / 'valid.json'
    print("กำลังแปลง YOLO -> COCO ...")
    print("  train:", yolo_split_to_coco(TRAIN_IMG_DIR, CLASS_NAMES, COCO_TRAIN_JSON), "(รูป, กล่อง)")
    print("  valid:", yolo_split_to_coco(VAL_IMG_DIR, CLASS_NAMES, COCO_VAL_JSON), "(รูป, กล่อง)")
else:
    print("\n--- รูปแบบ COCO ---")
    tr = _find_split_dir(dataset_root, TRAIN_SPLIT_NAMES, must_contain='_annotations.coco.json')
    va = _find_split_dir(dataset_root, VAL_SPLIT_NAMES, must_contain='_annotations.coco.json')
    if tr is None or va is None:
        raise FileNotFoundError("หา train/ หรือ valid/ ที่มี _annotations.coco.json ไม่เจอ")
    TRAIN_IMG_DIR, VAL_IMG_DIR = tr, va
    CLASS_NAMES, outs = normalize_coco_splits(
        {'train': tr / '_annotations.coco.json', 'valid': va / '_annotations.coco.json'}, coco_out)
    COCO_TRAIN_JSON, COCO_VAL_JSON = outs['train'], outs['valid']

NUM_CLASSES = len(CLASS_NAMES)
print(f"\nจำนวนคลาส: {NUM_CLASSES} -> {CLASS_NAMES}")

# ---- ย่อรูปทั้ง dataset ครั้งเดียว ----
if PRERESIZE_MAX_SIDE > 0:
    rs_root = Path(LOCAL_DIR) / f'resized_{PRERESIZE_MAX_SIDE}'
    t0 = time.time()
    print(f"\nกำลังย่อรูปเป็นด้านยาว {PRERESIZE_MAX_SIDE}px "
          "(ครั้งแรกใช้เวลาหลายนาที, รันซ้ำใน session เดิมจะข้ามรูปที่ย่อแล้ว)...")
    n_tr = preresize_split(TRAIN_IMG_DIR, COCO_TRAIN_JSON, rs_root / 'train',
                           coco_out / f'train_{PRERESIZE_MAX_SIDE}.json', PRERESIZE_MAX_SIDE)
    n_va = preresize_split(VAL_IMG_DIR, COCO_VAL_JSON, rs_root / 'valid',
                           coco_out / f'valid_{PRERESIZE_MAX_SIDE}.json', PRERESIZE_MAX_SIDE)
    TRAIN_IMG_DIR, VAL_IMG_DIR = rs_root / 'train', rs_root / 'valid'
    COCO_TRAIN_JSON = coco_out / f'train_{PRERESIZE_MAX_SIDE}.json'
    COCO_VAL_JSON = coco_out / f'valid_{PRERESIZE_MAX_SIDE}.json'
    print(f"ย่อเสร็จ: train {n_tr} รูป, valid {n_va} รูป ใน {time.time() - t0:.0f} วินาที")

print(f"TRAIN_IMG_DIR: {TRAIN_IMG_DIR}\nVAL_IMG_DIR:   {VAL_IMG_DIR}")


# %% [Cell 6] เทรนโมเดล RT-DETRv2-M (Official)
import csv
import math
import signal
import subprocess
import sys
import threading
import time

DRIVE_MODELS_PATH = Path(DRIVE_MODELS_DIR)
STOP_FLAG_PATH = Path(DRIVE_PROJECT_DIR) / 'STOP.flag'

# ============================================================================
# TRAINING MODE
# ============================================================================
training_mode = "auto"  # @param ["auto", "new", "continue_from_run"]
# auto: มี run ค้าง -> resume, ไม่มี -> run ใหม่
# new: เริ่ม run ใหม่จาก COCO pretrained (PRETRAINED_WEIGHTS)
# continue_from_run: ใช้ best.pth ของ run เก่าเป็นจุดตั้งต้น
source_run_name = "run9"  # @param {type:"string"}

# ============================================================================
# TRAINING CONFIGURATION
# ============================================================================
epochs = 300       # @param {type:"integer"}
imgsz = 640        # @param {type:"integer"}
batch = 8          # @param {type:"integer"}  (RT-DETR กิน VRAM มากกว่า YOLO: T4≈8-16, A100≈32-48)
workers = 24       # @param {type:"integer"}
device = 0         # @param {type:"integer"}
patience = 15      # @param {type:"integer"}
close_mosaic = 10  # @param {type:"integer"}  (ปิด aug หนักใน N epoch สุดท้าย)
use_amp = True     # @param {type:"boolean"}

# จำกัด workers ตามจำนวน CPU จริง (Colab ฟรีมีแค่ 2 core)
workers = max(1, min(workers, os.cpu_count() or 1))
print(f"ใช้ workers = {workers}, batch = {batch} (CPU = {os.cpu_count()})")
if PRERESIZE_MAX_SIDE > 0 and PRERESIZE_MAX_SIDE != imgsz:
    print(f"  [หมายเหตุ] PRERESIZE_MAX_SIDE ({PRERESIZE_MAX_SIDE}) != imgsz ({imgsz}) "
          "แนะนำให้ตั้งเท่ากัน")

# ============================================================================
# ROBOFLOW-STYLE AUGMENTATION
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
aug_motion_blur_max_px = 25    # @param {type:"integer"}
# ^ เดิม 100 (kernel 99x99 กิน CPU มาก) ถ้าต้องการเหมือน Run 9.5 เดิมทุกค่าให้ตั้ง 100

aug_p_affine = 1.0         # @param {type:"number"}  (Ultralytics สุ่มมุมทุกภาพ = 1.0)
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
# ติดตั้ง custom transform (Albumentations) เข้าไปใน registry ของ repo ทางการ
# ============================================================================
ALBU_MODULE_SRC = r'''
import numpy as np
import torch
import cv2
import albumentations as A
from PIL import Image
from torchvision import tv_tensors

from ...core import register


@register()
class AlbuRoboflow(torch.nn.Module):
    """Roboflow-style augmentation (Albumentations) ที่ปรับ bbox ให้ด้วย"""

    def __init__(self, imgsz=640, hflip=True, vflip=True, rotate_90=True, p_rotate_90=0.5,
                 rotation_degrees=15.0, shear_degrees=10.0, p_affine=1.0,
                 crop_max_percent=20, p_crop=0.3, cutout_holes=3, cutout_percent=10, p_cutout=0.3,
                 saturation_percent=25, hue_degrees=15, brightness_percent=15, exposure_percent=10,
                 p_color=0.3, grayscale_percent=15, p_grayscale=0.15, blur_max_px=2.5, p_blur=0.2,
                 noise_percent=0.1, p_noise=0.15, motion_blur_max_px=25, p_motion_blur=0.2,
                 camera_gain_sigma=0.05, p_camera_gain=0.2, min_visibility=0.1):
        super().__init__()
        t = []
        # ย่อก่อนเสมอ: augmentation ทั้งหมดทำบนรูปขนาด ~imgsz (เร็วกว่ารูปเต็มหลายเท่า)
        t.append(A.LongestMaxSize(max_size=imgsz))
        if hflip:
            t.append(A.HorizontalFlip(p=0.5))
        if vflip:
            t.append(A.VerticalFlip(p=0.5))
        if rotate_90:
            t.append(A.RandomRotate90(p=p_rotate_90))
        if rotation_degrees > 0 or shear_degrees > 0:
            t.append(A.Affine(rotate=(-rotation_degrees, rotation_degrees),
                              shear={'x': (-shear_degrees, shear_degrees), 'y': (-shear_degrees, shear_degrees)},
                              border_mode=cv2.BORDER_CONSTANT, fill=0, p=p_affine))
        if crop_max_percent > 0:
            smin = max(0.08, 1.0 - crop_max_percent / 100.0)
            t.append(A.RandomResizedCrop(size=(imgsz, imgsz), scale=(smin, 1.0), ratio=(0.9, 1.1), p=p_crop))
        if cutout_holes > 0 and cutout_percent > 0:
            hf = min(1.0, cutout_percent / 100.0)
            t.append(A.CoarseDropout(num_holes_range=(1, cutout_holes), hole_height_range=(0.03, hf),
                                     hole_width_range=(0.03, hf), fill=0, p=p_cutout))
        if saturation_percent > 0 or hue_degrees > 0:
            t.append(A.HueSaturationValue(hue_shift_limit=hue_degrees,
                                          sat_shift_limit=int(round(255 * saturation_percent / 100.0)),
                                          val_shift_limit=0, p=p_color))
        if brightness_percent > 0:
            t.append(A.RandomBrightnessContrast(brightness_limit=brightness_percent / 100.0,
                                                contrast_limit=0.0, p=p_color))
        if exposure_percent > 0:
            t.append(A.RandomGamma(gamma_limit=(100 - exposure_percent, 100 + exposure_percent), p=p_color))
        if grayscale_percent > 0:
            t.append(A.ToGray(p=p_grayscale))
        if blur_max_px > 0:
            t.append(A.GaussianBlur(blur_limit=(3, 5), sigma_limit=(0.1, blur_max_px), p=p_blur))
        if noise_percent > 0:
            t.append(A.GaussNoise(std_range=(0.0, noise_percent / 100.0), mean_range=(0.0, 0.0), p=p_noise))
        if motion_blur_max_px > 0:
            k = int(min(99, motion_blur_max_px))
            k = max(3, k - 1 if k % 2 == 0 else k)
            t.append(A.MotionBlur(blur_limit=(3, k), p=p_motion_blur))
        if camera_gain_sigma > 0:
            t.append(A.MultiplicativeNoise(multiplier=(max(0.0, 1 - camera_gain_sigma), 1 + camera_gain_sigma),
                                           per_channel=False, elementwise=False, p=p_camera_gain))
        self.aug = A.Compose(t, bbox_params=A.BboxParams(format='pascal_voc', label_fields=['keep_idx'],
                                                         min_visibility=min_visibility, clip=True))

    def forward(self, *inputs):
        sample = inputs[0] if (len(inputs) == 1 and isinstance(inputs[0], (tuple, list))) else inputs
        image, target, rest = sample[0], sample[1], tuple(sample[2:])

        img_np = np.asarray(image.convert('RGB'))
        h, w = img_np.shape[:2]
        boxes = target['boxes'].as_subclass(torch.Tensor).reshape(-1, 4).float().clone()
        boxes[:, 0::2] = boxes[:, 0::2].clamp(0, w)
        boxes[:, 1::2] = boxes[:, 1::2].clamp(0, h)
        valid = ((boxes[:, 2] - boxes[:, 0]) > 1) & ((boxes[:, 3] - boxes[:, 1]) > 1)
        idx_valid = torch.nonzero(valid).flatten().tolist()

        out = self.aug(image=img_np, bboxes=boxes[valid].numpy().tolist(), keep_idx=idx_valid)
        new_img = out['image']
        nh, nw = new_img.shape[:2]
        keep = torch.as_tensor(list(out['keep_idx']), dtype=torch.long)
        new_boxes = torch.as_tensor(np.array(out['bboxes'], dtype=np.float32).reshape(-1, 4))

        new_target = dict(target)
        for key in ('labels', 'iscrowd'):
            if key in target:
                new_target[key] = target[key][keep]
        new_target['boxes'] = tv_tensors.BoundingBoxes(new_boxes, format='XYXY', canvas_size=(nh, nw))
        if 'area' in target:
            new_target['area'] = (new_boxes[:, 2] - new_boxes[:, 0]) * (new_boxes[:, 3] - new_boxes[:, 1])
        new_target.pop('masks', None)
        return (Image.fromarray(new_img), new_target, *rest)
'''

_tf_dir = Path(RTDETR_DIR) / 'src' / 'data' / 'transforms'
(_tf_dir / 'albu_roboflow.py').write_text(ALBU_MODULE_SRC, encoding='utf-8')
_init_py = _tf_dir / '__init__.py'
_init_txt = _init_py.read_text(encoding='utf-8')
if 'albu_roboflow' not in _init_txt:
    _init_py.write_text(_init_txt.rstrip() + '\nfrom .albu_roboflow import AlbuRoboflow\n', encoding='utf-8')

# ----------------------------------------------------------------------------
# แพตช์ det_engine.py ของ repo ทางการ ให้ log ค่าที่ Ultralytics มี แต่ repo ทางการไม่มี:
#   1) lr ของทุก param group (-> lr/pg0, pg1, pg2 ใน results.csv)
#   2) val loss (giou / cls / l1) -> เขียนลงไฟล์ที่ระบุใน env PK_VAL_LOSS_PATH ทุก epoch
#      (ไม่ใส่ใน test_stats เพราะ det_solver.py คาดว่าทุกค่าใน test_stats เป็น list)
# ----------------------------------------------------------------------------
_engine_py = Path(RTDETR_DIR) / 'src' / 'solver' / 'det_engine.py'
_eng_txt = _engine_py.read_text(encoding='utf-8')
if 'PK_VAL_LOSS_PATH' not in _eng_txt:
    _patches = [
        ('        metric_logger.update(lr=optimizer.param_groups[0]["lr"])\n',
         '        metric_logger.update(lr=optimizer.param_groups[0]["lr"])\n'
         '        metric_logger.update(**{f"lr_pg{_j}": _pg["lr"] for _j, _pg in enumerate(optimizer.param_groups)})\n'),
        ("    header = 'Test:'\n",
         "    header = 'Test:'\n"
         "    val_loss_sum, val_loss_n = {}, 0\n"),
        ('        outputs = model(samples)\n',
         '        outputs = model(samples)\n'
         '        try:\n'
         '            for _k, _v in criterion(outputs, targets).items():\n'
         '                val_loss_sum[_k] = val_loss_sum.get(_k, 0.0) + float(_v) * len(targets)\n'
         '            val_loss_n += len(targets)\n'
         '        except Exception as _e:\n'
         '            if not val_loss_sum:\n'
         '                print(f"[PK] คำนวณ val loss ไม่ได้ (ข้าม): {_e}")\n'),
        ('    stats = {}\n    # stats = {k: meter',
         '    import os as _os, json as _json\n'
         '    _vl_path = _os.environ.get("PK_VAL_LOSS_PATH")\n'
         '    if _vl_path and dist_utils.is_main_process():\n'
         '        with open(_vl_path, "a", encoding="utf-8") as _f:\n'
         '            _f.write(_json.dumps({_k: _v / max(1, val_loss_n) for _k, _v in val_loss_sum.items()}) + "\\n")\n'
         '    stats = {}\n    # stats = {k: meter'),
    ]
    _ok = True
    for _old, _new in _patches:
        if _old not in _eng_txt:
            print(f"  [WARNING] แพตช์ det_engine.py ไม่สำเร็จ (repo เปลี่ยน?): ไม่พบ {_old.strip()!r}")
            _ok = False
            break
        _eng_txt = _eng_txt.replace(_old, _new, 1)
    if _ok:
        _engine_py.write_text(_eng_txt, encoding='utf-8')
        print("แพตช์ det_engine.py แล้ว (log lr ทุก group + val loss)")

BASE_CONFIG_PATH = Path(RTDETR_DIR) / 'configs' / 'rtdetrv2' / BASE_CONFIG_NAME
if not BASE_CONFIG_PATH.exists():
    print("configs ที่มี:", sorted(p.name for p in BASE_CONFIG_PATH.parent.glob('*.yml')))
    raise FileNotFoundError(f"ไม่พบ config {BASE_CONFIG_PATH}")


def build_run_config(run_name_: str) -> Path:
    """สร้าง config ของ run นี้ (include config ทางการของ RT-DETRv2-M แล้ว override)"""
    stop_epoch = max(1, epochs - close_mosaic)
    out_dir = f'{LOCAL_MODELS_DIR}/{run_name_}'

    train_dataset = {'img_folder': str(TRAIN_IMG_DIR), 'ann_file': str(COCO_TRAIN_JSON)}
    if use_roboflow_style_aug:
        albu_kwargs = dict(
            imgsz=imgsz, hflip=aug_horizontal_flip, vflip=aug_vertical_flip,
            rotate_90=aug_rotate_90, p_rotate_90=aug_p_rotate_90,
            rotation_degrees=float(aug_rotation_degrees), shear_degrees=float(aug_shear_degrees),
            p_affine=aug_p_affine, crop_max_percent=aug_crop_max_percent, p_crop=aug_p_crop,
            cutout_holes=aug_cutout_holes, cutout_percent=aug_cutout_percent, p_cutout=aug_p_cutout,
            saturation_percent=aug_saturation_percent, hue_degrees=aug_hue_degrees,
            brightness_percent=aug_brightness_percent, exposure_percent=aug_exposure_percent,
            p_color=aug_p_color, grayscale_percent=aug_grayscale_percent, p_grayscale=aug_p_grayscale,
            blur_max_px=float(aug_blur_max_px), p_blur=aug_p_blur,
            noise_percent=float(aug_noise_percent), p_noise=aug_p_noise,
            motion_blur_max_px=aug_motion_blur_max_px, p_motion_blur=aug_p_motion_blur,
            camera_gain_sigma=float(aug_camera_gain_sigma), p_camera_gain=aug_p_camera_gain,
        )
        train_dataset['transforms'] = {
            'type': 'Compose',
            'ops': [
                {'type': 'AlbuRoboflow', **albu_kwargs},
                {'type': 'SanitizeBoundingBoxes', 'min_size': 1},
                {'type': 'Resize', 'size': [imgsz, imgsz]},
                {'type': 'SanitizeBoundingBoxes', 'min_size': 1},
                {'type': 'ConvertPILImage', 'dtype': 'float32', 'scale': True},
                {'type': 'ConvertBoxes', 'fmt': 'cxcywh', 'normalize': True},
            ],
            'policy': {'name': 'stop_epoch', 'epoch': stop_epoch, 'ops': ['AlbuRoboflow']},
        }
    else:
        # ใช้ augmentation ทางการ แต่เลื่อน stop_epoch ตาม close_mosaic
        train_dataset['transforms'] = {'policy': {'epoch': stop_epoch}}
        if imgsz != 640:
            print("  [WARNING] ใช้ aug ทางการ + imgsz != 640: Resize ใน config ทางการยังเป็น 640")

    collate = {'stop_epoch': stop_epoch}
    if imgsz != 640:
        collate['scales'] = None  # multi-scale ทางการออกแบบรอบ 640

    cfg = {
        '__include__': [f'./{BASE_CONFIG_NAME}'],
        'num_classes': NUM_CLASSES,
        'remap_mscoco_category': False,
        'output_dir': out_dir,
        'epoches': int(epochs),          # (สะกดตาม repo ทางการ)
        'checkpoint_freq': 100000,       # ไม่ต้องเก็บ checkpointXXXX.pth (เก็บ last/best เอง)
        'eval_spatial_size': [imgsz, imgsz],
        'train_dataloader': {
            'total_batch_size': int(batch), 'num_workers': int(workers),
            'dataset': train_dataset, 'collate_fn': collate,
        },
        'val_dataloader': {
            'total_batch_size': int(batch), 'num_workers': int(workers),
            'dataset': {
                'img_folder': str(VAL_IMG_DIR), 'ann_file': str(COCO_VAL_JSON),
                'transforms': {'type': 'Compose', 'ops': [
                    {'type': 'Resize', 'size': [imgsz, imgsz]},
                    {'type': 'ConvertPILImage', 'dtype': 'float32', 'scale': True},
                ]},
            },
        },
    }
    cfg_path = BASE_CONFIG_PATH.parent / f'pk_{MODEL_NAME_TAG}_{run_name_}.yml'
    cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True), encoding='utf-8')
    return cfg_path


print("\n========== AUGMENTATION CONFIG ==========")
print(f"Roboflow-style augmentation: {use_roboflow_style_aug}")
print(f"Pre-resize dataset: {PRERESIZE_MAX_SIDE if PRERESIZE_MAX_SIDE > 0 else 'ปิด'}")
print(f"MotionBlur สูงสุด: {aug_motion_blur_max_px}px")
print(f"ปิด aug หนักตั้งแต่ epoch {max(1, epochs - close_mosaic) + 1} (close_mosaic={close_mosaic})")
print("Mosaic: ไม่มีใน pipeline ทางการของ RT-DETRv2 (ไม่ได้ใช้)")
print("========================================\n")


# ============================================================================
# CHECKPOINT HELPERS
# ============================================================================
def checkpoint_status(pt_path):
    """คืน (resume_ได้ไหม, last_epoch)"""
    try:
        ckpt = torch.load(str(pt_path), map_location='cpu', weights_only=False)
        last_epoch = int(ckpt.get('last_epoch', -1))
        has_opt = ckpt.get('optimizer') is not None
        del ckpt
        return (has_opt and 0 <= last_epoch < epochs - 1), last_epoch
    except Exception as e:
        print(f"  [WARNING] เช็ค checkpoint ไม่สำเร็จ ({e}) ถือว่า resume ไม่ได้ไว้ก่อน")
        return False, -1


def find_resumable_run():
    candidates = []
    for run_dir in DRIVE_MODELS_PATH.glob('run*'):
        if not run_dir.is_dir() or not run_dir.name[3:].isdigit():
            continue
        if (run_dir / 'IN_PROGRESS.flag').exists() and (run_dir / 'weights' / 'last.pth').exists():
            candidates.append(run_dir)
    if not candidates:
        return None
    return sorted(candidates, key=lambda p: int(p.name[3:]))[-1]


# ============================================================================
# METRICS: results.csv / results.png / per_class_metrics.csv / BEST_EPOCH
# ============================================================================
# คอลัมน์เรียงและตั้งชื่อให้ตรงกับ results.csv ของ Train RTDETR-L Augmentation.py (Ultralytics)
# (lr/pgN เติมต่อท้ายตามจำนวน param group จริง)
RESULTS_HEADER_BASE = ['epoch', 'time', 'train/giou_loss', 'train/cls_loss', 'train/l1_loss',
                       'metrics/precision(B)', 'metrics/recall(B)', 'metrics/mAP50(B)',
                       'metrics/mAP50-95(B)', 'val/giou_loss', 'val/cls_loss', 'val/l1_loss',
                       'validation_fitness']


def ultralytics_fitness(map50, map5095):
    return 0.1 * map50 + 0.9 * map5095


def append_results_row(run_dir: Path, values: dict, lrs):
    """เขียน 1 แถวลง results.csv (values = dict ตามชื่อคอลัมน์, lrs = list ของ lr แต่ละ group)"""
    path = run_dir / 'results.csv'
    header = RESULTS_HEADER_BASE + [f'lr/pg{j}' for j in range(len(lrs))]
    if path.exists():
        with open(path, encoding='utf-8') as f:
            old_header = f.readline().strip().split(',')
        if old_header != header:
            # results.csv เก่าจาก script รุ่นก่อน (คอลัมน์ไม่ตรง) -> เก็บสำรองแล้วเริ่มไฟล์ใหม่
            path.rename(run_dir / 'results_old_format.csv')
    new_file = not path.exists()
    with open(path, 'a', newline='', encoding='utf-8') as f:
        wr = csv.writer(f)
        if new_file:
            wr.writerow(header)
        wr.writerow([values.get(c, '') for c in RESULTS_HEADER_BASE] + [round(float(x), 8) for x in lrs])


def plot_results(run_dir: Path):
    """results.png 3x3 หน้าตาเดียวกับของ Train RTDETR-L Augmentation.py"""
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        path = run_dir / 'results.csv'
        if not path.exists():
            return
        rows = list(csv.DictReader(open(path, encoding='utf-8')))
        if not rows:
            return

        def col(name):
            out = []
            for r in rows:
                try:
                    out.append(float(r[name]))
                except (KeyError, TypeError, ValueError):
                    out.append(float('nan'))
            return out

        ep = col('epoch')
        panels = [('Train Box Loss', 'train/giou_loss'), ('Train Class Loss', 'train/cls_loss'),
                  ('Validation Class Loss', 'val/cls_loss'), ('Validation Box Loss', 'val/giou_loss'),
                  ('Precision', 'metrics/precision(B)'), ('Recall', 'metrics/recall(B)'),
                  ('mAP@50', 'metrics/mAP50(B)'), ('mAP@50-95', 'metrics/mAP50-95(B)'),
                  ('Validation Fitness', 'validation_fitness')]
        fig, axes = plt.subplots(3, 3, figsize=(14, 9.2))
        for ax, (title, key) in zip(axes.ravel(), panels):
            pts = [(x, y) for x, y in zip(ep, col(key)) if math.isfinite(x) and math.isfinite(y)]
            if pts:
                ax.plot([p[0] for p in pts], [p[1] for p in pts], marker='.', markersize=3, linewidth=1.0)
                ax.set_title(title)
            else:
                ax.set_title(f'{title} (no data)')
            ax.set_xlabel('Epoch'); ax.grid(True, alpha=0.25)
        fig.tight_layout(pad=1.0)
        fig.savefig(run_dir / 'results.png', dpi=160, bbox_inches='tight')
        plt.close(fig)
    except Exception as e:
        print(f"  [WARNING] วาด results.png ไม่สำเร็จ: {e}")


def precision_recall_at_best_f1(ev, per_class=False):
    """
    คำนวณ P / R แบบ Ultralytics (ค่าที่ confidence ซึ่ง F1 เฉลี่ยทุกคลาสสูงสุด, IoU=0.5)
    จาก COCOeval.eval (precision/scores/recThrs) เพราะ COCO metric ไม่มี P/R โดยตรง
    """
    import numpy as np
    prec = np.asarray(ev['precision'])[0, :, :, 0, -1]    # [R, K]
    scr = np.asarray(ev['scores'])[0, :, :, 0, -1]        # [R, K]
    rec_thrs = np.asarray(ev['params'].recThrs)
    x = np.linspace(0, 1, 1000)
    P, R, ks = [], [], []
    for k in range(prec.shape[1]):
        ok = prec[:, k] > -1
        if not ok.any():
            continue
        ks.append(k)
        s, p, r = scr[ok, k], prec[ok, k], rec_thrs[ok]
        order = np.argsort(-s)                            # confidence จากมากไปน้อย
        s, p, r = s[order], p[order], r[order]
        P.append(np.interp(-x, -s, p, left=1.0, right=0.0))
        R.append(np.interp(-x, -s, r, left=0.0))
    if not P:
        return (float('nan'), float('nan'), {}) if per_class else (float('nan'), float('nan'))
    Pm, Rm = np.mean(P, axis=0), np.mean(R, axis=0)
    f1 = 2 * Pm * Rm / (Pm + Rm + 1e-16)
    i = int(f1.argmax())
    if per_class:
        return float(Pm[i]), float(Rm[i]), {k: (float(p[i]), float(r[i])) for k, p, r in zip(ks, P, R)}
    return float(Pm[i]), float(Rm[i])


_VAL_STATS_CACHE = {}


def _val_class_counts():
    if not _VAL_STATS_CACHE:
        d = json.load(open(COCO_VAL_JSON, encoding='utf-8'))
        inst, imgs = {}, {}
        for a in d['annotations']:
            c = a['category_id']
            inst[c] = inst.get(c, 0) + 1
            imgs.setdefault(c, set()).add(a['image_id'])
        _VAL_STATS_CACHE.update(n_images=len(d['images']), inst=inst,
                                imgs={k: len(v) for k, v in imgs.items()})
    return _VAL_STATS_CACHE


def save_per_class_metrics(run_dir: Path):
    """อ่าน eval/latest.pth (COCOeval.eval ที่ repo ทางการเซฟทุก epoch)"""
    try:
        import numpy as np
        ev_path = run_dir / 'eval' / 'latest.pth'
        if not ev_path.exists():
            return
        ev = torch.load(str(ev_path), map_location='cpu', weights_only=False)
        prec = np.asarray(ev['precision'])   # [T, R, K, A, M]
        rec = np.asarray(ev['recall'])       # [T, K, A, M]
        cat_ids = list(ev['params'].catIds) if 'params' in ev else list(range(prec.shape[2]))
        stats = _val_class_counts()

        def _mean(x):
            x = x[x > -1]
            return float(x.mean()) if x.size else float('nan')

        p_all, r_all, pr_cls = precision_recall_at_best_f1(ev, per_class=True)
        rows, ap50s, aps = [], [], []
        for k, cid in enumerate(cat_ids):
            ap50 = _mean(prec[0, :, k, 0, -1]); ap = _mean(prec[:, :, k, 0, -1])
            pk, rk = pr_cls.get(k, (float('nan'), float('nan')))
            ap50s.append(ap50); aps.append(ap)
            name = CLASS_NAMES[cid] if 0 <= cid < len(CLASS_NAMES) else str(cid)
            rows.append([name, stats['imgs'].get(cid, 0), stats['inst'].get(cid, 0),
                         round(pk, 5), round(rk, 5), round(ap50, 5), round(ap, 5)])
        nanmean = lambda v: float(np.nanmean(v)) if len(v) else float('nan')
        rows.insert(0, ['all', stats['n_images'], sum(stats['inst'].values()),
                        round(p_all, 5), round(r_all, 5), round(nanmean(ap50s), 5), round(nanmean(aps), 5)])
        with open(run_dir / 'per_class_metrics.csv', 'w', newline='', encoding='utf-8') as f:
            wr = csv.writer(f)
            wr.writerow(['Class', 'Images', 'Instances', 'P', 'R', 'mAP50', 'mAP50-95'])
            wr.writerows(rows)
    except Exception as e:
        print(f"  [WARNING] เขียน per_class_metrics.csv ไม่สำเร็จ (ไม่กระทบการเทรน): {e}")


def _read_best_state(weights_dir: Path):
    sf = weights_dir / '.best_epoch_state.json'
    if sf.exists():
        try:
            return json.loads(sf.read_text(encoding='utf-8'))
        except Exception:
            pass
    return None


def update_best_epoch(run_dir: Path, epoch_display: int, fitness: float, is_latest_line: bool):
    """ถ้า Fitness ใหม่ดีที่สุด -> คัดลอก last.pth เป็น weights/best.pth + ไฟล์เปล่า BEST_EPOCH_<epoch>.txt"""
    try:
        if not math.isfinite(fitness):
            return
        local_weights = run_dir / 'weights'
        local_weights.mkdir(parents=True, exist_ok=True)
        prev = _read_best_state(local_weights)
        if prev is not None and fitness <= float(prev.get('fitness', -1)):
            return
        if is_latest_line and (run_dir / 'last.pth').exists():
            shutil.copy2(run_dir / 'last.pth', local_weights / 'best.pth')
        for old in local_weights.glob('BEST_EPOCH_*.txt'):
            old.unlink(missing_ok=True)
        (local_weights / f'BEST_EPOCH_{epoch_display}.txt').write_text('', encoding='utf-8')
        (local_weights / '.best_epoch_state.json').write_text(
            json.dumps({'epoch': epoch_display, 'fitness': fitness}), encoding='utf-8')
    except Exception as e:
        print(f"  [WARNING] อัปเดต BEST_EPOCH_<epoch>.txt ไม่สำเร็จ (ไม่กระทบการเทรน): {e}")


def _durable_copy(src: Path, dst: Path):
    """คัดลอกไป Drive แบบ tmp -> fsync -> ตรวจขนาด -> replace กันไฟล์ค้างครึ่งเดียว/ล้าหลังเมื่อ Colab หลุด"""
    tmp = Path(str(dst) + '.tmp')
    shutil.copy2(src, tmp)
    with open(tmp, 'rb') as f:
        os.fsync(f.fileno())
    if tmp.stat().st_size != Path(src).stat().st_size:
        raise IOError(f"ขนาดไฟล์ไม่ตรงหลังคัดลอก: {src}")
    os.replace(tmp, dst)


def trim_run_to_epoch(local_run: Path, last_epoch: int):
    """
    ตัด log.txt / results.csv / val_loss.jsonl ให้เหลือเฉพาะ epoch ที่ last.pth มีจริง (epoch <= last_epoch+1)
    กัน epoch ซ้ำตอน resume (เช่น 4,5,4,5,...) เมื่อ weights บน Drive ล้าหลังไฟล์ตัวเลข
    """
    keep_n = 0
    lp = local_run / 'log.txt'
    if lp.exists():
        kept = []
        for l in open(lp, encoding='utf-8'):
            if not l.strip():
                continue
            try:
                if int(json.loads(l).get('epoch', 10**9)) <= last_epoch:
                    kept.append(l.rstrip('\r\n') + '\n')
            except Exception:
                pass
        keep_n = len(kept)
        lp.write_text(''.join(kept), encoding='utf-8')
    vp = local_run / 'val_loss.jsonl'
    if vp.exists():
        vl = [l for l in open(vp, encoding='utf-8') if l.strip()][:keep_n]
        vp.write_text(''.join(vl), encoding='utf-8')
    rp = local_run / 'results.csv'
    if rp.exists():
        lines = open(rp, encoding='utf-8').read().splitlines()
        out = [lines[0]] if lines else []
        for l in lines[1:]:
            try:
                if int(float(l.split(',')[0])) <= last_epoch + 1:
                    out.append(l)
            except Exception:
                pass
        rp.write_text('\n'.join(out) + '\n', encoding='utf-8')
    sf = local_run / 'weights' / '.best_epoch_state.json'
    if sf.exists():
        try:
            if int(json.loads(sf.read_text(encoding='utf-8'))['epoch']) > last_epoch + 1:
                print("  [WARNING] best epoch เดิมใหม่กว่า last.pth บน Drive (sync ล้าหลัง) -> รีเซ็ต best state")
                sf.unlink()
                for f in (local_run / 'weights').glob('BEST_EPOCH_*.txt'):
                    f.unlink()
        except Exception:
            pass


def backup_to_drive(run_dir: Path, epoch_display):
    try:
        # ใช้ชื่อโฟลเดอร์ local ของ run นี้เอง ไม่พึ่ง global run_name
        drive_run = DRIVE_MODELS_PATH / Path(run_dir).name
        drive_weights = drive_run / 'weights'
        drive_weights.mkdir(parents=True, exist_ok=True)
        local_weights = run_dir / 'weights'

        if (run_dir / 'last.pth').exists():
            _durable_copy(run_dir / 'last.pth', drive_weights / 'last.pth')
        if (local_weights / 'best.pth').exists():
            _durable_copy(local_weights / 'best.pth', drive_weights / 'best.pth')
        for old in drive_weights.glob('BEST_EPOCH_*.txt'):
            old.unlink(missing_ok=True)
        for f in list(local_weights.glob('BEST_EPOCH_*.txt')) + [local_weights / '.best_epoch_state.json']:
            if f.exists():
                shutil.copy2(f, drive_weights / f.name)
        for fname in ('results.csv', 'results.png', 'per_class_metrics.csv', 'log.txt', 'val_loss.jsonl', 'args.yaml'):
            src = run_dir / fname
            if src.exists():
                shutil.copy2(src, drive_run / fname)
        print(f"  [backup] เซฟ weights + metrics + BEST_EPOCH_<epoch>.txt + กราฟ/ตาราง "
              f"กลับ Drive แล้ว (epoch {epoch_display})")
    except Exception as e:
        print(f"  [WARNING] backup รอบนี้ไม่สำเร็จ (จะลองใหม่ epoch ถัดไป): {e}")


# ============================================================================
# RUN OFFICIAL TRAINER + MONITOR (แทน callbacks ของ Ultralytics)
# ============================================================================
def preflight_check(cfg_path: Path):
    """ลองโหลด 1 batch + สร้างโมเดล แบบไม่ใช้ worker ถ้าพังจะเห็น error ชัด ๆ ภายในไม่กี่วินาที"""
    code = f"""
import sys, traceback
sys.path.insert(0, '.')
try:
    from src.core import YAMLConfig
    cfg = YAMLConfig(r'{cfg_path}', train_dataloader={{'num_workers': 0}}, val_dataloader={{'num_workers': 0}})
    for name in ('train_dataloader', 'val_dataloader'):
        loader = getattr(cfg, name)
        if hasattr(loader, 'set_epoch'): loader.set_epoch(0)
        imgs, tgts = next(iter(loader))
        print(f'[preflight] {{name}} OK: images {{tuple(imgs.shape)}}, boxes ในภาพแรก {{len(tgts[0]["boxes"])}}')
    m = cfg.model
    print('[preflight] สร้างโมเดล OK')
except Exception:
    traceback.print_exc(); sys.exit(1)
"""
    print("กำลังตรวจ dataset/augmentation/โมเดล ก่อนเทรน (preflight)...")
    r = subprocess.run([sys.executable, '-c', code], cwd=RTDETR_DIR, capture_output=True, text=True)
    print((r.stdout + r.stderr)[-4000:])
    if r.returncode != 0:
        raise RuntimeError("preflight ไม่ผ่าน -> ดู error ด้านบน (ส่งให้ Claude ได้เลย)")


def run_official_training(cfg_path: Path, tuning=None, resume=None):
    preflight_check(cfg_path)
    run_dir = Path(LOCAL_MODELS_DIR) / run_name
    run_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(cfg_path, run_dir / 'args.yaml')

    cmd = [sys.executable, 'tools/train.py', '-c', str(cfg_path), '--seed=0']
    if use_amp:
        cmd.append('--use-amp')
    if resume:
        cmd += ['-r', str(resume)]
    elif tuning:
        cmd += ['-t', str(tuning)]

    val_loss_path = run_dir / 'val_loss.jsonl'   # เขียนโดย det_engine.py ที่แพตช์ไว้ (1 บรรทัด/epoch)
    env = dict(os.environ, CUDA_VISIBLE_DEVICES=str(device), PYTHONUNBUFFERED='1',
               PK_VAL_LOSS_PATH=str(val_loss_path))
    print("คำสั่ง:", ' '.join(cmd))
    proc = subprocess.Popen(cmd, cwd=RTDETR_DIR, env=env, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, bufsize=1, start_new_session=True)

    log_path = run_dir / 'log.txt'
    n_done = sum(1 for l in open(log_path, encoding='utf-8') if l.strip()) if log_path.exists() else 0
    state = {'stopped_by': None}
    t_start = time.time()
    time_offset = 0.0   # เวลาสะสมของ epoch ก่อนหน้า (กรณี resume)
    _rc = run_dir / 'results.csv'
    if _rc.exists():
        try:
            time_offset = float(list(csv.DictReader(open(_rc, encoding='utf-8')))[-1].get('time') or 0.0)
        except Exception:
            pass

    def _read_val_losses():
        if not val_loss_path.exists():
            return []
        out = []
        for l in open(val_loss_path, encoding='utf-8'):
            if l.strip():
                try:
                    out.append(json.loads(l))
                except Exception:
                    out.append({})
        return out

    def _stop(reason):
        state['stopped_by'] = reason
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        except Exception:
            pass

    def _process_new_lines():
        nonlocal n_done
        if not log_path.exists():
            return
        lines = [l for l in open(log_path, encoding='utf-8') if l.strip()]
        new = lines[n_done:]
        val_losses = _read_val_losses()
        for i, line in enumerate(new):
            try:
                rec = json.loads(line)
            except Exception:
                continue
            ep = int(rec.get('epoch', n_done + i)) + 1
            st = rec.get('test_coco_eval_bbox') or [float('nan')] * 12
            ap, ap50 = float(st[0]), float(st[1])
            fit = ultralytics_fitness(ap50, ap)
            # P/R แบบ Ultralytics: ใช้ eval/latest.pth ได้เฉพาะ epoch ล่าสุดของรอบนี้
            # (ถ้า monitor ตามหลังหลาย epoch แถวก่อนหน้าจะเว้น P/R ว่าง)
            p_, r_ = float('nan'), float('nan')
            if i == len(new) - 1:
                try:
                    ev = torch.load(str(run_dir / 'eval' / 'latest.pth'), map_location='cpu', weights_only=False)
                    p_, r_ = precision_recall_at_best_f1(ev)
                except Exception as e:
                    print(f"  [WARNING] คำนวณ P/R ไม่สำเร็จ: {e}")
            vl = val_losses[n_done + i] if (n_done + i) < len(val_losses) else {}
            f5 = lambda x: '' if x is None or not math.isfinite(float(x)) else round(float(x), 5)
            t_total = round(time_offset + time.time() - t_start, 2)
            lrs = [rec[k] for k in sorted((k for k in rec if k.startswith('train_lr_pg')),
                                          key=lambda k: int(k[len('train_lr_pg'):]))] or [rec.get('train_lr', 0.0)]
            row = {
                'epoch': ep, 'time': t_total,
                'train/giou_loss': f5(rec.get('train_loss_giou')),
                'train/cls_loss': f5(rec.get('train_loss_vfl')),
                'train/l1_loss': f5(rec.get('train_loss_bbox')),
                'metrics/precision(B)': f5(p_), 'metrics/recall(B)': f5(r_),
                'metrics/mAP50(B)': f5(ap50), 'metrics/mAP50-95(B)': f5(ap),
                'val/giou_loss': f5(vl.get('loss_giou')),
                'val/cls_loss': f5(vl.get('loss_vfl')),
                'val/l1_loss': f5(vl.get('loss_bbox')),
                'validation_fitness': f5(fit),
            }
            append_results_row(run_dir, row, lrs)
            is_latest = (i == len(new) - 1)
            update_best_epoch(run_dir, ep, fit, is_latest)
            if is_latest:
                save_per_class_metrics(run_dir)
                plot_results(run_dir)
                backup_to_drive(run_dir, ep)
                print(f"  [epoch {ep}/{epochs}] train(giou={row['train/giou_loss']}, cls={row['train/cls_loss']}, "
                      f"l1={row['train/l1_loss']})  val(giou={row['val/giou_loss']}, cls={row['val/cls_loss']}, "
                      f"l1={row['val/l1_loss']})  P={row['metrics/precision(B)']} R={row['metrics/recall(B)']} "
                      f"mAP50={row['metrics/mAP50(B)']} mAP50-95={row['metrics/mAP50-95(B)']}")

                best = _read_best_state(run_dir / 'weights')
                if best and patience > 0 and ep - int(best['epoch']) >= patience:
                    print(f"  [EarlyStopping] ไม่ดีขึ้น {patience} epoch (best = epoch {best['epoch']}) -> หยุด")
                    _stop('patience')
                try:
                    if STOP_FLAG_PATH.exists():
                        print("  [STOP] พบไฟล์ STOP.flag บน Drive -> จบการเทรนแบบสมบูรณ์หลัง epoch นี้")
                        _stop('stop_flag')
                except Exception as e:
                    print(f"  [WARNING] เช็ค STOP.flag ไม่สำเร็จ: {e}")
        n_done = len(lines)

    def _monitor():
        while proc.poll() is None:
            time.sleep(10)
            try:
                _process_new_lines()
            except Exception as e:
                print(f"  [WARNING] monitor error: {e}")

    th = threading.Thread(target=_monitor, daemon=True)
    th.start()
    train_log_file = open(DRIVE_MODELS_PATH / run_name / 'train_stdout.log', 'a', encoding='utf-8')
    tail = []
    try:
        for line in proc.stdout:
            print(line, end='')
            train_log_file.write(line)
            train_log_file.flush()
            tail = (tail + [line])[-40:]
    except KeyboardInterrupt:
        print("\n[Interrupt] หยุดด้วยมือ -> IN_PROGRESS.flag ยังอยู่ รันใหม่จะ resume ได้")
        _stop('manual')
        proc.wait()
        raise
    proc.wait()
    th.join(timeout=30)
    _process_new_lines()
    backup_to_drive(run_dir, 'final')

    train_log_file.close()
    if proc.returncode != 0 and state['stopped_by'] is None:
        print("\n========== 40 บรรทัดสุดท้ายก่อนพัง ==========")
        print(''.join(tail))
        raise RuntimeError(f"การเทรนล้มเหลว (exit code {proc.returncode}) -> ดู error ด้านบน "
                           f"(log เต็มอยู่ที่ Drive: {run_name}/train_stdout.log)")
    return state['stopped_by']


# ============================================================================
# START FRESH / RESUME
# ============================================================================
def start_fresh_run(pretrained_weights):
    global run_name
    nums = [int(p.name[3:]) for p in DRIVE_MODELS_PATH.glob('run*') if p.is_dir() and p.name[3:].isdigit()]
    run_name = f'run{max(nums, default=0) + 1}'
    print(f"รอบนี้คือ: {run_name}")
    print(f"เริ่มจากจุดตั้งต้น: {pretrained_weights}")

    flag = DRIVE_MODELS_PATH / run_name / 'IN_PROGRESS.flag'
    flag.parent.mkdir(parents=True, exist_ok=True)
    flag.write_text('training started, not yet finished')

    local_run = Path(LOCAL_MODELS_DIR) / run_name
    if local_run.exists():
        shutil.rmtree(local_run)
    return run_official_training(build_run_config(run_name), tuning=pretrained_weights)


def resume_stuck_run(drive_run: Path):
    global run_name
    run_name = drive_run.name
    print(f"พบ {run_name} ที่มี IN_PROGRESS.flag ค้างอยู่ -> ตรวจสอบว่า resume ได้จริงไหม...")

    local_run = Path(LOCAL_MODELS_DIR) / run_name
    if local_run.exists():
        shutil.rmtree(local_run)
    (local_run / 'weights').mkdir(parents=True, exist_ok=True)

    # จัดโครงสร้างให้ตรงกับที่ trainer ทางการต้องการ (last.pth + log.txt อยู่ที่ root)
    shutil.copy2(drive_run / 'weights' / 'last.pth', local_run / 'last.pth')
    for f in (drive_run / 'weights').iterdir():
        if f.name != 'last.pth' and not f.name.endswith('.tmp'):
            shutil.copy2(f, local_run / 'weights' / f.name)
    for fname in ('log.txt', 'results.csv', 'val_loss.jsonl'):
        if (drive_run / fname).exists():
            shutil.copy2(drive_run / fname, local_run / fname)

    ok, last_epoch = checkpoint_status(local_run / 'last.pth')
    if ok:
        trim_run_to_epoch(local_run, last_epoch)
    if not ok:
        print(f"  [WARNING] checkpoint resume ต่อไม่ได้ (last_epoch={last_epoch}, epochs={epochs})")
        print(f"  แปลว่า {run_name} เทรนครบแล้ว แต่ IN_PROGRESS.flag ยังอยู่ -> เริ่ม run ใหม่จาก best.pth")
        (drive_run / 'IN_PROGRESS.flag').unlink(missing_ok=True)
        best = local_run / 'weights' / 'best.pth'
        seed_weights = str(best) if best.exists() else str(local_run / 'last.pth')
        tmp = Path(LOCAL_DIR) / f'_seed_{run_name}.pth'
        shutil.copy2(seed_weights, tmp)
        return start_fresh_run(pretrained_weights=str(tmp))

    print(f"-> ยืนยันว่า resume ได้จริง: ต่อจาก epoch {last_epoch + 1} ไปจนถึง {epochs} (epochs จาก Form มีผล)")
    return run_official_training(build_run_config(run_name), resume=local_run / 'last.pth')


# ============================================================================
# SELECT TRAINING MODE
# ============================================================================
if training_mode == "continue_from_run":
    src_best = DRIVE_MODELS_PATH / source_run_name / 'weights' / 'best.pth'
    if not src_best.exists():
        raise FileNotFoundError(f"ไม่พบ {src_best}\nเช็คว่า source_run_name = '{source_run_name}' ถูกต้องไหม")
    print(f"โหมด: ต่อยอดจาก run ({source_run_name})")
    tmp = Path(LOCAL_DIR) / f'_seed_{source_run_name}.pth'
    shutil.copy2(src_best, tmp)
    stopped_by = start_fresh_run(pretrained_weights=str(tmp))
elif training_mode == "new":
    print("โหมด: บังคับเริ่ม run ใหม่เสมอ")
    stopped_by = start_fresh_run(pretrained_weights=PRETRAINED_WEIGHTS)
else:
    resumable = find_resumable_run()
    if resumable is not None:
        print("โหมด: auto -> พบ run ค้างอยู่")
        stopped_by = resume_stuck_run(resumable)
    else:
        print("โหมด: auto -> ไม่พบ run ค้าง จะเริ่ม run ใหม่")
        stopped_by = start_fresh_run(pretrained_weights=PRETRAINED_WEIGHTS)

# ============================================================================
# TRAIN COMPLETE
# ============================================================================
(DRIVE_MODELS_PATH / run_name / 'IN_PROGRESS.flag').unlink(missing_ok=True)
print(f"เทรน {run_name} เสร็จสมบูรณ์แล้ว (ปิดสถานะ resume)")
if stopped_by == 'patience':
    print("หยุดเพราะ EarlyStopping (patience)")
if STOP_FLAG_PATH.exists():
    print("\nพบว่าหยุดเพราะ STOP.flag -> อย่าลืมลบไฟล์นี้ทิ้งก่อนเริ่ม run ถัดไป!")
    print(f"({STOP_FLAG_PATH})")


# %% [Cell 7] คัดลอกผลลัพธ์กลับ Google Drive
local_run_dir = f'{LOCAL_MODELS_DIR}/{run_name}'
drive_run_dir = f'{DRIVE_MODELS_DIR}/{run_name}'

print("กำลังคัดลอกผลลัพธ์จาก local ไป Drive...")
shutil.copytree(local_run_dir, drive_run_dir, dirs_exist_ok=True,
                ignore=shutil.ignore_patterns('checkpoint*.pth', 'last.pth', 'best.pth'))
# last.pth (ราก) ถูก backup ไว้ที่ weights/last.pth แล้ว; best.pth ของ repo (ตัดสินด้วย AP) เก็บแยกชื่อ
if os.path.exists(f'{local_run_dir}/best.pth'):
    shutil.copy2(f'{local_run_dir}/best.pth', f'{drive_run_dir}/weights/best_official_ap.pth')

best_pt_path = f'{drive_run_dir}/weights/best.pth'
markers = sorted(Path(f'{drive_run_dir}/weights').glob('BEST_EPOCH_*.txt'))
best_epoch_path = str(markers[-1]) if markers else "(ไม่พบไฟล์ BEST_EPOCH_<epoch>.txt)"

print("\nโมเดลที่ดีที่สุด (ตาม Fitness) อยู่ที่ Drive:")
print(best_pt_path)
print("\nEpoch ที่ดีที่สุด (จากชื่อไฟล์เปล่า):")
print(best_epoch_path)


# %% [Cell 8] ดูผลการเทรน
from IPython.display import Image as IPyImage
from IPython.display import display

print("เปิดดูกราฟและผลลัพธ์ทั้งหมดได้ที่:")
print(drive_run_dir)
print("\nBEST_EPOCH_<epoch>.txt:", best_epoch_path)
if os.path.exists(f'{drive_run_dir}/results.png'):
    display(IPyImage(filename=f'{drive_run_dir}/results.png', width=900))
if os.path.exists(f'{drive_run_dir}/per_class_metrics.csv'):
    print(open(f'{drive_run_dir}/per_class_metrics.csv', encoding='utf-8').read())


# %% [Cell 9] ทดสอบโมเดลกับรูปตัวอย่าง (ใช้ deploy mode ของ repo ทางการ)
import signal
import torch.nn as nn
import torchvision.transforms as T
from PIL import ImageDraw

if RTDETR_DIR not in sys.path:
    sys.path.insert(0, RTDETR_DIR)
from src.core import YAMLConfig

CONF_THRES = 0.3
cfg_for_test = BASE_CONFIG_PATH.parent / f'pk_{MODEL_NAME_TAG}_{run_name}.yml'
test_cfg = YAMLConfig(str(cfg_for_test), resume=best_pt_path, PResNet={'pretrained': False})
_ckpt = torch.load(best_pt_path, map_location='cpu', weights_only=False)
_state = _ckpt['ema']['module'] if 'ema' in _ckpt else _ckpt['model']
test_cfg.model.load_state_dict(_state)


class DeployModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.model = test_cfg.model.deploy()
        self.postprocessor = test_cfg.postprocessor.deploy()

    def forward(self, images, orig_sizes):
        return self.postprocessor(self.model(images), orig_sizes)


dev = torch.device(f'cuda:{device}' if torch.cuda.is_available() else 'cpu')
test_model = DeployModel().to(dev).eval()
to_tensor = T.Compose([T.Resize((imgsz, imgsz)), T.ToTensor()])
PALETTE = ['#FF3838', '#2C99A8', '#FFB21D', '#48F90A', '#8438FF', '#00C2FF', '#FF95C8', '#CFD231']


@torch.no_grad()
def predict_and_save(img_path: Path, out_path: Path):
    im = Image.open(img_path).convert('RGB')
    w, h = im.size
    labels, boxes, scores = test_model(to_tensor(im)[None].to(dev), torch.tensor([[w, h]], device=dev))
    draw = ImageDraw.Draw(im)
    for lb, bx, sc in zip(labels[0], boxes[0], scores[0]):
        if float(sc) < CONF_THRES:
            continue
        c = int(lb)
        color = PALETTE[c % len(PALETTE)]
        x1, y1, x2, y2 = [float(v) for v in bx]
        draw.rectangle([x1, y1, x2, y2], outline=color, width=3)
        name = CLASS_NAMES[c] if 0 <= c < len(CLASS_NAMES) else str(c)
        draw.text((x1 + 3, max(0, y1 - 12)), f'{name} {float(sc):.2f}', fill=color)
    im.save(out_path, quality=90)


all_valid_images = sorted(p for p in Path(VAL_IMG_DIR).rglob('*') if p.suffix.lower() in IMAGE_EXTS)
local_predict_dir = Path(LOCAL_MODELS_DIR) / f'{run_name}_test_predictions'
local_predict_dir.mkdir(parents=True, exist_ok=True)

PREDICT_TIMEOUT_SECONDS = 15
skipped_images, succeeded_count = [], 0


class _PredictTimeout(Exception):
    pass


def _timeout_handler(signum, frame):
    raise _PredictTimeout()


print(f"กำลังทดสอบกับ {len(all_valid_images)} รูป (timeout {PREDICT_TIMEOUT_SECONDS} วินาที/รูป)...")
_old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
for idx, img_path in enumerate(all_valid_images, start=1):
    signal.alarm(PREDICT_TIMEOUT_SECONDS)
    try:
        predict_and_save(img_path, local_predict_dir / f'{img_path.stem}.jpg')
        signal.alarm(0)
        succeeded_count += 1
    except _PredictTimeout:
        skipped_images.append(img_path.name)
        print(f"  [ข้าม] {img_path.name} ใช้เวลาเกิน {PREDICT_TIMEOUT_SECONDS} วินาที")
    except Exception as e:
        signal.alarm(0)
        skipped_images.append(img_path.name)
        print(f"  [ข้าม] {img_path.name} เกิดข้อผิดพลาด: {e}")
    if idx % 50 == 0:
        print(f"  ความคืบหน้า: {idx}/{len(all_valid_images)} รูป")
signal.signal(signal.SIGALRM, _old_handler)

print(f"\nเสร็จสิ้น: ทำนายสำเร็จ {succeeded_count}/{len(all_valid_images)} รูป")
if skipped_images:
    print(f"ข้ามไป {len(skipped_images)} รูป: {skipped_images[:10]}" + (" ..." if len(skipped_images) > 10 else ""))

drive_predict_dir = f'{DRIVE_MODELS_DIR}/{run_name}_test_predictions'
shutil.copytree(local_predict_dir, drive_predict_dir, dirs_exist_ok=True)
print("\nผลลัพธ์ถูกเซฟถาวรไว้ที่ Google Drive:")
print(drive_predict_dir)

for img_path in sorted(local_predict_dir.glob('*.jpg'))[:5]:
    display(IPyImage(filename=str(img_path), width=600))