from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
import mysql.connector
from datetime import datetime, timedelta
import uvicorn
from typing import List, Optional, Dict

app = FastAPI(title="FluxImage API Server")

# CẤU HÌNH DATABASE
DB_CONFIG = {
    'user': 'root',
    'password': 'ivihaengsung@1',
    'host': '127.0.0.1', # Chạy trên localhost của Server chứa DB
    'port': 3306,
    'database': 'pid_search_db',
    'raise_on_warnings': True,
    'connection_timeout': 10
}

def get_db_connection():
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except mysql.connector.Error as err:
        print(f"Database Error: {err}")
        return None

# --- API 1: KIỂM TRA KẾT NỐI (Theo tài liệu) ---
@app.get("/")
def check_status():
    conn = get_db_connection()
    status = "online" if conn else "offline"
    count = 0
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM images")
            count = cursor.fetchone()[0]
            conn.close()
        except:
            pass
    return {
        "status": status,
        "total_images": count
    }

# --- API 2: TÌM KIẾM THEO PID (Theo tài liệu) ---
@app.get("/search/{pid}")
def search_by_pid(pid: str):
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")

    cursor = conn.cursor(dictionary=True)
    try:
        query = "SELECT file_path, line, scan_date FROM images WHERE pid = %s"
        cursor.execute(query, (pid,))
        results = cursor.fetchall()
        if not results:
             raise HTTPException(status_code=404, detail="PID not found")
        return results
    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=str(err))
    finally:
        cursor.close()
        conn.close()

# --- API 3: TÌM KIẾM THEO NGÀY (Bổ sung cho App Recheck) ---
@app.get("/images_by_date")
def get_images_by_date(date: str = Query(..., description="Date in YYYY-MM-DD format")):
    """
    API Bổ sung: Lấy ảnh AOI TOP/BOT theo ngày để Recheck.
    """
    try:
        target_date = datetime.strptime(date, '%Y-%m-%d')
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")

    cursor = conn.cursor()
    try:
        # Optimization: Use timestamp range
        start_date = target_date.strftime('%Y-%m-%d 00:00:00')
        end_date = (target_date + timedelta(days=1)).strftime('%Y-%m-%d 00:00:00')

        query = ("SELECT file_path FROM images "
                 "WHERE scan_date >= %s AND scan_date < %s "
                 "AND (file_path LIKE '%AOI%TOP%' OR file_path LIKE '%AOI%BOT%')")
        
        cursor.execute(query, (start_date, end_date))
        # Chỉ trả về list string (file_path) cho nhẹ
        results = [row[0] for row in cursor]
        return results

    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=str(err))
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    # Chạy Host 0.0.0.0 để cho phép máy khác truy cập
    # Port 8080 theo hướng dẫn
    print("Starting API Server on Port 8080...")
    uvicorn.run(app, host="0.0.0.0", port=8080)
