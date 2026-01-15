from core.database_mysql import DatabaseManager
import logging
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_missing_index():
    db = DatabaseManager()
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        logger.info("⏳ Đang BẮT ĐẦU tạo Index cho cột 'scan_date'...")
        logger.info("⚠️ LƯU Ý: Với bảng lớn, việc này có thể mất vài phút. Vui lòng KHÔNG tắt chương trình.")
        
        start_time = time.time()
        
        # Lệnh ALTER TABLE để thêm index
        sql = "CREATE INDEX idx_scan_date ON images(scan_date)"
        cursor.execute(sql)
        
        end_time = time.time()
        elapsed = end_time - start_time
        
        logger.info(f"✅ Đã tạo Index THÀNH CÔNG! Thời gian thực thi: {elapsed:.2f} giây.")

    except Exception as e:
        if "Duplicate key name" in str(e):
             logger.info("ℹ️ Index đã tồn tại (không cần tạo lại).")
        else:
            logger.error(f"❌ Lỗi khi tạo Index: {e}")
            
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    fix_missing_index()
