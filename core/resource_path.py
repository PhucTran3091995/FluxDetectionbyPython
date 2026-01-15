import sys
import os

def resource_path(relative_path):
    """ 
    Lấy đường dẫn tuyệt đối của tài nguyên.
    Hoạt động cho cả môi trường chạy trực tiếp (Dev) và PyInstaller (Exe).
    """
    try:
        # PyInstaller tạo ra một thư mục tạm và lưu đường dẫn trong _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)
