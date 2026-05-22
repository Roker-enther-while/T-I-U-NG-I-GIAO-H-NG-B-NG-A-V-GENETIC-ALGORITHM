import os
import sys
import time
import webbrowser
from pathlib import Path
import subprocess

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SERVER_FILE = PROJECT_ROOT / "server.py"
SERVER_PORT = 5000

def stop_existing_server():
    if os.name != 'nt':
        return
    server_path = str(SERVER_FILE)
    project_root = str(PROJECT_ROOT)
    command = (
        f"$server = '{server_path}'; "
        f"$project = '{project_root}'; "
        f"$conn = Get-NetTCPConnection -LocalPort {SERVER_PORT} -State Listen "
        "-ErrorAction SilentlyContinue; "
        "if ($conn) { "
        "$conn | Select-Object -ExpandProperty OwningProcess -Unique | "
        "ForEach-Object { "
        "$ownerPid = $_; "
        "$proc = Get-CimInstance Win32_Process -Filter \"ProcessId=$ownerPid\" "
        "-ErrorAction SilentlyContinue; "
        "if ($proc -and $proc.CommandLine -and "
        "($proc.CommandLine -like \"*$server*\" -or "
        "($proc.CommandLine -like \"*server.py*\" -and $proc.CommandLine -like \"*$project*\"))) { "
        "Stop-Process -Id $ownerPid -Force -ErrorAction SilentlyContinue "
        "} "
        "} "
        "}"
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )

def launch_server():
    stop_existing_server()
    print("Khởi động Backend Server (Flask)...")
    process = subprocess.Popen(
        [sys.executable, str(SERVER_FILE)],
        cwd=str(PROJECT_ROOT)
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
