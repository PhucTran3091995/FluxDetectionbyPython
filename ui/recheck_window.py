import os
import cv2
import numpy as np
import pandas as pd
from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, 
                             QTextBrowser, QGraphicsScene, QGraphicsView, QFileDialog, QMessageBox)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap, QImage
from core.database_mysql import DatabaseManager

class RecheckWindow(QWidget):
    def __init__(self, image_paths, detections, helper):
        super().__init__()
        self.setWindowTitle("Recheck NG Images")
        self.resize(1200, 800)
        self.image_paths = image_paths
        self.detections = detections
        self.helper = helper
        self.helper = helper
        self.current_idx = 0
        self.log_list = []
        self.db = DatabaseManager()

        main_layout = QHBoxLayout()
        self.scene = QGraphicsScene()
        self.view = QGraphicsView(self.scene)
        self.view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.view.setStyleSheet("background-color: #313244; border: none;")
        
        main_layout.addWidget(self.view, 70)
        
        right_layout = QVBoxLayout()
        nav_layout = QHBoxLayout()
        self.btn_prev = QPushButton("<< Prev")
        self.btn_next = QPushButton("Next >>")
        self.btn_prev.clicked.connect(self.prev_image)
        self.btn_next.clicked.connect(self.next_image)
        nav_layout.addWidget(self.btn_prev)
        nav_layout.addWidget(self.btn_next)
        right_layout.addLayout(nav_layout)
        
        self.btn_confirm_ng = QPushButton("✅ CONFIRM NG")
        self.btn_confirm_ng.setStyleSheet("background-color: #f38ba8; color: #11111b; font-weight: bold; padding: 10px;")
        self.btn_confirm_ng.clicked.connect(self.on_confirm_ng)
        
        self.btn_confirm_ok = QPushButton("❌ FALSE POSITIVE (OK)")
        self.btn_confirm_ok.setStyleSheet("background-color: #a6e3a1; color: #1e1e2e; font-weight: bold; padding: 10px;")
        self.btn_confirm_ok.clicked.connect(self.on_confirm_ok)
        
        self.btn_export = QPushButton("Export Excel")
        self.btn_export.clicked.connect(self.export_excel)
        
        right_layout.addWidget(self.btn_confirm_ng)
        right_layout.addWidget(self.btn_confirm_ok)
        right_layout.addWidget(self.btn_export)
        
        self.lbl_status = QLabel("0 / 0")
        self.lbl_status.setStyleSheet("font-size: 16px; font-weight: bold; color: #89b4fa;")
        right_layout.addWidget(self.lbl_status)
        
        lbl_log_title = QLabel("Log List (NG Images):")
        lbl_log_title.setStyleSheet("font-weight: bold; color: #cdd6f4;")
        right_layout.addWidget(lbl_log_title)
        
        self.txt_log = QTextBrowser()
        self.txt_log.setPlaceholderText("Log list will appear here...")
        self.txt_log.setStyleSheet("QTextBrowser { background-color: #ffffff; color: #1e1e2e; border: 1px solid #45475a; border-radius: 6px; padding: 5px; }")
        
        right_layout.addWidget(self.txt_log)
        right_layout.addStretch()

        main_layout.addLayout(right_layout, 30)
        self.setLayout(main_layout)
        QTimer.singleShot(0, self.show_image)

    def show_image(self):
        if not self.image_paths: return
        path = self.image_paths[self.current_idx]
        dets = self.detections.get(path, [])
        
        # Đọc ảnh có hỗ trợ tiếng Việt
        stream = open(path, "rb")
        bytes = bytearray(stream.read())
        numpyarray = np.asarray(bytes, dtype=np.uint8)
        img = cv2.imdecode(numpyarray, cv2.IMREAD_UNCHANGED)
        
        if img is None: return
        
        # Bỏ kênh alpha nếu có
        if img.shape[2] == 4:
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        for d in dets:
            x1, y1, x2, y2 = int(d['x1']), int(d['y1']), int(d['x2']), int(d['y2'])
            score = d['score']
            label = d['label'] # Lấy tên label đã xử lý từ helper
            
            # Màu sắc: Flux/Foreign = Đỏ, Khác = Vàng
            color = (255, 0, 0) # Đỏ RGB
            if "flux" in label.lower() or "foreign" in label.lower():
                color = (255, 0, 0)
            else:
                color = (255, 255, 0)

            # Vẽ box
            cv2.rectangle(img, (x1, y1), (x2, y2), color, 3) 
            
            # Vẽ Label background
            text = f"{label} {score:.2f}"
            (text_w, text_h), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            cv2.rectangle(img, (x1, y1 - 20), (x1 + text_w, y1), color, -1)
            cv2.putText(img, text, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        h, w, ch = img.shape
        bytes_per_line = ch * w
        q_img = QImage(img.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(q_img)
        self.scene.clear()
        self.scene.addPixmap(pixmap)
        self.fit_to_view()
        self.lbl_status.setText(f"Image: {self.current_idx + 1} / {len(self.image_paths)}")

    def fit_to_view(self):
        if not self.scene.items(): return
        rect = self.scene.itemsBoundingRect()
        if rect.isNull(): return
        self.view.setSceneRect(rect)
        vp = self.view.viewport().size()
        if vp.width() <= 1 or vp.height() <= 1:
            QTimer.singleShot(0, self.fit_to_view)
            return
        self.view.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.fit_to_view()

    def next_image(self):
        if self.image_paths:
            self.current_idx = (self.current_idx + 1) % len(self.image_paths)
            self.show_image()

    def prev_image(self):
        if self.image_paths:
            self.current_idx = (self.current_idx - 1 + len(self.image_paths)) % len(self.image_paths)
            self.show_image()
            
    def on_confirm_ng(self):
        if not self.image_paths: return
        file_path = self.image_paths[self.current_idx]
        
        # Call DB to mark CONFIRMED
        self.db.update_validation_status(file_path, is_defect=True)
        
        # Add to local log for display
        fname = os.path.basename(file_path)
        if fname not in self.log_list:
            self.log_list.append(f"[CONFIRMED] {fname}")
            self.update_log_view()
            
        QMessageBox.information(self, "Confirmed", "Image Marked as CONFIRMED NG.")

    def on_confirm_ok(self):
        if not self.image_paths: return
        file_path = self.image_paths[self.current_idx]
        
        # Call DB to delete/mark False Positive
        self.db.update_validation_status(file_path, is_defect=False)
        
        # Remove from current list and refresh
        self.image_paths.pop(self.current_idx)
        if not self.image_paths:
            self.scene.clear()
            self.lbl_status.setText("0 / 0")
            QMessageBox.information(self, "Empty", "No more images in this list.")
            self.close()
            return
            
        # Adjust index
        if self.current_idx >= len(self.image_paths):
            self.current_idx = len(self.image_paths) - 1
            
        self.show_image()
        QMessageBox.information(self, "Removed", "Image Removed from NG List.")
            
    def update_log_view(self):
        log_content = "\n".join(self.log_list)
        self.txt_log.setPlainText(log_content)

    def export_excel(self):
        if not self.log_list: return
        path, _ = QFileDialog.getSaveFileName(self, "Save Excel", "log.xlsx", "Excel Files (*.xlsx)")
        if path:
            df = pd.DataFrame({'Filename': self.log_list})
            df.to_excel(path, index=False)
            QMessageBox.information(self, "Success", "Exported successfully!")
