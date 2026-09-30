#!/usr/bin/env python3
"""
extract_frames.py — เครื่องมือแตกเฟรมภาพจากวิดีโอ (Multi Video Tool)

ใช้ดึงเฟรมภาพจากวิดีโอ (เช่น ฟุตเทจ CCTV) ออกมาเป็นไฟล์ภาพ .jpg/.png
เหมาะสำหรับเตรียมข้อมูลสำหรับ label ภาพ / เทรนโมเดล YOLO ฯลฯ

วิธีใช้แบบ CLI (บรรทัดคำสั่ง):
    # ดึงทุกเฟรม
    python extract_frames.py -i video.mp4 -o out_frames

    # ดึง 2 เฟรมต่อวินาที
    python extract_frames.py -i video.mp4 -o out_frames --fps 2

    # ดึงทุกๆ 30 เฟรม (เช่น วิดีโอ 30fps จะได้ 1 ภาพ/วินาที)
    python extract_frames.py -i video.mp4 -o out_frames --interval 30

    # ดึงเฉพาะช่วงเวลา 00:07:00 ถึง 00:09:00 ของวิดีโอ
    python extract_frames.py -i video.mp4 -o out_frames --fps 1 --start 00:07:00 --end 00:09:00

    # ประมวลผลทั้งโฟลเดอร์ (ทุกวิดีโอในโฟลเดอร์) พร้อมย่อขนาดภาพ
    python extract_frames.py -i videos_folder -o out_frames --fps 1 --resize 1280x720

วิธีใช้แบบ GUI (หน้าต่างโปรแกรม):
    python extract_frames.py
    (รันโดยไม่ใส่ argument ใดๆ จะเปิดหน้าต่าง GUI ให้เลือกไฟล์ผ่านปุ่มกด)

ติดตั้ง dependency ที่ต้องใช้ (ครั้งเดียว):
    pip install opencv-python
"""

import argparse
import sys
from pathlib import Path

VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv", ".m4v", ".ts"}


def _open_video_capture(path):
    """เปิดวิดีโอด้วย cv2.VideoCapture พร้อม fallback สำหรับ path ที่มีอักษรไทย/ยูนิโค้ดบน Windows
    (บางครั้ง path ที่ไม่ใช่ ASCII เปิดไม่ได้ตรงๆ จึงลองใช้ Windows short path เป็นทางเลือกสำรอง)"""
    import cv2

    path_str = str(path)
    cap = cv2.VideoCapture(path_str)
    if cap.isOpened():
        return cap

    if sys.platform == "win32":
        try:
            import ctypes

            buf = ctypes.create_unicode_buffer(260)
            n = ctypes.windll.kernel32.GetShortPathNameW(path_str, buf, 260)
            if n and buf.value and buf.value != path_str:
                cap2 = cv2.VideoCapture(buf.value)
                if cap2.isOpened():
                    return cap2
        except Exception:
            pass

    return cap  # คืนตัวเดิม (isOpened() จะเป็น False ถ้าเปิดไม่ได้จริงๆ)


def _open_video_writer(path, fourcc, fps, size):
    """เปิด cv2.VideoWriter พร้อม fallback สำหรับ path ที่มีอักษรไทย/ยูนิโค้ดบน Windows
    (เขียนวิดีโอไป path ที่ไม่ใช่ ASCII บางเครื่องอาจเขียนไม่ได้ตรงๆ เหมือนปัญหาที่เจอกับ imwrite)"""
    import cv2

    path_str = str(path)
    Path(path_str).parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(path_str, fourcc, fps, size)
    if writer.isOpened():
        return writer, path_str

    if sys.platform == "win32":
        try:
            import ctypes

            # short path ใช้ได้เฉพาะไฟล์/โฟลเดอร์ที่มีอยู่จริงแล้ว จึงต้องหา short path ของโฟลเดอร์ปลายทาง
            # แล้วค่อยต่อชื่อไฟล์ (ที่ควรเป็น ASCII อยู่แล้ว) เข้าไปเอง
            parent = Path(path_str).parent
            buf = ctypes.create_unicode_buffer(260)
            n = ctypes.windll.kernel32.GetShortPathNameW(str(parent), buf, 260)
            if n and buf.value:
                alt_path = str(Path(buf.value) / Path(path_str).name)
                if alt_path != path_str:
                    writer2 = cv2.VideoWriter(alt_path, fourcc, fps, size)
                    if writer2.isOpened():
                        return writer2, alt_path
        except Exception:
            pass

    return writer, path_str  # คืนตัวเดิม (isOpened() จะเป็น False ถ้าเปิดไม่ได้จริงๆ)


def _write_image(fpath, frame, img_format, quality):
    """บันทึกภาพแบบรองรับ path ที่มีอักษรไทย/ยูนิโค้ด (ไม่ใช้ cv2.imwrite ตรงๆ
    เพราะบน Windows มันเขียนไฟล์ไป path ที่ไม่ใช่ ASCII ไม่ได้)"""
    import cv2

    ext = f".{img_format.lower()}"
    if img_format.lower() in ("jpg", "jpeg"):
        params = [cv2.IMWRITE_JPEG_QUALITY, quality]
    else:
        params = []
    ok, buf = cv2.imencode(ext, frame, params)
    if not ok:
        return False
    buf.tofile(str(fpath))
    return True


def parse_timestamp(ts):
    """แปลงสตริงเวลา 'HH:MM:SS' / 'MM:SS' / วินาที เป็นจำนวนวินาที (float)"""
    if ts is None:
        return None
    if isinstance(ts, (int, float)):
        return float(ts)
    ts = str(ts).strip()
    if ts == "":
        return None
    parts = ts.split(":")
    parts = [float(p) for p in parts]
    if len(parts) == 3:
        h, m, s = parts
        return h * 3600 + m * 60 + s
    elif len(parts) == 2:
        m, s = parts
        return m * 60 + s
    elif len(parts) == 1:
        return parts[0]
    raise ValueError(f"รูปแบบเวลาไม่ถูกต้อง: {ts}")


def parse_resize(spec):
    """แปลง 'WIDTHxHEIGHT' เป็น (width, height)"""
    if not spec:
        return None
    spec = spec.lower().replace(" ", "")
    w, h = spec.split("x")
    return (int(w), int(h))


def _find_ffprobe():
    """หา ffprobe ในเครื่อง (ปกติติดมากับ ffmpeg ในแพ็กเดียวกัน) คืนค่า path หรือ None"""
    import shutil as _shutil

    exe_name = "ffprobe.exe" if sys.platform == "win32" else "ffprobe"
    found = _shutil.which(exe_name) or _shutil.which("ffprobe")
    if found:
        return found
    local = Path(__file__).resolve().parent / "ffmpeg" / exe_name
    if local.exists():
        return str(local)
    return None


def probe_video_info(video_path):
    """เปิดวิดีโอแค่เพื่ออ่านข้อมูล (fps, จำนวนเฟรม, ความยาว) แบบเร็วๆ ไม่ถอดรหัสภาพ
    คืนค่า dict {fps, total_frames, duration_sec} หรือ None ถ้าเปิดไม่ได้

    หมายเหตุ: ค่า frame count จาก OpenCV บางครั้งไม่แม่นยำสำหรับไฟล์ที่ผ่านการตัดต่อแบบ
    stream copy มาก่อน (เช่นไฟล์ที่ได้จากโหมดตัดคลิปแบบเร็วของโปรแกรมนี้เอง) จึงใช้ ffprobe
    (ถ้ามีในเครื่อง) ช่วยตรวจสอบความยาวให้แม่นยำขึ้น"""
    import cv2

    cap = _open_video_capture(video_path)
    if not cap.isOpened():
        return None
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    duration = total_frames / fps if fps else 0

    ffprobe_path = _find_ffprobe()
    if ffprobe_path:
        try:
            import subprocess

            result = subprocess.run(
                [ffprobe_path, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(video_path)],
                capture_output=True, text=True, timeout=30,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            probed_duration = float(result.stdout.strip())
            if probed_duration > 0 and fps > 0:
                # ถ้าค่าจาก OpenCV กับ ffprobe ต่างกันมาก (>5%) ให้เชื่อ ffprobe แทน (แม่นยำกว่า)
                if duration <= 0 or abs(probed_duration - duration) / max(duration, 0.01) > 0.05:
                    duration = probed_duration
                    total_frames = round(duration * fps)
        except Exception:
            pass

    return {"fps": fps, "total_frames": total_frames, "duration_sec": duration}


def format_hms(seconds):
    """แปลงวินาที (float) เป็นสตริง HH:MM:SS"""
    seconds = max(0, int(round(seconds)))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def compute_frame_step(video_fps, fps=None, interval_frames=None):
    """คำนวณว่าจะบันทึกภาพทุกๆ กี่เฟรม จาก fps เป้าหมายหรือค่า interval ที่กำหนด
    ใช้ร่วมกันทั้งตอนแตกเฟรมจริงและตอนประมาณการในหน้า GUI เพื่อให้ตัวเลขตรงกันเป๊ะ"""
    if fps is not None and fps > 0:
        return max(1, round(video_fps / fps))
    elif interval_frames is not None:
        return max(1, int(interval_frames))
    return 1


def estimate_extraction(video_fps, total_frames, start_sec, end_sec, fps=None, interval_frames=None):
    """คำนวณจำนวนภาพที่จะได้ ณ ช่วงเวลา/อัตราที่กำหนด โดยไม่ต้องเปิดวิดีโอจริง (คำนวณล่วงหน้าก่อนกดเริ่ม)"""
    start_frame = int(start_sec * video_fps) if start_sec is not None else 0
    end_frame = int(end_sec * video_fps) if end_sec is not None else total_frames
    end_frame = min(end_frame, total_frames)
    span = max(0, end_frame - start_frame)
    if span <= 0:
        return 0
    frame_step = compute_frame_step(video_fps, fps=fps, interval_frames=interval_frames)
    return (span + frame_step - 1) // frame_step  # ceil division — ตรงกับจำนวนจริงที่ extract_frames จะบันทึก


def format_size(num_bytes):
    """แปลงจำนวนไบต์เป็นข้อความอ่านง่าย เช่น '12.3 MB'"""
    if num_bytes is None:
        return "-"
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{int(size)} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


# ระดับความเข้มของการกรองภาพซ้ำ — ยิ่งค่ามาก ยิ่งกรองภาพที่คล้ายกันออกเยอะขึ้น (เก็บภาพน้อยลง)
# ค่านี้ปรับเทียบจากวิดีโอทดสอบที่มี sensor noise สมจริง (ไม่ใช่แค่ภาพนิ่งสนิทแบบไม่มี noise เลย)
DEDUP_LEVELS = {"low": 0.5, "medium": 1.5, "high": 3.0}

# ถ้า sampling ห่างกว่านี้ (ข้าม >= N เฟรมต่อภาพที่เก็บ) จะ seek กระโดดตรงไปตำแหน่งเป้าหมายแทนการเดินผ่านทีละเฟรม
# ค่านี้ได้จากการวัดจริงเทียบกับวิดีโอ H.264 ที่ keyframe ทุก 1 และ 2 วินาที — ต่ำกว่านี้ seek มักช้ากว่าเดิม
# (โอเวอร์เฮดของการ seek เอง สูงกว่าที่ประหยัดได้จากการข้ามเฟรม) สูงกว่านี้ seek เร็วกว่าชัดเจน (1.7x - 3x+)
SEEK_MODE_MIN_STEP = 80

# ถ้าวิดีโอไฟล์เดียวมีจำนวนเฟรมที่ต้องเดินผ่าน (แบบ grab/read ทีละเฟรม ไม่ใช่ seek-mode)
# มากกว่าค่านี้ จะแบ่งเป็นหลายช่วงประมวลผลพร้อมกันด้วยหลาย thread แทนการเดินทีละเฟรมตัวเดียว
# (แต่ละ thread เปิดไฟล์เดียวกันคนละ VideoCapture คนละตำแหน่ง — OpenCV/FFmpeg ปล่อย GIL
# ระหว่างถอดรหัสจึงเร็วขึ้นจริงบนเครื่องหลาย core) ต่ำกว่านี้ overhead การเปิดหลาย VideoCapture
# ไม่คุ้มกับที่ประหยัดได้ ค่านี้เป็นค่าประมาณ ยังไม่ได้วัดละเอียดเท่า SEEK_MODE_MIN_STEP ด้านบน
#
# หมายเหตุสำคัญ: ถ้าเปิด dedup (กรองภาพซ้ำ) พร้อมกับโหมดนี้ แต่ละช่วงจะเทียบภาพซ้ำแยกกัน
# ไม่ต่อเนื่องข้ามรอยต่อระหว่างช่วง — อาจพลาดคู่ภาพซ้ำที่อยู่คนละฝั่งรอยต่อพอดีไปบ้าง
# (ผลกระทบเล็กน้อยในทางปฏิบัติ เพราะรอยต่อมีจำนวนน้อยเทียบกับภาพทั้งหมด)
PARALLEL_SINGLE_VIDEO_MIN_FRAMES = 4000


def _make_dedup_thumb(frame):
    """ย่อภาพให้เล็กและเป็นขาวดำ สำหรับเทียบความเหมือนระหว่างเฟรม (เร็ว ไม่กินแรงประมวลผลมาก)"""
    import cv2

    small = cv2.resize(frame, (64, 64), interpolation=cv2.INTER_AREA)
    return cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)


def _frame_diff_percent(thumb_a, thumb_b):
    """คืนค่าความต่างเฉลี่ยระหว่างภาพย่อสองภาพ เป็นเปอร์เซ็นต์ (0 = เหมือนกันทุกพิกเซล, 100 = ต่างสุดขั้ว)"""
    import cv2

    diff = cv2.absdiff(thumb_a, thumb_b)
    return float(diff.mean()) / 255.0 * 100.0


def _extract_frame_range(
    video_path,
    output_dir,
    video_fps,
    frame_step,
    chunk_start,
    chunk_end,
    img_format,
    quality,
    resize,
    prefix,
    log,
    cancel_event,
    progress_callback,
    dedup_enabled,
    dedup_threshold,
):
    """แตกเฟรมเฉพาะช่วง [chunk_start, chunk_end) ของวิดีโอไฟล์เดียว โดยเปิด VideoCapture
    ของตัวเอง แยกอิสระจาก instance อื่น — เรียกได้ทั้งแบบรันช่วงเดียว (ทั้งไฟล์ = 1 ช่วง
    เหมือนพฤติกรรมเดิม) หรือรันพร้อมกันหลาย thread คนละช่วงพร้อมกันก็ได้ (ดู
    _extract_frames_single_parallel ด้านล่าง)

    chunk_start ต้องอยู่บน "ตาราง" การสุ่มตัวอย่างเดียวกันทั้งไฟล์เสมอ (คือ
    (chunk_start - จุดเริ่มต้นจริงของทั้งวิดีโอ) หารด้วย frame_step ลงตัว) ไม่งั้นเฟรมที่
    เลือกเก็บของแต่ละช่วงจะเหลื่อมกันไม่ตรงตาราง

    คืนค่า tuple: (saved_count, cancelled, skipped_dedup, diff_stats)
    """
    import cv2

    cap = _open_video_capture(video_path)
    if not cap.isOpened():
        log(f"[ERROR] เปิดวิดีโอไม่ได้ (ช่วงเฟรม {chunk_start}-{chunk_end}): {video_path}")
        return 0, False, 0, []

    saved_count = 0
    cancelled = False
    last_saved_thumb = None
    skipped_dedup = 0
    diff_stats = []
    frames_to_process = max(1, chunk_end - chunk_start)

    def try_save_frame(frame, at_frame_idx):
        nonlocal saved_count, last_saved_thumb, skipped_dedup
        should_save = True
        if dedup_enabled:
            thumb = _make_dedup_thumb(frame)
            if last_saved_thumb is not None:
                diff_pct = _frame_diff_percent(thumb, last_saved_thumb)
                diff_stats.append(diff_pct)
                if diff_pct < dedup_threshold:
                    should_save = False
                    skipped_dedup += 1
            if should_save:
                last_saved_thumb = thumb

        if should_save:
            f = frame
            if resize:
                f = cv2.resize(f, resize, interpolation=cv2.INTER_AREA)
            timestamp_sec = at_frame_idx / video_fps
            fname = f"{prefix}_frame{at_frame_idx:06d}_t{timestamp_sec:.2f}s.{img_format}"
            fpath = Path(output_dir) / fname
            if _write_image(fpath, f, img_format, quality):
                saved_count += 1
            else:
                log(f"[WARN] บันทึกภาพไม่สำเร็จ: {fname}")

    use_seek_mode = frame_step >= SEEK_MODE_MIN_STEP
    frame_idx = chunk_start
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)

    if use_seek_mode:
        total_targets = max(1, (frames_to_process + frame_step - 1) // frame_step)
        target_count = 0
        while frame_idx < chunk_end:
            if cancel_event is not None and cancel_event.is_set():
                cancelled = True
                break
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if not ret:
                break
            try_save_frame(frame, frame_idx)
            target_count += 1
            frame_idx += frame_step
            if progress_callback is not None:
                progress_callback(min(target_count * frame_step, frames_to_process), frames_to_process)
    else:
        while frame_idx < chunk_end:
            if cancel_event is not None and cancel_event.is_set():
                cancelled = True
                break

            is_target = (frame_idx - chunk_start) % frame_step == 0
            if is_target:
                ret, frame = cap.read()
                if not ret:
                    break
                try_save_frame(frame, frame_idx)
            else:
                ret = cap.grab()
                if not ret:
                    break
            frame_idx += 1

            processed = frame_idx - chunk_start
            if progress_callback is not None and (processed % 10 == 0 or processed >= frames_to_process):
                progress_callback(min(processed, frames_to_process), frames_to_process)

    cap.release()
    if progress_callback is not None and not cancelled:
        progress_callback(frames_to_process, frames_to_process)
    return saved_count, cancelled, skipped_dedup, diff_stats


def _extract_frames_single_parallel(
    video_path,
    output_dir,
    video_fps,
    frame_step,
    start_frame,
    end_frame,
    img_format,
    quality,
    resize,
    prefix,
    log,
    cancel_event,
    progress_callback,
    dedup_enabled,
    dedup_threshold,
    max_workers,
):
    """แบ่งวิดีโอไฟล์เดียวออกเป็นหลายช่วง (chunk) ให้แต่ละ thread เปิดไฟล์เดียวกันคนละ
    VideoCapture คนละตำแหน่ง ประมวลผลพร้อมกัน — ใช้เมื่อวิดีโอยาว/ใหญ่พอ (ดู
    PARALLEL_SINGLE_VIDEO_MIN_FRAMES) และไม่ได้อยู่ในโหมด seek (ซึ่งเร็วพอแล้วในตัวเอง)
    คืนค่า tuple: (saved_count, cancelled, skipped_dedup, diff_stats) รวมจากทุกช่วง
    """
    import threading as _threading
    from concurrent.futures import ThreadPoolExecutor, as_completed

    total_targets = max(1, (end_frame - start_frame + frame_step - 1) // frame_step)
    max_workers = max(1, min(max_workers, total_targets))
    chunk_target_size = max(1, (total_targets + max_workers - 1) // max_workers)

    # แบ่งช่วงเฟรมตาม "จำนวนเป้าหมายที่จะเก็บ" ไม่ใช่แบ่งตามเวลาเฉย ๆ เพื่อให้แต่ละช่วง
    # มีปริมาณงานใกล้เคียงกัน และยังคงอยู่บนตารางการสุ่มตัวอย่างเดียวกันทั้งไฟล์
    chunks = []
    cursor = start_frame
    chunk_idx = 0
    while cursor < end_frame:
        end_target_idx = min(total_targets, (chunk_idx + 1) * chunk_target_size)
        chunk_end = min(end_frame, start_frame + end_target_idx * frame_step)
        if chunk_end <= cursor:
            break
        chunks.append((cursor, chunk_end))
        cursor = chunk_end
        chunk_idx += 1

    log(f"[INFO] แตกเฟรมวิดีโอนี้แบบขนาน {len(chunks)} ช่วงพร้อมกัน (เร็วขึ้นสำหรับไฟล์ยาว/ใหญ่)")
    if dedup_enabled:
        log("[หมายเหตุ] เปิด dedup พร้อมโหมดขนาน — แต่ละช่วงกรองภาพซ้ำแยกกัน อาจพลาดคู่ภาพซ้ำ")
        log("           ที่อยู่คนละฝั่งรอยต่อระหว่างช่วงไปบ้างเล็กน้อย (ผลกระทบน้อยในทางปฏิบัติ)")

    total_frames_all = max(1, end_frame - start_frame)
    progress_lock = _threading.Lock()
    progress_map = {i: 0 for i in range(len(chunks))}
    saved_total = 0
    any_cancelled = False
    skipped_dedup_total = 0
    diff_stats_all = []

    def make_cb(idx):
        def cb(done, _total_this_chunk):
            with progress_lock:
                progress_map[idx] = done
                current = sum(progress_map.values())
            if progress_callback is not None:
                progress_callback(min(current, total_frames_all), total_frames_all)

        return cb

    def worker(idx, c_start, c_end):
        return _extract_frame_range(
            video_path, output_dir, video_fps, frame_step, c_start, c_end,
            img_format, quality, resize, prefix, log, cancel_event,
            make_cb(idx), dedup_enabled, dedup_threshold,
        )

    with ThreadPoolExecutor(max_workers=len(chunks)) as executor:
        futures = {executor.submit(worker, i, c[0], c[1]): i for i, c in enumerate(chunks)}
        for future in as_completed(futures):
            try:
                n, cancelled, skipped, diffs = future.result()
                saved_total += n
                any_cancelled = any_cancelled or cancelled
                skipped_dedup_total += skipped
                diff_stats_all.extend(diffs)
            except Exception as e:
                log(f"[ERROR] {e}")

    return saved_total, any_cancelled, skipped_dedup_total, diff_stats_all


def extract_frames(
    video_path,
    output_dir,
    fps=None,
    interval_frames=None,
    start_sec=None,
    end_sec=None,
    img_format="jpg",
    quality=95,
    resize=None,
    prefix=None,
    log=print,
    cancel_event=None,
    progress_callback=None,
    dedup_enabled=False,
    dedup_threshold=3.0,
    max_workers=None,
):
    """แตกเฟรมจากวิดีโอไฟล์เดียว คืนค่าจำนวนภาพที่บันทึกได้

    cancel_event: threading.Event ที่ถ้าถูก set() จะหยุดทำงานกลางคันอย่างปลอดภัย
    progress_callback: ฟังก์ชัน callback(frames_done, frames_total) เรียกเป็นระยะระหว่างทำงาน
    dedup_enabled: ถ้า True จะข้ามภาพที่คล้ายกับภาพล่าสุดที่บันทึกไปมากเกินไป (ไม่บันทึกซ้ำ)
    dedup_threshold: ภาพที่ต่างจากภาพล่าสุดน้อยกว่าค่านี้ (% ความต่างเฉลี่ย) จะถูกข้าม — ยิ่งค่าน้อยยิ่งกรองน้อย
    max_workers: จำนวน thread สูงสุดที่จะใช้ประมวลผลวิดีโอไฟล์นี้พร้อมกัน (ดู
        PARALLEL_SINGLE_VIDEO_MIN_FRAMES) ถ้าไม่ระบุจะใช้ตาม os.cpu_count() อัตโนมัติ
        ใส่ 1 เพื่อบังคับให้เดินทีละเฟรมแบบเดิม (ปิดโหมดขนานสำหรับไฟล์นี้)
    """
    import os as _os

    video_path = Path(video_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    info = probe_video_info(video_path)
    if info is None:
        log(f"[ERROR] เปิดวิดีโอไม่ได้: {video_path}")
        return 0

    video_fps = info["fps"]
    total_frames = info["total_frames"]
    duration = info["duration_sec"]

    frame_step = compute_frame_step(video_fps, fps=fps, interval_frames=interval_frames)
    start_frame = int(start_sec * video_fps) if start_sec is not None else 0
    end_frame = int(end_sec * video_fps) if end_sec is not None else total_frames
    end_frame = min(end_frame, total_frames)
    prefix = prefix or video_path.stem

    log(f"[INFO] {video_path.name}: {video_fps:.2f} FPS, {total_frames} เฟรม, {duration:.1f} วินาที")
    log(f"[INFO] บันทึกทุกๆ {frame_step} เฟรม (ช่วงเฟรม {start_frame}-{end_frame})")

    frames_to_process = max(1, end_frame - start_frame)
    use_seek_mode = frame_step >= SEEK_MODE_MIN_STEP

    if max_workers is None:
        max_workers = max(1, _os.cpu_count() or 2)

    # ใช้โหมดขนาน (หลาย thread เปิดไฟล์เดียวกันคนละตำแหน่ง) เฉพาะตอนที่คุ้มค่าจริง ๆ:
    # ต้องไม่ใช่ seek-mode อยู่แล้ว (นั่นเร็วพอในตัวเองอยู่แล้ว), ไฟล์ต้องยาว/ใหญ่พอ,
    # และเครื่องต้องมีมากกว่า 1 core ถึงจะได้ประโยชน์จริง
    should_parallelize = (
        not use_seek_mode and frames_to_process >= PARALLEL_SINGLE_VIDEO_MIN_FRAMES and max_workers > 1
    )

    if should_parallelize:
        saved_count, cancelled, skipped_dedup, diff_stats = _extract_frames_single_parallel(
            video_path, output_dir, video_fps, frame_step, start_frame, end_frame,
            img_format, quality, resize, prefix, log, cancel_event,
            progress_callback, dedup_enabled, dedup_threshold, max_workers,
        )
    else:
        saved_count, cancelled, skipped_dedup, diff_stats = _extract_frame_range(
            video_path, output_dir, video_fps, frame_step, start_frame, end_frame,
            img_format, quality, resize, prefix, log, cancel_event,
            progress_callback, dedup_enabled, dedup_threshold,
        )

    if cancelled:
        log(f"[ยกเลิก] หยุดกลางคัน — บันทึกไปแล้ว {saved_count} เฟรม -> {output_dir}")
    else:
        if dedup_enabled:
            if diff_stats:
                log(
                    f"[INFO] dedup: ข้ามไป {skipped_dedup}/{len(diff_stats)} ภาพ "
                    f"(ค่าความต่างที่วัดได้ ต่ำสุด {min(diff_stats):.2f}% สูงสุด {max(diff_stats):.2f}% "
                    f"เฉลี่ย {sum(diff_stats)/len(diff_stats):.2f}% | เกณฑ์ที่ตั้งไว้ {dedup_threshold:.1f}%)"
                )
                if skipped_dedup == 0 and min(diff_stats) > dedup_threshold:
                    log(
                        f"[หมายเหตุ] ไม่มีภาพไหนถูกกรองเลย เพราะค่าต่ำสุดที่วัดได้ ({min(diff_stats):.2f}%) "
                        f"ยังสูงกว่าเกณฑ์ ({dedup_threshold:.1f}%) — วิดีโอนี้อาจมี noise/แสงกระพริบเยอะกว่าปกติ "
                        f"ลองเพิ่มความเข้มการกรอง หรือปรับเป็น \"มาก\" ดู"
                    )
            else:
                log("[INFO] dedup: เปิดใช้งานแต่มีภาพให้เทียบไม่ถึง 2 ภาพ จึงยังไม่มีผลกรอง")
        if progress_callback is not None:
            progress_callback(frames_to_process, frames_to_process)
        log(f"[DONE] บันทึก {saved_count} เฟรม -> {output_dir}")
    return saved_count


def _process_videos_parallel(
    videos, output_dir, log, cancel_event, video_progress_callback, progress_callback, max_workers, **kwargs
):
    """ประมวลผลหลายวิดีโอพร้อมกันด้วย thread pool (OpenCV ปล่อย GIL ระหว่างถอดรหัส/เข้ารหัสภาพ
    จึงได้ความเร็วเพิ่มขึ้นจริงแม้เป็น thread ไม่ใช่ process) คืนค่าจำนวนภาพรวมที่บันทึกได้"""
    import os
    import threading as _threading
    from concurrent.futures import ThreadPoolExecutor, as_completed

    if max_workers is None:
        max_workers = min(4, max(1, os.cpu_count() or 2))

    log(f"[INFO] ประมวลผลแบบขนาน {max_workers} ไฟล์พร้อมกัน (ทั้งหมด {len(videos)} วิดีโอ)")
    if video_progress_callback is not None:
        video_progress_callback(0, len(videos), f"กำลังประมวลผล {len(videos)} วิดีโอพร้อมกัน...")

    # คำนวณจำนวนเฟรมรวมทั้งหมดล่วงหน้า เพื่อใช้คำนวณ % ความคืบหน้ารวมของทั้งแบทช์
    frame_counts = {}
    total_frames_all = 0
    for v in videos:
        info = probe_video_info(v)
        cnt = info["total_frames"] if info else 0
        frame_counts[v] = cnt
        total_frames_all += cnt

    progress_lock = _threading.Lock()
    progress_map = {v: 0 for v in videos}
    state = {"completed": 0, "saved_total": 0}

    def make_progress_cb(v):
        def cb(done, _total_this_video):
            with progress_lock:
                progress_map[v] = done
                current = sum(progress_map.values())
                completed = state["completed"]
            if progress_callback is not None and total_frames_all > 0:
                progress_callback(current, total_frames_all)
            if video_progress_callback is not None:
                video_progress_callback(completed, len(videos), f"กำลังประมวลผล {len(videos)} วิดีโอพร้อมกัน...")

        return cb

    def worker(v):
        sub_out = Path(output_dir) / v.stem
        prefixed_log = lambda msg, _name=v.name: log(f"[{_name}] {msg}")
        n = extract_frames(
            v, sub_out, log=prefixed_log, cancel_event=cancel_event,
            progress_callback=make_progress_cb(v), **kwargs
        )
        with progress_lock:
            state["saved_total"] += n
            state["completed"] += 1
        return n

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(worker, v): v for v in videos}
        for future in as_completed(futures):
            v = futures[future]
            try:
                future.result()
            except Exception as e:
                log(f"[ERROR] {v.name}: {e}")

    return state["saved_total"]


def process_input(
    input_path, output_dir, log=print, cancel_event=None,
    video_progress_callback=None, progress_callback=None,
    parallel=True, max_workers=None, **kwargs
):
    """รับได้ทั้งไฟล์วิดีโอเดี่ยวหรือโฟลเดอร์ที่มีหลายวิดีโอ

    video_progress_callback: ฟังก์ชัน callback(index, total_videos, video_name) เรียกตอนเริ่มแต่ละวิดีโอ
    parallel: ถ้า True และมีวิดีโอมากกว่า 1 ไฟล์ในโฟลเดอร์ จะประมวลผลพร้อมกันหลายไฟล์ (เร็วขึ้น)
    """
    input_path = Path(input_path)
    total = 0

    if input_path.is_dir():
        videos = sorted(p for p in input_path.iterdir() if p.suffix.lower() in VIDEO_EXTENSIONS)
        if not videos:
            log(f"[WARN] ไม่พบไฟล์วิดีโอในโฟลเดอร์: {input_path}")
            return 0

        if parallel and len(videos) > 1:
            total = _process_videos_parallel(
                videos, output_dir, log=log, cancel_event=cancel_event,
                video_progress_callback=video_progress_callback, progress_callback=progress_callback,
                max_workers=max_workers, **kwargs
            )
        else:
            for i, v in enumerate(videos, start=1):
                if cancel_event is not None and cancel_event.is_set():
                    log("[ยกเลิก] หยุดก่อนเริ่มไฟล์ถัดไป")
                    break
                if video_progress_callback is not None:
                    video_progress_callback(i, len(videos), v.name)
                sub_out = Path(output_dir) / v.stem
                total += extract_frames(
                    v, sub_out, log=log, cancel_event=cancel_event,
                    progress_callback=progress_callback, **kwargs
                )
        log(f"\n[SUMMARY] รวมทั้งหมด {total} เฟรม จาก {len(videos)} วิดีโอ")
    elif input_path.is_file():
        if video_progress_callback is not None:
            video_progress_callback(1, 1, input_path.name)
        total = extract_frames(
            input_path, output_dir, log=log, cancel_event=cancel_event,
            progress_callback=progress_callback, **kwargs
        )
    else:
        log(f"[ERROR] ไม่พบไฟล์หรือโฟลเดอร์: {input_path}")

    return total


def _find_ffmpeg():
    """หา ffmpeg ในเครื่อง คืนค่า path ของ ffmpeg หรือ None ถ้าไม่พบ
    เช็คทั้ง PATH ของระบบ และโฟลเดอร์ ffmpeg/ ที่อาจวางไว้ข้างๆ สคริปต์นี้"""
    import shutil as _shutil

    exe_name = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
    found = _shutil.which(exe_name) or _shutil.which("ffmpeg")
    if found:
        return found
    local = Path(__file__).resolve().parent / "ffmpeg" / exe_name
    if local.exists():
        return str(local)
    return None


def _run_ffmpeg(cmd, log, timeout=1800):
    """เรียก ffmpeg แบบไม่ให้มีหน้าต่าง console โผล่ขึ้นมา คืนค่า True ถ้าสำเร็จ (returncode 0)"""
    import subprocess

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except Exception as e:
        log(f"[หมายเหตุ] เรียก ffmpeg ไม่สำเร็จ: {e}")
        return False

    if result.returncode != 0:
        tail = (result.stderr or "").strip().splitlines()[-1:] or [""]
        log(f"[หมายเหตุ] ffmpeg คืนค่า error: {tail[0][:200]}")
        return False
    return True


def _ffmpeg_trim(ffmpeg_path, video_path, output_path, start_sec, end_sec, log):
    """ตัดวิดีโอด้วย ffmpeg แบบ stream copy (เร็วมาก ไม่เข้ารหัสใหม่ แต่จุดตัดจะปัดไปที่ keyframe
    ที่ใกล้ที่สุด อาจคลาดเคลื่อนได้เล็กน้อย) คืนค่า True/False ว่าสำเร็จหรือไม่"""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [ffmpeg_path, "-y"]
    if start_sec is not None:
        cmd += ["-ss", f"{start_sec:.3f}"]
    cmd += ["-i", str(video_path)]
    if start_sec is not None and end_sec is not None:
        cmd += ["-t", f"{max(0.0, end_sec - start_sec):.3f}"]
    elif end_sec is not None:
        cmd += ["-t", f"{end_sec:.3f}"]
    cmd += ["-c", "copy", str(output_path)]

    log("[INFO] กำลังตัดคลิปด้วย ffmpeg (โหมดเร็ว ไม่เข้ารหัสใหม่)...")
    if not _run_ffmpeg(cmd, log):
        return False
    if not output_path.exists() or output_path.stat().st_size == 0:
        log("[หมายเหตุ] ffmpeg สร้างไฟล์ผลลัพธ์ไม่สำเร็จ")
        return False

    log(f"[DONE] ตัดคลิปสำเร็จด้วย ffmpeg -> {output_path}")
    return True


def trim_video(
    video_path,
    output_path,
    start_sec=None,
    end_sec=None,
    log=print,
    cancel_event=None,
    progress_callback=None,
    fast_mode=True,
):
    """ตัดวิดีโอตามช่วงเวลาที่กำหนด บันทึกเป็นไฟล์วิดีโอใหม่ คืนค่า True/False ว่าสำเร็จหรือไม่

    fast_mode: ถ้า True และเครื่องมี ffmpeg จะตัดแบบ stream copy (เร็วมาก แต่จุดตัดปัดไปที่
    keyframe ใกล้เคียง อาจคลาดเคลื่อน ≤ ~2 วินาที) ถ้า False หรือไม่มี ffmpeg จะเข้ารหัสใหม่ทีละเฟรม
    ด้วย OpenCV แทน (แม่นยำระดับเฟรม แต่ช้ากว่า)
    """
    video_path = Path(video_path)

    if fast_mode:
        ffmpeg_path = _find_ffmpeg()
        if ffmpeg_path:
            if _ffmpeg_trim(ffmpeg_path, video_path, output_path, start_sec, end_sec, log):
                if progress_callback is not None:
                    progress_callback(1, 1)
                return True
            log("[INFO] จะใช้วิธีเข้ารหัสใหม่ทีละเฟรมแทน (ช้ากว่าแต่แม่นยำและทำงานได้แน่นอน)")
        else:
            log("[หมายเหตุ] ไม่พบ ffmpeg ในเครื่อง จะใช้วิธีเข้ารหัสใหม่ทีละเฟรมแทน (ช้ากว่าเล็กน้อยแต่แม่นยำ)")

    return _trim_video_opencv(video_path, output_path, start_sec, end_sec, log, cancel_event, progress_callback)


def _trim_video_opencv(video_path, output_path, start_sec, end_sec, log, cancel_event, progress_callback):
    """ตัดวิดีโอแบบเข้ารหัสใหม่ทีละเฟรมด้วย OpenCV (แม่นยำระดับเฟรม, ใช้เมื่อไม่มี ffmpeg
    หรือเมื่อผู้ใช้เลือกโหมดแม่นยำ) คืนค่า True/False ว่าสำเร็จหรือไม่"""
    import cv2

    video_path = Path(video_path)
    cap = _open_video_capture(video_path)
    if not cap.isOpened():
        log(f"[ERROR] เปิดวิดีโอไม่ได้: {video_path}")
        return False

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    start_frame = int(start_sec * fps) if start_sec is not None else 0
    end_frame = int(end_sec * fps) if end_sec is not None else total_frames
    end_frame = min(end_frame, total_frames)
    span = max(0, end_frame - start_frame)

    if span <= 0:
        log("[ERROR] ช่วงเวลาที่เลือกไม่มีความยาว (เริ่ม >= สิ้นสุด หรือเกินความยาววิดีโอ)")
        cap.release()
        return False

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer, actual_path = _open_video_writer(output_path, fourcc, fps, (width, height))
    if not writer.isOpened():
        log(f"[ERROR] สร้างไฟล์วิดีโอปลายทางไม่ได้: {output_path}")
        cap.release()
        return False

    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    frame_idx = start_frame
    written = 0
    cancelled = False
    log(f"[INFO] ตัดวิดีโอ {video_path.name}: {format_hms(start_frame / fps)} - {format_hms(end_frame / fps)} ({span} เฟรม)")

    while frame_idx < end_frame:
        if cancel_event is not None and cancel_event.is_set():
            cancelled = True
            log(f"[ยกเลิก] หยุดกลางคัน — ตัดไปแล้ว {written} เฟรม")
            break
        ret, frame = cap.read()
        if not ret:
            break
        writer.write(frame)
        written += 1
        frame_idx += 1
        if progress_callback is not None and span > 0 and (written % max(1, span // 200) == 0 or written == span):
            progress_callback(written, span)

    cap.release()
    writer.release()

    if cancelled:
        return False

    if written <= 0:
        log("[ERROR] ไม่ได้เฟรมเลย ไฟล์ผลลัพธ์อาจไม่สมบูรณ์")
        return False

    log(f"[DONE] ตัดวิดีโอสำเร็จ {written} เฟรม -> {actual_path}")
    return True


def _probe_video_params(video_path):
    """อ่านพารามิเตอร์วิดีโอ (ขนาด/fps/fourcc) สำหรับเช็คว่าจะต่อแบบ ffmpeg stream copy ได้ไหม
    (ต้องมีพารามิเตอร์เหล่านี้ตรงกันทุกไฟล์ ไม่งั้น stream copy จะทำให้ไฟล์เสีย)"""
    import cv2

    cap = _open_video_capture(video_path)
    if not cap.isOpened():
        return None
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = round(cap.get(cv2.CAP_PROP_FPS) or 0, 2)
    fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))
    cap.release()
    return (w, h, fps, fourcc)


def _ffmpeg_concat(ffmpeg_path, video_paths, output_path, log):
    """ต่อวิดีโอด้วย ffmpeg concat demuxer แบบ stream copy (เร็วมาก ไม่เข้ารหัสใหม่)
    ใช้ได้เฉพาะกรณีวิดีโอทุกไฟล์มีขนาด/fps/codec ตรงกันเท่านั้น คืนค่า True/False"""
    import tempfile

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    def esc(p):
        return str(Path(p).resolve()).replace("'", "'\\''")

    list_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            for p in video_paths:
                f.write(f"file '{esc(p)}'\n")
            list_path = f.name

        cmd = [ffmpeg_path, "-y", "-f", "concat", "-safe", "0", "-i", list_path, "-c", "copy", str(output_path)]
        log("[INFO] กำลังต่อคลิปด้วย ffmpeg (โหมดเร็ว ไม่เข้ารหัสใหม่)...")
        if not _run_ffmpeg(cmd, log):
            return False
    finally:
        if list_path:
            try:
                Path(list_path).unlink()
            except Exception:
                pass

    if not output_path.exists() or output_path.stat().st_size == 0:
        log("[หมายเหตุ] ffmpeg สร้างไฟล์ผลลัพธ์ไม่สำเร็จ")
        return False

    log(f"[DONE] ต่อคลิปสำเร็จด้วย ffmpeg -> {output_path}")
    return True


def merge_videos(
    video_paths,
    output_path,
    log=print,
    cancel_event=None,
    progress_callback=None,
    fast_mode=True,
):
    """ต่อวิดีโอหลายไฟล์เข้าด้วยกันตามลำดับที่ระบุ บันทึกเป็นไฟล์วิดีโอใหม่ คืนค่า True/False

    fast_mode: ถ้า True, มี ffmpeg, และวิดีโอทุกไฟล์มีขนาด/fps/codec ตรงกันหมด จะต่อแบบ
    stream copy (เร็วมาก ไม่เสียคุณภาพ) ถ้าพารามิเตอร์ไม่ตรงกันหรือไม่มี ffmpeg จะต่อแบบเข้ารหัสใหม่
    ด้วย OpenCV แทน (ปรับขนาดให้ตรงกับไฟล์แรกอัตโนมัติ ใช้ได้กับวิดีโอที่ขนาดไม่เท่ากัน)
    """
    video_paths = [Path(p) for p in video_paths]
    if len(video_paths) < 2:
        log("[ERROR] ต้องเลือกวิดีโออย่างน้อย 2 ไฟล์ถึงจะต่อได้")
        return False

    if fast_mode:
        ffmpeg_path = _find_ffmpeg()
        if ffmpeg_path:
            params_list = [_probe_video_params(p) for p in video_paths]
            if all(p is not None for p in params_list) and len(set(params_list)) == 1:
                if _ffmpeg_concat(ffmpeg_path, video_paths, output_path, log):
                    if progress_callback is not None:
                        progress_callback(1, 1)
                    return True
                log("[INFO] จะใช้วิธีเข้ารหัสใหม่ทีละเฟรมแทน (ช้ากว่าแต่ทำงานได้แน่นอน)")
            else:
                log(
                    "[หมายเหตุ] วิดีโอแต่ละไฟล์มีขนาด/fps/รูปแบบไม่ตรงกัน "
                    "จึงต้องเข้ารหัสใหม่ (โหมดเร็วของ ffmpeg ใช้ได้เฉพาะไฟล์ที่พารามิเตอร์ตรงกันทั้งหมด)"
                )
        else:
            log("[หมายเหตุ] ไม่พบ ffmpeg ในเครื่อง จะใช้วิธีเข้ารหัสใหม่ทีละเฟรมแทน")

    return _merge_videos_opencv(video_paths, output_path, log, cancel_event, progress_callback)


def _merge_videos_opencv(video_paths, output_path, log, cancel_event, progress_callback):
    """ต่อวิดีโอแบบเข้ารหัสใหม่ทีละเฟรมด้วย OpenCV ใช้ fps/ขนาดของวิดีโอไฟล์แรกเป็นมาตรฐาน
    วิดีโอไฟล์อื่นที่ขนาดไม่ตรงจะถูกย่อ/ขยายให้พอดี คืนค่า True/False ว่าสำเร็จหรือไม่"""
    import cv2

    # เปิดไฟล์แรกเพื่อดึง fps/ขนาดมาตรฐาน
    first_info = probe_video_info(video_paths[0])
    if first_info is None:
        log(f"[ERROR] เปิดวิดีโอไม่ได้: {video_paths[0]}")
        return False

    cap0 = _open_video_capture(video_paths[0])
    width = int(cap0.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap0.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap0.release()
    fps = first_info["fps"]
    target_size = (width, height)

    # รวมจำนวนเฟรมทั้งหมดของทุกไฟล์ ไว้คำนวณ % ความคืบหน้ารวม
    infos = [first_info]
    for p in video_paths[1:]:
        info = probe_video_info(p)
        if info is None:
            log(f"[ERROR] เปิดวิดีโอไม่ได้: {p}")
            return False
        infos.append(info)
    total_frames_all = sum(i["total_frames"] for i in infos)

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer, actual_path = _open_video_writer(output_path, fourcc, fps, target_size)
    if not writer.isOpened():
        log(f"[ERROR] สร้างไฟล์วิดีโอปลายทางไม่ได้: {output_path}")
        return False

    written_total = 0
    cancelled = False
    for idx, (path, info) in enumerate(zip(video_paths, infos), start=1):
        if cancel_event is not None and cancel_event.is_set():
            cancelled = True
            break
        log(f"[INFO] ({idx}/{len(video_paths)}) กำลังต่อ: {path.name}")
        cap = _open_video_capture(path)
        if not cap.isOpened():
            log(f"[WARN] ข้ามไฟล์ที่เปิดไม่ได้: {path.name}")
            continue

        this_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        this_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        needs_resize = (this_w, this_h) != target_size
        if needs_resize:
            log(f"[หมายเหตุ] {path.name} ขนาด {this_w}x{this_h} ไม่ตรงกับไฟล์แรก ({width}x{height}) — จะปรับขนาดให้อัตโนมัติ")

        while True:
            if cancel_event is not None and cancel_event.is_set():
                cancelled = True
                break
            ret, frame = cap.read()
            if not ret:
                break
            if needs_resize:
                frame = cv2.resize(frame, target_size, interpolation=cv2.INTER_AREA)
            writer.write(frame)
            written_total += 1
            if progress_callback is not None and total_frames_all > 0:
                step = max(1, total_frames_all // 200)
                if written_total % step == 0 or written_total == total_frames_all:
                    progress_callback(written_total, total_frames_all)
        cap.release()
        if cancelled:
            break

    writer.release()

    if cancelled:
        log(f"[ยกเลิก] หยุดกลางคัน — ต่อไปแล้ว {written_total} เฟรม")
        return False

    if written_total <= 0:
        log("[ERROR] ไม่ได้เฟรมเลย ไฟล์ผลลัพธ์อาจไม่สมบูรณ์")
        return False

    log(f"[DONE] ต่อวิดีโอสำเร็จ {len(video_paths)} ไฟล์ รวม {written_total} เฟรม -> {actual_path}")
    return True


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}


def _read_image_safe(path):
    """อ่านภาพแบบรองรับ path ภาษาไทย/ยูนิโค้ด (ไม่ใช้ cv2.imread ตรงๆ เพราะมีปัญหากับ
    path ที่ไม่ใช่ ASCII บน Windows เหมือนกับที่เจอตอนเขียนไฟล์) คืนค่า numpy array หรือ None"""
    import cv2
    import numpy as np

    try:
        data = np.fromfile(str(path), dtype=np.uint8)
        if data.size == 0:
            return None
        return cv2.imdecode(data, cv2.IMREAD_COLOR)
    except Exception:
        return None


def images_to_video(image_paths, output_path, fps=25.0, log=print, cancel_event=None, progress_callback=None):
    """รวมภาพหลายไฟล์เป็นวิดีโอไฟล์เดียว เรียงตามลำดับที่ให้มา
    ใช้ขนาดของภาพแรกเป็นมาตรฐาน ภาพอื่นที่ขนาดไม่ตรงจะถูกย่อ/ขยายให้พอดี คืนค่า True/False"""
    import cv2

    image_paths = [Path(p) for p in image_paths]
    if len(image_paths) < 1:
        log("[ERROR] ต้องเลือกภาพอย่างน้อย 1 ภาพ")
        return False
    if fps is None or fps <= 0:
        log("[ERROR] FPS ต้องมากกว่า 0")
        return False

    first_img = _read_image_safe(image_paths[0])
    if first_img is None:
        log(f"[ERROR] เปิดภาพไม่ได้: {image_paths[0]}")
        return False

    h, w = first_img.shape[:2]
    target_size = (w, h)

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer, actual_path = _open_video_writer(output_path, fourcc, fps, target_size)
    if not writer.isOpened():
        log(f"[ERROR] สร้างไฟล์วิดีโอปลายทางไม่ได้: {output_path}")
        return False

    total = len(image_paths)
    written = 0
    cancelled = False
    log(f"[INFO] กำลังรวม {total} ภาพเป็นวิดีโอ ที่ {fps} FPS (ขนาด {w}x{h})...")

    for idx, img_path in enumerate(image_paths):
        if cancel_event is not None and cancel_event.is_set():
            cancelled = True
            log(f"[ยกเลิก] หยุดกลางคัน — รวมไปแล้ว {written} ภาพ")
            break

        img = _read_image_safe(img_path)
        if img is None:
            log(f"[WARN] ข้ามภาพที่เปิดไม่ได้: {img_path.name}")
            continue
        if img.shape[1] != w or img.shape[0] != h:
            img = cv2.resize(img, target_size, interpolation=cv2.INTER_AREA)
        writer.write(img)
        written += 1

        if progress_callback is not None:
            step = max(1, total // 200)
            if written % step == 0 or written == total:
                progress_callback(written, total)

    writer.release()

    if cancelled:
        return False

    if written <= 0:
        log("[ERROR] ไม่ได้ภาพเลย ไฟล์ผลลัพธ์อาจไม่สมบูรณ์")
        return False

    log(f"[DONE] รวมภาพเป็นวิดีโอสำเร็จ {written} ภาพ (~{written / fps:.1f} วินาที) -> {actual_path}")
    return True


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def build_arg_parser():
    p = argparse.ArgumentParser(
        description="แตกเฟรมภาพจากวิดีโอ",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("-i", "--input", help="ไฟล์วิดีโอ หรือ โฟลเดอร์ที่มีวิดีโอหลายไฟล์")
    p.add_argument("-o", "--output", default="output_frames", help="โฟลเดอร์ปลายทางสำหรับเก็บภาพ (ค่าเริ่มต้น: output_frames)")
    rate = p.add_mutually_exclusive_group()
    rate.add_argument("--fps", type=float, help="จำนวนภาพที่ต้องการต่อวินาที เช่น 1, 2, 0.5")
    rate.add_argument("--interval", type=int, help="ดึงภาพทุกๆ N เฟรม (แทนการใช้ --fps)")
    p.add_argument("--start", help="เวลาเริ่มต้นในวิดีโอ รูปแบบ HH:MM:SS หรือวินาที")
    p.add_argument("--end", help="เวลาสิ้นสุดในวิดีโอ รูปแบบ HH:MM:SS หรือวินาที")
    p.add_argument("--format", default="jpg", choices=["jpg", "jpeg", "png"], help="นามสกุลไฟล์ภาพ (ค่าเริ่มต้น: jpg)")
    p.add_argument("--quality", type=int, default=95, help="คุณภาพ JPEG 1-100 (ค่าเริ่มต้น: 95)")
    p.add_argument("--resize", help="ย่อขนาดภาพ เช่น 1280x720")
    p.add_argument("--prefix", help="คำนำหน้าชื่อไฟล์ภาพ (ค่าเริ่มต้น: ใช้ชื่อไฟล์วิดีโอ)")
    p.add_argument(
        "--no-parallel", action="store_true",
        help="ปิดการประมวลผลหลายวิดีโอพร้อมกัน (ปกติจะเปิดอัตโนมัติเมื่อเลือกทั้งโฟลเดอร์)",
    )
    p.add_argument("--dedup", action="store_true", help="ข้ามภาพที่ซ้ำ/คล้ายกับภาพล่าสุดที่บันทึกไปมากเกินไป")
    p.add_argument(
        "--dedup-level", default="medium", choices=["low", "medium", "high"],
        help="ความเข้มการกรองภาพซ้ำเมื่อเปิด --dedup (ค่าเริ่มต้น: medium)",
    )
    p.add_argument("--gui", action="store_true", help="เปิดหน้าต่างโปรแกรม (GUI)")
    return p


def run_cli(args):
    if not args.input:
        print("[ERROR] ต้องระบุ -i/--input (ไฟล์วิดีโอหรือโฟลเดอร์)")
        sys.exit(1)

    try:
        start_sec = parse_timestamp(args.start)
        end_sec = parse_timestamp(args.end)
        resize = parse_resize(args.resize)
    except ValueError as e:
        print(f"[ERROR] {e}")
        sys.exit(1)

    last_printed = {"pct": -10}

    def cli_progress(done, total):
        pct = int(done / total * 100) if total else 0
        if pct - last_printed["pct"] >= 10 or pct >= 100:
            print(f"[ความคืบหน้า] {pct}%")
            last_printed["pct"] = pct

    process_input(
        args.input,
        args.output,
        fps=args.fps,
        interval_frames=args.interval,
        start_sec=start_sec,
        end_sec=end_sec,
        img_format=args.format,
        quality=args.quality,
        resize=resize,
        prefix=args.prefix,
        progress_callback=cli_progress,
        parallel=not args.no_parallel,
        dedup_enabled=args.dedup,
        dedup_threshold=DEDUP_LEVELS.get(args.dedup_level, 1.5),
    )


# --------------------------------------------------------------------------
# GUI (tkinter — มากับ Python อยู่แล้ว ไม่ต้องติดตั้งเพิ่ม)
# --------------------------------------------------------------------------

def launch_gui(parent=None):
    """เปิด Multi Video Tool — ถ้าไม่ส่ง parent มา จะสร้างหน้าต่างของตัวเอง (พฤติกรรม
    เดิมตอนรันเป็นสคริปต์เดี่ยว) ถ้าส่ง parent มา (เช่น จาก PK Studio) จะสร้างเป็น
    ttk.Frame ฝังอยู่ใน parent นั้นแทน แล้ว return ตัว Frame กลับไปให้ผู้เรียก pack()
    เอง — โค้ดภายในฟังก์ชันทั้งหมด (2500+ บรรทัด) ใช้ตัวแปร root แค่ในลักษณะ
    .pack()/.after() ซึ่งทำงานเหมือนกันทั้งบน tk.Tk() และ ttk.Frame จึงไม่ต้องแก้
    โค้ดส่วนกลางของฟังก์ชันเลยแม้แต่บรรทัดเดียว"""
    import threading
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk, simpledialog

    standalone = parent is None
    if standalone:
        root = tk.Tk()
        root.title("Multi Video Tool")
        root.geometry("780x760")
        root.minsize(680, 420)
        root.resizable(True, True)
    else:
        root = ttk.Frame(parent)

    pad = {"padx": 10, "pady": 4}

    def make_scrollable_tab(parent):
        """สร้างพื้นที่เลื่อนได้ (scrollable) + ที่ว่างสำหรับปุ่มด้านล่างสุด ไว้ในแท็บใดๆ ก็ได้
        คืนค่า (content_frame, button_holder_frame) — ใส่เนื้อหาลง content_frame และปุ่มลง button_holder_frame"""
        button_holder = ttk.Frame(parent)
        button_holder.pack(side="bottom", fill="x", pady=8)

        canvas_frame = tk.Frame(parent)
        canvas_frame.pack(side="top", fill="both", expand=True)

        canvas = tk.Canvas(canvas_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
        content_frame = ttk.Frame(canvas)

        content_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        content_window = canvas.create_window((0, 0), window=content_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        def _resize(event):
            canvas.itemconfig(content_window, width=event.width)

        canvas.bind("<Configure>", _resize)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def _on_wheel(event):
            if getattr(event, "num", None) == 4:
                canvas.yview_scroll(-1, "units")
            elif getattr(event, "num", None) == 5:
                canvas.yview_scroll(1, "units")
            else:
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        # bind เฉพาะตอนเมาส์อยู่เหนือ canvas นี้เท่านั้น (ไม่ให้แย่งการเลื่อนของแท็บอื่น)
        canvas.bind("<Enter>", lambda e: (canvas.bind_all("<MouseWheel>", _on_wheel), canvas.bind_all("<Button-4>", _on_wheel), canvas.bind_all("<Button-5>", _on_wheel)))
        canvas.bind("<Leave>", lambda e: (canvas.unbind_all("<MouseWheel>"), canvas.unbind_all("<Button-4>"), canvas.unbind_all("<Button-5>")))

        return content_frame, button_holder

    # --- แท็บสำหรับแต่ละฟังก์ชัน ---
    notebook = ttk.Notebook(root)
    notebook.pack(side="top", fill="both", expand=True)

    tab_extract = ttk.Frame(notebook)
    notebook.add(tab_extract, text="1. แตกเฟรม")

    content, run_btn_holder = make_scrollable_tab(tab_extract)

    extract_queue = []  # รายการวิดีโอที่จะแตกเฟรม แต่ละตัวเป็น dict {"path", "start", "end", "info", "preview_frame"}
    output_var = tk.StringVar(value=str(Path.cwd() / "output_frames"))
    mode_var = tk.StringVar(value="fps")
    rate_var = tk.StringVar(value="1")
    format_var = tk.StringVar(value="jpg")
    resize_var = tk.StringVar()
    prefix_var = tk.StringVar()
    dedup_var = tk.BooleanVar(value=False)
    dedup_level_var = tk.StringVar(value="medium")
    clip_start_var = tk.StringVar()
    clip_end_var = tk.StringVar()
    clip_info_var = tk.StringVar(value="(เลือกคลิปในรายการด้านบนเพื่อตั้งค่าช่วงเวลาเฉพาะคลิปนั้น)")
    estimate_total_var = tk.StringVar(value="-")

    selected_clip_holder = {"idx": None}

    # --- 1) รายการวิดีโอ ---
    frm_in = ttk.LabelFrame(content, text="1) รายการวิดีโอ (จะแตกเฟรมทีละคลิปตามลำดับบนลงล่าง)")
    frm_in.pack(fill="x", **pad)

    queue_listbox_frame = ttk.Frame(frm_in)
    queue_listbox_frame.pack(fill="x", padx=6, pady=6)
    queue_listbox = tk.Listbox(queue_listbox_frame, height=6, selectmode="extended")
    queue_listbox.pack(side="left", fill="both", expand=True)
    queue_scrollbar = ttk.Scrollbar(queue_listbox_frame, orient="vertical", command=queue_listbox.yview)
    queue_scrollbar.pack(side="left", fill="y")
    queue_listbox.configure(yscrollcommand=queue_scrollbar.set)

    def queue_refresh_listbox():
        queue_listbox.delete(0, "end")
        for i, item in enumerate(extract_queue, start=1):
            info = item.get("info")
            dur_txt = format_hms(info["duration_sec"]) if info else "กำลังอ่าน..."
            trim_txt = ""
            if item.get("start") or item.get("end"):
                trim_txt = f"  [ตัด {item.get('start') or '0:00'}–{item.get('end') or 'จบคลิป'}]"
            queue_listbox.insert("end", f"{i}. {Path(item['path']).name}  ({dur_txt}){trim_txt}")
        queue_count_var.set(f"ทั้งหมด {len(extract_queue)} วิดีโอ")
        schedule_estimate_update()

    def probe_queue_items(items):
        """อ่านข้อมูล (fps/ความยาว) + เฟรมตัวอย่าง ของวิดีโอที่เพิ่งเพิ่มเข้ามา ทำงานเบื้องหลัง"""
        def worker():
            for item in items:
                if item.get("info") is not None:
                    continue
                info = probe_video_info(item["path"])
                item["info"] = info
                frame = None
                if info and info["total_frames"] > 0:
                    try:
                        import cv2

                        cap = _open_video_capture(item["path"])
                        if cap.isOpened():
                            mid_frame = int(info["total_frames"] * 0.3)
                            cap.set(cv2.CAP_PROP_POS_FRAMES, mid_frame)
                            ret, f = cap.read()
                            if ret:
                                frame = f
                            cap.release()
                    except Exception:
                        frame = None
                item["preview_frame"] = frame

            def apply():
                queue_refresh_listbox()
                on_queue_select()

            root.after(0, apply)

        threading.Thread(target=worker, daemon=True).start()

    def queue_add_files():
        paths = filedialog.askopenfilenames(
            title="เลือกไฟล์วิดีโอ (เลือกได้หลายไฟล์)",
            filetypes=[("Video files", "*.mp4 *.avi *.mov *.mkv *.wmv *.flv *.m4v *.ts"), ("All files", "*.*")],
        )
        if not paths:
            return
        new_items = [{"path": p, "start": "", "end": "", "info": None, "preview_frame": None} for p in paths]
        extract_queue.extend(new_items)
        queue_refresh_listbox()
        probe_queue_items(new_items)

    def queue_add_folder():
        folder = filedialog.askdirectory(title="เลือกโฟลเดอร์ที่มีวิดีโอหลายไฟล์")
        if not folder:
            return
        found = sorted(p for p in Path(folder).iterdir() if p.suffix.lower() in VIDEO_EXTENSIONS)
        if not found:
            messagebox.showinfo("ไม่พบวิดีโอ", "ไม่พบไฟล์วิดีโอในโฟลเดอร์ที่เลือก")
            return
        new_items = [{"path": str(p), "start": "", "end": "", "info": None, "preview_frame": None} for p in found]
        extract_queue.extend(new_items)
        queue_refresh_listbox()
        probe_queue_items(new_items)

    def queue_remove_selected():
        sel = list(queue_listbox.curselection())
        for idx in reversed(sel):
            del extract_queue[idx]
        selected_clip_holder["idx"] = None
        queue_refresh_listbox()
        on_queue_select()

    def queue_move_up():
        sel = list(queue_listbox.curselection())
        if not sel or sel[0] == 0:
            return
        for idx in sel:
            extract_queue[idx - 1], extract_queue[idx] = extract_queue[idx], extract_queue[idx - 1]
        queue_refresh_listbox()
        for idx in sel:
            queue_listbox.selection_set(idx - 1)
        on_queue_select()

    def queue_move_down():
        sel = list(queue_listbox.curselection())
        if not sel or sel[-1] == len(extract_queue) - 1:
            return
        for idx in reversed(sel):
            extract_queue[idx + 1], extract_queue[idx] = extract_queue[idx], extract_queue[idx + 1]
        queue_refresh_listbox()
        for idx in sel:
            queue_listbox.selection_set(idx + 1)
        on_queue_select()

    def queue_clear_all():
        extract_queue.clear()
        selected_clip_holder["idx"] = None
        queue_refresh_listbox()
        on_queue_select()

    queue_btn_row = ttk.Frame(frm_in)
    queue_btn_row.pack(fill="x", padx=6, pady=(0, 6))
    ttk.Button(queue_btn_row, text="+ เพิ่มวิดีโอ...", command=queue_add_files).pack(side="left", padx=(0, 4))
    ttk.Button(queue_btn_row, text="+ เพิ่มทั้งโฟลเดอร์...", command=queue_add_folder).pack(side="left", padx=4)
    ttk.Button(queue_btn_row, text="- ลบที่เลือก", command=queue_remove_selected).pack(side="left", padx=4)
    ttk.Button(queue_btn_row, text="▲ เลื่อนขึ้น", command=queue_move_up).pack(side="left", padx=4)
    ttk.Button(queue_btn_row, text="▼ เลื่อนลง", command=queue_move_down).pack(side="left", padx=4)
    ttk.Button(queue_btn_row, text="ล้างทั้งหมด", command=queue_clear_all).pack(side="left", padx=4)

    queue_count_var = tk.StringVar(value="ทั้งหมด 0 วิดีโอ")
    ttk.Label(frm_in, textvariable=queue_count_var).pack(anchor="w", padx=6, pady=(0, 6))

    # --- 2) ตัดช่วงเวลาเฉพาะคลิปที่เลือก ---
    frm_trim = ttk.LabelFrame(content, text="2) ตัดช่วงเวลาเฉพาะคลิปที่เลือกในรายการ (ไม่บังคับ, รูปแบบ HH:MM:SS)")
    frm_trim.pack(fill="x", **pad)

    def on_queue_select(event=None):
        sel = queue_listbox.curselection()
        if len(sel) != 1:
            selected_clip_holder["idx"] = None
            clip_info_var.set("(เลือกคลิปเดียวในรายการด้านบนเพื่อตั้งค่าช่วงเวลาเฉพาะคลิปนั้น)")
            clip_start_var.set("")
            clip_end_var.set("")
            return
        idx = sel[0]
        selected_clip_holder["idx"] = idx
        item = extract_queue[idx]
        clip_start_var.set(item.get("start", ""))
        clip_end_var.set(item.get("end", ""))
        info = item.get("info")
        if info:
            clip_info_var.set(
                f"{Path(item['path']).name}  —  ความยาว: {format_hms(info['duration_sec'])}  |  "
                f"{info['fps']:.1f} FPS  |  {info['total_frames']} เฟรม"
            )
        else:
            clip_info_var.set(f"{Path(item['path']).name}  —  กำลังอ่านข้อมูล...")

    queue_listbox.bind("<<ListboxSelect>>", on_queue_select)

    clip_trim_debounce_holder = {"id": None}

    def save_clip_trim(*_args):
        idx = selected_clip_holder["idx"]
        if idx is None or idx >= len(extract_queue):
            return
        extract_queue[idx]["start"] = clip_start_var.get()
        extract_queue[idx]["end"] = clip_end_var.get()

        def _apply():
            queue_refresh_listbox()
            if idx < len(extract_queue):
                queue_listbox.selection_set(idx)

        if clip_trim_debounce_holder["id"] is not None:
            try:
                root.after_cancel(clip_trim_debounce_holder["id"])
            except Exception:
                pass
        clip_trim_debounce_holder["id"] = root.after(300, _apply)

    def clip_set_start_beginning():
        clip_start_var.set("00:00:00")

    def clip_set_end_finish():
        idx = selected_clip_holder["idx"]
        if idx is None:
            messagebox.showinfo("ท้ายคลิป", "กรุณาเลือกคลิปในรายการด้านบนก่อน")
            return
        info = extract_queue[idx].get("info")
        if info is not None:
            clip_end_var.set(format_hms(info["duration_sec"]))
        else:
            messagebox.showinfo("ท้ายคลิป", "ยังไม่ทราบความยาววิดีโอ (กำลังอ่านข้อมูลอยู่ ลองอีกครั้งสักครู่)")

    def clip_select_whole():
        clip_set_start_beginning()
        clip_set_end_finish()

    ttk.Label(frm_trim, text="เริ่ม:").grid(row=0, column=0, padx=(6, 2), pady=4)
    ttk.Entry(frm_trim, textvariable=clip_start_var, width=10).grid(row=0, column=1)
    ttk.Button(frm_trim, text="⏮ ต้นคลิป", width=10, command=clip_set_start_beginning).grid(row=0, column=2, padx=4)

    ttk.Label(frm_trim, text="สิ้นสุด:").grid(row=0, column=3, padx=(12, 2))
    ttk.Entry(frm_trim, textvariable=clip_end_var, width=10).grid(row=0, column=4)
    ttk.Button(frm_trim, text="ท้ายคลิป ⏭", width=10, command=clip_set_end_finish).grid(row=0, column=5, padx=4)

    ttk.Button(frm_trim, text="ทั้งคลิป (ต้น-จบ)", command=clip_select_whole).grid(row=0, column=6, padx=(12, 6))
    ttk.Label(frm_trim, textvariable=clip_info_var).grid(row=1, column=0, columnspan=7, padx=6, pady=(4, 6), sticky="w")

    clip_start_var.trace_add("write", save_clip_trim)
    clip_end_var.trace_add("write", save_clip_trim)

    # --- 3) โฟลเดอร์ปลายทาง ---
    frm_out = ttk.LabelFrame(content, text="3) โฟลเดอร์ปลายทาง")
    frm_out.pack(fill="x", **pad)
    ttk.Entry(frm_out, textvariable=output_var, width=45).pack(side="left", fill="x", expand=True, padx=6, pady=6)

    def pick_output():
        path = filedialog.askdirectory(title="เลือกโฟลเดอร์ปลายทาง")
        if path:
            output_var.set(path)

    def create_named_folder():
        name = simpledialog.askstring(
            "สร้างโฟลเดอร์ใหม่",
            "ตั้งชื่อโฟลเดอร์ใหม่ (จะสร้างไว้ใต้โฟลเดอร์ปลายทางปัจจุบัน):",
            parent=root,
        )
        if not name or not name.strip():
            return
        new_path = Path(output_var.get()) / name.strip()
        try:
            new_path.mkdir(parents=True, exist_ok=True)
            output_var.set(str(new_path))
        except Exception as e:
            messagebox.showerror("ผิดพลาด", f"สร้างโฟลเดอร์ไม่สำเร็จ: {e}")

    ttk.Button(frm_out, text="เลือกโฟลเดอร์...", command=pick_output).pack(side="left", padx=2)
    ttk.Button(frm_out, text="+ สร้างโฟลเดอร์ใหม่...", command=create_named_folder).pack(side="left", padx=2)

    # --- แถวตั้งค่าอัตราการดึงเฟรม ---
    frm_rate = ttk.LabelFrame(content, text="4) อัตราการดึงเฟรม (ใช้ร่วมกันทุกคลิปในรายการ)")
    frm_rate.pack(fill="x", **pad)
    ttk.Radiobutton(frm_rate, text="ภาพต่อวินาที (FPS)", variable=mode_var, value="fps").grid(row=0, column=0, sticky="w", padx=6, pady=4)
    ttk.Radiobutton(frm_rate, text="ทุกๆ N เฟรม", variable=mode_var, value="interval").grid(row=1, column=0, sticky="w", padx=6, pady=4)
    ttk.Entry(frm_rate, textvariable=rate_var, width=10).grid(row=0, column=1, rowspan=2, padx=6)
    ttk.Label(frm_rate, text="(ปล่อยว่าง/ใส่ 0 = ดึงทุกเฟรม)").grid(row=0, column=2, rowspan=2, sticky="w")

    # --- แถวอื่นๆ ---
    frm_misc = ttk.LabelFrame(content, text="5) ตัวเลือกอื่นๆ (ใช้ร่วมกันทุกคลิปในรายการ)")
    frm_misc.pack(fill="x", **pad)
    ttk.Label(frm_misc, text="นามสกุลภาพ:").grid(row=0, column=0, padx=6, pady=4, sticky="w")
    ttk.Combobox(frm_misc, textvariable=format_var, values=["jpg", "png"], width=8, state="readonly").grid(row=0, column=1)
    ttk.Label(frm_misc, text="ย่อขนาด (WxH):").grid(row=0, column=2, padx=6, sticky="w")
    ttk.Entry(frm_misc, textvariable=resize_var, width=12).grid(row=0, column=3)
    ttk.Label(frm_misc, text="คำนำหน้าชื่อไฟล์:").grid(row=1, column=0, padx=6, pady=4, sticky="w")
    ttk.Entry(frm_misc, textvariable=prefix_var, width=20).grid(row=1, column=1, columnspan=2, sticky="w")

    dedup_level_frame = ttk.Frame(frm_misc)

    def _toggle_dedup_level_frame():
        if dedup_var.get():
            dedup_level_frame.grid(row=3, column=0, columnspan=3, padx=(24, 6), pady=(0, 6), sticky="w")
        else:
            dedup_level_frame.grid_forget()
        schedule_estimate_update()

    ttk.Checkbutton(
        frm_misc, text="ข้ามภาพที่ซ้ำ/คล้ายกันเกินไป (ลดภาพซ้ำ เหมาะกับเตรียมข้อมูลไป label เช่น Roboflow)",
        variable=dedup_var, command=_toggle_dedup_level_frame,
    ).grid(row=2, column=0, columnspan=3, padx=6, pady=(4, 4), sticky="w")

    dedup_custom_var = tk.StringVar(value="1.5")

    def get_dedup_threshold():
        if dedup_level_var.get() == "custom":
            try:
                return float(dedup_custom_var.get())
            except ValueError:
                return DEDUP_LEVELS["medium"]
        return DEDUP_LEVELS.get(dedup_level_var.get(), DEDUP_LEVELS["medium"])

    ttk.Label(dedup_level_frame, text="ความเข้มการกรอง:").pack(side="left", padx=(0, 6))
    ttk.Radiobutton(
        dedup_level_frame, text="น้อย (เก็บภาพเยอะ)", variable=dedup_level_var, value="low",
        command=lambda: schedule_estimate_update(),
    ).pack(side="left", padx=4)
    ttk.Radiobutton(
        dedup_level_frame, text="ปานกลาง", variable=dedup_level_var, value="medium",
        command=lambda: schedule_estimate_update(),
    ).pack(side="left", padx=4)
    ttk.Radiobutton(
        dedup_level_frame, text="มาก (เก็บภาพน้อยลงชัดเจน)", variable=dedup_level_var, value="high",
        command=lambda: schedule_estimate_update(),
    ).pack(side="left", padx=4)
    ttk.Radiobutton(
        dedup_level_frame, text="กำหนดเอง (%):", variable=dedup_level_var, value="custom",
        command=lambda: schedule_estimate_update(),
    ).pack(side="left", padx=(4, 2))
    ttk.Entry(dedup_level_frame, textvariable=dedup_custom_var, width=6).pack(side="left")

    # --- ประมาณการ ---
    frm_estimate = ttk.LabelFrame(content, text="6) ประมาณการ")
    frm_estimate.pack(fill="x", **pad)
    estimate_label = ttk.Label(frm_estimate, textvariable=estimate_total_var, font=("Segoe UI", 12, "bold"), wraplength=700)
    estimate_label.pack(anchor="w", padx=10, pady=(10, 4))
    estimate_detail_box = tk.Text(frm_estimate, height=5, wrap="word", state="disabled")
    estimate_detail_box.pack(fill="x", padx=10, pady=(0, 10))

    def update_preview_and_estimate():
        """คำนวณจำนวนภาพ+ขนาดไฟล์โดยประมาณของทุกคลิปในรายการ แสดงทั้งรายคลิปและรวมทั้งหมด"""
        if not extract_queue:
            estimate_total_var.set("-")
            estimate_detail_box.configure(state="normal")
            estimate_detail_box.delete("1.0", "end")
            estimate_detail_box.configure(state="disabled")
            return

        try:
            rate = float(rate_var.get()) if rate_var.get().strip() else None
        except ValueError:
            estimate_total_var.set("(ค่าอัตราดึงเฟรมไม่ถูกต้อง)")
            estimate_label.configure(foreground="red")
            return
        fps_val = rate if mode_var.get() == "fps" and rate else None
        interval_val = int(rate) if mode_var.get() == "interval" and rate else None

        try:
            resize = parse_resize(resize_var.get()) if resize_var.get().strip() else None
        except ValueError:
            estimate_total_var.set("(รูปแบบขนาดย่อไม่ถูกต้อง เช่น 1280x720)")
            estimate_label.configure(foreground="red")
            return

        lines = []
        total_count = 0
        total_bytes = 0
        any_bytes_unknown = False

        for item in extract_queue:
            name = Path(item["path"]).name
            info = item.get("info")
            if info is None:
                lines.append(f"• {name}: กำลังคำนวณ...")
                continue
            try:
                start_sec = parse_timestamp(item.get("start", ""))
                end_sec = parse_timestamp(item.get("end", ""))
            except ValueError:
                lines.append(f"• {name}: (ช่วงเวลาที่ตั้งไว้ไม่ถูกต้อง)")
                continue

            count = estimate_extraction(
                info["fps"], info["total_frames"], start_sec, end_sec, fps=fps_val, interval_frames=interval_val
            )
            total_count += count

            per_frame_bytes = None
            frame = item.get("preview_frame")
            if frame is not None:
                try:
                    import cv2

                    f = cv2.resize(frame, resize, interpolation=cv2.INTER_AREA) if resize else frame
                    ext = f".{format_var.get()}"
                    params = [cv2.IMWRITE_JPEG_QUALITY, 95] if format_var.get().lower() in ("jpg", "jpeg") else []
                    ok, buf = cv2.imencode(ext, f, params)
                    if ok:
                        per_frame_bytes = len(buf.tobytes())
                except Exception:
                    per_frame_bytes = None

            if per_frame_bytes is not None:
                clip_bytes = count * per_frame_bytes
                total_bytes += clip_bytes
                lines.append(f"• {name}: ~{count:,} ภาพ (~{format_size(clip_bytes)})")
            else:
                any_bytes_unknown = True
                lines.append(f"• {name}: ~{count:,} ภาพ")

        dedup_note = "  (ค่าสูงสุด — ถ้าเปิดข้ามภาพซ้ำ จำนวนจริงจะน้อยกว่านี้)" if dedup_var.get() else ""
        size_text = format_size(total_bytes) + ("+" if any_bytes_unknown else "")
        total_text = f"รวมทั้งหมด ~{total_count:,} ภาพ (~{size_text}) จาก {len(extract_queue)} วิดีโอ{dedup_note}"
        if total_count > 3000:
            total_text += "  ⚠ ภาพเยอะมาก ลองลด FPS หรือเพิ่มค่า interval"
            estimate_label.configure(foreground="dark orange")
        else:
            estimate_label.configure(foreground="dark green")
        estimate_total_var.set(total_text)

        estimate_detail_box.configure(state="normal")
        estimate_detail_box.delete("1.0", "end")
        estimate_detail_box.insert("1.0", "\n".join(lines))
        estimate_detail_box.configure(state="disabled")

    debounce_holder = {"id": None}

    def schedule_estimate_update(*_args):
        if debounce_holder["id"] is not None:
            try:
                root.after_cancel(debounce_holder["id"])
            except Exception:
                pass
        debounce_holder["id"] = root.after(350, update_preview_and_estimate)

    for _var in (rate_var, resize_var):
        _var.trace_add("write", schedule_estimate_update)
    mode_var.trace_add("write", lambda *_: update_preview_and_estimate())
    format_var.trace_add("write", lambda *_: update_preview_and_estimate())

    # --- แถบความคืบหน้า ---
    frm_progress = ttk.LabelFrame(content, text="ความคืบหน้า")
    frm_progress.pack(fill="x", **pad)
    current_video_var = tk.StringVar(value="")
    percent_var = tk.StringVar(value="0%")
    ttk.Label(frm_progress, textvariable=current_video_var).pack(anchor="w", padx=6, pady=(4, 0))
    progress_row = ttk.Frame(frm_progress)
    progress_row.pack(fill="x", padx=6, pady=(0, 6))
    progress_bar = ttk.Progressbar(progress_row, mode="determinate", maximum=100)
    progress_bar.pack(side="left", fill="x", expand=True)
    ttk.Label(progress_row, textvariable=percent_var, width=5).pack(side="left", padx=(8, 0))

    # --- log box ---
    frm_log = ttk.LabelFrame(content, text="สถานะการทำงาน")
    frm_log.pack(fill="both", expand=True, **pad)
    log_box = tk.Text(frm_log, height=6, wrap="word", state="disabled")
    log_box.pack(fill="both", expand=True, padx=6, pady=6)

    def log(msg):
        def _do():
            log_box.configure(state="normal")
            log_box.insert("end", str(msg) + "\n")
            log_box.see("end")
            log_box.configure(state="disabled")

        root.after(0, _do)

    def update_progress(done, total):
        pct = int(done / total * 100) if total else 0

        def _do():
            progress_bar["value"] = pct
            percent_var.set(f"{pct}%")

        root.after(0, _do)

    def update_current_video(index, total_videos, name):
        def _do():
            current_video_var.set(f"วิดีโอที่ {index}/{total_videos}: {name}")
            progress_bar["value"] = 0
            percent_var.set("0%")

        root.after(0, _do)

    run_btn = None
    stop_btn = None
    cancel_event_holder = {"event": None}

    def set_running_state(running):
        run_btn.configure(state="disabled" if running else "normal")
        stop_btn.configure(state="normal" if running else "disabled")

    def run_extraction():
        if not extract_queue:
            messagebox.showerror("ผิดพลาด", "กรุณาเพิ่มวิดีโออย่างน้อย 1 ไฟล์ก่อน")
            return
        try:
            rate = float(rate_var.get()) if rate_var.get().strip() else None
            resize = parse_resize(resize_var.get()) if resize_var.get().strip() else None
        except ValueError as e:
            messagebox.showerror("รูปแบบไม่ถูกต้อง", str(e))
            return

        parsed_items = []
        for item in extract_queue:
            try:
                s = parse_timestamp(item.get("start", ""))
                e = parse_timestamp(item.get("end", ""))
            except ValueError as ex:
                messagebox.showerror("รูปแบบเวลาไม่ถูกต้อง", f"{Path(item['path']).name}: {ex}")
                return
            parsed_items.append((item["path"], s, e))

        fps = rate if mode_var.get() == "fps" and rate else None
        interval_frames = int(rate) if mode_var.get() == "interval" and rate else None

        cancel_event = threading.Event()
        cancel_event_holder["event"] = cancel_event

        set_running_state(True)
        log_box.configure(state="normal")
        log_box.delete("1.0", "end")
        log_box.configure(state="disabled")
        progress_bar["value"] = 0
        percent_var.set("0%")
        current_video_var.set("")

        def worker():
            import os as _os
            from concurrent.futures import ThreadPoolExecutor, as_completed

            n_items = len(parsed_items)
            saved_holder = {"n": 0}
            completed_holder = {"n": 0}
            progress_lock = threading.Lock()

            def do_one(idx, path, start_sec, end_sec, progress_cb):
                name = Path(path).name
                prefixed_log = (lambda msg, _n=name: log(f"[{_n}] {msg}")) if n_items > 1 else log
                sub_out = Path(output_var.get()) / Path(path).stem
                n = extract_frames(
                    path,
                    sub_out,
                    fps=fps,
                    interval_frames=interval_frames,
                    start_sec=start_sec,
                    end_sec=end_sec,
                    img_format=format_var.get(),
                    resize=resize,
                    prefix=prefix_var.get() or None,
                    log=prefixed_log,
                    cancel_event=cancel_event,
                    progress_callback=progress_cb,
                    dedup_enabled=dedup_var.get(),
                    dedup_threshold=get_dedup_threshold(),
                )
                with progress_lock:
                    saved_holder["n"] += n
                    completed_holder["n"] += 1
                return n

            try:
                # ประมวลผลหลายวิดีโอพร้อมกันด้วย thread pool เหมือนที่ใช้อยู่แล้วฝั่ง CLI/โฟลเดอร์
                # (OpenCV ปล่อย GIL ระหว่างถอดรหัส/เข้ารหัสภาพ จึงได้ความเร็วเพิ่มขึ้นจริง)
                # ถ้ามีวิดีโอแค่ไฟล์เดียว ประมวลผลตรง ๆ ไม่ต้องผ่าน thread pool ให้ยุ่งยากเปล่า ๆ
                if n_items > 1:
                    max_workers = min(4, max(1, _os.cpu_count() or 2), n_items)
                    log(f"[INFO] ประมวลผลแบบขนาน {max_workers} ไฟล์พร้อมกัน (ทั้งหมด {n_items} วิดีโอ)")
                    current_video_var.set(f"กำลังประมวลผล {n_items} วิดีโอพร้อมกัน...")

                    # คำนวณจำนวนเฟรมรวมทั้งหมดล่วงหน้า (จากข้อมูลที่ probe ไว้แล้วตอนเพิ่มเข้ารายการ)
                    # ไว้ใช้คำนวณ % ความคืบหน้ารวมของทั้งแบทช์ ให้แถบ progress ขยับต่อเนื่องสมูท
                    frame_counts = [
                        (item.get("info") or {}).get("total_frames", 0) for item in extract_queue
                    ]
                    total_frames_all = sum(frame_counts) or 1
                    progress_map = {i: 0 for i in range(n_items)}

                    def make_progress_cb(idx):
                        def cb(done, _total_this_video):
                            with progress_lock:
                                progress_map[idx] = done
                                current = sum(progress_map.values())
                            update_progress(current, total_frames_all)

                        return cb

                    with ThreadPoolExecutor(max_workers=max_workers) as executor:
                        futures = {
                            executor.submit(do_one, i, path, s, e, make_progress_cb(i)): i
                            for i, (path, s, e) in enumerate(parsed_items)
                        }
                        for future in as_completed(futures):
                            try:
                                future.result()
                            except Exception as ex:
                                log(f"[ERROR] {ex}")
                else:
                    path, start_sec, end_sec = parsed_items[0]
                    update_current_video(1, 1, Path(path).name)
                    do_one(0, path, start_sec, end_sec, update_progress)

                total_saved = saved_holder["n"]
                log(f"\n[SUMMARY] รวมทั้งหมด {total_saved} เฟรม จาก {n_items} วิดีโอ")
                if cancel_event.is_set():
                    log("\n⏹ ยกเลิกการทำงานแล้ว")
                else:
                    log("\n✅ เสร็จสิ้น! เปิดโฟลเดอร์ปลายทางเพื่อดูภาพที่แตกออกมาได้เลย")
            except Exception as e:
                log(f"\n❌ เกิดข้อผิดพลาด: {e}")
            finally:
                root.after(0, lambda: set_running_state(False))

        threading.Thread(target=worker, daemon=True).start()

    def stop_extraction():
        ev = cancel_event_holder["event"]
        if ev is not None:
            ev.set()
            stop_btn.configure(state="disabled")
            log("\n[กำลังหยุด...] รอให้เฟรมปัจจุบันเขียนเสร็จสักครู่")

    run_btn = ttk.Button(run_btn_holder, text="▶  เริ่มแตกเฟรม", command=run_extraction)
    run_btn.pack(side="left", expand=True, padx=(0, 4))
    stop_btn = ttk.Button(run_btn_holder, text="■  หยุด", command=stop_extraction, state="disabled")
    stop_btn.pack(side="left", expand=True, padx=(4, 0))

    # ============================================================
    # แท็บ 2: ตัดคลิป (Trim)
    # ============================================================
    tab_trim = ttk.Frame(notebook)
    notebook.add(tab_trim, text="2. ตัดคลิป")
    trim_content, trim_btn_holder = make_scrollable_tab(tab_trim)

    trim_input_var = tk.StringVar()
    trim_output_var = tk.StringVar()
    trim_start_var = tk.StringVar()
    trim_end_var = tk.StringVar()
    trim_duration_var = tk.StringVar(value="")
    trim_info_holder = {"info": None}

    frm_trim_in = ttk.LabelFrame(trim_content, text="1) เลือกวิดีโอที่จะตัด")
    frm_trim_in.pack(fill="x", **pad)
    frm_trim_in.columnconfigure(0, weight=1)
    ttk.Entry(frm_trim_in, textvariable=trim_input_var, width=45).grid(row=0, column=0, padx=6, pady=6, sticky="ew")

    def trim_load_info(path):
        trim_info_holder["info"] = None
        trim_duration_var.set("กำลังอ่านข้อมูลวิดีโอ...")

        def worker():
            info = probe_video_info(path)

            def apply():
                trim_info_holder["info"] = info
                if info:
                    trim_duration_var.set(
                        f"ความยาว: {format_hms(info['duration_sec'])}  |  {info['fps']:.1f} FPS  |  {info['total_frames']} เฟรม"
                    )
                else:
                    trim_duration_var.set("(อ่านข้อมูลวิดีโอไม่ได้ — ไฟล์อาจเสียหายหรือไม่ใช่วิดีโอ)")

            root.after(0, apply)

        threading.Thread(target=worker, daemon=True).start()

    def trim_pick_file():
        path = filedialog.askopenfilename(
            title="เลือกไฟล์วิดีโอที่จะตัด",
            filetypes=[("Video files", "*.mp4 *.avi *.mov *.mkv *.wmv *.flv *.m4v *.ts"), ("All files", "*.*")],
        )
        if path:
            trim_input_var.set(path)
            trim_load_info(path)
            if not trim_output_var.get().strip():
                p = Path(path)
                trim_output_var.set(str(p.with_name(p.stem + "_ตัด.mp4")))

    ttk.Button(frm_trim_in, text="ไฟล์วิดีโอ...", command=trim_pick_file).grid(row=0, column=1, padx=6)
    ttk.Label(frm_trim_in, textvariable=trim_duration_var).grid(
        row=1, column=0, columnspan=2, padx=6, pady=(0, 6), sticky="w"
    )

    frm_trim_range = ttk.LabelFrame(trim_content, text="2) ช่วงเวลาที่จะตัด (รูปแบบ HH:MM:SS ปล่อยว่าง = ทั้งคลิป)")
    frm_trim_range.pack(fill="x", **pad)

    def trim_set_start_beginning():
        trim_start_var.set("00:00:00")

    def trim_set_end_finish():
        info = trim_info_holder.get("info")
        if info is not None:
            trim_end_var.set(format_hms(info["duration_sec"]))
        else:
            messagebox.showinfo("ท้ายคลิป", "ยังไม่ทราบความยาววิดีโอ กรุณาเลือกไฟล์วิดีโอก่อน")

    def trim_select_whole():
        trim_set_start_beginning()
        trim_set_end_finish()

    ttk.Label(frm_trim_range, text="เริ่ม:").grid(row=0, column=0, padx=(6, 2), pady=6)
    ttk.Entry(frm_trim_range, textvariable=trim_start_var, width=10).grid(row=0, column=1)
    ttk.Button(frm_trim_range, text="⏮ ต้นคลิป", width=10, command=trim_set_start_beginning).grid(row=0, column=2, padx=4)
    ttk.Label(frm_trim_range, text="สิ้นสุด:").grid(row=0, column=3, padx=(12, 2))
    ttk.Entry(frm_trim_range, textvariable=trim_end_var, width=10).grid(row=0, column=4)
    ttk.Button(frm_trim_range, text="ท้ายคลิป ⏭", width=10, command=trim_set_end_finish).grid(row=0, column=5, padx=4)
    ttk.Button(frm_trim_range, text="ทั้งคลิป", command=trim_select_whole).grid(row=0, column=6, padx=(12, 6))

    frm_trim_out = ttk.LabelFrame(trim_content, text="3) ไฟล์ผลลัพธ์ (.mp4)")
    frm_trim_out.pack(fill="x", **pad)
    frm_trim_out.columnconfigure(0, weight=1)
    ttk.Entry(frm_trim_out, textvariable=trim_output_var, width=45).grid(row=0, column=0, padx=6, pady=6, sticky="ew")

    def trim_pick_output():
        path = filedialog.asksaveasfilename(
            title="บันทึกวิดีโอที่ตัดแล้วเป็น...",
            defaultextension=".mp4",
            filetypes=[("MP4 video", "*.mp4")],
            initialfile=Path(trim_output_var.get()).name if trim_output_var.get().strip() else "clip_ตัด.mp4",
        )
        if path:
            trim_output_var.set(path)

    ttk.Button(frm_trim_out, text="เลือกตำแหน่งบันทึก...", command=trim_pick_output).grid(row=0, column=1, padx=6)

    trim_mode_var = tk.StringVar(value="fast")
    frm_trim_mode = ttk.LabelFrame(trim_content, text="4) โหมดการตัด")
    frm_trim_mode.pack(fill="x", **pad)
    ttk.Radiobutton(
        frm_trim_mode, text="เร็ว (ffmpeg, ไม่เข้ารหัสใหม่ — จุดตัดอาจคลาดเคลื่อน ≤2 วิ ที่ keyframe ใกล้เคียง)",
        variable=trim_mode_var, value="fast",
    ).pack(anchor="w", padx=6, pady=(6, 2))
    ttk.Radiobutton(
        frm_trim_mode, text="แม่นยำ (เข้ารหัสใหม่ทีละเฟรม — ตัดตรงเป๊ะ แต่ช้ากว่า)",
        variable=trim_mode_var, value="accurate",
    ).pack(anchor="w", padx=6, pady=(0, 6))
    ttk.Label(
        frm_trim_mode,
        text="หมายเหตุ: ถ้าไม่มี ffmpeg ในเครื่อง จะใช้โหมดแม่นยำให้อัตโนมัติไม่ว่าจะเลือกโหมดไหน",
    ).pack(anchor="w", padx=6, pady=(0, 6))

    frm_trim_progress = ttk.LabelFrame(trim_content, text="ความคืบหน้า")
    frm_trim_progress.pack(fill="x", **pad)
    trim_percent_var = tk.StringVar(value="0%")
    trim_progress_row = ttk.Frame(frm_trim_progress)
    trim_progress_row.pack(fill="x", padx=6, pady=6)
    trim_progress_bar = ttk.Progressbar(trim_progress_row, mode="determinate", maximum=100)
    trim_progress_bar.pack(side="left", fill="x", expand=True)
    ttk.Label(trim_progress_row, textvariable=trim_percent_var, width=5).pack(side="left", padx=(8, 0))

    frm_trim_log = ttk.LabelFrame(trim_content, text="สถานะการทำงาน")
    frm_trim_log.pack(fill="both", expand=True, **pad)
    trim_log_box = tk.Text(frm_trim_log, height=6, wrap="word", state="disabled")
    trim_log_box.pack(fill="both", expand=True, padx=6, pady=6)

    def trim_log(msg):
        def _do():
            trim_log_box.configure(state="normal")
            trim_log_box.insert("end", str(msg) + "\n")
            trim_log_box.see("end")
            trim_log_box.configure(state="disabled")

        root.after(0, _do)

    def trim_update_progress(done, total):
        pct = int(done / total * 100) if total else 0

        def _do():
            trim_progress_bar["value"] = pct
            trim_percent_var.set(f"{pct}%")

        root.after(0, _do)

    trim_run_btn = None
    trim_stop_btn = None
    trim_cancel_holder = {"event": None}

    def trim_set_running(running):
        trim_run_btn.configure(state="disabled" if running else "normal")
        trim_stop_btn.configure(state="normal" if running else "disabled")

    def trim_run():
        if not trim_input_var.get().strip() or not Path(trim_input_var.get()).is_file():
            messagebox.showerror("ผิดพลาด", "กรุณาเลือกไฟล์วิดีโอที่จะตัดก่อน")
            return
        if not trim_output_var.get().strip():
            messagebox.showerror("ผิดพลาด", "กรุณาระบุตำแหน่งไฟล์ผลลัพธ์ก่อน")
            return
        try:
            start_sec = parse_timestamp(trim_start_var.get())
            end_sec = parse_timestamp(trim_end_var.get())
        except ValueError as e:
            messagebox.showerror("รูปแบบเวลาไม่ถูกต้อง", str(e))
            return
        if start_sec is None and end_sec is None:
            if not messagebox.askyesno(
                "ยืนยัน", "ไม่ได้ระบุช่วงเวลา จะเป็นการคัดลอก/เข้ารหัสทั้งคลิปใหม่ทั้งไฟล์ ต้องการดำเนินการต่อหรือไม่?"
            ):
                return

        cancel_event = threading.Event()
        trim_cancel_holder["event"] = cancel_event
        trim_set_running(True)
        trim_log_box.configure(state="normal")
        trim_log_box.delete("1.0", "end")
        trim_log_box.configure(state="disabled")
        trim_progress_bar["value"] = 0
        trim_percent_var.set("0%")

        def worker():
            try:
                ok = trim_video(
                    trim_input_var.get(),
                    trim_output_var.get(),
                    start_sec=start_sec,
                    end_sec=end_sec,
                    log=trim_log,
                    cancel_event=cancel_event,
                    progress_callback=trim_update_progress,
                    fast_mode=(trim_mode_var.get() == "fast"),
                )
                if cancel_event.is_set():
                    trim_log("\n⏹ ยกเลิกการทำงานแล้ว")
                elif ok:
                    trim_log("\n✅ เสร็จสิ้น! ตัดคลิปเรียบร้อยแล้ว")
                else:
                    trim_log("\n❌ ตัดคลิปไม่สำเร็จ ดูรายละเอียดข้อผิดพลาดด้านบน")
            except Exception as e:
                trim_log(f"\n❌ เกิดข้อผิดพลาด: {e}")
            finally:
                root.after(0, lambda: trim_set_running(False))

        threading.Thread(target=worker, daemon=True).start()

    def trim_stop():
        ev = trim_cancel_holder["event"]
        if ev is not None:
            ev.set()
            trim_stop_btn.configure(state="disabled")
            trim_log("\n[กำลังหยุด...] รอให้เฟรมปัจจุบันเขียนเสร็จสักครู่")

    trim_run_btn = ttk.Button(trim_btn_holder, text="✂  ตัดคลิป", command=trim_run)
    trim_run_btn.pack(side="left", expand=True, padx=(0, 4))
    trim_stop_btn = ttk.Button(trim_btn_holder, text="■  หยุด", command=trim_stop, state="disabled")
    trim_stop_btn.pack(side="left", expand=True, padx=(4, 0))

    # ============================================================
    # แท็บ 3: ต่อคลิป (Merge)
    # ============================================================
    tab_merge = ttk.Frame(notebook)
    notebook.add(tab_merge, text="3. ต่อคลิป")
    merge_content, merge_btn_holder = make_scrollable_tab(tab_merge)

    merge_files = []  # เก็บ path เต็มของไฟล์ตามลำดับที่จะต่อ
    merge_output_var = tk.StringVar()

    frm_merge_list = ttk.LabelFrame(merge_content, text="1) รายการวิดีโอ (จะต่อตามลำดับบนลงล่าง)")
    frm_merge_list.pack(fill="x", **pad)

    merge_listbox_frame = ttk.Frame(frm_merge_list)
    merge_listbox_frame.pack(fill="x", padx=6, pady=6)
    merge_listbox = tk.Listbox(merge_listbox_frame, height=6, selectmode="extended")
    merge_listbox.pack(side="left", fill="both", expand=True)
    merge_list_scrollbar = ttk.Scrollbar(merge_listbox_frame, orient="vertical", command=merge_listbox.yview)
    merge_list_scrollbar.pack(side="left", fill="y")
    merge_listbox.configure(yscrollcommand=merge_list_scrollbar.set)

    def merge_refresh_listbox():
        merge_listbox.delete(0, "end")
        for i, p in enumerate(merge_files, start=1):
            merge_listbox.insert("end", f"{i}. {Path(p).name}")

    def merge_add_files():
        paths = filedialog.askopenfilenames(
            title="เลือกวิดีโอที่จะต่อ (เลือกได้หลายไฟล์)",
            filetypes=[("Video files", "*.mp4 *.avi *.mov *.mkv *.wmv *.flv *.m4v *.ts"), ("All files", "*.*")],
        )
        for p in paths:
            merge_files.append(p)
        merge_refresh_listbox()

    def merge_remove_selected():
        sel = list(merge_listbox.curselection())
        for idx in reversed(sel):
            del merge_files[idx]
        merge_refresh_listbox()

    def merge_move_up():
        sel = list(merge_listbox.curselection())
        if not sel or sel[0] == 0:
            return
        for idx in sel:
            merge_files[idx - 1], merge_files[idx] = merge_files[idx], merge_files[idx - 1]
        merge_refresh_listbox()
        for idx in sel:
            merge_listbox.selection_set(idx - 1)

    def merge_move_down():
        sel = list(merge_listbox.curselection())
        if not sel or sel[-1] == len(merge_files) - 1:
            return
        for idx in reversed(sel):
            merge_files[idx + 1], merge_files[idx] = merge_files[idx], merge_files[idx + 1]
        merge_refresh_listbox()
        for idx in sel:
            merge_listbox.selection_set(idx + 1)

    def merge_clear_all():
        merge_files.clear()
        merge_refresh_listbox()

    merge_btn_row = ttk.Frame(frm_merge_list)
    merge_btn_row.pack(fill="x", padx=6, pady=(0, 6))
    ttk.Button(merge_btn_row, text="+ เพิ่มวิดีโอ...", command=merge_add_files).pack(side="left", padx=(0, 4))
    ttk.Button(merge_btn_row, text="- ลบที่เลือก", command=merge_remove_selected).pack(side="left", padx=4)
    ttk.Button(merge_btn_row, text="▲ เลื่อนขึ้น", command=merge_move_up).pack(side="left", padx=4)
    ttk.Button(merge_btn_row, text="▼ เลื่อนลง", command=merge_move_down).pack(side="left", padx=4)
    ttk.Button(merge_btn_row, text="ล้างทั้งหมด", command=merge_clear_all).pack(side="left", padx=4)

    ttk.Label(
        frm_merge_list,
        text="หมายเหตุ: ถ้าวิดีโอมีขนาด/ความละเอียดไม่เท่ากัน โปรแกรมจะปรับให้เท่ากับไฟล์แรกในรายการอัตโนมัติ",
    ).pack(anchor="w", padx=6, pady=(0, 6))

    frm_merge_out = ttk.LabelFrame(merge_content, text="2) ไฟล์ผลลัพธ์ (.mp4)")
    frm_merge_out.pack(fill="x", **pad)
    frm_merge_out.columnconfigure(0, weight=1)
    ttk.Entry(frm_merge_out, textvariable=merge_output_var, width=45).grid(row=0, column=0, padx=6, pady=6, sticky="ew")

    def merge_pick_output():
        path = filedialog.asksaveasfilename(
            title="บันทึกวิดีโอที่ต่อแล้วเป็น...",
            defaultextension=".mp4",
            filetypes=[("MP4 video", "*.mp4")],
            initialfile="clip_ต่อ.mp4",
        )
        if path:
            merge_output_var.set(path)

    ttk.Button(frm_merge_out, text="เลือกตำแหน่งบันทึก...", command=merge_pick_output).grid(row=0, column=1, padx=6)

    frm_merge_progress = ttk.LabelFrame(merge_content, text="ความคืบหน้า")
    frm_merge_progress.pack(fill="x", **pad)
    merge_current_var = tk.StringVar(value="")
    ttk.Label(frm_merge_progress, textvariable=merge_current_var).pack(anchor="w", padx=6, pady=(4, 0))
    merge_percent_var = tk.StringVar(value="0%")
    merge_progress_row = ttk.Frame(frm_merge_progress)
    merge_progress_row.pack(fill="x", padx=6, pady=(0, 6))
    merge_progress_bar = ttk.Progressbar(merge_progress_row, mode="determinate", maximum=100)
    merge_progress_bar.pack(side="left", fill="x", expand=True)
    ttk.Label(merge_progress_row, textvariable=merge_percent_var, width=5).pack(side="left", padx=(8, 0))

    frm_merge_log = ttk.LabelFrame(merge_content, text="สถานะการทำงาน")
    frm_merge_log.pack(fill="both", expand=True, **pad)
    merge_log_box = tk.Text(frm_merge_log, height=6, wrap="word", state="disabled")
    merge_log_box.pack(fill="both", expand=True, padx=6, pady=6)

    def merge_log(msg):
        def _do():
            merge_log_box.configure(state="normal")
            merge_log_box.insert("end", str(msg) + "\n")
            merge_log_box.see("end")
            merge_log_box.configure(state="disabled")

        root.after(0, _do)

    def merge_update_progress(done, total):
        pct = int(done / total * 100) if total else 0

        def _do():
            merge_progress_bar["value"] = pct
            merge_percent_var.set(f"{pct}%")

        root.after(0, _do)

    merge_run_btn = None
    merge_stop_btn = None
    merge_cancel_holder = {"event": None}

    def merge_set_running(running):
        merge_run_btn.configure(state="disabled" if running else "normal")
        merge_stop_btn.configure(state="normal" if running else "disabled")

    def merge_run():
        if len(merge_files) < 2:
            messagebox.showerror("ผิดพลาด", "กรุณาเลือกวิดีโออย่างน้อย 2 ไฟล์ถึงจะต่อได้")
            return
        if not merge_output_var.get().strip():
            messagebox.showerror("ผิดพลาด", "กรุณาระบุตำแหน่งไฟล์ผลลัพธ์ก่อน")
            return

        cancel_event = threading.Event()
        merge_cancel_holder["event"] = cancel_event
        merge_set_running(True)
        merge_log_box.configure(state="normal")
        merge_log_box.delete("1.0", "end")
        merge_log_box.configure(state="disabled")
        merge_progress_bar["value"] = 0
        merge_percent_var.set("0%")
        merge_current_var.set(f"กำลังต่อวิดีโอ {len(merge_files)} ไฟล์...")

        files_snapshot = list(merge_files)

        def worker():
            try:
                ok = merge_videos(
                    files_snapshot,
                    merge_output_var.get(),
                    log=merge_log,
                    cancel_event=cancel_event,
                    progress_callback=merge_update_progress,
                )
                if cancel_event.is_set():
                    merge_log("\n⏹ ยกเลิกการทำงานแล้ว")
                elif ok:
                    merge_log("\n✅ เสร็จสิ้น! ต่อคลิปเรียบร้อยแล้ว")
                else:
                    merge_log("\n❌ ต่อคลิปไม่สำเร็จ ดูรายละเอียดข้อผิดพลาดด้านบน")
            except Exception as e:
                merge_log(f"\n❌ เกิดข้อผิดพลาด: {e}")
            finally:
                root.after(0, lambda: merge_set_running(False))

        threading.Thread(target=worker, daemon=True).start()

    def merge_stop():
        ev = merge_cancel_holder["event"]
        if ev is not None:
            ev.set()
            merge_stop_btn.configure(state="disabled")
            merge_log("\n[กำลังหยุด...] รอให้เฟรมปัจจุบันเขียนเสร็จสักครู่")

    merge_run_btn = ttk.Button(merge_btn_holder, text="🔗  ต่อคลิป", command=merge_run)
    merge_run_btn.pack(side="left", expand=True, padx=(0, 4))
    merge_stop_btn = ttk.Button(merge_btn_holder, text="■  หยุด", command=merge_stop, state="disabled")
    merge_stop_btn.pack(side="left", expand=True, padx=(4, 0))

    # ============================================================
    # แท็บ 4: ภาพเป็นวิดีโอ (Images to Video)
    # ============================================================
    tab_i2v = ttk.Frame(notebook)
    notebook.add(tab_i2v, text="4. ภาพเป็นวิดีโอ")
    i2v_content, i2v_btn_holder = make_scrollable_tab(tab_i2v)

    i2v_files = []  # เก็บ path เต็มของภาพตามลำดับที่จะรวม
    i2v_output_var = tk.StringVar()
    i2v_fps_var = tk.StringVar(value="25")

    frm_i2v_list = ttk.LabelFrame(i2v_content, text="1) รายการภาพ (จะรวมตามลำดับบนลงล่าง)")
    frm_i2v_list.pack(fill="x", **pad)

    i2v_listbox_frame = ttk.Frame(frm_i2v_list)
    i2v_listbox_frame.pack(fill="x", padx=6, pady=6)
    i2v_listbox = tk.Listbox(i2v_listbox_frame, height=6, selectmode="extended")
    i2v_listbox.pack(side="left", fill="both", expand=True)
    i2v_list_scrollbar = ttk.Scrollbar(i2v_listbox_frame, orient="vertical", command=i2v_listbox.yview)
    i2v_list_scrollbar.pack(side="left", fill="y")
    i2v_listbox.configure(yscrollcommand=i2v_list_scrollbar.set)

    def i2v_refresh_listbox():
        i2v_listbox.delete(0, "end")
        for i, p in enumerate(i2v_files, start=1):
            i2v_listbox.insert("end", f"{i}. {Path(p).name}")
        i2v_count_var.set(f"ทั้งหมด {len(i2v_files)} ภาพ")

    def i2v_add_files():
        paths = filedialog.askopenfilenames(
            title="เลือกภาพที่จะรวม (เลือกได้หลายไฟล์)",
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp *.tif *.tiff *.webp"), ("All files", "*.*")],
        )
        for p in paths:
            i2v_files.append(p)
        i2v_refresh_listbox()

    def i2v_add_folder():
        folder = filedialog.askdirectory(title="เลือกโฟลเดอร์ที่มีภาพ (จะเรียงตามชื่อไฟล์อัตโนมัติ)")
        if not folder:
            return
        found = sorted(
            p for p in Path(folder).iterdir() if p.suffix.lower() in IMAGE_EXTENSIONS
        )
        if not found:
            messagebox.showinfo("ไม่พบภาพ", "ไม่พบไฟล์ภาพในโฟลเดอร์ที่เลือก")
            return
        for p in found:
            i2v_files.append(str(p))
        i2v_refresh_listbox()

    def i2v_remove_selected():
        sel = list(i2v_listbox.curselection())
        for idx in reversed(sel):
            del i2v_files[idx]
        i2v_refresh_listbox()

    def i2v_move_up():
        sel = list(i2v_listbox.curselection())
        if not sel or sel[0] == 0:
            return
        for idx in sel:
            i2v_files[idx - 1], i2v_files[idx] = i2v_files[idx], i2v_files[idx - 1]
        i2v_refresh_listbox()
        for idx in sel:
            i2v_listbox.selection_set(idx - 1)

    def i2v_move_down():
        sel = list(i2v_listbox.curselection())
        if not sel or sel[-1] == len(i2v_files) - 1:
            return
        for idx in reversed(sel):
            i2v_files[idx + 1], i2v_files[idx] = i2v_files[idx], i2v_files[idx + 1]
        i2v_refresh_listbox()
        for idx in sel:
            i2v_listbox.selection_set(idx + 1)

    def i2v_clear_all():
        i2v_files.clear()
        i2v_refresh_listbox()

    i2v_btn_row = ttk.Frame(frm_i2v_list)
    i2v_btn_row.pack(fill="x", padx=6, pady=(0, 6))
    ttk.Button(i2v_btn_row, text="+ เพิ่มทั้งโฟลเดอร์...", command=i2v_add_folder).pack(side="left", padx=(0, 4))
    ttk.Button(i2v_btn_row, text="+ เพิ่มภาพ...", command=i2v_add_files).pack(side="left", padx=4)
    ttk.Button(i2v_btn_row, text="- ลบที่เลือก", command=i2v_remove_selected).pack(side="left", padx=4)
    ttk.Button(i2v_btn_row, text="▲ เลื่อนขึ้น", command=i2v_move_up).pack(side="left", padx=4)
    ttk.Button(i2v_btn_row, text="▼ เลื่อนลง", command=i2v_move_down).pack(side="left", padx=4)
    ttk.Button(i2v_btn_row, text="ล้างทั้งหมด", command=i2v_clear_all).pack(side="left", padx=4)

    i2v_count_var = tk.StringVar(value="ทั้งหมด 0 ภาพ")
    ttk.Label(frm_i2v_list, textvariable=i2v_count_var).pack(anchor="w", padx=6, pady=(0, 2))
    ttk.Label(
        frm_i2v_list,
        text="หมายเหตุ: \"เพิ่มทั้งโฟลเดอร์\" จะเรียงภาพตามชื่อไฟล์ให้อัตโนมัติ (เหมาะกับภาพจากแท็บแตกเฟรม) "
        "ถ้าภาพมีขนาดไม่เท่ากัน โปรแกรมจะปรับให้เท่ากับภาพแรกในรายการอัตโนมัติ",
    ).pack(anchor="w", padx=6, pady=(0, 6))

    frm_i2v_settings = ttk.LabelFrame(i2v_content, text="2) การตั้งค่าวิดีโอ")
    frm_i2v_settings.pack(fill="x", **pad)
    ttk.Label(frm_i2v_settings, text="FPS (ภาพต่อวินาที):").grid(row=0, column=0, padx=6, pady=6, sticky="w")
    ttk.Entry(frm_i2v_settings, textvariable=i2v_fps_var, width=10).grid(row=0, column=1, sticky="w")

    frm_i2v_out = ttk.LabelFrame(i2v_content, text="3) ไฟล์ผลลัพธ์ (.mp4)")
    frm_i2v_out.pack(fill="x", **pad)
    frm_i2v_out.columnconfigure(0, weight=1)
    ttk.Entry(frm_i2v_out, textvariable=i2v_output_var, width=45).grid(row=0, column=0, padx=6, pady=6, sticky="ew")

    def i2v_pick_output():
        path = filedialog.asksaveasfilename(
            title="บันทึกวิดีโอเป็น...",
            defaultextension=".mp4",
            filetypes=[("MP4 video", "*.mp4")],
            initialfile="ภาพเป็นวิดีโอ.mp4",
        )
        if path:
            i2v_output_var.set(path)

    ttk.Button(frm_i2v_out, text="เลือกตำแหน่งบันทึก...", command=i2v_pick_output).grid(row=0, column=1, padx=6)

    frm_i2v_progress = ttk.LabelFrame(i2v_content, text="ความคืบหน้า")
    frm_i2v_progress.pack(fill="x", **pad)
    i2v_percent_var = tk.StringVar(value="0%")
    i2v_progress_row = ttk.Frame(frm_i2v_progress)
    i2v_progress_row.pack(fill="x", padx=6, pady=6)
    i2v_progress_bar = ttk.Progressbar(i2v_progress_row, mode="determinate", maximum=100)
    i2v_progress_bar.pack(side="left", fill="x", expand=True)
    ttk.Label(i2v_progress_row, textvariable=i2v_percent_var, width=5).pack(side="left", padx=(8, 0))

    frm_i2v_log = ttk.LabelFrame(i2v_content, text="สถานะการทำงาน")
    frm_i2v_log.pack(fill="both", expand=True, **pad)
    i2v_log_box = tk.Text(frm_i2v_log, height=6, wrap="word", state="disabled")
    i2v_log_box.pack(fill="both", expand=True, padx=6, pady=6)

    def i2v_log(msg):
        def _do():
            i2v_log_box.configure(state="normal")
            i2v_log_box.insert("end", str(msg) + "\n")
            i2v_log_box.see("end")
            i2v_log_box.configure(state="disabled")

        root.after(0, _do)

    def i2v_update_progress(done, total):
        pct = int(done / total * 100) if total else 0

        def _do():
            i2v_progress_bar["value"] = pct
            i2v_percent_var.set(f"{pct}%")

        root.after(0, _do)

    i2v_run_btn = None
    i2v_stop_btn = None
    i2v_cancel_holder = {"event": None}

    def i2v_set_running(running):
        i2v_run_btn.configure(state="disabled" if running else "normal")
        i2v_stop_btn.configure(state="normal" if running else "disabled")

    def i2v_run():
        if len(i2v_files) < 1:
            messagebox.showerror("ผิดพลาด", "กรุณาเลือกภาพอย่างน้อย 1 ภาพก่อน")
            return
        if not i2v_output_var.get().strip():
            messagebox.showerror("ผิดพลาด", "กรุณาระบุตำแหน่งไฟล์ผลลัพธ์ก่อน")
            return
        try:
            fps = float(i2v_fps_var.get())
            if fps <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("ผิดพลาด", "กรุณาใส่ค่า FPS ให้ถูกต้อง (ตัวเลขมากกว่า 0)")
            return

        cancel_event = threading.Event()
        i2v_cancel_holder["event"] = cancel_event
        i2v_set_running(True)
        i2v_log_box.configure(state="normal")
        i2v_log_box.delete("1.0", "end")
        i2v_log_box.configure(state="disabled")
        i2v_progress_bar["value"] = 0
        i2v_percent_var.set("0%")

        files_snapshot = list(i2v_files)

        def worker():
            try:
                ok = images_to_video(
                    files_snapshot,
                    i2v_output_var.get(),
                    fps=fps,
                    log=i2v_log,
                    cancel_event=cancel_event,
                    progress_callback=i2v_update_progress,
                )
                if cancel_event.is_set():
                    i2v_log("\n⏹ ยกเลิกการทำงานแล้ว")
                elif ok:
                    i2v_log("\n✅ เสร็จสิ้น! รวมภาพเป็นวิดีโอเรียบร้อยแล้ว")
                else:
                    i2v_log("\n❌ รวมภาพเป็นวิดีโอไม่สำเร็จ ดูรายละเอียดข้อผิดพลาดด้านบน")
            except Exception as e:
                i2v_log(f"\n❌ เกิดข้อผิดพลาด: {e}")
            finally:
                root.after(0, lambda: i2v_set_running(False))

        threading.Thread(target=worker, daemon=True).start()

    def i2v_stop():
        ev = i2v_cancel_holder["event"]
        if ev is not None:
            ev.set()
            i2v_stop_btn.configure(state="disabled")
            i2v_log("\n[กำลังหยุด...] รอให้ภาพปัจจุบันเขียนเสร็จสักครู่")

    i2v_run_btn = ttk.Button(i2v_btn_holder, text="🎬  สร้างวิดีโอ", command=i2v_run)
    i2v_run_btn.pack(side="left", expand=True, padx=(0, 4))
    i2v_stop_btn = ttk.Button(i2v_btn_holder, text="■  หยุด", command=i2v_stop, state="disabled")
    i2v_stop_btn.pack(side="left", expand=True, padx=(4, 0))

    if standalone:
        root.mainloop()
    else:
        return root


def main():
    parser = build_arg_parser()
    args = parser.parse_args()

    if args.gui or (not args.input and len(sys.argv) == 1):
        try:
            launch_gui()
        except ImportError:
            print("[ERROR] tkinter ไม่พร้อมใช้งานในระบบนี้ กรุณาใช้งานผ่าน CLI แทน (ดู --help)")
            sys.exit(1)
    else:
        run_cli(args)


if __name__ == "__main__":
    main()
