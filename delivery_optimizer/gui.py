import os
import sys
import time
import webbrowser
from pathlib import Path
import subprocess

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SERVER_FILE = PROJECT_ROOT / "server.py"

def launch_server():
    print("Khởi động Backend Server (Flask)...")
    creationflags = 0
    if os.name == 'nt':
        creationflags = subprocess.CREATE_NO_WINDOW
        
    process = subprocess.Popen(
        [sys.executable, str(SERVER_FILE)],
        cwd=str(PROJECT_ROOT),
        creationflags=creationflags
    )
    return process

def main():
    print("Đang kết nối Giao diện HTML với Backend Python...")
    
    # Chạy server ở nền
    server_process = launch_server()
    
    # Đợi máy chủ Flask khởi động
    time.sleep(2.0)
    
    # Mở trình duyệt với chế độ App (không có thanh địa chỉ)
    url = "http://127.0.0.1:5000/"
    opened = False
    try:
        if os.name == 'nt':
            edge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
            chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
            
            if os.path.exists(edge_path):
                subprocess.Popen([edge_path, f"--app={url}"])
                opened = True
            elif os.path.exists(chrome_path):
                subprocess.Popen([chrome_path, f"--app={url}"])
                opened = True
                
    except Exception as e:
        print(f"Lỗi khi mở chế độ App: {e}")
        
    if not opened:
        webbrowser.open(url)
        
    print("\nỨng dụng đã được mở trong trình duyệt.")
    print("Giao diện HTML (delivery_optimizer_demo.html) hiện đang được xử lý bởi backend Python.")
    print("Vui lòng không đóng cửa sổ console này khi đang sử dụng.")
    print("\nNhấn Ctrl+C để thoát và tắt server.")
    
    try:
        server_process.wait()
    except KeyboardInterrupt:
        print("\nĐang tắt server...")
        server_process.terminate()

if __name__ == "__main__":
    main()
