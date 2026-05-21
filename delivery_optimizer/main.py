import sys
import os

# Thêm thư mục gốc vào path để import các module local
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import sys
sys.stdout.reconfigure(encoding='utf-8')
import gui

def main():
    print("--- KHỞI CHẠY GIAO DIỆN TỐI ƯU GIAO HÀNG ---")
    gui.main()

if __name__ == "__main__":
    main()
