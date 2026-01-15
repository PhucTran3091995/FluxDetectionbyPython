from core.database_mysql import DatabaseManager
import datetime

print("Testing database connection...")
db = DatabaseManager()
conn = db.get_connection()

if conn:
    print("Connection successful!")
    try:
        cursor = conn.cursor()
        print("Executing test query...")
        cursor.execute("SELECT COUNT(*) FROM images")
        count = cursor.fetchone()[0]
        print(f"Total images in DB: {count}")
    except Exception as e:
        print(f"Query Error: {e}")
    finally:
        conn.close()
else:
    print("Connection FAILED.")
