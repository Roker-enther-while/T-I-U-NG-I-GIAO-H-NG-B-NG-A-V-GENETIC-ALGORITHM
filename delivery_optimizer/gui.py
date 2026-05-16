import socket
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SERVER_FILE = PROJECT_ROOT / "server.py"
DEFAULT_PORT = 5000


class DeliveryApp:
    """Launcher app-window cho backend Python trong server.py."""

    def __init__(self, port=DEFAULT_PORT, open_browser=True):
        self.port = port
        self.open_browser = open_browser
        self.url = f"http://127.0.0.1:{self.port}/"
        self.server_process = None

    def mainloop(self):
        self.run()

    def run(self):
        if not SERVER_FILE.exists():
            raise FileNotFoundError(f"Khong tim thay backend Python: {SERVER_FILE}")

        if not is_port_available(self.port):
            print(f"Port {self.port} dang duoc su dung. Thu mo app tai server hien co...")
        else:
            self.server_process = subprocess.Popen(
                [sys.executable, str(SERVER_FILE)],
                cwd=str(PROJECT_ROOT),
            )

        print("==================================================")
        print("     DELIVROUTE - PYTHON BACKEND APP")
        print("==================================================")
        print(" Backend: server.py")
        print(" Source thuat toan: delivery_optimizer/")
        print(f" URL: {self.url}")
        print(" Nhan Ctrl+C de dung app.")
        print()

        if self.open_browser:
            threading.Thread(target=open_app_window_after_ready, args=(self.url,), daemon=True).start()

        try:
            while True:
                if self.server_process and self.server_process.poll() is not None:
                    raise RuntimeError("Backend server.py da dung bat thuong.")
                time.sleep(0.5)
        except KeyboardInterrupt:
            print("\nDang dung DelivRoute...")
        finally:
            if self.server_process and self.server_process.poll() is None:
                self.server_process.terminate()
                try:
                    self.server_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.server_process.kill()


def is_port_available(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        return sock.connect_ex(("127.0.0.1", port)) != 0


def open_app_window_after_ready(url):
    wait_for_server(url)
    browser = find_app_browser()
    if browser:
        subprocess.Popen(
            [
                str(browser),
                f"--app={url}",
                "--new-window",
                "--disable-features=Translate",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return
    webbrowser.open(url)


def wait_for_server(url, timeout=20):
    import urllib.request

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except Exception:
            time.sleep(0.25)


def find_app_browser():
    candidates = [
        Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def main(argv=None):
    argv = argv or sys.argv[1:]
    open_browser = "--no-browser" not in argv
    app = DeliveryApp(open_browser=open_browser)
    app.mainloop()


if __name__ == "__main__":
    main()
