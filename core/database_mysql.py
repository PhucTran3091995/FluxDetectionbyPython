import mysql.connector
from mysql.connector import pooling
import logging
from datetime import datetime, timedelta

# Cấu hình log
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_CONFIG = {
    "host": "10.7.10.6",
    "port": 3306,
    "user": "root",
    "password": "ivihaengsung@1",
    "database": "pid_search_db"
}

# Biến global để giữ Pool (Singleton ở cấp module)
db_pool = None

def _initialize_pool():
    global db_pool
    if db_pool:
        return

    try:
        db_pool = mysql.connector.pooling.MySQLConnectionPool(
            pool_name="pid_pool",
            pool_size=10,
            pool_reset_session=True,
            **DB_CONFIG
        )
        logger.info("Đã khởi tạo MySQL Connection Pool thành công.")
    except mysql.connector.Error as err:
        logger.error(f"Lỗi khởi tạo Connection Pool: {err}")
        # Nếu không có DB, thử tạo DB
        _attempt_create_database()

def _attempt_create_database():
    global db_pool
    try:
        # Kết nối không cần DB name để tạo DB
        temp_config = DB_CONFIG.copy()
        temp_config.pop('database', None)
        
        conn = mysql.connector.connect(**temp_config)
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']}")
        conn.close()
        
        # Thử lại khởi tạo pool
        db_pool = mysql.connector.pooling.MySQLConnectionPool(
            pool_name="pid_pool",
            pool_size=10,
            pool_reset_session=True,
            **DB_CONFIG
        )
        logger.info("Đã tự động tạo Database và khởi tạo Pool.")
    except Exception as e:
        logger.critical(f"Không thể tự động tạo Database: {e}")

# Khởi tạo pool ngay khi import module
_initialize_pool()

class DatabaseManager:
    def __init__(self):
        # Đảm bảo pool đã được load (trong trường hợp import fail trước đó)
        if not db_pool:
            _initialize_pool()

    def get_connection(self):
        if not db_pool:
            raise Exception("Database Connection Pool chưa được khởi tạo.")
        return db_pool.get_connection()

    def init_db(self):
        """Tạo bảng và tối ưu schema (Chạy thủ công hoặc khi khởi động App)"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 1. Bảng IMAGES
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS images (
                    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                    pid VARCHAR(30) CHARACTER SET ascii COLLATE ascii_general_ci NOT NULL,
                    file_path VARCHAR(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
                    line VARCHAR(20) CHARACTER SET ascii COLLATE ascii_general_ci,
                    scan_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE KEY idx_path_unique (file_path),
                    INDEX idx_pid (pid),
                    INDEX idx_scan_date (scan_date)
                ) ENGINE=InnoDB DEFAULT CHARSET=ascii
            ''')

            # 2. Migration Logic (Optional - Code cũ từ user)
            self._migrate_schema(cursor, conn)

            # 3. Bảng DIRECTORY_STATES
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS directory_states (
                    dir_path VARCHAR(500) CHARACTER SET ascii COLLATE ascii_general_ci PRIMARY KEY,
                    last_mtime DOUBLE NOT NULL,
                    last_scan TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=ascii
            ''')

            # 4. Bảng CHECKED_HISTORY (Để tránh check lại ảnh cũ)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS checked_history (
                    file_path VARCHAR(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci PRIMARY KEY,
                    check_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=ascii
            ''')

            # 5. Bảng SCAN_RESULTS
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS scan_results (
                    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                    file_path VARCHAR(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
                    is_ng BOOLEAN DEFAULT FALSE,
                    defect_type VARCHAR(100),
                    bbox_data TEXT, 
                    status VARCHAR(20) DEFAULT 'PENDING',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_created_at (created_at),
                    UNIQUE KEY idx_path_result (file_path)
                ) ENGINE=InnoDB DEFAULT CHARSET=ascii
            ''')
            
            # Migration: Ensure status column exists if table existed
            try:
                cursor.execute("ALTER TABLE scan_results ADD COLUMN status VARCHAR(20) DEFAULT 'PENDING'")
            except: pass

            
            conn.commit()
            cursor.close()
            conn.close()
            logger.info("Database Schema Checked/Initialized.")
        except Exception as e:
            logger.error(f"Lỗi init_db: {e}")

    def _migrate_schema(self, cursor, conn):
        try:
            # Kiểm tra xem bảng hiện tại có phải là schema cũ không
            cursor.execute("SELECT COLUMN_TYPE FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'images' AND COLUMN_NAME = 'file_path'", (DB_CONFIG['database'],))
            res = cursor.fetchone()
            if res and '750' in str(res[0]):
                logger.info("Phát hiện Schema cũ (Varchar 750). Tiến hành tối ưu...")
                cursor.execute("DELETE FROM images WHERE CHAR_LENGTH(pid) > 30")
                conn.commit()
                cursor.execute('''
                    ALTER TABLE images 
                    MODIFY id INT UNSIGNED AUTO_INCREMENT,
                    MODIFY file_path VARCHAR(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
                    MODIFY pid VARCHAR(30) CHARACTER SET ascii COLLATE ascii_general_ci NOT NULL,
                    MODIFY line VARCHAR(20) CHARACTER SET ascii COLLATE ascii_general_ci DEFAULT NULL
                ''')
                logger.info("Đã tối ưu hóa xong Database.")
        except Exception as e:
            logger.warning(f"Lỗi migrate schema: {e}")

    # --- CÁC HÀM CẦN THIẾT CHO APP ---

    def get_aoi_images(self, target_date):
        """
        Lấy danh sách ảnh AOI theo ngày để Recheck.
        target_date: datetime object
        Returns: list of file paths (strings)
        """
        results = []
        conn = None
        cursor = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Tính toán range thời gian cho cả ngày
            start_date = target_date.strftime('%Y-%m-%d 00:00:00')
            next_day = target_date + timedelta(days=1)
            end_date = next_day.strftime('%Y-%m-%d 00:00:00')

            query = ("SELECT file_path FROM images "
                     "WHERE scan_date >= %s AND scan_date < %s "
                     "AND (file_path LIKE '%AOI%TOP%' OR file_path LIKE '%AOI%BOT%')")
            
            cursor.execute(query, (start_date, end_date))
            results = [row[0] for row in cursor.fetchall()]
            
        except mysql.connector.Error as err:
            logger.error(f"Lỗi get_aoi_images: {err}")
        finally:
            if cursor: cursor.close()
            if conn: conn.close()
        
        return results

    def get_new_unchecked_aoi_images(self):
        """
        Lấy danh sách ảnh AOI mới chưa từng được kiểm tra (check_history).
        Chỉ lấy ảnh của NGÀY HÔN NAY để tối ưu tốc độ.
        """
        results = []
        conn = None
        cursor = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Chỉ lấy ảnh từ đầu ngày hôm nay trở đi
            start_date = datetime.now().strftime('%Y-%m-%d 00:00:00')
            
            # Logic: Lấy ảnh trong bảng IMAGES mà chưa có trong CHECKED_HISTORY
            # Sử dụng LEFT JOIN ... IS NULL để tìm sự khác biệt
            query = ("SELECT i.file_path "
                     "FROM images i "
                     "LEFT JOIN checked_history c ON i.file_path = c.file_path "
                     "WHERE i.scan_date >= %s "
                     "AND (i.file_path LIKE '%AOI%TOP%' OR i.file_path LIKE '%AOI%BOT%') "
                     "AND c.file_path IS NULL "
                     "LIMIT 100") # Lấy mỗi lần 100 ảnh để xử lý dần
            
            cursor.execute(query, (start_date,))
            results = [row[0] for row in cursor.fetchall()]
            
        except mysql.connector.Error as err:
            logger.error(f"Lỗi get_new_unchecked: {err}")
        finally:
            if cursor: cursor.close()
            if conn: conn.close()
        
        return results

    def mark_as_checked(self, file_path):
        conn = None
        cursor = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            sql = "INSERT IGNORE INTO checked_history (file_path) VALUES (%s)"
            cursor.execute(sql, (file_path,))
            conn.commit()
        except mysql.connector.Error as err:
            logger.error(f"Lỗi mark_as_checked: {err}")
        finally:
            if cursor: cursor.close()
            if conn: conn.close()



    def cleanup_old_history(self, days=4):
        """Xoa lich su kiem tra cu hon 'days' ngay co dinh"""
        conn = None
        cursor = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Tinh ngay gio cut-off
            cutoff_date = datetime.now() - timedelta(days=days)
            cutoff_str = cutoff_date.strftime('%Y-%m-%d %H:%M:%S')
            
            sql = "DELETE FROM checked_history WHERE check_date < %s"
            cursor.execute(sql, (cutoff_str,))
            deleted_count = cursor.rowcount
            conn.commit()
            
            if deleted_count > 0:
                logger.info(f"Da don dep lich su cu: {deleted_count} records (Check date < {cutoff_str})")
        except mysql.connector.Error as err:
            logger.error(f"Lỗi cleanup_old_history: {err}")
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

    def insert_images_batch(self, image_list):
        """image_list: list of tuples (pid, file_path, line)"""
        if not image_list:
            return
        conn = None
        cursor = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            sql = "INSERT IGNORE INTO images (pid, file_path, line) VALUES (%s, %s, %s)"
            cursor.executemany(sql, image_list)
            conn.commit()
        except mysql.connector.Error as err:
            logger.error(f"Lỗi chèn dữ liệu batch: {err}")
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

    def search_by_pid(self, pid):
        results = []
        conn = None
        cursor = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)
            sql = "SELECT file_path, line, scan_date FROM images WHERE pid = %s"
            cursor.execute(sql, (pid,))
            results = cursor.fetchall()
        except mysql.connector.Error as err:
            logger.error(f"Lỗi search_by_pid: {err}")
        finally:
            if cursor: cursor.close()
            if conn: conn.close()
        return results

    def get_dir_state(self, dir_path):
        conn = None
        cursor = None
        result = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT last_mtime FROM directory_states WHERE dir_path = %s", (dir_path,))
            row = cursor.fetchone()
            if row:
                result = row[0]
        except mysql.connector.Error:
            pass
        finally:
            if cursor: cursor.close()
            if conn: conn.close()
        return result

    def update_dir_state(self, dir_path, mtime):
        conn = None
        cursor = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            sql = "INSERT INTO directory_states (dir_path, last_mtime) VALUES (%s, %s) ON DUPLICATE KEY UPDATE last_mtime = %s"
            cursor.execute(sql, (dir_path, mtime, mtime))
            conn.commit()
        except mysql.connector.Error as err:
            logger.error(f"Lỗi update_dir_state: {err}")
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

    def save_scan_result(self, file_path, is_ng, defect_type, bbox_json):
        """Lưu kết quả kiểm tra vào bảng scan_results"""
        conn = None
        cursor = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            sql = """
                INSERT INTO scan_results (file_path, is_ng, defect_type, bbox_data, created_at)
                VALUES (%s, %s, %s, %s, NOW())
                ON DUPLICATE KEY UPDATE 
                    is_ng = VALUES(is_ng), 
                    defect_type = VALUES(defect_type), 
                    bbox_data = VALUES(bbox_data),
                    created_at = NOW()
            """
            cursor.execute(sql, (file_path, is_ng, defect_type, bbox_json))
            conn.commit()
        except mysql.connector.Error as err:
            logger.error(f"Lỗi save_scan_result: {err}")
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

    def get_latest_ng_results(self, limit=50):
        """Lấy danh sách NG mới nhất cho Client hiển thị (Chỉ lấy PENDING hoặc CONFIRMED)"""
        results = []
        conn = None
        cursor = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)
            # Chỉ lấy ảnh chưa xử lý hoặc đã confirm, bỏ qua ảnh đã đánh dấu FALSE POSITIVE (đã xóa)
            sql = "SELECT * FROM scan_results WHERE is_ng = 1 AND status != 'FALSE_POSITIVE' ORDER BY created_at DESC LIMIT %s"
            cursor.execute(sql, (limit,))
            results = cursor.fetchall()
        except mysql.connector.Error as err:
            logger.error(f"Lỗi get_latest_ng_results: {err}")
        finally:
            if cursor: cursor.close()
            if conn: conn.close()
        return results

    def get_today_scan_count(self):
        """Lấy tổng số lượng ảnh đã scan trong ngày hôm nay"""
        count = 0
        conn = None
        cursor = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            today_str = datetime.now().strftime('%Y-%m-%d 00:00:00')
            sql = "SELECT COUNT(*) FROM checked_history WHERE check_date >= %s"
            cursor.execute(sql, (today_str,))
            count = cursor.fetchone()[0]
        except mysql.connector.Error:
            pass
        finally:
            if cursor: cursor.close()
            if conn: conn.close()
        return count

    def update_validation_status(self, file_path, is_defect):
        """Cập nhật trạng thái xác nhận từ Client"""
        conn = None
        cursor = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if is_defect:
                # Xác nhận lỗi -> Update status CONFIRMED
                sql = "UPDATE scan_results SET status = 'CONFIRMED' WHERE file_path = %s"
                cursor.execute(sql, (file_path,))
            else:
                # Không phải lỗi -> Xóa khỏi bảng scan_results (hoặc đánh dấu FALSE_POSITIVE)
                # Client yêu cầu "xóa khỏi list" -> Xóa record là sạch nhất
                sql = "DELETE FROM scan_results WHERE file_path = %s"
                cursor.execute(sql, (file_path,))
                
            conn.commit()
        except mysql.connector.Error as err:
            logger.error(f"Lỗi update_validation_status: {err}")
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

if __name__ == "__main__":
    # Test Module
    print("Testing Database Manager...")
    db = DatabaseManager()
    db.init_db()
    
    # Test Count
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM images')
        cnt = cursor.fetchone()[0]
        print(f"Total images in DB: {cnt}")
        conn.close()
    except Exception as e:
        print(f"Test failed: {e}")
