import os
from PyQt6.QtCore import QThread, pyqtSignal

class FluxWorker(QThread):
    progress_update = pyqtSignal(int, int) # value, max
    finished_signal = pyqtSignal(int, int, dict, list) 
    
    def __init__(self, folder_path, model_helper, conf, iou, brightness):
        super().__init__()
        self.folder_path = folder_path
        self.helper = model_helper
        self.conf = conf
        self.iou = iou
        self.brightness = brightness
        self.is_running = True

    def run(self):
        # Các đuôi file ảnh hợp lệ
        valid_exts = ('.jpg', '.jpeg', '.png', '.bmp')
        
        try:
            # Lấy danh sách file và lọc ngay tại đây
            all_files = os.listdir(self.folder_path)
            files = []
            
            for f in all_files:
                # Chuyển về chữ thường để so sánh cho chuẩn (JPG -> jpg, OCR -> ocr)
                name_lower = f.lower()
                
                # ĐIỀU KIỆN 1: Phải là file ảnh
                is_image = name_lower.endswith(valid_exts)
                
                # ĐIỀU KIỆN 2: Tên file KHÔNG ĐƯỢC chứa chữ "ocr"
                # Nó sẽ chặn hết: _OCR2, _ocr, .OCR...
                is_not_ocr = "ocr" not in name_lower
                
                if is_image and is_not_ocr:
                    full_path = os.path.join(self.folder_path, f)
                    files.append(full_path)
                    
        except Exception as e:
            print(f"Lỗi đọc thư mục: {e}")
            files = []
        
        # --- Phần xử lý detection bên dưới giữ nguyên ---
        total = len(files)
        detections_dict = {}
        image_paths = []
        ng_count = 0
        ok_count = 0

        for i, file_path in enumerate(files):
            if not self.is_running: break
            
            # Gọi helper để detect
            dets = self.helper.detect(file_path, self.conf, self.iou)
            
            # Nếu có lỗi -> NG
            if len(dets) > 0:
                ng_count += 1
                detections_dict[file_path] = dets
                image_paths.append(file_path)
            else:
                ok_count += 1

            # Cập nhật tiến trình
            self.progress_update.emit(i + 1, total)

        # Gửi tín hiệu hoàn tất về Main Window
        self.finished_signal.emit(ng_count, ok_count, detections_dict, image_paths)

    def stop(self):
        self.is_running = False
