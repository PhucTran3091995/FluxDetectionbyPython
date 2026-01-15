@echo off
echo Dang build ung dung FluxApp...
echo Vui long cho doi, qua trinh nay co the mat vai phut...

:: Build command
:: --clean: Xoa cache cu
:: --noconfirm: Khong hoi lai
:: --onedir: Tao thu muc (khuyen dung cho app AI/DB) thay vi onefile
:: --windowed: Khong hien cua so CMD
:: --icon: Icon app
:: --add-data: Nhung file tai nguyen (Windows dung dau cham phay ;)
:: --exclude-module: Loai bo thu vien khong can thiet de giam dung luong

pyinstaller --clean --noconfirm --onedir --windowed ^
    --name "FluxApp_QA" ^
    --icon "icon.jpg" ^
    --add-data "best.onnx;." ^
    --add-data "data.yaml;." ^
    --add-data "icon.jpg;." ^
    --hidden-import "mysql.connector.plugins" ^
    --exclude-module "matplotlib" ^
    --exclude-module "tkinter" ^
    --exclude-module "notebook" ^
    --exclude-module "scipy" ^
    --exclude-module "IPython" ^
    "main.py"

echo.
echo ========================================================
echo BUILD HOAN TAT!
echo Kiem tra thu muc 'dist/FluxApp_QA' de lay ung dung.
echo ========================================================
pause