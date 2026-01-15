import os
import ctypes
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QLineEdit, QPushButton, QProgressBar, QMessageBox, 
                             QTabWidget, QGridLayout, QGroupBox, QDateEdit, QTableWidget, 
                             QTableWidgetItem, QHeaderView)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QIcon

from core.yolo_helper import YoloHelper
from workers.flux_worker import FluxWorker
from workers.flux_worker import FluxWorker
from workers.client_monitor_worker import ClientMonitorWorker
from ui.recheck_window import RecheckWindow
from ui.styles import STYLESHEET
from datetime import datetime

from core.resource_path import resource_path

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Flux Detected by QA TEAM")
        self.resize(1100, 650)

        # 1. Cài icon cho cửa sổ ứng dụng
        icon_path = resource_path("icon.jpg")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # 2. Fix lỗi icon không hiện dưới thanh Taskbar của Windows
        myappid = 'mycompany.fluxapp.yolov11.version1' 
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)   
        
        self.yolo = YoloHelper(resource_path("best.onnx"), resource_path("data.yaml"))
        
        self.conf_threshold = 0.5
        self.iou_threshold = 0.2
        self.brightness_val = 1.0
        
        self.workers = {}
        self.workers = {}
        self.results = {}
        self.server_detections = {} # Store detections from server {path: list_of_boxes}

        # MAIN LAYOUT
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # HEADER
        header = QLabel("Flux Detection use AI")
        header.setStyleSheet("font-size: 24px; font-weight: bold; color: #89b4fa; margin-bottom: 10px;")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(header)

        # TABS -> Xoa tab, chi giu lai nhung tab can thiet
        tabs = QTabWidget()
        main_layout.addWidget(tabs)
        
        # 1. DATABASE CHECK (Dua len dau)
        tab_db = QWidget()
        self.setup_db_tab(tab_db)
        tabs.addTab(tab_db, "  DATABASE CHECK  ")

        # 2. PROCESSING DASHBOARD
        tab_main = QWidget()
        self.setup_main_tab(tab_main)
        tabs.addTab(tab_main, "  PROCESSING DASHBOARD  ")
        
        # Tab Settings da bi xoa theo yeu cau

    def setup_main_tab(self, widget):
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        group_scan = QGroupBox("Active Scan Channels")
        group_layout = QGridLayout()
        group_layout.setVerticalSpacing(15)
        group_layout.setHorizontalSpacing(15)
        
        self.rows = []
        for i in range(5):
            self.create_row(i, group_layout)
            
        group_scan.setLayout(group_layout)
        layout.addWidget(group_scan)
        layout.addStretch()
        widget.setLayout(layout)

    def create_row(self, index, layout):
        lbl = QLabel(f"CHANNEL {index + 1}")
        lbl.setStyleSheet("font-weight: bold; color: #bac2de;")
        layout.addWidget(lbl, index, 0)
        
        txt_path = QLineEdit()
        txt_path.setPlaceholderText("Enter folder path here...")
        txt_path.setMinimumWidth(300)
        layout.addWidget(txt_path, index, 1)
        
        btn_start = QPushButton("START")
        btn_start.setObjectName("btn_start")
        btn_start.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_start.clicked.connect(lambda: self.start_process(index, txt_path.text()))
        layout.addWidget(btn_start, index, 2)
        
        btn_stop = QPushButton("STOP")
        btn_stop.setObjectName("btn_stop")
        btn_stop.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_stop.setEnabled(False)
        btn_stop.clicked.connect(lambda: self.stop_process(index))
        layout.addWidget(btn_stop, index, 3)
        
        pbar = QProgressBar()
        pbar.setValue(0)
        pbar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pbar.setFormat("Ready")
        pbar.setMinimumWidth(200)
        layout.addWidget(pbar, index, 4)
        
        btn_recheck = QPushButton("RECHECK")
        btn_recheck.setObjectName("btn_recheck")
        btn_recheck.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_recheck.setEnabled(False)
        btn_recheck.clicked.connect(lambda: self.open_recheck(index))
        layout.addWidget(btn_recheck, index, 5)
        
        self.rows.append({
            "path": txt_path,
            "btn_start": btn_start,
            "btn_stop": btn_stop,
            "pbar": pbar,
            "btn_recheck": btn_recheck
        })

    def start_process(self, index, folder_path):
        if not os.path.exists(folder_path):
            QMessageBox.warning(self, "Error", "Folder not found!")
            return

        controls = self.rows[index]
        controls['btn_start'].setEnabled(False)
        controls['btn_stop'].setEnabled(True)
        controls['pbar'].setValue(0)
        controls['pbar'].setFormat("⏳ Đang suy nghĩ...")
        controls['btn_recheck'].setEnabled(False)
        
        worker = FluxWorker(folder_path, self.yolo, self.conf_threshold, self.iou_threshold, self.brightness_val)
        worker.progress_update.connect(lambda curr, total: self.update_pbar_display(index, curr, total))
        worker.finished_signal.connect(lambda ng, ok, dets, paths: self.on_finished(index, ng, ok, dets, paths))
        
        self.workers[index] = worker
        worker.start()

    def update_pbar_display(self, index, current, total):
        pbar = self.rows[index]['pbar']
        pbar.setMaximum(total)
        pbar.setValue(current)
        percent = int(current / total * 100) if total > 0 else 0
        
        status_msg = ""
        if percent < 10: status_msg = "🚀 Initializing..."
        elif percent < 20: status_msg = "👀 Scanning..."
        elif percent < 90: status_msg = "✨ Processing..."
        else: status_msg = "✅ Finishing..."
        pbar.setFormat(f"{status_msg} ({percent}%)")

    def stop_process(self, index):
        if index in self.workers:
            self.workers[index].stop()

    def on_finished(self, index, ng_count, ok_count, detections_dict, image_paths):
        msg = QMessageBox(self)
        msg.setWindowTitle("Scan Complete")
        msg.setText(f"Finished Channel {index + 1}\n\nFlux Detected (NG): {ng_count}\nClean (OK): {ok_count}")
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setStyleSheet("QLabel{color: white;} QMessageBox{background-color: #1e1e2e;}")
        msg.exec()
        
        controls = self.rows[index]
        controls['btn_start'].setEnabled(True)
        controls['btn_stop'].setEnabled(False)
        
        if ng_count > 0:
            controls['btn_recheck'].setEnabled(True)
            controls['btn_recheck'].setText(f"RECHECK ({ng_count})")
            self.results[index] = {"paths": image_paths, "detections": detections_dict}
        else:
            self.results[index] = None
            controls['btn_recheck'].setText("RECHECK")

    def open_recheck(self, index):
        data = self.results.get(index)
        if data:
            self.recheck_window = RecheckWindow(data['paths'], data['detections'], self.yolo)
            self.recheck_window.setStyleSheet(STYLESHEET)
            self.recheck_window.show()

    def setup_settings_tab(self, widget):
        layout = QVBoxLayout()
        layout.setContentsMargins(50, 50, 50, 50)
        layout.setSpacing(20)
        
        grp = QGroupBox("Algorithm Parameters")
        grp_layout = QVBoxLayout()
        
        row1 = QHBoxLayout()
        lbl1 = QLabel("Confidence Threshold (0-1):")
        lbl1.setMinimumWidth(250)
        self.txt_conf = QLineEdit(str(self.conf_threshold))
        row1.addWidget(lbl1)
        row1.addWidget(self.txt_conf)
        grp_layout.addLayout(row1)

        row2 = QHBoxLayout()
        lbl2 = QLabel("Brightness/Contrast Factor (1.0 = Normal):")
        lbl2.setMinimumWidth(250)
        self.txt_bright = QLineEdit(str(self.brightness_val))
        row2.addWidget(lbl2)
        row2.addWidget(self.txt_bright)
        grp_layout.addLayout(row2)
        
        grp.setLayout(grp_layout)
        layout.addWidget(grp)

        btn_update = QPushButton("SAVE SETTINGS")
        btn_update.setMinimumHeight(40)
        btn_update.clicked.connect(self.update_settings)
        layout.addWidget(btn_update)
        
        layout.addStretch()
        widget.setLayout(layout)

    def update_settings(self):
        try:
            c_val = float(self.txt_conf.text())
            if 0 <= c_val <= 1:
                self.conf_threshold = c_val
            
            b_val = float(self.txt_bright.text())
            if b_val > 0:
                self.brightness_val = b_val
                
            QMessageBox.information(self, "Success", "Settings Updated Successfully!")
        except:
            QMessageBox.warning(self, "Error", "Invalid number format!")

    def setup_db_tab(self, widget):
        layout = QHBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # --- LEFT PANEL (Controls) ---
        left_panel = QGroupBox("Control Panel")
        left_layout = QVBoxLayout()
        left_layout.setSpacing(15)
        
        # Date Picker -> Xoa, luon dung ngay hien tai
        # lbl_date = QLabel("Select Date:")
        # self.date_picker = QDateEdit()
        # ...
        # left_layout.addWidget(lbl_date)
        # left_layout.addWidget(self.date_picker)
        
        # Info Label
        self.lbl_db_info = QLabel("Total Images: --")
        self.lbl_db_info.setStyleSheet("color: #bac2de; font-weight: bold;")
        left_layout.addWidget(self.lbl_db_info)

        # Status Label (New) -> Hien thi trang thai ket noi
        self.lbl_db_status = QLabel("System Ready")
        self.lbl_db_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_db_status.setStyleSheet("background-color: #27293d; color: #bac2de; padding: 5px; border-radius: 5px;")
        left_layout.addWidget(self.lbl_db_status)


        # Buttons
        self.btn_db_start = QPushButton("CONNECT SERVER")
        self.btn_db_start.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_db_start.clicked.connect(self.start_db_check)
        self.btn_db_start.setMinimumHeight(40)
        left_layout.addWidget(self.btn_db_start)
        
        self.btn_db_stop = QPushButton("DISCONNECT")
        self.btn_db_stop.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_db_stop.clicked.connect(self.stop_db_check)
        self.btn_db_stop.setEnabled(False)
        self.btn_db_stop.setStyleSheet("background-color: #f38ba8; color: #11111b;")
        left_layout.addWidget(self.btn_db_stop)
        
        self.btn_view_results = QPushButton("VIEW NG GALLERY")
        self.btn_view_results.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_view_results.clicked.connect(self.open_db_recheck_gallery)
        self.btn_view_results.setStyleSheet("background-color: #89b4fa; color: #1e1e2e;")
        left_layout.addWidget(self.btn_view_results)
        
        # Progress
        self.db_pbar = QProgressBar()
        self.db_pbar.setValue(0)
        self.db_pbar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.db_pbar.setFormat("Ready")
        left_layout.addWidget(self.db_pbar)

        left_layout.addStretch()
        left_panel.setLayout(left_layout)
        left_panel.setFixedWidth(300)
        layout.addWidget(left_panel)
        
        # --- RIGHT PANEL (Results) ---
        right_panel = QGroupBox("Recheck Results (NG)")
        right_layout = QVBoxLayout()
        
        self.table_ng = QTableWidget()
        self.table_ng.cellDoubleClicked.connect(self.on_table_ng_double_click) # Add double click event
        self.table_ng.setColumnCount(2)
        self.table_ng.setHorizontalHeaderLabels(["Image Path", "Defect Type"])
        self.table_ng.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table_ng.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table_ng.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        right_layout.addWidget(self.table_ng)
        
        right_panel.setLayout(right_layout)
        layout.addWidget(right_panel)
        
        widget.setLayout(layout)
        self.db_worker = None

    def start_db_check(self):
        self.table_ng.setRowCount(0) # Clear previous results
        self.server_detections = {} 
        
        # Create Client Monitor Worker
        self.db_worker = ClientMonitorWorker()
        
        # Connect Signals
        self.db_worker.new_results_signal.connect(self.on_server_results)
        self.db_worker.scan_count_signal.connect(self.on_scan_count_update)
        self.db_worker.log_message.connect(self.on_db_log)
        
        # UI State
        self.btn_db_start.setEnabled(False)
        self.btn_db_stop.setEnabled(True)
        
        self.db_worker.start()

    def stop_db_check(self):
        if self.db_worker:
            self.db_worker.stop()
            self.lbl_db_status.setText("Disconnected")
            self.lbl_db_status.setStyleSheet("background-color: #f38ba8; color: #1e1e2e;")
            self.btn_db_start.setEnabled(True)
            self.btn_db_stop.setEnabled(False)

    def on_server_results(self, new_items):
        self.lbl_db_status.setText("MONITORING (Live)")
        self.lbl_db_status.setStyleSheet("background-color: #a6e3a1; color: #1e1e2e; font-weight: bold;")
        
        for item in new_items:
            path = item['file_path']
            defect = item.get('defect_type', 'NG')
            detections = item.get('detections', [])
            
            # Store for Gallery View
            self.server_detections[path] = detections
            
            # Add to Table (if not exists?)
            # Since we clear table on start, and worker fetches latest LIMIT, duplicate check might be needed if we append.
            # Convert to set for O(1) check if needed, but for now simple insert
            
            row_idx = 0 # Insert at top
            self.table_ng.insertRow(row_idx)
            self.table_ng.setItem(row_idx, 0, QTableWidgetItem(path))
            self.table_ng.setItem(row_idx, 1, QTableWidgetItem(defect))
        
    def on_scan_count_update(self, count):
         self.lbl_db_info.setText(f"Checked Today: {count} | Found NG: {self.table_ng.rowCount()}")

    def on_db_log(self, message):
        if "Found" in message:
            # Only used for connection status now
            pass
        self.db_pbar.setFormat(message)

    def on_db_progress(self, current, total):
        self.db_pbar.setMaximum(total)
        self.db_pbar.setValue(current)
        percent = int(current / total * 100) if total > 0 else 0
        
        # Hien thi chi lơt: Dang quet [Hien tai] / [Tong]
        self.db_pbar.setFormat(f"Scanning... {current}/{total} ({percent}%)")
        self.lbl_db_status.setText(f"CHECKING: {current}/{total}")


    def on_db_image_processed(self, path, status):
        # Only add to table if NG or Error
        if status != "OK" and status != "File Not Found":
            row_idx = self.table_ng.rowCount()
            self.table_ng.insertRow(row_idx)
            self.table_ng.setItem(row_idx, 0, QTableWidgetItem(path))
            self.table_ng.setItem(row_idx, 1, QTableWidgetItem(status))
            # Smooth scroll to bottom
            self.table_ng.scrollToBottom()

    def on_db_finished(self):
        QMessageBox.information(self, "Recheck Complete", "Database Image Recheck Finished!")
        self.btn_db_start.setEnabled(True)
        self.btn_db_stop.setEnabled(False)
        # self.date_picker.setEnabled(True)
        self.db_pbar.setFormat("Finished")
        
        # Reset Status
        self.lbl_db_status.setText("System Ready")
        self.lbl_db_status.setStyleSheet("background-color: #a6e3a1; color: #1e1e2e; font-weight: bold; padding: 5px; border-radius: 5px;")


    def on_table_ng_double_click(self, row, col):
        # Open the file link directly when double clicking
        path_item = self.table_ng.item(row, 0)
        if path_item:
            path = path_item.text()
            if os.path.exists(path):
                try:
                    os.startfile(path)
                except Exception as e:
                    QMessageBox.warning(self, "Error", f"Cannot open file: {e}")
            else:
                QMessageBox.warning(self, "Error", f"File not found:\n{path}")


    def open_db_recheck_gallery(self, start_index=0):
        paths = []
        
        row_count = self.table_ng.rowCount()
        if row_count == 0:
            QMessageBox.warning(self, "Info", "No NG images found yet.")
            return

        # Collect paths from table
        for i in range(row_count):
            path_item = self.table_ng.item(i, 0)
            if path_item:
                paths.append(path_item.text())
        
        # Open RecheckWindow with SERVER DETECTIONS
        if not paths:
             QMessageBox.warning(self, "Info", "No images to display.")
             return

        # Use the stored dictionary of detections (Key = Image Path, Value = List of Box Dicts)
        self.recheck_window = RecheckWindow(paths, self.server_detections, self.yolo)
        self.recheck_window.setStyleSheet(STYLESHEET)
        try:
            self.recheck_window.current_idx = start_index 
            self.recheck_window.show_image() # Force refresh
        except: pass
        self.recheck_window.show()
        # We might need to adjust RecheckWindow to handle already drawn images better (not re-draw)
        # But user asked to "hien thi tat ca anh loi... kem voi vi tri loi da duoc khoanh".
        # Since RecheckWorker already saves images with boxes, we just show them.
        # However, RecheckWindow current logic is to re-draw boxes based on 'detections' dict.
        # If we pass empty dict, it just shows the image. 
        # Since the saved image already has boxes! This works perfectly.
        
        self.recheck_window.setStyleSheet(STYLESHEET)
        self.recheck_window.current_idx = start_index 
        self.recheck_window.show()

