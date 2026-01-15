from core.database_mysql import DatabaseManager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_indexes():
    db = DatabaseManager()
    try:
        conn = db.get_connection()
        cursor = conn.cursor(dictionary=True) # Use dictionary cursor for easier reading
        
        logger.info("Checking indexes on table 'images'...")
        cursor.execute("SHOW INDEX FROM images")
        indexes = cursor.fetchall()
        
        found_scan_date_index = False
        
        print(f"{'Key Name':<20} {'Column Name':<20} {'Non_unique':<10}")
        print("-" * 50)
        
        for idx in indexes:
            key_name = idx.get('Key_name')
            col_name = idx.get('Column_name')
            non_unique = idx.get('Non_unique')
            print(f"{key_name:<20} {col_name:<20} {non_unique:<10}")
            
            if col_name == 'scan_date':
                found_scan_date_index = True
                
        print("-" * 50)
        
        if found_scan_date_index:
            logger.info("✅ Đã có Index cho cột 'scan_date'.")
            return True
        else:
            logger.warning("❌ CẢNH BÁO: Chưa có Index cho cột 'scan_date'. Đây là nguyên nhân gây chậm!")
            return False

    except Exception as e:
        logger.error(f"Lỗi kiểm tra: {e}")
        return False
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    check_indexes()
