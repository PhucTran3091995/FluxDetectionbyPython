
STYLESHEET = """
QMainWindow { background-color: #1e1e2e; color: #cdd6f4; }
QWidget { font-family: 'Segoe UI', sans-serif; font-size: 10pt; }
QTabWidget::pane { border: 1px solid #313244; background: #1e1e2e; }
QTabBar::tab { background: #313244; color: #a6adc8; padding: 10px 20px; border-top-left-radius: 4px; border-top-right-radius: 4px; margin-right: 2px; }
QTabBar::tab:selected { background: #89b4fa; color: #1e1e2e; font-weight: bold; }
QGroupBox { border: 1px solid #45475a; border-radius: 8px; margin-top: 20px; font-weight: bold; color: #89b4fa; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
QLineEdit { background-color: #313244; border: 1px solid #45475a; border-radius: 6px; padding: 8px; color: #ffffff; }
QLineEdit:focus { border: 1px solid #89b4fa; }
QLabel { color: #cdd6f4; }
QPushButton { background-color: #45475a; color: white; padding: 8px 16px; border-radius: 6px; font-weight: bold; }
QPushButton:hover { background-color: #585b70; }
QPushButton:disabled { background-color: #313244; color: #6c7086; }
QPushButton#btn_start { background-color: #0d6efd; }
QPushButton#btn_start:hover { background-color: #0b5ed7; }
QPushButton#btn_stop { background-color: #e63946; }
QPushButton#btn_stop:hover { background-color: #d62828; }
QPushButton#btn_recheck { background-color: #f39c12; color: #1e1e2e; }
QPushButton#btn_recheck:hover { background-color: #e67e22; }
QProgressBar { border: 1px solid #45475a; border-radius: 6px; text-align: center; background-color: #313244; color: white; font-weight: bold; }
QProgressBar::chunk { background-color: #2ecc71; border-radius: 5px; }
"""
