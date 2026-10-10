"""PKT Data (written in English) -> Thai. Exact texts and {n}-templates of its labels, buttons, dialogs, messages and logs.
Technical words (FPS, FFmpeg, YOLO, best.pt, classes.txt, Auto-Label, Batch, Heat Map, embedding ...) stay English."""

EXACT = {'▶  Extract Frames': '▶  เริ่มดึงเฟรม',
 '■  Stop': '■  หยุด',
 '1) Video Queue': '1) คิววิดีโอ',
 '+ Add Videos...': '+ เพิ่มวิดีโอ...',
 '+ Add Folder (All Subfolders)...': '+ เพิ่มโฟลเดอร์ (รวมโฟลเดอร์ย่อยทั้งหมด)...',
 '- Remove Selected': '- ลบที่เลือก',
 '▲ Move Up': '▲ เลื่อนขึ้น',
 '▼ Move Down': '▼ เลื่อนลง',
 'Clear All': 'ล้างทั้งหมด',
 '0 videos': '0 วิดีโอ',
 '2) Output Folder': '2) โฟลเดอร์ผลลัพธ์',
 'Browse...': 'เลือก...',
 '+ New Folder...': '+ สร้างโฟลเดอร์ใหม่...',
 'Output Structure:': 'โครงสร้างผลลัพธ์:',
 'Preserve original folder structure': 'คงโครงสร้างโฟลเดอร์เดิมไว้',
 'Do not preserve structure (use Output folder only)': 'ไม่คงโครงสร้าง (ใส่ในโฟลเดอร์ผลลัพธ์โฟลเดอร์เดียว)',
 '3) Frame Sampling': '3) การสุ่มเฟรม',
 'Frames per second (FPS)': 'จำนวนเฟรมต่อวินาที (FPS)',
 'Every N frames': 'ทุก N เฟรม',
 '(Blank or 0 = every frame)': '(เว้นว่างหรือ 0 = ทุกเฟรม)',
 '4) Output Options': '4) ตัวเลือกไฟล์ผลลัพธ์',
 'Image format:': 'ชนิดไฟล์ภาพ:',
 'Resize (WxH):': 'ปรับขนาด (กว้างxสูง):',
 'Filename prefix:': 'คำนำหน้าชื่อไฟล์:',
 'Deduplication level:': 'ระดับการตัดภาพซ้ำ:',
 'Low (keep more)': 'ต่ำ (เก็บมากกว่า)',
 'Medium': 'กลาง',
 'High (keep fewer)': 'สูง (เก็บน้อยกว่า)',
 'Custom (%):': 'กำหนดเอง (%):',
 'Skip near-duplicate frames': 'ข้ามเฟรมที่เกือบซ้ำกัน',
 '5) Estimate': '5) ประมาณการ',
 'Progress': 'ความคืบหน้า',
 'Activity Log': 'บันทึกการทำงาน',
 '✂  Trim Video': '✂  ตัดวิดีโอ',
 '1) Select Video to Trim': '1) เลือกวิดีโอที่จะตัด',
 'Video File...': 'ไฟล์วิดีโอ...',
 '2) Trim Range (HH:MM:SS, blank = entire clip)': '2) ช่วงที่จะตัด (HH:MM:SS, เว้นว่าง = ทั้งคลิป)',
 'Start:': 'เริ่ม:',
 '⏮ Start': '⏮ เริ่มต้น',
 'End:': 'จบ:',
 'End ⏭': 'ท้ายสุด ⏭',
 'Entire Clip': 'ทั้งคลิป',
 '3) Output File (.mp4)': '3) ไฟล์ผลลัพธ์ (.mp4)',
 'Choose Output Location...': 'เลือกที่บันทึก...',
 '4) Trim Mode': '4) วิธีตัด',
 'Fast (FFmpeg, no re-encoding — cut may vary by up to ~2 sec near keyframes)': 'เร็ว (FFmpeg ไม่เข้ารหัสใหม่ — จุดตัดอาจคลาดเคลื่อนได้ถึง '
                                                                                '~2 วินาทีใกล้ keyframe)',
 'Precise (frame-by-frame re-encoding — exact cuts, slower)': 'แม่นยำ (เข้ารหัสใหม่ทีละเฟรม — ตัดตรงเป๊ะ แต่ช้ากว่า)',
 'Note: If FFmpeg is unavailable, precise mode will be used automatically.': 'หมายเหตุ: ถ้าไม่มี FFmpeg จะใช้โหมดแม่นยำโดยอัตโนมัติ',
 '🔗  Merge Videos': '🔗  รวมวิดีโอ',
 '1) Video List (merged top to bottom)': '1) รายการวิดีโอ (ต่อกันจากบนลงล่าง)',
 'Note: Videos with different sizes/resolutions will be adjusted to match the first file.': 'หมายเหตุ: '
                                                                                            'วิดีโอที่ขนาด/ความละเอียดต่างกันจะถูกปรับให้เท่ากับไฟล์แรก',
 '2) Output File (.mp4)': '2) ไฟล์ผลลัพธ์ (.mp4)',
 '🎬  Create Video': '🎬  สร้างวิดีโอ',
 '1) Image List (combined top to bottom)': '1) รายการภาพ (ต่อกันจากบนลงล่าง)',
 '+ Add Folder...': '+ เพิ่มโฟลเดอร์...',
 '+ Add Images...': '+ เพิ่มภาพ...',
 '0 images': '0 ภาพ',
 '2) Video Settings': '2) ตั้งค่าวิดีโอ',
 'FPS (frames per second):': 'FPS (เฟรมต่อวินาที):',
 '📁 Open': '📁 เปิด',
 '💾 Save': '💾 บันทึก',
 '💾 Save All': '💾 บันทึกทั้งหมด',
 '💾 Save As...': '💾 บันทึกเป็น...',
 '↶ Undo': '↶ ย้อนกลับ',
 '↷ Redo': '↷ ทำซ้ำ',
 '🤖 Model': '🤖 โมเดล',
 '🏷️ Classes': '🏷️ คลาส',
 '🔍 Search': '🔍 ค้นหา',
 '⌨️ Shortcuts': '⌨️ ปุ่มลัด',
 'Reviewed: 0/0 | Total: 0': 'ตรวจแล้ว: 0/0 | ทั้งหมด: 0',
 'Status Filter:': 'ตัวกรองสถานะ:',
 'Zoom:': 'ซูม:',
 'Reset': 'รีเซ็ต',
 '◄ Prev': '◄ ก่อนหน้า',
 'Next ►': 'ถัดไป ►',
 'Jump to Image:': 'ไปที่ภาพ:',
 'Go': 'ไป',
 'No dataset loaded': 'ยังไม่ได้เปิดชุดข้อมูล',
 'Active Class Setup': 'ตั้งค่าคลาสที่ใช้',
 'Active Class for new box:': 'คลาสที่ใช้กับกรอบใหม่:',
 'Type Class ID + Enter to apply': 'พิมพ์เลขคลาส + Enter เพื่อใช้',
 '📦 Current Image Boxes & Visibility': '📦 กรอบในภาพปัจจุบันและการแสดงผล',
 '📊 All Dataset Summary': '📊 สรุปทั้งชุดข้อมูล',
 '✂️ Dataset Curator & Splitter': '✂️ คัดเลือกและแบ่งชุดข้อมูล',
 '1. Model File (best.pt) — optional ranking aid': '1. ไฟล์โมเดล (best.pt) — ใช้ช่วยจัดอันดับ (ไม่บังคับ)',
 '2. Source Dataset (before train/valid/test split)': '2. ชุดข้อมูลต้นทาง (ก่อนแบ่ง train/valid/test)',
 '3. Output Folder (selected dataset)': '3. โฟลเดอร์ผลลัพธ์ (ชุดข้อมูลที่เลือกแล้ว)',
 'Scan Dataset': 'สแกนชุดข้อมูล',
 '4. Target Images per Class': '4. จำนวนภาพเป้าหมายต่อคลาส',
 'Use a large value (e.g. 999999) to keep all images for a class.': 'ใส่ค่ามาก ๆ (เช่น 999999) เพื่อเก็บภาพของคลาสนั้นทั้งหมด',
 'Start Curation': 'เริ่มคัดเลือก',
 'Cancel': 'ยกเลิก',
 'Dataset not scanned': 'ยังไม่ได้สแกนชุดข้อมูล',
 '1. Source Dataset (before split)': '1. ชุดข้อมูลต้นทาง (ก่อนแบ่ง)',
 '2. Output Dataset': '2. ชุดข้อมูลผลลัพธ์',
 '3. classes.txt (optional)': '3. classes.txt (ไม่บังคับ)',
 '4. Train / Valid / Test Split (%)': '4. สัดส่วน Train / Valid / Test (%)',
 '(must total 100)': '(ต้องรวมได้ 100)',
 'Start Split': 'เริ่มแบ่ง',
 '📊 Analytics & Dataset Insights': '📊 วิเคราะห์และข้อมูลเชิงลึกของชุดข้อมูล',
 '📁 Scan Dataset': '📁 สแกนชุดข้อมูล',
 'Total Images': 'จำนวนภาพทั้งหมด',
 'Total Objects': 'จำนวนวัตถุทั้งหมด',
 'Avg Objects/Image': 'วัตถุเฉลี่ยต่อภาพ',
 'Background Images': 'ภาพพื้นหลัง',
 'Overview': 'ภาพรวม',
 'Objects per Image': 'วัตถุต่อภาพ',
 'BBox Heat Map': 'Heat Map ของกรอบ',
 'Image Dimensions': 'ขนาดภาพ',
 '📈 Class Distribution': '📈 การกระจายของคลาส',
 'Class': 'คลาส',
 'Images': 'จำนวนภาพ',
 'Instances': 'จำนวนวัตถุ',
 'Share (%)': 'สัดส่วน (%)',
 'Scan a dataset to view this chart.': 'สแกนชุดข้อมูลเพื่อดูกราฟนี้',
 '📂 Open Video': '📂 เปิดวิดีโอ',
 'No video loaded': 'ยังไม่ได้เปิดวิดีโอ',
 '❓ Help': '❓ วิธีใช้',
 '📂 Load': '📂 โหลด',
 '🐍 Export .py': '🐍 ส่งออก .py',
 '🗑 Clear All': '🗑 ล้างทั้งหมด',
 '◀◀ 1s': '◀◀ 1 วินาที',
 '1s ▶▶': '1 วินาที ▶▶',
 'Go to frame:': 'ไปที่เฟรม:',
 '⤢ Reset View': '⤢ รีเซ็ตมุมมอง',
 'Zone Snap': 'ดูดติด Zone',
 'Snap to zone points / edges': 'ดูดติดจุด / ขอบของโซน',
 'Snap radius:': 'รัศมีดูดติด:',
 'Zone name': 'ชื่อโซน',
 'Name for the next zone:': 'ชื่อของโซนถัดไป:',
 '+ Save this name to the list below': '+ บันทึกชื่อนี้ลงรายการด้านล่าง',
 'Saved names (click, or type a number + Enter):': 'ชื่อที่บันทึกไว้ (คลิก หรือพิมพ์เลข + Enter):',
 '✕ Remove Selected': '✕ ลบที่เลือก',
 'Type a number + Enter to load a saved name': 'พิมพ์เลข + Enter เพื่อโหลดชื่อที่บันทึกไว้',
 '✔ Finish Zone': '✔ จบโซน',
 '✕ Cancel Draw': '✕ ยกเลิกการวาด',
 'Points placed: 0': 'จุดที่วางแล้ว: 0',
 'Zones': 'โซน',
 'Show name labels on canvas': 'แสดงชื่อโซนบนภาพ',
 'Pts': 'จุด',
 'Area px²': 'พื้นที่ px²',
 'Rename': 'เปลี่ยนชื่อ',
 '🎨 Color': '🎨 สี',
 '🏷 Toggle Label': '🏷 เปิด/ปิดชื่อ',
 'Delete': 'ลบ',
 'Open a video to begin.': 'เปิดวิดีโอเพื่อเริ่มต้น',
 '●  Dataset workspace': '●  พื้นที่ชุดข้อมูล',
 'valid split is empty; data.yaml uses train/images for validation': 'ชุด valid ว่างเปล่า; data.yaml ใช้ train/images เป็นชุดตรวจสอบ',
 'Multi Video Tool': 'เครื่องมือวิดีโอ (Multi Video Tool)',
 'Select video files': 'เลือกไฟล์วิดีโอ',
 'Select a folder containing videos': 'เลือกโฟลเดอร์ที่มีวิดีโอ',
 'Select output folder': 'เลือกโฟลเดอร์ผลลัพธ์',
 'Create New Folder': 'สร้างโฟลเดอร์ใหม่',
 'Enter a folder name:': 'ใส่ชื่อโฟลเดอร์:',
 'Select Video to Trim': 'เลือกวิดีโอที่จะตัด',
 'Save Trimmed Video As...': 'บันทึกวิดีโอที่ตัดแล้วเป็น...',
 'Select Videos to Merge (multiple files allowed)': 'เลือกวิดีโอที่จะรวม (เลือกได้หลายไฟล์)',
 'Save Merged Video As...': 'บันทึกวิดีโอที่รวมแล้วเป็น...',
 'Select Images to Combine (multiple files allowed)': 'เลือกภาพที่จะรวม (เลือกได้หลายไฟล์)',
 'Select Image Folder (sorted by filename)': 'เลือกโฟลเดอร์ภาพ (เรียงตามชื่อไฟล์)',
 'Save Video As...': 'บันทึกวิดีโอเป็น...',
 'No videos found': 'ไม่พบวิดีโอ',
 'No video files were found in the selected folder or any subfolder.': 'ไม่พบไฟล์วิดีโอในโฟลเดอร์ที่เลือกหรือโฟลเดอร์ย่อยใด ๆ',
 'Error': 'ข้อผิดพลาด',
 'Add at least one video first.': 'กรุณาเพิ่มวิดีโออย่างน้อยหนึ่งไฟล์ก่อน',
 'End of Video': 'ท้ายวิดีโอ',
 'Video duration is unknown. Please select a video first.': 'ไม่ทราบความยาววิดีโอ กรุณาเลือกวิดีโอก่อน',
 'Please specify an output file first.': 'กรุณาระบุไฟล์ผลลัพธ์ก่อน',
 'Please select at least 2 videos to merge.': 'กรุณาเลือกวิดีโออย่างน้อย 2 ไฟล์เพื่อรวม',
 'No image files found in the selected folder.': 'ไม่พบไฟล์ภาพในโฟลเดอร์ที่เลือก',
 'Please select at least 1 image first.': 'กรุณาเลือกภาพอย่างน้อย 1 ภาพก่อน',
 '(Invalid frame rate)': '(อัตราเฟรมไม่ถูกต้อง)',
 '(Invalid resize format, e.g. 1280x720)': '(รูปแบบขนาดไม่ถูกต้อง เช่น 1280x720)',
 'Invalid Input': 'ข้อมูลไม่ถูกต้อง',
 'Invalid Time': 'เวลาไม่ถูกต้อง',
 'Please enter a valid FPS value (greater than 0).': 'กรุณาใส่ค่า FPS ที่ถูกต้อง (มากกว่า 0)',
 'Manage Classes & Colors': 'จัดการคลาสและสี',
 'Add new class (several: separate with commas)': 'เพิ่มคลาสใหม่ (หลายคลาส: คั่นด้วยจุลภาค)',
 'Import classes': 'นำเข้าคลาส',
 'From loaded model': 'จากโมเดลที่โหลดไว้',
 'Rename class': 'เปลี่ยนชื่อคลาส',
 'Choose a model (.pt) or class list (classes.txt / data.yaml)': 'เลือกโมเดล (.pt) หรือรายการคลาส (classes.txt / data.yaml)',
 'Merge classes': 'รวมคลาส',
 'Map each class': 'จับคู่แต่ละคลาส',
 'Select one class': 'เลือกหนึ่งคลาส',
 'Change class order': 'เปลี่ยนลำดับคลาส',
 'Changing the order changes YOLO class IDs and updates every label file in this dataset.\n\nContinue?': 'การเปลี่ยนลำดับจะเปลี่ยน class '
                                                                                                         'ID ของ YOLO '
                                                                                                         'และแก้ไฟล์ป้ายกำกับทุกไฟล์ในชุดข้อมูลนี้\n'
                                                                                                         '\n'
                                                                                                         'ดำเนินการต่อหรือไม่?',
 'Select classes': 'เลือกคลาส',
 'Select one or more classes to delete.': 'เลือกคลาสที่จะลบอย่างน้อยหนึ่งคลาส',
 'Delete classes': 'ลบคลาส',
 'Select two or more classes to merge (Ctrl/Shift+click).': 'เลือกคลาสที่จะรวมตั้งแต่สองคลาสขึ้นไป (Ctrl/Shift+คลิก)',
 'Add class': 'เพิ่มคลาส',
 'Those classes already exist.': 'มีคลาสเหล่านี้อยู่แล้ว',
 'Select YOLO model (best.pt)': 'เลือกโมเดล YOLO (best.pt)',
 'Enter a name.': 'กรุณาใส่ชื่อ',
 'Classes  (click to select, Ctrl/Shift for several, double-click to rename)': 'คลาส  (คลิกเพื่อเลือก, Ctrl/Shift เพื่อเลือกหลายคลาส, '
                                                                               'ดับเบิลคลิกเพื่อเปลี่ยนชื่อ)',
 'Add': 'เพิ่ม',
 'From model / file…': 'จากโมเดล / ไฟล์…',
 'Model → my classes…': 'โมเดล → คลาสของฉัน…',
 'Class change': 'เปลี่ยนคลาส',
 'Keep which class id?': 'จะเก็บ class id ไหนไว้?',
 'Merged class name:': 'ชื่อคลาสที่รวมแล้ว:',
 'Merge': 'รวม',
 'Use these as my class list (replace). Labels I already made follow by name;\nmy classes that match none of them are kept at the end.': 'ใช้รายการนี้เป็นคลาสของฉัน '
                                                                                                                                         '(แทนที่) '
                                                                                                                                         'ป้ายกำกับที่ทำไว้แล้วจะตามชื่อ\n'
                                                                                                                                         'ส่วนคลาสของฉันที่ไม่ตรงกับรายการนี้จะถูกเก็บไว้ท้ายสุด',
 'Keep my classes and choose where each one goes (map / merge / skip / add new).': 'เก็บคลาสของฉันไว้ แล้วเลือกว่าแต่ละคลาสจะไปไหน (จับคู่ '
                                                                                   '/ รวม / ข้าม / เพิ่มใหม่)',
 'Auto-match': 'จับคู่อัตโนมัติ',
 'All → new class': 'ทั้งหมด → คลาสใหม่',
 'All → skip': 'ทั้งหมด → ข้าม',
 'Apply': 'ใช้',
 'Could not load this model.': 'โหลดโมเดลนี้ไม่ได้',
 'Replace class list': 'แทนที่รายการคลาส',
 'Your class list will be replaced and label files updated to the new class IDs.\n\nContinue?': 'รายการคลาสของคุณจะถูกแทนที่ '
                                                                                                'และไฟล์ป้ายกำกับจะถูกแก้เป็น class ID '
                                                                                                'ใหม่\n'
                                                                                                '\n'
                                                                                                'ดำเนินการต่อหรือไม่?',
 'Select dataset folder': 'เลือกโฟลเดอร์ชุดข้อมูล',
 'Object Count per Image': 'จำนวนวัตถุต่อภาพ',
 'Frequency (number of images)': 'ความถี่ (จำนวนภาพ)',
 'Horizontal position (0 = left, 1 = right)': 'ตำแหน่งแนวนอน (0 = ซ้าย, 1 = ขวา)',
 'Vertical position (0 = bottom, 1 = top)': 'ตำแหน่งแนวตั้ง (0 = ล่าง, 1 = บน)',
 'Width (pixels)': 'ความกว้าง (พิกเซล)',
 'Height (pixels)': 'ความสูง (พิกเซล)',
 'No image files found in the selected folder. Check the dataset layout.': 'ไม่พบไฟล์ภาพในโฟลเดอร์ที่เลือก ตรวจสอบโครงสร้างชุดข้อมูล',
 'All': 'ทั้งหมด',
 'Reviewed': 'ตรวจแล้ว',
 'Unreviewed': 'ยังไม่ตรวจ',
 'Labeled': 'ติดป้ายแล้ว',
 'Unlabeled': 'ยังไม่ติดป้าย',
 'Keyboard Shortcuts Cheat Sheet': 'สรุปปุ่มลัด',
 'Shortcut / Action': 'ปุ่มลัด / การกระทำ',
 'Description': 'คำอธิบาย',
 'Advanced Image Search Filter': 'ตัวกรองค้นหาภาพขั้นสูง',
 'Matching Rule': 'เงื่อนไขการจับคู่',
 'Select Classes to Search': 'เลือกคลาสที่จะค้นหา',
 'Model classes do not match': 'คลาสของโมเดลไม่ตรงกัน',
 'Select Auto-labeled Output Directory': 'เลือกโฟลเดอร์ผลลัพธ์ของ Auto-Label',
 'No YOLO model is loaded.\n\nYes  = load a YOLO model file\nNo   = label from boxes you already drew (no model needed)\nCancel = do nothing': 'ยังไม่ได้โหลดโมเดล '
                                                                                                                                               'YOLO\n'
                                                                                                                                               '\n'
                                                                                                                                               'Yes  '
                                                                                                                                               '= '
                                                                                                                                               'โหลดไฟล์โมเดล '
                                                                                                                                               'YOLO\n'
                                                                                                                                               'No   '
                                                                                                                                               '= '
                                                                                                                                               'ติดป้ายจากกรอบที่คุณวาดไว้แล้ว '
                                                                                                                                               '(ไม่ต้องใช้โมเดล)\n'
                                                                                                                                               'Cancel '
                                                                                                                                               '= '
                                                                                                                                               'ไม่ทำอะไร',
 'Reference match threshold': 'เกณฑ์ความคล้ายของ Reference',
 'Minimum similarity (0.30-0.99).\nHigher = fewer, safer boxes. Lower = more boxes, more mistakes.\nEvery result should still be reviewed.': 'ความคล้ายขั้นต่ำ '
                                                                                                                                             '(0.30-0.99)\n'
                                                                                                                                             'สูง '
                                                                                                                                             '= '
                                                                                                                                             'กรอบน้อยแต่ปลอดภัยกว่า '
                                                                                                                                             'ต่ำ '
                                                                                                                                             '= '
                                                                                                                                             'กรอบมากแต่ผิดพลาดมากกว่า\n'
                                                                                                                                             'ควรตรวจทุกผลลัพธ์อีกครั้งเสมอ',
 'Select output folder for Save As': 'เลือกโฟลเดอร์ผลลัพธ์สำหรับ บันทึกเป็น',
 'Save Dataset As': 'บันทึกชุดข้อมูลเป็น',
 'Dataset folder name:': 'ชื่อโฟลเดอร์ชุดข้อมูล:',
 'Save As Complete': 'บันทึกเป็นเสร็จสิ้น',
 'Save All': 'บันทึกทั้งหมด',
 'Saved labels directly to dataset folder!': 'บันทึกป้ายกำกับลงโฟลเดอร์ชุดข้อมูลโดยตรงแล้ว!',
 'Warning': 'คำเตือน',
 'Enter an image number.': 'กรุณาใส่เลขภาพ',
 'Info': 'ข้อมูล',
 'No classes available to filter.': 'ไม่มีคลาสให้กรอง',
 'Class update warning': 'คำเตือนการอัปเดตคลาส',
 'No valid image files found!': 'ไม่พบไฟล์ภาพที่ใช้ได้!',
 'No Reference Boxes': 'ไม่มีกรอบอ้างอิง',
 'Draw boxes on a few images first (and save them). Reference mode learns from images that already have labels.': 'วาดกรอบในภาพสองสามภาพก่อน '
                                                                                                                  '(แล้วบันทึก) โหมด '
                                                                                                                  'Reference '
                                                                                                                  'เรียนรู้จากภาพที่มีป้ายกำกับอยู่แล้ว',
 'Dataset Not Open': 'ยังไม่ได้เปิดชุดข้อมูล',
 'Open a dataset folder first.': 'กรุณาเปิดโฟลเดอร์ชุดข้อมูลก่อน',
 'Auto-Label Complete': 'Auto-Label เสร็จสิ้น',
 'Open a dataset folder before starting Batch Auto-Label.': 'กรุณาเปิดโฟลเดอร์ชุดข้อมูลก่อนเริ่ม Batch Auto-Label',
 'A batch job is already running.': 'มีงาน Batch กำลังทำงานอยู่แล้ว',
 'Nothing to Process': 'ไม่มีอะไรให้ประมวลผล',
 'All images already have labels. Batch Auto-Label skips labeled images.': 'ทุกภาพมีป้ายกำกับแล้ว Batch Auto-Label จะข้ามภาพที่ติดป้ายแล้ว',
 'Confirm Batch Auto-Label': 'ยืนยัน Batch Auto-Label',
 'No images match current filter criteria!': 'ไม่มีภาพที่ตรงกับเงื่อนไขตัวกรอง!',
 'Save As': 'บันทึกเป็น',
 'Open a dataset first.': 'กรุณาเปิดชุดข้อมูลก่อน',
 '⌨️ Keyboard Shortcuts': '⌨️ ปุ่มลัด',
 '🔍 Filter Images by Class Occurrence': '🔍 กรองภาพตามคลาสที่ปรากฏ',
 'OR (Has AT LEAST ONE selected class)': 'OR (มีคลาสที่เลือกอย่างน้อยหนึ่งคลาส)',
 'AND (Must contain ALL selected classes together)': 'AND (ต้องมีคลาสที่เลือกครบทุกคลาสพร้อมกัน)',
 'Apply Filter': 'ใช้ตัวกรอง',
 'Reset Search': 'รีเซ็ตการค้นหา',
 'Model Loaded': 'โหลดโมเดลแล้ว',
 'Model Load Failed': 'โหลดโมเดลไม่สำเร็จ',
 'Batch Auto-Label: reading reference boxes...': 'Batch Auto-Label: กำลังอ่านกรอบอ้างอิง...',
 'Select model file': 'เลือกไฟล์โมเดล',
 'Select source dataset': 'เลือกชุดข้อมูลต้นทาง',
 'Scanning...': 'กำลังสแกน...',
 'Curating dataset...': 'กำลังคัดเลือกชุดข้อมูล...',
 'Select classes.txt': 'เลือก classes.txt',
 'Scan complete. Review the split and start.': 'สแกนเสร็จแล้ว ตรวจสอบสัดส่วนแล้วเริ่มได้เลย',
 'Splitting dataset...': 'กำลังแบ่งชุดข้อมูล...',
 'Missing Information': 'ข้อมูลไม่ครบ',
 'Select a model file and source dataset before scanning.': 'กรุณาเลือกไฟล์โมเดลและชุดข้อมูลต้นทางก่อนสแกน',
 'Not Scanned': 'ยังไม่ได้สแกน',
 'Scan the dataset first.': 'กรุณาสแกนชุดข้อมูลก่อน',
 'Select an output folder first.': 'กรุณาเลือกโฟลเดอร์ผลลัพธ์ก่อน',
 'Cancelling...': 'กำลังยกเลิก...',
 'Select a source dataset first.': 'กรุณาเลือกชุดข้อมูลต้นทางก่อน',
 'Split Total Error': 'ผลรวมสัดส่วนไม่ถูกต้อง',
 'Current Images': 'จำนวนภาพปัจจุบัน',
 'Target Images': 'จำนวนภาพเป้าหมาย',
 'Invalid Number': 'ตัวเลขไม่ถูกต้อง',
 'Target values must be whole numbers.': 'ค่าเป้าหมายต้องเป็นจำนวนเต็ม',
 'Train/valid/test ratios must be numeric.': 'สัดส่วน train/valid/test ต้องเป็นตัวเลข',
 'Warnings (classes with too few images for all three splits):': 'คำเตือน (คลาสที่มีภาพน้อยเกินไปสำหรับทั้งสามชุด):',
 'Copying files...': 'กำลังคัดลอกไฟล์...',
 'Computing difficulty (prediction vs. ground truth)...': 'กำลังคำนวณความยาก (ผลทำนายเทียบกับค่าจริง)...',
 'Selecting images...': 'กำลังเลือกภาพ...',
 'Could Not Load Video Tool': 'โหลดเครื่องมือวิดีโอไม่ได้',
 'Could Not Load Other': 'โหลด Other ไม่ได้',
 'Name': 'ชื่อ',
 'Select a video': 'เลือกวิดีโอ',
 'How to draw / edit a zone': 'วิธีวาด / แก้ไขโซน',
 'Undid last zone change.': 'ย้อนการแก้ไขโซนล่าสุดแล้ว',
 'Redid zone change.': 'ทำซ้ำการแก้ไขโซนแล้ว',
 'Rename zone': 'เปลี่ยนชื่อโซน',
 'New name:': 'ชื่อใหม่:',
 'Delete zone': 'ลบโซน',
 'Clear all zones': 'ล้างโซนทั้งหมด',
 'Delete every zone? You can Undo this afterward.': 'ลบโซนทั้งหมดหรือไม่? ย้อนกลับได้ภายหลัง',
 'Save zones': 'บันทึกโซน',
 'Saved': 'บันทึกแล้ว',
 'Load zones': 'โหลดโซน',
 'Zone code (Python)': 'โค้ดโซน (Python)',
 'Enter a frame number.': 'กรุณาใส่เลขเฟรม',
 'Missing name': 'ยังไม่มีชื่อ',
 'Type a name in the field above first.': 'กรุณาพิมพ์ชื่อในช่องด้านบนก่อน',
 'No selection': 'ยังไม่ได้เลือก',
 'Select a saved name from the list first.': 'กรุณาเลือกชื่อที่บันทึกไว้จากรายการก่อน',
 'Nothing to undo.': 'ไม่มีอะไรให้ย้อน',
 'Nothing to redo.': 'ไม่มีอะไรให้ทำซ้ำ',
 'Not enough points': 'จุดไม่พอ',
 'A zone needs at least 3 points.': 'โซนต้องมีอย่างน้อย 3 จุด',
 'Please name the zone before finishing it.': 'กรุณาตั้งชื่อโซนก่อนจบ',
 'Select one zone': 'เลือกหนึ่งโซน',
 'Rename needs exactly one zone selected.': 'การเปลี่ยนชื่อต้องเลือกโซนเพียงหนึ่งโซน',
 'Select one or more zones from the list first.': 'กรุณาเลือกโซนอย่างน้อยหนึ่งโซนจากรายการก่อน',
 'Nothing to save': 'ไม่มีอะไรให้บันทึก',
 'No zones have been drawn yet.': 'ยังไม่ได้วาดโซนใด ๆ',
 'Nothing to export': 'ไม่มีอะไรให้ส่งออก',
 'Copied to clipboard.': 'คัดลอกไปยังคลิปบอร์ดแล้ว',
 'Save zone code': 'บันทึกโค้ดโซน',
 'Open new video': 'เปิดวิดีโอใหม่',
 "Opening a new video will clear the zones you've drawn so far (save them first if you want to keep them). Continue?": 'การเปิดวิดีโอใหม่จะล้างโซนที่วาดไว้ทั้งหมด '
                                                                                                                       '(บันทึกก่อนถ้าอยากเก็บไว้) '
                                                                                                                       'ดำเนินการต่อหรือไม่?',
 'Save failed': 'บันทึกไม่สำเร็จ',
 'Load failed': 'โหลดไม่สำเร็จ',
 '📋 Copy to Clipboard': '📋 คัดลอกไปคลิปบอร์ด',
 '💾 Save as .py': '💾 บันทึกเป็น .py',
 'Close': 'ปิด',
 'Cannot delete': 'ลบไม่ได้',
 'Resolution mismatch': 'ความละเอียดไม่ตรงกัน',
 '[WARN] Dedup is on - parts are processed one after another so the comparison stays in order': '[WARN] เปิด dedup อยู่ — '
                                                                                                'ประมวลผลทีละส่วนต่อเนื่องกัน '
                                                                                                'เพื่อให้การเปรียบเทียบเรียงลำดับถูกต้อง',
 '            (this is slower than without dedup)': '            (ช้ากว่าตอนไม่เปิด dedup)',
 '[INFO] dedup: fewer than 2 frames were compared': '[INFO] dedup: เปรียบเทียบได้น้อยกว่า 2 เฟรม',
 '[CANCELLED] Stopped before the next video': '[CANCELLED] หยุดก่อนวิดีโอถัดไป',
 '[INFO] Fast mode with ffmpeg (no re-encoding)...': '[INFO] โหมดเร็วด้วย ffmpeg (ไม่เข้ารหัสใหม่)...',
 '[WARN] ffmpeg did not produce an output file': '[WARN] ffmpeg ไม่ได้สร้างไฟล์ผลลัพธ์',
 '[INFO] Falling back to precise mode (frame by frame)': '[INFO] สลับไปใช้โหมดแม่นยำ (ทีละเฟรม)',
 '[WARN] ffmpeg was not found - using precise mode (frame by frame)': '[WARN] ไม่พบ ffmpeg — ใช้โหมดแม่นยำ (ทีละเฟรม)',
 '[ERROR] Invalid range (the end must be after the start)': '[ERROR] ช่วงไม่ถูกต้อง (เวลาจบต้องอยู่หลังเวลาเริ่ม)',
 '[ERROR] No frames were written': '[ERROR] ไม่มีเฟรมถูกเขียนเลย',
 '[ERROR] Select at least 2 videos': '[ERROR] เลือกวิดีโออย่างน้อย 2 ไฟล์',
 '[WARN] ffmpeg was not found - using precise mode': '[WARN] ไม่พบ ffmpeg — ใช้โหมดแม่นยำ',
 '[ERROR] Select at least 1 image': '[ERROR] เลือกภาพอย่างน้อย 1 ภาพ',
 '[ERROR] FPS must be greater than 0': '[ERROR] FPS ต้องมากกว่า 0',
 '\n⏹ Cancelled.': '\n⏹ ยกเลิกแล้ว',
 '\n✅ Done!': '\n✅ เสร็จแล้ว!',
 '\n[...] Stopping...': '\n[...] กำลังหยุด...',
 '\n✅ Trim completed.': '\n✅ ตัดวิดีโอเสร็จแล้ว',
 '\n❌ Trim failed.': '\n❌ ตัดวิดีโอไม่สำเร็จ',
 '\n✅ Merge completed.': '\n✅ รวมวิดีโอเสร็จแล้ว',
 '\n❌ Merge failed.': '\n❌ รวมวิดีโอไม่สำเร็จ',
 '\n✅ Video creation completed.': '\n✅ สร้างวิดีโอเสร็จแล้ว',
 '\n❌ Video creation failed.': '\n❌ สร้างวิดีโอไม่สำเร็จ',
 'No start or end time is set. Trim the entire clip?': 'ยังไม่ได้กำหนดเวลาเริ่มหรือจบ ตัดทั้งคลิปหรือไม่?',
 'Note: the images are combined in the order listed. Use "Clear All" to start over (the order follows the list, top to bottom).': 'หมายเหตุ: '
                                                                                                                                  'ภาพจะถูกต่อตามลำดับในรายการ '
                                                                                                                                  '(จากบนลงล่าง) '
                                                                                                                                  'กด '
                                                                                                                                  '"ล้างทั้งหมด" '
                                                                                                                                  'เพื่อเริ่มใหม่',
 '  (maximum estimate; deduplication may reduce the final count)': '  (ค่าประมาณสูงสุด; การตัดภาพซ้ำอาจทำให้จำนวนจริงน้อยลง)',
 '＋ New class': '＋ คลาสใหม่',
 '✕ Skip (ignore)': '✕ ข้าม (ไม่ใช้)',
 'Model or class list': 'โมเดลหรือรายการคลาส',
 'PyTorch Model': 'โมเดล PyTorch',
 'PyTorch model': 'โมเดล PyTorch',
 'Histogram of Object Count by Image': 'ฮิสโทแกรมจำนวนวัตถุต่อภาพ',
 'Annotation Heat Map': 'Heat Map ของกรอบที่ติดป้าย',
 'Dimension Insights': 'ข้อมูลเชิงลึกของขนาด',
 '✓ Reviewed': '✓ ตรวจแล้ว',
 '⚠ Unreviewed': '⚠ ยังไม่ตรวจ',
 'Class Breakdown (Whole Folder):': 'แยกตามคลาส (ทั้งโฟลเดอร์):',
 'No usable reference boxes were found in the other labeled images.': 'ไม่พบกรอบอ้างอิงที่ใช้ได้ในภาพอื่นที่ติดป้ายแล้ว',
 'No usable reference boxes were found in the labeled images.': 'ไม่พบกรอบอ้างอิงที่ใช้ได้ในภาพที่ติดป้ายแล้ว',
 'At least one split ratio must be greater than 0.': 'สัดส่วนการแบ่งอย่างน้อยหนึ่งชุดต้องมากกว่า 0',
 'Ultralytics is not installed. Please run: pip install ultralytics': 'ยังไม่ได้ติดตั้ง Ultralytics กรุณารัน: pip install ultralytics',
 'Out of GPU memory even with batch size 1 - the GPU is too small for this model. Use a smaller model (e.g. yolo26n/yolo26s instead of yolo26m)': 'หน่วยความจำ '
                                                                                                                                                  'GPU '
                                                                                                                                                  'ไม่พอแม้ใช้ '
                                                                                                                                                  'batch '
                                                                                                                                                  'size '
                                                                                                                                                  '1 '
                                                                                                                                                  '— '
                                                                                                                                                  'GPU '
                                                                                                                                                  'เล็กเกินไปสำหรับโมเดลนี้ '
                                                                                                                                                  'ใช้โมเดลที่เล็กกว่า '
                                                                                                                                                  '(เช่น '
                                                                                                                                                  'yolo26n/yolo26s '
                                                                                                                                                  'แทน '
                                                                                                                                                  'yolo26m)',
 '(no video loaded)': '(ยังไม่ได้เปิดวิดีโอ)',
 'Python file': 'ไฟล์ Python',
 'Video files': 'ไฟล์วิดีโอ',
 'Image files': 'ไฟล์ภาพ',
 'Process videos one at a time instead of in parallel (slower, uses less memory)': 'ประมวลผลวิดีโอทีละไฟล์แทนพร้อมกัน (ช้ากว่า '
                                                                                   'ใช้หน่วยความจำน้อยกว่า)',
 '1. Extract Frames': '1. ดึงเฟรม',
 '[WARN] The videos differ in size/fps/codec, so they cannot be joined without re-encoding (precise mode is used instead of ffmpeg copy)': '[WARN] '
                                                                                                                                           'วิดีโอมีขนาด/fps/codec '
                                                                                                                                           'ไม่ตรงกัน '
                                                                                                                                           'จึงรวมโดยไม่เข้ารหัสใหม่ไม่ได้ '
                                                                                                                                           '(ใช้โหมดแม่นยำแทน '
                                                                                                                                           'ffmpeg '
                                                                                                                                           'copy)',
 'Previous image': 'ภาพก่อนหน้า',
 'Review and go to next image': 'ทำเครื่องหมายว่าตรวจแล้วและไปภาพถัดไป',
 'Enter Class ID and press Enter': 'พิมพ์ Class ID แล้วกด Enter',
 'Delete typed digits / selected BBox': 'ลบตัวเลขที่พิมพ์ / กรอบที่เลือก',
 'Delete selected BBox': 'ลบกรอบที่เลือก',
 'Right click → left click': 'คลิกขวา → คลิกซ้าย',
 'Right-click a BBox, then left-click again to delete': 'คลิกขวาที่กรอบ แล้วคลิกซ้ายอีกครั้งเพื่อลบ',
 'Save current image': 'บันทึกภาพปัจจุบัน',
 'Undo': 'ย้อนกลับ',
 'Redo': 'ทำซ้ำ',
 'Cancel Class ID entry': 'ยกเลิกการพิมพ์ Class ID',
 'Scroll Wheel': 'ล้อเมาส์',
 'Zoom in / out': 'ซูมเข้า / ออก',
 'Right click + drag': 'คลิกขวา + ลาก',
 'Pan image': 'เลื่อนภาพ',
 'Double left click (empty area)': 'ดับเบิลคลิกซ้าย (พื้นที่ว่าง)',
 'Double right click (empty area)': 'ดับเบิลคลิกขวา (พื้นที่ว่าง)',
 '1) Left-click to place polygon points (need 3+)\n2) Right-click to undo the last point; right-click + drag pans the view\n3) Set a name below (before or after drawing) — or type a saved name\'s number + Enter to recall it\n4) Click back near the first point, press Enter, double-click, or press "Finish Zone" to close it\n5) Select ONE zone in the list to drag its points; right-click a point to delete it. Ctrl/Shift-click to select several zones at once — color, label toggle, and delete apply to all of them\n6) Shift constrains a new segment perpendicular to the selected reference (X/Y/Z, custom, or previous segment)\n7) Zone Snap makes new/edit points share exact coordinates with existing zone vertices or any point on existing edges\n8) Scroll wheel zooms toward the cursor; Undo/Redo (or Ctrl+Z / Ctrl+Y) step through zone changes': '1) '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             'คลิกซ้ายเพื่อวางจุดของรูปหลายเหลี่ยม '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             '(ต้องมี '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             '3 '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             'จุดขึ้นไป)\n'
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             '2) '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             'คลิกขวาเพื่อย้อนจุดล่าสุด; '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             'คลิกขวา '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             '+ '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             'ลาก '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             '= '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             'เลื่อนมุมมอง\n'
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             '3) '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             'ตั้งชื่อด้านล่าง '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             '(ก่อนหรือหลังวาดก็ได้) '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             '— '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             'หรือพิมพ์เลขของชื่อที่บันทึกไว้ '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             '+ '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             'Enter '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             'เพื่อเรียกใช้\n'
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             '4) '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             'คลิกกลับใกล้จุดแรก '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             'กด '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             'Enter '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             'ดับเบิลคลิก '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             'หรือกด '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             '"จบโซน" '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             'เพื่อปิดรูป\n'
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             '5) '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             'เลือกโซนเดียวในรายการเพื่อลากจุด; '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             'คลิกขวาที่จุดเพื่อลบ '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             'Ctrl/Shift+คลิกเพื่อเลือกหลายโซนพร้อมกัน '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             '— '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             'การเปลี่ยนสี '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             'เปิด/ปิดชื่อ '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             'และการลบจะใช้กับทุกโซนที่เลือก\n'
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             '6) '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             'กด '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             'Shift '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             'เพื่อบังคับให้ส่วนใหม่ตั้งฉากกับแนวอ้างอิงที่เลือก '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             '(X/Y/Z '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             'กำหนดเอง '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             'หรือส่วนก่อนหน้า)\n'
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             '7) '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             'ดูดติด '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             'Zone '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             'ทำให้จุดใหม่/จุดที่แก้ใช้พิกัดเดียวกับจุดยอดของโซนเดิม '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             'หรือจุดใด '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             'ๆ '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             'บนขอบที่มีอยู่\n'
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             '8) '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             'ล้อเมาส์ซูมเข้าหาเคอร์เซอร์; '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             'ย้อนกลับ/ทำซ้ำ '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             '(หรือ '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             'Ctrl+Z '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             '/ '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             'Ctrl+Y) '
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             'ย้อนไปตามการแก้ไขโซน'}

TEMPLATES = {'{0} — unreadable: {1}': '{0} — อ่านไม่ได้: {1}',
 '{0}:{1} — negative class id': '{0}:{1} — class id ติดลบ',
 '{0}:{1} — expected YOLO 5+ fields': '{0}:{1} — ต้องมีอย่างน้อย 5 ช่องตามรูปแบบ YOLO',
 '{0}:{1} — coordinates outside 0..1': '{0}:{1} — พิกัดอยู่นอกช่วง 0..1',
 '{0}:{1} — invalid class id': '{0}:{1} — class id ไม่ถูกต้อง',
 '{0}:{1} — non-numeric coordinates': '{0}:{1} — พิกัดไม่ใช่ตัวเลข',
 'class {0}: {1} image(s), cannot appear in every split': 'คลาส {0}: มี {1} ภาพ จึงอยู่ครบทุกชุดไม่ได้',
 '[INFO] Processing in {0} part(s) (frame ranges / threads)': '[INFO] แบ่งประมวลผลเป็น {0} ส่วน (ช่วงเฟรม / เธรด)',
 '[INFO] {0}: {1} FPS, {2} frames, {3} seconds': '[INFO] {0}: {1} FPS, {2} เฟรม, {3} วินาที',
 '[INFO] Taking one frame every {0} frames (frames {1}-{2})': '[INFO] เก็บ 1 เฟรมทุก ๆ {0} เฟรม (เฟรม {1}-{2})',
 '[INFO] Using {0} parallel worker(s) ({1} videos)': '[INFO] ใช้ {0} ตัวทำงานพร้อมกัน ({1} วิดีโอ)',
 '[DONE] ffmpeg -> {0}': '[DONE] ffmpeg -> {0}',
 '[INFO] Trimming {0}: {1} - {2} ({3} frames)': '[INFO] กำลังตัด {0}: {1} - {2} ({3} เฟรม)',
 '[DONE] {0} frames written -> {1}': '[DONE] เขียน {0} เฟรมแล้ว -> {1}',
 '[DONE] {0} videos merged, {1} frames -> {2}': '[DONE] รวม {0} วิดีโอ รวม {1} เฟรม -> {2}',
 '[INFO] Creating a video from {0} images at {1} FPS (size {2}x{3})...': '[INFO] กำลังสร้างวิดีโอจาก {0} ภาพ ที่ {1} FPS (ขนาด {2}x{3})...',
 '[DONE] {0} frames (~{1} seconds) -> {2}': '[DONE] {0} เฟรม (~{1} วินาที) -> {2}',
 '[ERROR] Cannot open the video (frames {0}-{1}): {2}': '[ERROR] เปิดวิดีโอไม่ได้ (เฟรม {0}-{1}): {2}',
 '[ERROR] Cannot read the video information: {0}': '[ERROR] อ่านข้อมูลวิดีโอไม่ได้: {0}',
 '[CANCELLED] Stopped - {0} images saved -> {1}': '[CANCELLED] หยุดแล้ว — บันทึกไป {0} ภาพ -> {1}',
 '[DONE] {0} images saved -> {1}': '[DONE] บันทึก {0} ภาพแล้ว -> {1}',
 '\n[SUMMARY] {0} images saved from {1} videos': '\n[SUMMARY] บันทึก {0} ภาพจาก {1} วิดีโอ',
 '[WARN] ffmpeg reported an error: {0}': '[WARN] ffmpeg แจ้งข้อผิดพลาด: {0}',
 '[ERROR] Cannot create the output file: {0}': '[ERROR] สร้างไฟล์ผลลัพธ์ไม่ได้: {0}',
 '[INFO] ({0}/{1}) Adding: {2}': '[INFO] ({0}/{1}) กำลังเพิ่ม: {2}',
 '[CANCELLED] Stopped - {0} frames written': '[CANCELLED] หยุดแล้ว — เขียนไป {0} เฟรม',
 '[ERROR] Cannot read the image: {0}': '[ERROR] อ่านภาพไม่ได้: {0}',
 '{0} videos': '{0} วิดีโอ',
 '[WARN] No video files found: {0}': '[WARN] ไม่พบไฟล์วิดีโอ: {0}',
 '[ERROR] Input not found: {0}': '[ERROR] ไม่พบอินพุต: {0}',
 '[WARN] Could not run ffmpeg: {0}': '[WARN] เรียก ffmpeg ไม่ได้: {0}',
 '[WARN] Cannot open: {0}': '[WARN] เปิดไม่ได้: {0}',
 '[INFO] {0} is {1}x{2}, different from the first video ({3}x{4}) - resizing': '[INFO] {0} ขนาด {1}x{2} ต่างจากวิดีโอแรก ({3}x{4}) — '
                                                                               'กำลังปรับขนาด',
 '[WARN] Cannot read the image, skipped: {0}': '[WARN] อ่านภาพไม่ได้ ข้ามไป: {0}',
 '- {0}: ~{1} frames': '- {0}: ~{1} เฟรม',
 'Video {0}/{1}: {2}': 'วิดีโอ {0}/{1}: {2}',
 '[WARN] Could not write the image: {0}': '[WARN] เขียนภาพไม่ได้: {0}',
 '[INFO] dedup: skipped {0}/{1} similar frames (difference min {2}%, max {3}%, average {4}% | threshold {5}%)': '[INFO] dedup: ข้าม '
                                                                                                                '{0}/{1} เฟรมที่คล้ายกัน '
                                                                                                                '(ความต่างต่ำสุด {2}%, '
                                                                                                                'สูงสุด {3}%, เฉลี่ย {4}% '
                                                                                                                '| เกณฑ์ {5}%)',
 'Could not create folder: {0}': 'สร้างโฟลเดอร์ไม่ได้: {0}',
 '• {0}: Calculating...': '• {0}: กำลังคำนวณ...',
 '[ERROR] {0}': '[ERROR] {0}',
 '[WARN] Even the smallest difference ({0}%) is above the threshold ({1}%) - nothing was skipped; the video may contain noise or fast motion. Try a higher dedup level.': '[WARN] '
                                                                                                                                                                          'แม้ความต่างที่น้อยที่สุด '
                                                                                                                                                                          '({0}%) '
                                                                                                                                                                          'ก็ยังเกินเกณฑ์ '
                                                                                                                                                                          '({1}%) '
                                                                                                                                                                          '— '
                                                                                                                                                                          'จึงไม่ได้ข้ามเฟรมใดเลย '
                                                                                                                                                                          'วิดีโออาจมี '
                                                                                                                                                                          'noise '
                                                                                                                                                                          'หรือภาพเคลื่อนไหวเร็ว '
                                                                                                                                                                          'ลองเพิ่มระดับ '
                                                                                                                                                                          'dedup',
 '[ERROR] {0}: {1}': '[ERROR] {0}: {1}',
 '• {0}: (Invalid time range)': '• {0}: (ช่วงเวลาไม่ถูกต้อง)',
 'Processing {0} videos in parallel...': 'กำลังประมวลผล {0} วิดีโอพร้อมกัน...',
 '\n❌ Error: {0}': '\n❌ ข้อผิดพลาด: {0}',
 'Duration: {0}  |  {1} FPS  |  {2} frames': 'ความยาว: {0}  |  {1} FPS  |  {2} เฟรม',
 'New name for [{0}] {1}:': 'ชื่อใหม่ของ [{0}] {1}:',
 'Classes from {0}': 'คลาสจาก {0}',
 '{0} mapped to existing · {1} added as new · {2} skipped': 'จับคู่กับของเดิม {0} · เพิ่มใหม่ {1} · ข้าม {2}',
 '{0} boxes': '{0} กรอบ',
 'Select exactly one class to {0}.': 'ต้องเลือกเพียงหนึ่งคลาสเพื่อ {0}',
 'Delete {0} class(es):\n{1}\n\nThis removes {2} box(es) from your label files and cannot be undone.\n\nContinue?': 'ลบ {0} คลาส:\n'
                                                                                                                    '{1}\n'
                                                                                                                    '\n'
                                                                                                                    'จะลบกรอบ {2} '
                                                                                                                    'กรอบออกจากไฟล์ป้ายกำกับ '
                                                                                                                    'และย้อนกลับไม่ได้\n'
                                                                                                                    '\n'
                                                                                                                    'ดำเนินการต่อหรือไม่?',
 'Merge {0} classes into "{1}"?\n{2} box(es) in your label files will be relabeled (exact duplicate boxes created by the merge are removed).\n\nContinue?': 'รวม '
                                                                                                                                                            '{0} '
                                                                                                                                                            'คลาสเข้าเป็น '
                                                                                                                                                            '"{1}" '
                                                                                                                                                            'หรือไม่?\n'
                                                                                                                                                            'กรอบ '
                                                                                                                                                            '{2} '
                                                                                                                                                            'กรอบในไฟล์ป้ายกำกับจะถูกเปลี่ยนป้าย '
                                                                                                                                                            '(กรอบที่ซ้ำกันเป๊ะจากการรวมจะถูกลบ)\n'
                                                                                                                                                            '\n'
                                                                                                                                                            'ดำเนินการต่อหรือไม่?',
 'Your class list becomes these {0} classes.': 'รายการคลาสของคุณจะเป็น {0} คลาสนี้',
 '{0} has {1} classes. How should they be used?': '{0} มี {1} คลาส ต้องการใช้อย่างไร?',
 'Scan failed: {0}': 'สแกนไม่สำเร็จ: {0}',
 'Choose Color for [{0}] {1}': 'เลือกสีของ [{0}] {1}',
 '{0} class(es) of this model are not in your class list and would be ignored:\n\n{1}\n\nOpen the class mapping now? (map them to your classes, add them as new classes, or skip them)': 'โมเดลนี้มี '
                                                                                                                                                                                         '{0} '
                                                                                                                                                                                         'คลาสที่ไม่อยู่ในรายการคลาสของคุณ '
                                                                                                                                                                                         'และจะถูกข้าม:\n'
                                                                                                                                                                                         '\n'
                                                                                                                                                                                         '{1}\n'
                                                                                                                                                                                         '\n'
                                                                                                                                                                                         'เปิดหน้าจับคู่คลาสตอนนี้ไหม '
                                                                                                                                                                                         '(จับคู่กับคลาสของคุณ '
                                                                                                                                                                                         'เพิ่มเป็นคลาสใหม่ '
                                                                                                                                                                                         'หรือข้าม)',
 'Auto-Label processing: {0}': 'Auto-Label กำลังประมวลผล: {0}',
 'Filtered Images: {0} | Reviewed: {1}': 'ภาพที่กรองได้: {0} | ตรวจแล้ว: {1}',
 'Image index is out of range. Valid range: 1 to {0}.': 'เลขภาพอยู่นอกช่วง ช่วงที่ใช้ได้: 1 ถึง {0}',
 'Auto-Label error: {0}': 'Auto-Label ผิดพลาด: {0}',
 'Processing failed for {0}\n\n{1}': 'ประมวลผล {0} ไม่สำเร็จ\n\n{1}',
 'Found {0} unlabeled images out of {1} total.\nRun Auto-Label on these images?\n(Existing labels will not be modified.)': 'พบภาพที่ยังไม่ติดป้าย '
                                                                                                                           '{0} '
                                                                                                                           'ภาพจากทั้งหมด '
                                                                                                                           '{1} ภาพ\n'
                                                                                                                           'รัน Auto-Label '
                                                                                                                           'กับภาพเหล่านี้หรือไม่?\n'
                                                                                                                           '(ป้ายกำกับที่มีอยู่จะไม่ถูกแก้ไข)',
 'Batch failed: {0}': 'Batch ไม่สำเร็จ: {0}',
 'Model loaded:\n{0}': 'โหลดโมเดลแล้ว:\n{0}',
 'Auto-Label cancelled: {0}': 'ยกเลิก Auto-Label: {0}',
 'This folder already contains files:\n{0}\n\nUse this folder anyway?': 'โฟลเดอร์นี้มีไฟล์อยู่แล้ว:\n{0}\n\nจะใช้โฟลเดอร์นี้ต่อไปหรือไม่?',
 'File not found: {0}': 'ไม่พบไฟล์: {0}',
 'Unexpected error: {0}': 'ข้อผิดพลาดที่ไม่คาดคิด: {0}',
 'Typing: [{0}] ➔ {1} (Press ENTER)': 'กำลังพิมพ์: [{0}] ➔ {1} (กด ENTER)',
 'Typing: [{0}] (Out of range!)': 'กำลังพิมพ์: [{0}] (เกินช่วง!)',
 'Batch Auto-Label: {0}/{1} images...': 'Batch Auto-Label: {0}/{1} ภาพ...',
 'Batch Auto-Label (reference): {0}/{1} images...': 'Batch Auto-Label (reference): {0}/{1} ภาพ...',
 'Scan complete: {0} images. Set targets and start curation.': 'สแกนเสร็จแล้ว: {0} ภาพ ตั้งเป้าหมายแล้วเริ่มคัดเลือกได้เลย',
 'Copying files {0}/{1}...': 'กำลังคัดลอกไฟล์ {0}/{1}...',
 'Output: {0}': 'ผลลัพธ์: {0}',
 'Current total is {0}; it must equal 100.': 'ผลรวมตอนนี้คือ {0} ต้องเท่ากับ 100',
 'Found {0} images — use a large target to keep all images.': 'พบ {0} ภาพ — ใช้เป้าหมายค่ามากเพื่อเก็บทุกภาพ',
 '{0}: only 1 image; it cannot be distributed across all splits.': '{0}: มีเพียง 1 ภาพ จึงแจกให้ครบทุกชุดไม่ได้',
 '{0}: only 2 images; it cannot represent all three splits.': '{0}: มีเพียง 2 ภาพ จึงเป็นตัวแทนครบทั้งสามชุดไม่ได้',
 'Computing embeddings for {0} images...': 'กำลังคำนวณ embedding ของ {0} ภาพ...',
 'Computing embeddings {0}/{1}...': 'กำลังคำนวณ embedding {0}/{1}...',
 'Missing file: {0}\nPlace extract_frames.py in the tools folder.': 'ไม่พบไฟล์: {0}\nวาง extract_frames.py ไว้ในโฟลเดอร์ tools',
 'Load failed: {0}': 'โหลดไม่สำเร็จ: {0}',
 'Missing file: {0}': 'ไม่พบไฟล์: {0}',
 'Loaded video: {0}  ({1}x{2}, {3} frames)': 'โหลดวิดีโอแล้ว: {0}  ({1}x{2}, {3} เฟรม)',
 'Frame {0}/{1}{2}': 'เฟรม {0}/{1}{2}',
 'Frame {0}/{1}{2} (dragging...)': 'เฟรม {0}/{1}{2} (กำลังลาก...)',
 "Saved '{0}' as preset #{1}.": "บันทึก '{0}' เป็นชื่อที่ #{1} แล้ว",
 "Loaded #{0}: '{1}' — press Enter (or Finish Zone) to close the polygon.": "โหลด #{0}: '{1}' แล้ว — กด Enter (หรือ จบโซน) "
                                                                            'เพื่อปิดรูปหลายเหลี่ยม',
 "Added zone '{0}' — {1} points, area ≈ {2} px².": "เพิ่มโซน '{0}' แล้ว — {1} จุด พื้นที่ ≈ {2} px²",
 'Saved {0} zone(s) to: {1}': 'บันทึก {0} โซนไปที่: {1}',
 'Saved {0} zone(s) to:\n{1}': 'บันทึก {0} โซนไปที่:\n{1}',
 'Loaded {0} zone(s) from: {1}': 'โหลด {0} โซนจาก: {1}',
 'Video: {0}  ({1}x{2})': 'วิดีโอ: {0}  ({1}x{2})',
 'Generated: {0}': 'สร้างเมื่อ: {0}',
 '{0} zone(s) — ready to copy or save.': '{0} โซน — พร้อมคัดลอกหรือบันทึก',
 'Could not open video:\n{0}': 'เปิดวิดีโอไม่ได้:\n{0}',
 'Could not read frame {0}.': 'อ่านเฟรม {0} ไม่ได้',
 'Valid range: 1 to {0}.': 'ช่วงที่ใช้ได้: 1 ถึง {0}',
 'No saved name #{0} — save one first.': 'ไม่มีชื่อที่บันทึกไว้ #{0} — บันทึกก่อน',
 'Points placed: {0}': 'จุดที่วางแล้ว: {0}',
 'Saved to: {0}': 'บันทึกไปที่: {0}',
 'Typing: [{0}] → {1} (Enter to load)': 'กำลังพิมพ์: [{0}] → {1} (Enter เพื่อโหลด)',
 'Typing: [{0}] (out of range)': 'กำลังพิมพ์: [{0}] (เกินช่วง)',
 'Could not save zones:\n{0}': 'บันทึกโซนไม่ได้:\n{0}',
 'Could not read zones file:\n{0}': 'อ่านไฟล์โซนไม่ได้:\n{0}',
 'This zone file was made for a {0}x{1} frame, but the current video is {2}x{3}. Zone positions may not line up. Load anyway?': 'ไฟล์โซนนี้สร้างสำหรับเฟรมขนาด '
                                                                                                                                '{0}x{1} '
                                                                                                                                'แต่วิดีโอปัจจุบันขนาด '
                                                                                                                                '{2}x{3} '
                                                                                                                                'ตำแหน่งโซนอาจไม่ตรงกัน '
                                                                                                                                'โหลดต่อไปหรือไม่?',
 'Invalid time format: {0}': 'รูปแบบเวลาไม่ถูกต้อง: {0}',
 'Dimension Insights (median: {0}x{1})': 'ข้อมูลเชิงลึกของขนาด (ค่ากลาง: {0}x{1})',
 'Auto-label complete: {0} objects found': 'Auto-Label เสร็จแล้ว: พบ {0} วัตถุ',
 'Batch Auto-Label {0}!\nSuccess: {1} | Errors: {2} | Total: {3}': 'Batch Auto-Label {0}!\nสำเร็จ: {1} | ผิดพลาด: {2} | ทั้งหมด: {3}',
 'Total Dataset Images: {0}': 'จำนวนภาพทั้งชุดข้อมูล: {0}',
 'Total Dataset Boxes:  {0}': 'จำนวนกรอบทั้งชุดข้อมูล:  {0}',
 'Dataset saved successfully\n\n{0}': 'บันทึกชุดข้อมูลสำเร็จ\n\n{0}',
 'Could not update these label files:\n{0}': 'แก้ไฟล์ป้ายกำกับเหล่านี้ไม่ได้:\n{0}',
 'Complete! Original images {0} -> selected images {1}': 'เสร็จสิ้น! ภาพต้นฉบับ {0} -> ภาพที่เลือก {1}',
 'Color for {0} zone(s)': 'สีของ {0} โซน',
 "Color for '{0}'": "สีของ '{0}'",
 "Delete zone '{0}'?": "ลบโซน '{0}' หรือไม่?",
 'Created data.yaml at: {0}': 'สร้าง data.yaml ที่: {0}',
 'Estimated total: ~{0} frames from {1} videos{2}': 'ประมาณการรวม: ~{0} เฟรมจาก {1} วิดีโอ{2}'}
