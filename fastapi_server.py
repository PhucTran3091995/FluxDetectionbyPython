from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
import mysql.connector
from datetime import datetime, timedelta
import uvicorn
from typing import List

app = FastAPI(title="FluxImage API")

# Database Configuration
DB_CONFIG = {
    'user': 'root',
    'password': 'ivihaengsung@1',
    'host': '127.0.0.1', # Assuming API runs on the same server as DB, or change to 10.7.10.6
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

@app.get("/images", response_model=List[str])
def get_images(date: str = Query(..., description="Date in YYYY-MM-DD format")):
    """
    Fetch AOI TOP/BOT images for a specific date.
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
        
        results = [row[0] for row in cursor]
        return results

    except mysql.connector.Error as err:
        raise HTTPException(status_code=500, detail=f"Query Error: {str(err)}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    # Run with: python fastapi_server.py
    # Host 0.0.0.0 allows access from other machines
    uvicorn.run(app, host="0.0.0.0", port=8000)
