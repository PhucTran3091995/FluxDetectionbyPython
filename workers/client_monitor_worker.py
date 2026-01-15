import json
import time
from PyQt6.QtCore import QThread, pyqtSignal
from core.database_mysql import DatabaseManager

class ClientMonitorWorker(QThread):
    new_results_signal = pyqtSignal(list) # List of dicts
    scan_count_signal = pyqtSignal(int)
    log_message = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.is_running = True
        self.db = DatabaseManager()
        self.last_seen_ids = set()

    def run(self):
        self.log_message.emit("Connected to Server. Monitoring for defects...")
        
        while self.is_running:
            try:
                # Poll DB for latest NG results
                results = self.db.get_latest_ng_results(limit=100)
                
                new_items = []
                for row in results:
                    row_id = row['id']
                    if row_id not in self.last_seen_ids:
                        # Parse bbox_json
                        try:
                            row['detections'] = json.loads(row['bbox_data'])
                        except:
                            row['detections'] = []
                        
                        new_items.append(row)
                        self.last_seen_ids.add(row_id)
                
                if new_items:
                    # Sort by id/time to show latest
                    self.new_results_signal.emit(new_items)
                
                # Fetch Scan Count
                count = self.db.get_today_scan_count()
                self.scan_count_signal.emit(count)

                # Sleep 5 seconds
                for _ in range(5):
                    if not self.is_running: break
                    time.sleep(1)
                    
            except Exception as e:
                self.log_message.emit(f"Connection Error: {e}")
                time.sleep(5)

    def stop(self):
        self.is_running = False
