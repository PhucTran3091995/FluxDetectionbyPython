import cv2
import numpy as np
import os
import shutil
from datetime import datetime
from PyQt6.QtCore import QThread, pyqtSignal
from core.database_mysql import DatabaseManager
from core.yolo_helper import YoloHelper

class RecheckWorker(QThread):
    # Signals
    progress_update = pyqtSignal(int, int) # current, total
    image_processed = pyqtSignal(str, str) # image_path, status (OK/NG/Error)
    log_message = pyqtSignal(str)
    finished_check = pyqtSignal()
    
    def __init__(self, target_date, model_path, yaml_path, conf=0.25, iou=0.45, parent=None):
        super().__init__(parent)
        self.target_date = target_date
        self.conf = conf
        self.iou = iou
        self.is_running = True
        self.db = DatabaseManager()
        
        # Initialize AI Model
        self.yolo = YoloHelper(model_path, yaml_path)
        
        # Setup output directory
        self.output_base_dir = "recheck_ng"
        self.today_dir = os.path.join(self.output_base_dir, target_date.strftime("%Y-%m-%d"))
        if not os.path.exists(self.today_dir):
            os.makedirs(self.today_dir)
            
        # Clean up old history (>4 days)
        self.db.cleanup_old_history(days=4)

    def run(self):
        self.log_message.emit("Scanning service started...")
        total_checked = 0
        
        while self.is_running:
            try:
                # 1. Fetch NEW Unchecked Images
                image_list = self.db.get_new_unchecked_aoi_images()
                
                if not image_list:
                    self.log_message.emit(f"K có ảnh mới chờ 30 phút... (Checked: {total_checked})")
                    # Check every 1 second to allow interruption (stop button)
                    for _ in range(1800): # 1800s = 30 mins
                        if not self.is_running: break
                        self.sleep(1)
                    continue

                self.log_message.emit(f"Processing {len(image_list)} new images...")

                for img_path in image_list:
                    if not self.is_running: break
                    
                    total_checked += 1
                    self.progress_update.emit(total_checked, total_checked) # Just increment for running count

                    # 2. Mark Checked FIRST (To avoid crash loop re-processing same image)
                    self.db.mark_as_checked(img_path)

                    # 3. Verify file exists
                    if not os.path.exists(img_path):
                        self.image_processed.emit(img_path, "File Not Found (Skipped)")
                        continue

                    # 4. SKIP OCR IMAGES
                    if "_ocr" in img_path.lower() or "_OCR" in img_path:
                        continue
                        
                    # 5. Run Detection Logic
                    try:
                        results = self.yolo.detect(img_path, conf=self.conf, iou=self.iou)
                        is_ng = False
                        defect_labels = []
                        for res in results:
                            label = res['label']
                            if "flux" in label.lower() or "defect" in label.lower():
                                is_ng = True
                                defect_labels.append(label)
                        
                        if is_ng:
                            # Draw Bounding Boxes
                            try:
                                # Robust Read for Network Paths (Fixes missing boxes)
                                stream = open(img_path, "rb")
                                bytes = bytearray(stream.read())
                                numpyarray = np.asarray(bytes, dtype=np.uint8)
                                img_cv = cv2.imdecode(numpyarray, cv2.IMREAD_UNCHANGED)
                                
                                if img_cv is not None:
                                    # Handle alpha channel
                                    if img_cv.shape[2] == 4: img_cv = cv2.cvtColor(img_cv, cv2.COLOR_BGRA2BGR)

                                    for res in results:
                                        # Check if it is a defect to draw
                                        label = res.get('label', '')
                                        # Optional: Only draw flux/defect boxes if desired, or all boxes?
                                        # The NG condition was "flux" or "defect". 
                                        # Usually we want to verify what triggered it.
                                        
                                        if 'x1' in res:
                                            x1 = int(res['x1'])
                                            y1 = int(res['y1'])
                                            x2 = int(res['x2'])
                                            y2 = int(res['y2'])
                                            
                                            cv2.rectangle(img_cv, (x1, y1), (x2, y2), (0, 0, 255), 2)
                                            cv2.putText(img_cv, f"{label}", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                                    
                                    filename = os.path.basename(img_path)
                                    dst_path = os.path.join(self.today_dir, filename)
                                    
                                    # Robust Write
                                    is_success, im_buf_arr = cv2.imencode(".jpg", img_cv)
                                    if is_success:
                                        im_buf_arr.tofile(dst_path)
                                    else:
                                        # Fallback
                                        cv2.imwrite(dst_path, img_cv)
                                else:
                                    # If read failed, throw error to trigger backup copy
                                    raise ValueError("Image decode failed")
                            except:
                                # If drawing/reading fails, backup the original image
                                filename = os.path.basename(img_path)
                                dst_path = os.path.join(self.today_dir, filename)
                                shutil.copy2(img_path, dst_path)

                            # Always emit ORIGINAL path so UI can open it, but Gallery will find the Saved NG version automatically
                            self.image_processed.emit(img_path, f"NG: {', '.join(defect_labels)}")
                        else:
                            # self.image_processed.emit(img_path, "OK") # Reduce noise log
                            pass
                            
                    except Exception as e:
                        self.image_processed.emit(img_path, f"Error: {e}")
            
            except Exception as outer_e:
                self.log_message.emit(f"System Error: {outer_e}")
                self.sleep(5)

        self.log_message.emit("Scanning service stopped.")
        self.finished_check.emit()

    def stop(self):
        self.is_running = False
