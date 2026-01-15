@echo off
echo Dang build ung dung FluxApp (Toi uu cho PyQt6 + Giam dung luong)...
echo Vui long cho doi...

:: Build command
:: --onedir: Khuyen khich cho app lon de chay nhanh va on dinh
:: --noconsole: An CMD
:: --upx-dir: Su dung UPX de nen exe va dll (Can cai dat UPX neu muon cuc ky nho gon, neu khong co the bo qua)
:: --exclude-module: Loai bo cac module nang khong dung nhu matplotlib, pandas (neu code khong dung), pillow (neu dung opencv roi)

:: QUAN TRONG: Them --hidden-import cho PyQt6
pyinstaller --clean --noconfirm --onedir --windowed ^
    --name "FluxApp_Light" ^
    --icon "icon.jpg" ^
    --add-data "best.onnx;." ^
    --add-data "data.yaml;." ^
    --add-data "icon.jpg;." ^
    --hidden-import "PyQt6" ^
    --hidden-import "PyQt6.QtCore" ^
    --hidden-import "PyQt6.QtGui" ^
    --hidden-import "PyQt6.QtWidgets" ^
    --hidden-import "mysql.connector.plugins" ^
    --exclude-module "matplotlib" ^
    --exclude-module "tkinter" ^
    --exclude-module "notebook" ^
    --exclude-module "scipy" ^
    --exclude-module "IPython" ^
    --exclude-module "http" ^
    --exclude-module "xml" ^
    --exclude-module "pydoc" ^
    --exclude-module "lib2to3" ^
    "main.py"

echo.
echo ========================================================
echo BUILD HOAN TAT!
echo Kiem tra thu muc 'dist/FluxApp_Light'.
echo Neu bi loi font: Copy thu muc 'styles' hoac 'fonts' vao cung thu muc exe (neu app co dung font rieng)
echo ========================================================
pause
