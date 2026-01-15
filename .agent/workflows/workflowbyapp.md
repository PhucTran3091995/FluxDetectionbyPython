---
description: A tree of documents
---

d:/24. C Study/9. FluxApp_Python/
│
├── main.py                # File khởi chạy ứng dụng (Entry point)
│
├── core/                  # Chứa logic cốt lõi
│   └── yolo_helper.py     # Xử lý AI YOLO (Di chuyển từ file gốc)
│
├── ui/                    # Chứa thành phần giao diện
│   ├── main_window.py     # Cửa sổ chính (Tách từ main.py cũ)
│   ├── recheck_window.py  # Cửa sổ Recheck (Tách từ main.py cũ)
│   └── styles.py          # CSS Stylesheet (Để riêng cho gọn)
│
└── workers/               # Chứa các luồng xử lý nền (Background Threads)
    └── flux_worker.py     # Luồng quét ảnh (FluxWorker)