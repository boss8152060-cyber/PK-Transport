"""
=========================================================================
PK Studio - Tab: Dataset Curator & Splitter

รวม 2 เครื่องมือที่ทดสอบผ่านแล้วแยกกันเข้าไว้ในแท็บเดียว (ซ้าย = Curator,
ขวา = Splitter) — logic ภายในทั้งหมด (must-keep/candidate-pool, embedding,
difficulty จริงจาก IoU matching, greedy selection, stratified split) เหมือน
กับ 4_dataset_curator_gui.py และ 5_dataset_splitter_gui.py ทุกประการ ไม่มี
การลดทอนส่วนไหนออก (ต่างจากเวอร์ชันที่เคยเห็นซึ่ง difficulty ถูกปิดเป็น
ค่าคงที่ 0.5)
=========================================================================
"""

import random
import shutil
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk


class CuratorSplitterTab(ttk.Frame):
    """แท็บหลัก — แบ่งซ้าย/ขวาเป็น Curator กับ Splitter คนละส่วนกัน
    ทำงานอิสระจากกันได้ ไม่จำเป็นต้องใช้ Curator ก่อนถึงจะใช้ Splitter ได้"""

    def __init__(self, parent):
        super().__init__(parent, padding=10)

        ttk.Label(
            self, text="✂️ Dataset Curator & Splitter", font=("Segoe UI", 12, "bold")
        ).pack(anchor="w", pady=(0, 10))

        paned = ttk.PanedWindow(self, orient="horizontal")
        paned.pack(fill="both", expand=True)

        curator_panel = CuratorPanel(paned)
        splitter_panel = SplitterPanel(paned)

        paned.add(curator_panel, weight=1)
        paned.add(splitter_panel, weight=1)


class CuratorPanel(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding=10)

        self.model_path = tk.StringVar()
        self.source_folder = tk.StringVar()
        self.output_folder = tk.StringVar()

        self._model = None
        self._scan_result = None
        self._target_vars = {}

        self._build_ui()

    # =================================================================
    # UI
    # =================================================================
    def _build_ui(self) -> None:
        pad = {"padx": 10, "pady": 6}

        frame_model = ttk.LabelFrame(self, text="1. ไฟล์โมเดล (best.pt) — ใช้ช่วยเลือกรูป")
        frame_model.pack(fill="x", **pad)
        ttk.Entry(frame_model, textvariable=self.model_path).pack(
            side="left", fill="x", expand=True, padx=5, pady=5
        )
        ttk.Button(frame_model, text="เลือกไฟล์...", command=self._pick_model).pack(
            side="right", padx=5, pady=5
        )

        frame_src = ttk.LabelFrame(
            self, text="2. โฟลเดอร์รูป+label ที่ยังไม่แบ่ง train/valid/test"
        )
        frame_src.pack(fill="x", **pad)
        ttk.Entry(frame_src, textvariable=self.source_folder).pack(
            side="left", fill="x", expand=True, padx=5, pady=5
        )
        ttk.Button(frame_src, text="เลือกโฟลเดอร์...", command=self._pick_source).pack(
            side="right", padx=5, pady=5
        )

        frame_out = ttk.LabelFrame(self, text="3. โฟลเดอร์ปลายทาง (เก็บ dataset ที่คัดแล้ว)")
        frame_out.pack(fill="x", **pad)
        ttk.Entry(frame_out, textvariable=self.output_folder).pack(
            side="left", fill="x", expand=True, padx=5, pady=5
        )
        ttk.Button(frame_out, text="เลือกโฟลเดอร์...", command=self._pick_output).pack(
            side="right", padx=5, pady=5
        )

        self.scan_button = ttk.Button(
            self, text="สแกนโฟลเดอร์ (โหลดรายชื่อ class)", command=self._start_scan
        )
        self.scan_button.pack(pady=6)

        self.class_frame = ttk.LabelFrame(
            self, text="4. ตั้งจำนวนรูปเป้าหมายต่อ class (สแกนก่อนถึงจะเห็นรายชื่อ)"
        )
        self.class_frame.pack(fill="both", expand=True, **pad)
        ttk.Label(
            self.class_frame,
            text="ใส่ตัวเลขสูง ๆ (เช่น 999999) ถ้าอยากเก็บ class นั้นไว้ทั้งหมด ไม่ต้องลด",
            wraplength=580,
        ).pack(padx=5, pady=5)

        self.run_button = ttk.Button(
            self, text="เริ่มคัด Dataset", command=self._start_run, state="disabled"
        )
        self.run_button.pack(pady=8)

        self.progress = ttk.Progressbar(self, mode="determinate")
        self.progress.pack(fill="x", padx=10)

        self.status_label = ttk.Label(self, text="ยังไม่ได้สแกนโฟลเดอร์", wraplength=580)
        self.status_label.pack(padx=10, pady=8)

    def _pick_model(self) -> None:
        path = filedialog.askopenfilename(
            title="เลือกไฟล์โมเดล", filetypes=[("PyTorch model", "*.pt")]
        )
        if path:
            self.model_path.set(path)

    def _pick_source(self) -> None:
        path = filedialog.askdirectory(title="เลือกโฟลเดอร์รูป+label ที่ยังไม่แบ่ง")
        if path:
            self.source_folder.set(path)

    def _pick_output(self) -> None:
        path = filedialog.askdirectory(title="เลือกโฟลเดอร์ปลายทาง")
        if path:
            self.output_folder.set(path)

    # =================================================================
    # ขั้นสแกน: โหลดโมเดล + อ่านรูป/label ทั้งหมด + นับจำนวนต่อ class
    # =================================================================
    def _start_scan(self) -> None:
        if not self.model_path.get() or not self.source_folder.get():
            messagebox.showwarning("ข้อมูลไม่ครบ", "กรุณาเลือกไฟล์โมเดลและโฟลเดอร์ต้นทางก่อนสแกน")
            return
        self.scan_button.config(state="disabled")
        self.status_label.config(text="กำลังสแกน...")
        thread = threading.Thread(target=self._scan_job, daemon=True)
        thread.start()

    @staticmethod
    def _find_images_and_labels(source: Path):
        """หาไฟล์รูป+label คู่กัน รองรับทั้ง 2 แบบ:
        1) มีโฟลเดอร์ย่อย images/ กับ labels/ แยกกัน (แบบที่ Auto Label Tool ส่งออกมา)
        2) รูปกับไฟล์ .txt วางปนกันในโฟลเดอร์เดียวแบบเรียบ (แบบที่ Roboflow export ให้บ่อย)
        คืนค่า dict: stem -> (image_path, label_path หรือ None ถ้าไม่มี label)"""
        image_extensions = {".jpg", ".jpeg", ".png", ".bmp"}
        images_dir = source / "images"
        labels_dir = source / "labels"

        image_files = {}
        if images_dir.is_dir() and labels_dir.is_dir():
            for img_path in sorted(images_dir.iterdir()):
                if img_path.suffix.lower() not in image_extensions:
                    continue
                label_path = labels_dir / f"{img_path.stem}.txt"
                image_files[img_path.stem] = (img_path, label_path if label_path.exists() else None)
        else:
            for img_path in sorted(source.iterdir()):
                if img_path.suffix.lower() not in image_extensions:
                    continue
                label_path = source / f"{img_path.stem}.txt"
                image_files[img_path.stem] = (img_path, label_path if label_path.exists() else None)

        return image_files

    def _scan_job(self) -> None:
        try:
            from ultralytics import YOLO
        except ImportError:
            self._show_error("ยังไม่ได้ติดตั้ง ultralytics กรุณารัน: pip install ultralytics")
            return

        try:
            if self._model is None or getattr(self._model, "ckpt_path", None) != self.model_path.get():
                self._model = YOLO(self.model_path.get())
            model = self._model

            names_dict = model.names
            class_names = [names_dict[i] for i in range(len(names_dict))]

            source = Path(self.source_folder.get())
            image_files = self._find_images_and_labels(source)
            if not image_files:
                self._show_error(
                    "ไม่พบไฟล์รูปในโฟลเดอร์ที่เลือก (เช็คว่ามีโฟลเดอร์ images/labels หรือรูป+.txt วางปนกันไหม)"
                )
                return

            image_labels = {}
            for stem, (img_path, label_path) in image_files.items():
                labels_here = []
                if label_path is not None:
                    with open(label_path, encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if not line:
                                continue
                            cls_idx = int(line.split()[0])
                            if 0 <= cls_idx < len(class_names):
                                labels_here.append(class_names[cls_idx])
                image_labels[stem] = labels_here

            current_image_count = {
                c: sum(1 for labs in image_labels.values() if c in labs) for c in class_names
            }

            self._scan_result = {
                "class_names": class_names,
                "image_files": image_files,
                "image_labels": image_labels,
                "current_image_count": current_image_count,
            }

            self.after(0, self._build_class_rows, class_names, current_image_count, len(image_files))

        except Exception as exc:
            self._show_error(f"เกิดข้อผิดพลาดตอนสแกน: {exc}")

    def _build_class_rows(self, class_names, current_image_count, n_images) -> None:
        for widget in self.class_frame.winfo_children():
            widget.destroy()

        ttk.Label(
            self.class_frame,
            text=f"พบทั้งหมด {n_images} รูป — ใส่ตัวเลขสูง ๆ (เช่น 999999) ถ้าอยากเก็บ class นั้นไว้ทั้งหมด",
            wraplength=580,
        ).grid(row=0, column=0, columnspan=3, padx=5, pady=5, sticky="w")

        ttk.Label(self.class_frame, text="Class", font=("", 9, "bold")).grid(
            row=1, column=0, padx=5, sticky="w"
        )
        ttk.Label(self.class_frame, text="มีอยู่ตอนนี้ (รูป)", font=("", 9, "bold")).grid(
            row=1, column=1, padx=5, sticky="w"
        )
        ttk.Label(self.class_frame, text="เป้าหมาย (รูป)", font=("", 9, "bold")).grid(
            row=1, column=2, padx=5, sticky="w"
        )

        self._target_vars = {}
        for i, c in enumerate(class_names, start=2):
            current = current_image_count.get(c, 0)
            ttk.Label(self.class_frame, text=c).grid(row=i, column=0, padx=5, pady=2, sticky="w")
            ttk.Label(self.class_frame, text=str(current)).grid(row=i, column=1, padx=5, pady=2)
            target_var = tk.StringVar(value=str(current))
            ttk.Entry(self.class_frame, textvariable=target_var, width=10).grid(
                row=i, column=2, padx=5, pady=2
            )
            self._target_vars[c] = target_var

        self.scan_button.config(state="normal")
        self.run_button.config(state="normal")
        self.status_label.config(
            text=f"สแกนเสร็จแล้ว พบ {n_images} รูป — ตั้งเป้าหมายแล้วกด \"เริ่มคัด Dataset\" ได้เลย"
        )

    # =================================================================
    # ขั้นคัดเลือกจริง
    # =================================================================
    def _start_run(self) -> None:
        if self._scan_result is None:
            messagebox.showwarning("ยังไม่ได้สแกน", "กรุณากด \"สแกนโฟลเดอร์\" ก่อน")
            return
        if not self.output_folder.get():
            messagebox.showwarning("ข้อมูลไม่ครบ", "กรุณาเลือกโฟลเดอร์ปลายทางก่อน")
            return

        try:
            target_counts = {c: int(v.get()) for c, v in self._target_vars.items()}
        except ValueError:
            messagebox.showerror("ตัวเลขไม่ถูกต้อง", "ช่องเป้าหมายต้องเป็นตัวเลขจำนวนเต็มเท่านั้น")
            return

        self.run_button.config(state="disabled")
        self.scan_button.config(state="disabled")
        self.status_label.config(text="กำลังคัด Dataset...")
        thread = threading.Thread(target=self._run_job, args=(target_counts,), daemon=True)
        thread.start()

    def _run_job(self, target_counts: dict) -> None:
        try:
            import torch

            scan = self._scan_result
            class_names = scan["class_names"]
            image_files = scan["image_files"]
            image_labels = scan["image_labels"]
            current_image_count = scan["current_image_count"]
            model = self._model

            # ---- แยก must_keep (คุ้มครอง) กับ candidate_pool (คัดเลือกได้) ----
            over_target_classes = {c for c in class_names if target_counts[c] < current_image_count[c]}
            protected_classes = set(class_names) - over_target_classes
            must_keep_stems = {
                stem for stem, labs in image_labels.items()
                if not labs or any(c in protected_classes for c in labs)
            }
            candidate_pool_stems = list(set(image_labels.keys()) - must_keep_stems)

            base_count = {c: sum(1 for s in must_keep_stems if c in image_labels[s]) for c in over_target_classes}
            remaining_quota = {c: max(0, target_counts[c] - base_count[c]) for c in over_target_classes}

            self._log(f"must_keep: {len(must_keep_stems)} รูป, candidate_pool: {len(candidate_pool_stems)} รูป")

            selected_stems = []
            if candidate_pool_stems and any(v > 0 for v in remaining_quota.values()):
                # ---- ดึง embedding (ความหลากหลาย) — batch เล็ก + auto-retry กัน OOM ----
                self.after(0, lambda: self.status_label.config(
                    text=f"กำลังดึง embedding ของ {len(candidate_pool_stems)} รูป..."
                ))
                candidate_paths = [str(image_files[s][0]) for s in candidate_pool_stems]

                def embed_progress(done, total):
                    self.after(0, lambda: self.status_label.config(
                        text=f"กำลังดึง embedding {done}/{total} รูป..."
                    ))

                raw_embeddings = self._run_with_oom_retry(
                    model, candidate_paths, initial_batch_size=8, progress_cb=embed_progress
                )
                embeddings_map = {}
                for stem, emb in zip(candidate_pool_stems, raw_embeddings):
                    emb = emb.float()
                    embeddings_map[stem] = emb / (emb.norm() + 1e-8)

                # ---- คำนวณ difficulty (เทียบ predict กับ label จริง) ----
                self.after(0, lambda: self.status_label.config(
                    text="กำลังคำนวณความยาก (เทียบผลทำนายกับ label จริง)..."
                ))
                difficulty_map = self._compute_difficulty(model, class_names, candidate_pool_stems, image_files)

                # ---- greedy selection ----
                self.after(0, lambda: self.status_label.config(text="กำลังเลือกรูป..."))
                remaining = dict(remaining_quota)
                pool = list(candidate_pool_stems)
                selected_embeds = []
                W_DIVERSITY, W_DIFFICULTY, W_RELEVANCE = 1.0, 1.0, 2.0

                while pool and any(v > 0 for v in remaining.values()):
                    best_score, best_i = -1e18, None
                    for i, stem in enumerate(pool):
                        labs = image_labels[stem]
                        relevance = sum(1 for c in labs if remaining.get(c, 0) > 0)
                        if relevance == 0:
                            continue
                        if selected_embeds:
                            sims = torch.stack([torch.dot(embeddings_map[stem], e) for e in selected_embeds])
                            diversity = 1.0 - float(sims.max())
                        else:
                            diversity = 1.0
                        score = (
                            W_DIVERSITY * diversity
                            + W_DIFFICULTY * difficulty_map[stem]
                            + W_RELEVANCE * relevance
                        )
                        if score > best_score:
                            best_score, best_i = score, i

                    if best_i is None:
                        break

                    stem = pool.pop(best_i)
                    selected_stems.append(stem)
                    selected_embeds.append(embeddings_map[stem])
                    for c in image_labels[stem]:
                        if c in remaining:
                            remaining[c] = max(0, remaining[c] - 1)

                self._log(f"เลือกจาก candidate_pool ได้ {len(selected_stems)} รูป")

            final_stems = must_keep_stems | set(selected_stems)

            # ---- คัดลอกไฟล์ไปโฟลเดอร์ปลายทาง ----
            self.after(0, lambda: self.status_label.config(text="กำลังคัดลอกไฟล์..."))
            output = Path(self.output_folder.get())
            images_out = output / "images"
            labels_out = output / "labels"
            images_out.mkdir(parents=True, exist_ok=True)
            labels_out.mkdir(parents=True, exist_ok=True)

            self.after(0, lambda: self.progress.config(maximum=len(final_stems), value=0))
            for idx, stem in enumerate(final_stems, start=1):
                img_path, label_path = image_files[stem]
                shutil.copy2(img_path, images_out / img_path.name)
                if label_path is not None:
                    shutil.copy2(label_path, labels_out / label_path.name)
                if idx % 20 == 0 or idx == len(final_stems):
                    self.after(0, self._update_progress, idx, len(final_stems))

            final_image_count = {c: sum(1 for s in final_stems if c in image_labels[s]) for c in class_names}
            summary_lines = [f"เสร็จสิ้น! รูปเดิม {len(image_labels)} -> รูปที่คัดแล้ว {len(final_stems)}", ""]
            summary_lines.append(f"{'Class':<15}{'เดิม':>8}{'เป้าหมาย':>10}{'ได้จริง':>10}")
            for c in class_names:
                summary_lines.append(
                    f"{c:<15}{current_image_count[c]:>8}{target_counts[c]:>10}{final_image_count[c]:>10}"
                )
            summary_lines.append("")
            summary_lines.append(f"ผลลัพธ์อยู่ที่: {output.resolve()}")
            summary = "\n".join(summary_lines)

            self.after(0, lambda: self.status_label.config(text=summary))
            self.after(0, lambda: self.run_button.config(state="normal"))
            self.after(0, lambda: self.scan_button.config(state="normal"))

        except Exception as exc:
            self._show_error(f"เกิดข้อผิดพลาด: {exc}")

    @staticmethod
    def _run_with_oom_retry(model, paths, initial_batch_size, progress_cb=None):
        """เรียก model.embed() เป็นก้อน ๆ (batch) แทนที่จะส่งรูปทั้งหมดเข้าไปทีเดียว
        (สาเหตุของ CUDA out of memory ที่เจอบนการ์ดจอ VRAM น้อย) — ถ้าเจอ OOM ระหว่างทาง
        จะลด batch size ลงครึ่งหนึ่งแล้วลองใหม่อัตโนมัติ จนกว่าจะผ่านหรือเหลือ batch=1
        แล้วยัง OOM อยู่ (ถือว่าการ์ดจอเล็กเกินไปจริง ๆ ต้อง error ออกไป)"""
        import torch

        results = []
        i = 0
        batch_size = initial_batch_size
        while i < len(paths):
            batch = paths[i:i + batch_size]
            try:
                out = model.embed(batch, verbose=False)
                results.extend(out)
                i += len(batch)
                if progress_cb is not None:
                    progress_cb(i, len(paths))
            except torch.cuda.OutOfMemoryError:
                torch.cuda.empty_cache()
                if batch_size == 1:
                    raise RuntimeError(
                        "การ์ดจอ VRAM ไม่พอแม้ทีละ 1 รูป — ลองปิดโปรแกรมอื่นที่ใช้ GPU อยู่ "
                        "หรือใช้โมเดลขนาดเล็กกว่า (เช่น yolo26n/yolo26s แทน yolo26m)"
                    )
                batch_size = max(1, batch_size // 2)
        return results

    @staticmethod
    def _predict_with_oom_retry(model, paths, initial_batch_size, conf):
        """เหมือน _run_with_oom_retry แต่สำหรับ model.predict()"""
        import torch

        results = []
        i = 0
        batch_size = initial_batch_size
        while i < len(paths):
            batch = paths[i:i + batch_size]
            try:
                out = model.predict(batch, verbose=False, conf=conf)
                results.extend(out)
                i += len(batch)
            except torch.cuda.OutOfMemoryError:
                torch.cuda.empty_cache()
                if batch_size == 1:
                    raise RuntimeError(
                        "การ์ดจอ VRAM ไม่พอแม้ทีละ 1 รูป — ลองปิดโปรแกรมอื่นที่ใช้ GPU อยู่ "
                        "หรือใช้โมเดลขนาดเล็กกว่า (เช่น yolo26n/yolo26s แทน yolo26m)"
                    )
                batch_size = max(1, batch_size // 2)
        return results

    @staticmethod
    def _compute_difficulty(model, class_names, candidate_pool_stems, image_files):
        """รัน predict เทียบกับ label จริง คืน difficulty score (0=ทายถูกมั่นใจเต็มที่,
        1=ทายพลาด/ไม่มั่นใจเลย) เฉลี่ยต่อรูป — ใช้จับคู่กรอบด้วย IoU >= 0.5 + class ตรงกัน"""

        def yolo_txt_to_xyxy(label_path, img_w, img_h):
            boxes = []
            if label_path is None:
                return boxes
            with open(label_path, encoding="utf-8") as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) != 5:
                        continue
                    cls_idx, cx, cy, w, h = int(parts[0]), *map(float, parts[1:])
                    if not (0 <= cls_idx < len(class_names)):
                        continue
                    x1 = (cx - w / 2) * img_w
                    y1 = (cy - h / 2) * img_h
                    x2 = (cx + w / 2) * img_w
                    y2 = (cy + h / 2) * img_h
                    boxes.append([x1, y1, x2, y2, class_names[cls_idx]])
            return boxes

        def iou_xyxy(box_a, box_b):
            xa1, ya1, xa2, ya2 = box_a
            xb1, yb1, xb2, yb2 = box_b
            ix1, iy1 = max(xa1, xb1), max(ya1, yb1)
            ix2, iy2 = min(xa2, xb2), min(ya2, yb2)
            iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
            inter = iw * ih
            area_a = max(0.0, xa2 - xa1) * max(0.0, ya2 - ya1)
            area_b = max(0.0, xb2 - xb1) * max(0.0, yb2 - yb1)
            union = area_a + area_b - inter
            return inter / union if union > 0 else 0.0

        IOU_MATCH_THRESHOLD = 0.5
        difficulty_map = {}
        candidate_paths = [str(image_files[s][0]) for s in candidate_pool_stems]
        results = CuratorPanel._predict_with_oom_retry(
            model, candidate_paths, initial_batch_size=8, conf=0.15
        )

        for stem, result in zip(candidate_pool_stems, results):
            img_w, img_h = result.orig_shape[1], result.orig_shape[0]
            _, label_path = image_files[stem]
            gt_boxes = yolo_txt_to_xyxy(label_path, img_w, img_h)

            if not gt_boxes:
                difficulty_map[stem] = 0.0
                continue

            pred_boxes = result.boxes.xyxy.cpu().numpy()
            pred_cls = [class_names[int(c)] for c in result.boxes.cls.cpu().numpy()]
            pred_conf = result.boxes.conf.cpu().numpy()

            per_box_difficulty = []
            for gx1, gy1, gx2, gy2, gt_cls in gt_boxes:
                best_iou, best_conf = 0.0, 0.0
                for (px1, py1, px2, py2), p_cls, p_conf in zip(pred_boxes, pred_cls, pred_conf):
                    if p_cls != gt_cls:
                        continue
                    iou = iou_xyxy((gx1, gy1, gx2, gy2), (px1, py1, px2, py2))
                    if iou > best_iou:
                        best_iou, best_conf = iou, p_conf
                per_box_difficulty.append(1.0 - float(best_conf) if best_iou >= IOU_MATCH_THRESHOLD else 1.0)

            difficulty_map[stem] = sum(per_box_difficulty) / len(per_box_difficulty)

        return difficulty_map

    def _update_progress(self, current: int, total: int) -> None:
        self.progress.config(value=current)
        self.status_label.config(text=f"กำลังคัดลอกไฟล์ {current}/{total}...")

    def _log(self, message: str) -> None:
        self.after(0, lambda: self.status_label.config(text=message))

    def _show_error(self, message: str) -> None:
        self.after(0, lambda: messagebox.showerror("ข้อผิดพลาด", message))
        self.after(0, lambda: self.run_button.config(state="normal"))
        self.after(0, lambda: self.scan_button.config(state="normal"))


class SplitterPanel(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding=10)

        self.source_folder = tk.StringVar()
        self.output_folder = tk.StringVar()
        self.classes_file = tk.StringVar()  # ไฟล์ classes.txt หรือ data.yaml (ถ้ามี ใช้ระบุชื่อ class)
        self.train_pct = tk.StringVar(value="70")
        self.valid_pct = tk.StringVar(value="20")
        self.test_pct = tk.StringVar(value="10")

        self._scan_result = None

        self._build_ui()

    # =================================================================
    # UI
    # =================================================================
    def _build_ui(self) -> None:
        pad = {"padx": 10, "pady": 6}

        frame_src = ttk.LabelFrame(self, text="1. โฟลเดอร์รูป+label ที่ยังไม่แบ่ง")
        frame_src.pack(fill="x", **pad)
        ttk.Entry(frame_src, textvariable=self.source_folder).pack(
            side="left", fill="x", expand=True, padx=5, pady=5
        )
        ttk.Button(frame_src, text="เลือกโฟลเดอร์...", command=self._pick_source).pack(
            side="right", padx=5, pady=5
        )

        frame_out = ttk.LabelFrame(self, text="2. โฟลเดอร์ปลายทาง (เก็บ dataset ที่แบ่งแล้ว)")
        frame_out.pack(fill="x", **pad)
        ttk.Entry(frame_out, textvariable=self.output_folder).pack(
            side="left", fill="x", expand=True, padx=5, pady=5
        )
        ttk.Button(frame_out, text="เลือกโฟลเดอร์...", command=self._pick_output).pack(
            side="right", padx=5, pady=5
        )

        frame_classes = ttk.LabelFrame(
            self, text="3. ไฟล์ classes.txt (ถ้ามี — ใช้ตั้งชื่อ class ใน data.yaml ที่จะสร้างให้)"
        )
        frame_classes.pack(fill="x", **pad)
        ttk.Entry(frame_classes, textvariable=self.classes_file).pack(
            side="left", fill="x", expand=True, padx=5, pady=5
        )
        ttk.Button(frame_classes, text="เลือกไฟล์...", command=self._pick_classes_file).pack(
            side="right", padx=5, pady=5
        )

        frame_ratio = ttk.LabelFrame(self, text="4. สัดส่วน train / valid / test (%)")
        frame_ratio.pack(fill="x", **pad)
        row = ttk.Frame(frame_ratio)
        row.pack(padx=5, pady=8)
        ttk.Label(row, text="train:").pack(side="left")
        ttk.Entry(row, textvariable=self.train_pct, width=6).pack(side="left", padx=(4, 16))
        ttk.Label(row, text="valid:").pack(side="left")
        ttk.Entry(row, textvariable=self.valid_pct, width=6).pack(side="left", padx=(4, 16))
        ttk.Label(row, text="test:").pack(side="left")
        ttk.Entry(row, textvariable=self.test_pct, width=6).pack(side="left", padx=(4, 16))
        ttk.Label(row, text="(รวมกันต้องได้ 100)").pack(side="left")

        self.scan_button = ttk.Button(
            self, text="สแกนโฟลเดอร์", command=self._start_scan
        )
        self.scan_button.pack(pady=6)

        self.summary_text = tk.Text(self, height=10, wrap="word", state="disabled")
        self.summary_text.pack(fill="both", expand=True, padx=10, pady=4)

        self.run_button = ttk.Button(
            self, text="เริ่มแบ่ง Dataset", command=self._start_run, state="disabled"
        )
        self.run_button.pack(pady=8)

        self.progress = ttk.Progressbar(self, mode="determinate")
        self.progress.pack(fill="x", padx=10)

        self.status_label = ttk.Label(self, text="ยังไม่ได้สแกนโฟลเดอร์", wraplength=580)
        self.status_label.pack(padx=10, pady=8)

    def _pick_source(self) -> None:
        path = filedialog.askdirectory(title="เลือกโฟลเดอร์รูป+label ที่ยังไม่แบ่ง")
        if path:
            self.source_folder.set(path)

    def _pick_output(self) -> None:
        path = filedialog.askdirectory(title="เลือกโฟลเดอร์ปลายทาง")
        if path:
            self.output_folder.set(path)

    def _pick_classes_file(self) -> None:
        path = filedialog.askopenfilename(
            title="เลือกไฟล์ classes.txt", filetypes=[("Text/YAML", "*.txt *.yaml *.yml"), ("All files", "*.*")]
        )
        if path:
            self.classes_file.set(path)

    # =================================================================
    # ขั้นสแกน
    # =================================================================
    @staticmethod
    def _find_images_and_labels(source: Path):
        """หาไฟล์รูป+label คู่กัน รองรับทั้ง 2 แบบ: มี images/+labels/ แยกโฟลเดอร์
        หรือรูป+.txt วางปนกันแบบเรียบ — เหมือนกับที่ Dataset Curator ใช้"""
        image_extensions = {".jpg", ".jpeg", ".png", ".bmp"}
        images_dir = source / "images"
        labels_dir = source / "labels"

        image_files = {}
        if images_dir.is_dir() and labels_dir.is_dir():
            for img_path in sorted(images_dir.iterdir()):
                if img_path.suffix.lower() not in image_extensions:
                    continue
                label_path = labels_dir / f"{img_path.stem}.txt"
                image_files[img_path.stem] = (img_path, label_path if label_path.exists() else None)
        else:
            for img_path in sorted(source.iterdir()):
                if img_path.suffix.lower() not in image_extensions:
                    continue
                label_path = source / f"{img_path.stem}.txt"
                image_files[img_path.stem] = (img_path, label_path if label_path.exists() else None)

        return image_files

    @staticmethod
    def _load_class_names(classes_file_str: str, max_class_idx: int):
        """อ่านชื่อ class จากไฟล์ classes.txt (บรรทัดละ 1 ชื่อ) หรือ data.yaml (key names)
        ถ้าไม่ได้เลือกไฟล์ไว้ จะตั้งชื่อเป็น class0, class1, ... แทน (ใช้งานได้ปกติ
        แค่ชื่อไม่สวย แนะนำให้เลือกไฟล์ classes.txt ถ้ามีเพื่อให้ data.yaml อ่านง่ายขึ้น)"""
        if classes_file_str:
            p = Path(classes_file_str)
            if p.suffix.lower() in (".yaml", ".yml"):
                import yaml

                with open(p, encoding="utf-8") as f:
                    cfg = yaml.safe_load(f)
                names = cfg.get("names")
                if isinstance(names, dict):
                    return [names[i] for i in range(len(names))]
                return list(names)
            else:
                with open(p, encoding="utf-8") as f:
                    return [line.strip() for line in f if line.strip()]
        return [f"class{i}" for i in range(max_class_idx + 1)]

    def _start_scan(self) -> None:
        if not self.source_folder.get():
            messagebox.showwarning("ข้อมูลไม่ครบ", "กรุณาเลือกโฟลเดอร์ต้นทางก่อน")
            return
        self.scan_button.config(state="disabled")
        self.status_label.config(text="กำลังสแกน...")
        thread = threading.Thread(target=self._scan_job, daemon=True)
        thread.start()

    def _scan_job(self) -> None:
        try:
            source = Path(self.source_folder.get())
            image_files = self._find_images_and_labels(source)
            if not image_files:
                self._show_error(
                    "ไม่พบไฟล์รูปในโฟลเดอร์ที่เลือก (เช็คว่ามีโฟลเดอร์ images/labels หรือรูป+.txt วางปนกันไหม)"
                )
                return

            image_labels = {}  # stem -> list of class index (int)
            max_class_idx = -1
            for stem, (img_path, label_path) in image_files.items():
                labels_here = []
                if label_path is not None:
                    with open(label_path, encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if not line:
                                continue
                            cls_idx = int(line.split()[0])
                            labels_here.append(cls_idx)
                            max_class_idx = max(max_class_idx, cls_idx)
                image_labels[stem] = labels_here

            class_names = self._load_class_names(self.classes_file.get(), max_class_idx)

            current_count = {i: sum(1 for labs in image_labels.values() if i in labs) for i in range(len(class_names))}
            n_background = sum(1 for labs in image_labels.values() if not labs)

            self._scan_result = {
                "image_files": image_files,
                "image_labels": image_labels,
                "class_names": class_names,
                "current_count": current_count,
                "n_background": n_background,
            }

            self.after(0, self._show_scan_summary, class_names, current_count, n_background, len(image_files))

        except Exception as exc:
            self._show_error(f"เกิดข้อผิดพลาดตอนสแกน: {exc}")

    def _show_scan_summary(self, class_names, current_count, n_background, n_total) -> None:
        lines = [f"พบทั้งหมด {n_total} รูป (รูปพื้นหลังไม่มี object: {n_background})", ""]
        lines.append(f"{'Class':<15}{'Images':>10}")
        for i, name in enumerate(class_names):
            warn = ""
            c = current_count[i]
            if 0 < c < 3:
                warn = "  ⚠ น้อยมาก อาจแบ่งครบ 3 กลุ่มไม่ได้"
            lines.append(f"{name:<15}{c:>10}{warn}")

        self.summary_text.config(state="normal")
        self.summary_text.delete("1.0", "end")
        self.summary_text.insert("1.0", "\n".join(lines))
        self.summary_text.config(state="disabled")

        self.scan_button.config(state="normal")
        self.run_button.config(state="normal")
        self.status_label.config(text="สแกนเสร็จแล้ว ตรวจดูสัดส่วนแล้วกด \"เริ่มแบ่ง Dataset\" ได้เลย")

    # =================================================================
    # ขั้นแบ่งจริง (Iterative Stratified Split)
    # =================================================================
    def _start_run(self) -> None:
        if self._scan_result is None:
            messagebox.showwarning("ยังไม่ได้สแกน", "กรุณากด \"สแกนโฟลเดอร์\" ก่อน")
            return
        if not self.output_folder.get():
            messagebox.showwarning("ข้อมูลไม่ครบ", "กรุณาเลือกโฟลเดอร์ปลายทางก่อน")
            return

        try:
            train_p = float(self.train_pct.get())
            valid_p = float(self.valid_pct.get())
            test_p = float(self.test_pct.get())
        except ValueError:
            messagebox.showerror("ตัวเลขไม่ถูกต้อง", "สัดส่วน train/valid/test ต้องเป็นตัวเลขเท่านั้น")
            return

        if abs((train_p + valid_p + test_p) - 100) > 0.01:
            messagebox.showerror("สัดส่วนไม่ครบ 100", f"ตอนนี้รวมกันได้ {train_p + valid_p + test_p} ต้องรวมกันได้ 100 พอดี")
            return

        self.run_button.config(state="disabled")
        self.scan_button.config(state="disabled")
        self.status_label.config(text="กำลังแบ่ง Dataset...")
        thread = threading.Thread(
            target=self._run_job, args=(train_p / 100, valid_p / 100, test_p / 100), daemon=True
        )
        thread.start()

    @staticmethod
    def _stratified_split(image_labels: dict, class_names: list, train_ratio: float, valid_ratio: float, test_ratio: float, seed: int = 0):
        """แบ่งภาพเป็น train/valid/test โดยเริ่มจาก class ที่หายากที่สุดก่อน
        (ตอนที่โควตายังไม่ถูกรูปอื่นแย่งไปหมด) เพื่อรับประกันว่า class หายาก
        มีโอกาสได้ตัวแทนอยู่ในทุกกลุ่มตามสัดส่วนที่ตั้งไว้ ไม่ใช่กระจุกอยู่ train
        อย่างเดียว — คืนค่า dict: stem -> 'train' | 'valid' | 'test'"""
        rng = random.Random(seed)

        n_classes = len(class_names)
        class_to_images = {i: [] for i in range(n_classes)}
        background_images = []
        for stem, labs in image_labels.items():
            if not labs:
                background_images.append(stem)
            for c in set(labs):  # set กันนับซ้ำถ้า class เดียวมีหลาย instance ในรูปเดียว
                class_to_images[c].append(stem)

        # เรียง class จากหายากสุด (จำนวนรูปน้อยสุด) ไปมากสุด — ประมวลผลก่อนเพื่อความสำคัญ
        class_order = sorted(range(n_classes), key=lambda c: len(class_to_images[c]))

        assignment = {}  # stem -> split name
        warnings = []

        def assign_group(stems, name_for_warning):
            unassigned = [s for s in stems if s not in assignment]
            if not unassigned:
                return
            rng.shuffle(unassigned)
            n = len(unassigned)

            if n == 1:
                assignment[unassigned[0]] = "train"
                warnings.append(f"{name_for_warning}: มีแค่ 1 รูป ใส่ไว้ train อย่างเดียว (ไม่มีใน valid/test)")
                return
            if n == 2:
                assignment[unassigned[0]] = "train"
                assignment[unassigned[1]] = "valid"
                warnings.append(f"{name_for_warning}: มีแค่ 2 รูป ใส่ train 1 valid 1 (ไม่มีใน test)")
                return

            test_n = max(1, round(n * test_ratio)) if test_ratio > 0 else 0
            valid_n = max(1, round(n * valid_ratio)) if valid_ratio > 0 else 0
            # กันไม่ให้ test+valid เกินจำนวนที่มี (edge case ตอน n น้อย ๆ)
            while test_n + valid_n >= n:
                if valid_n >= test_n and valid_n > 0:
                    valid_n -= 1
                elif test_n > 0:
                    test_n -= 1
                else:
                    break
            train_n = n - test_n - valid_n

            for s in unassigned[:test_n]:
                assignment[s] = "test"
            for s in unassigned[test_n:test_n + valid_n]:
                assignment[s] = "valid"
            for s in unassigned[test_n + valid_n:]:
                assignment[s] = "train"

        for c in class_order:
            assign_group(class_to_images[c], class_names[c])

        # รูปพื้นหลัง (ไม่มี class เลย) แบ่งทีหลังสุด ตามสัดส่วนปกติเหมือนกัน
        assign_group(background_images, "รูปพื้นหลัง (ไม่มี object)")

        # เผื่อมีรูปที่ยังไม่ถูกกำหนด (ไม่ควรมีถ้า logic ถูกต้อง แต่กันเหนียวไว้)
        leftover = [s for s in image_labels if s not in assignment]
        assign_group(leftover, "อื่น ๆ")

        return assignment, warnings

    def _run_job(self, train_ratio: float, valid_ratio: float, test_ratio: float) -> None:
        try:
            scan = self._scan_result
            image_files = scan["image_files"]
            image_labels = scan["image_labels"]
            class_names = scan["class_names"]

            assignment, warnings = self._stratified_split(
                image_labels, class_names, train_ratio, valid_ratio, test_ratio
            )

            output = Path(self.output_folder.get())
            for split in ("train", "valid", "test"):
                (output / split / "images").mkdir(parents=True, exist_ok=True)
                (output / split / "labels").mkdir(parents=True, exist_ok=True)

            self.after(0, lambda: self.progress.config(maximum=len(assignment), value=0))
            for idx, (stem, split) in enumerate(assignment.items(), start=1):
                img_path, label_path = image_files[stem]
                shutil.copy2(img_path, output / split / "images" / img_path.name)
                if label_path is not None:
                    shutil.copy2(label_path, output / split / "labels" / label_path.name)
                if idx % 20 == 0 or idx == len(assignment):
                    self.after(0, self._update_progress, idx, len(assignment))

            # นับผลจริงหลังแบ่ง เพื่อสรุปให้ดู
            split_counts = {"train": 0, "valid": 0, "test": 0}
            for split in assignment.values():
                split_counts[split] += 1

            data_yaml_path = output / "data.yaml"
            with open(data_yaml_path, "w", encoding="utf-8") as f:
                f.write("train: train/images\nval: valid/images\ntest: test/images\n\n")
                f.write(f"nc: {len(class_names)}\nnames: {class_names}\n")

            summary_lines = [
                f"เสร็จสิ้น! แบ่งได้ train={split_counts['train']}, "
                f"valid={split_counts['valid']}, test={split_counts['test']}",
                f"สร้าง data.yaml ให้แล้วที่: {data_yaml_path}",
            ]
            if warnings:
                summary_lines.append("")
                summary_lines.append("คำเตือน (class ที่มีรูปน้อยเกินจะแบ่งครบ 3 กลุ่ม):")
                summary_lines.extend(f"  - {w}" for w in warnings)
            summary_lines.append("")
            summary_lines.append(f"ผลลัพธ์อยู่ที่: {output.resolve()}")
            summary = "\n".join(summary_lines)

            self.after(0, lambda: self.status_label.config(text=summary))
            self.after(0, lambda: self.run_button.config(state="normal"))
            self.after(0, lambda: self.scan_button.config(state="normal"))

        except Exception as exc:
            self._show_error(f"เกิดข้อผิดพลาด: {exc}")

    def _update_progress(self, current: int, total: int) -> None:
        self.progress.config(value=current)
        self.status_label.config(text=f"กำลังคัดลอกไฟล์ {current}/{total}...")

    def _show_error(self, message: str) -> None:
        self.after(0, lambda: messagebox.showerror("ข้อผิดพลาด", message))
        self.after(0, lambda: self.run_button.config(state="normal"))
        self.after(0, lambda: self.scan_button.config(state="normal"))
