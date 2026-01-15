import time
import json
import os
import logging
from datetime import datetime
from core.database_mysql import DatabaseManager
from core.yolo_helper import YoloHelper
from core.resource_path import resource_path

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - SERVER - %(message)s',
    handlers=[
        logging.FileHandler("server_log.txt"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ServerApp:
    def __init__(self):
        self.db = DatabaseManager()
        self.db.init_db()  # Ensure tables exist
        
        logger.info("Initializing AI Model...")
        self.yolo = YoloHelper(resource_path("best.onnx"), resource_path("data.yaml"))
        
        # Settings (Could be loaded from config file)
        self.conf = 0.5
        self.iou = 0.2
        self.is_running = True

    def run(self):
        logger.info("Server Service Started. Waiting for images...")
        
        while self.is_running:
            try:
                # 1. Fetch new images
                image_list = self.db.get_new_unchecked_aoi_images()
                
                if not image_list:
                    logger.info("No new images found. Waiting 30 seconds...")
                    time.sleep(30)
                    continue
                
                logger.info(f"Processing batch of {len(image_list)} images...")
                
                for img_path in image_list:
                    self.process_image(img_path)
                    
            except Exception as e:
                logger.error(f"Global Loop Error: {e}")
                time.sleep(5)

    def process_image(self, img_path):
        try:
            # 1. Mark as checked immediately to prevent re-processing on crash
            self.db.mark_as_checked(img_path)
            
            if not os.path.exists(img_path):
                logger.warning(f"File not found: {img_path}")
                return

            # Skip OCR
            if "ocr" in img_path.lower():
                return

            # 2. Run Detection
            results = self.yolo.detect(img_path, conf=self.conf, iou=self.iou)
            
            is_ng = False
            defect_labels = []
            
            for res in results:
                label = res.get('label', '')
                if "flux" in label.lower() or "defect" in label.lower():
                    is_ng = True
                    defect_labels.append(label)
            
            # 3. Save Result if NG
            if is_ng:
                bbox_json = json.dumps(results)
                defect_str = ", ".join(defect_labels)
                self.db.save_scan_result(img_path, True, defect_str, bbox_json)
                logger.info(f"[NG] Found {defect_str} in {os.path.basename(img_path)}")
            else:
                # Optional: Save OK results too if statistics are needed, but for now only NG
                # self.db.save_scan_result(img_path, False, "OK", "[]")
                logger.info(f"[OK] {os.path.basename(img_path)}")

        except Exception as e:
            logger.error(f"Error processing {img_path}: {e}")

if __name__ == "__main__":
    app = ServerApp()
    try:
        app.run()
    except KeyboardInterrupt:
        logger.info("Server Stopped by User.")
