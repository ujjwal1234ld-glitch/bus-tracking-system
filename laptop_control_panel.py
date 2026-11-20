"""One-click Laptop Control Panel launcher.

Run this on your laptop:
    python3 laptop_control_panel.py

It starts the Python Bus Tracking Server + SQLite database, shows your laptop's
Wi-Fi URL for drivers and students to connect from their phones, and opens the
Admin Control Panel in your laptop browser.
"""

import socket
import threading
import time
import webbrowser

from server.app import create_server
from server.config import DB_PATH, HOST, PORT


def get_lan_ip() -> str:
    """Detect the laptop's local Wi-Fi IP address so phones can connect."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
        sock.close()
        return ip
    except Exception:
        return "127.0.0.1"


def main() -> None:
    lan_ip = get_lan_ip()
    admin_url = f"http://127.0.0.1:{PORT}/admin"
    mobile_server_url = f"http://{lan_ip}:{PORT}"
    apk_download_url = f"http://{lan_ip}:{PORT}/download"

    server = create_server(HOST, PORT, DB_PATH)

    print("=" * 64)
    print("  BUS TRACKING SYSTEM - LAPTOP SERVER & ADMIN CONTROL PANEL")
    print("=" * 64)
    print(f"  Laptop Admin Panel : {admin_url}")
    print(f"  Mobile Server URL  : {mobile_server_url}")
    print(f"  Phone APK Download : {apk_download_url}")
    print(f"  SQLite Database    : {DB_PATH}")
    print("=" * 64)
    print("  Keep this window open while drivers and students use the app.")
    print("  Press Ctrl+C to stop the server.")

    def _open_browser():
        time.sleep(0.8)
        webbrowser.open(admin_url)

    threading.Thread(target=_open_browser, daemon=True).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Bus Tracking Server...")
        server.server_close()


if __name__ == "__main__":
    main()
