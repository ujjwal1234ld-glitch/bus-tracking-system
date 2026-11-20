"""Pure-Python HTTP JSON API + Laptop Admin Control Panel + Instant Mobile App server.

Uses only Python's standard library (http.server + sqlite3) so it runs on any
laptop without needing heavy web frameworks.
"""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import socket
from typing import Any, Dict
from urllib.parse import parse_qs, urlparse

from server.admin_ui import ADMIN_DASHBOARD_HTML, render_download_page
from server.config import DB_PATH, HOST, PORT
from server.database import BusDatabase
from server.mobile_web_ui import MOBILE_APP_HTML, PWA_MANIFEST_JSON
from server.seed_demo_data import seed_demo_data

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APK_FILE_PATH = os.path.join(PROJECT_ROOT, "downloads", "bustracker.apk")
ASSETS_ROOT = os.path.join(PROJECT_ROOT, "assets")


def _detect_lan_url(port: int) -> str:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
        sock.close()
    except Exception:
        ip = "127.0.0.1"
    return f"http://{ip}:{port}"


def create_server(
    host: str = HOST, port: int = PORT, db_path: str = DB_PATH
) -> ThreadingHTTPServer:
    """Create and return a configured ThreadingHTTPServer instance."""
    db = BusDatabase(db_path=db_path)

    class BusTrackerHandler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:
            print(f"[Server] {self.address_string()} - {format % args}")

        def _send_json(self, status_code: int, payload: Dict[str, Any]) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_html(self, status_code: int, html: str) -> None:
            body = html.encode("utf-8")
            self.send_response(status_code)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_file(self, file_path: str, content_type: str, download_name: str = "") -> None:
            if not os.path.exists(file_path):
                self._send_json(404, {"error": f"File not found: {download_name or file_path}"})
                return
            with open(file_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            if download_name:
                self.send_header("Content-Disposition", f'attachment; filename="{download_name}"')
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

        def _read_json_body(self) -> Dict[str, Any]:
            length = int(self.headers.get("Content-Length", "0"))
            if length == 0:
                return {}
            raw = self.rfile.read(length).decode("utf-8")
            return json.loads(raw)

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            path = parsed.path.rstrip("/") or "/"
            params = parse_qs(parsed.query)
            actual_port = self.server.server_address[1]
            lan_url = _detect_lan_url(actual_port)

            try:
                # Laptop Admin Dashboard, Instant Mobile App (/app), & APK Download Page
                if path in ("/", "/admin"):
                    self._send_html(200, ADMIN_DASHBOARD_HTML)
                elif path == "/app":
                    self._send_html(200, MOBILE_APP_HTML)
                elif path == "/manifest.json":
                    self._send_json(200, PWA_MANIFEST_JSON)
                elif path.startswith("/assets/"):
                    rel = path[len("/assets/"):].lstrip("/")
                    full_path = os.path.normpath(os.path.join(ASSETS_ROOT, rel))
                    if full_path.startswith(ASSETS_ROOT) and os.path.isfile(full_path):
                        self._send_file(full_path, "image/png")
                    else:
                        self._send_json(404, {"error": "Asset not found."})
                elif path == "/download":
                    self._send_html(200, render_download_page(lan_url, os.path.exists(APK_FILE_PATH)))
                elif path == "/download/app.apk":
                    self._send_file(
                        APK_FILE_PATH,
                        "application/vnd.android.package-archive",
                        "bustracker.apk",
                    )
                elif path == "/api/admin/overview":
                    overview = db.get_admin_overview()
                    overview["lan_url"] = lan_url
                    self._send_json(200, overview)
                elif path == "/api/admin/backup-db":
                    self._send_file(db_path, "application/octet-stream", "bus_tracker_backup.db")

                # Mobile App REST API
                elif path == "/health":
                    self._send_json(200, {"status": "ok"})
                elif path == "/api/routes":
                    self._send_json(200, {"routes": db.list_routes()})
                elif path.startswith("/api/routes/") and path.endswith("/enrollments"):
                    route_id = int(path.split("/")[3])
                    self._send_json(200, {"enrollments": db.list_route_enrollments(route_id)})
                elif path.startswith("/api/routes/") and path.endswith("/wait-requests"):
                    route_id = int(path.split("/")[3])
                    self._send_json(200, {"wait_requests": db.list_wait_requests(route_id)})
                elif path.startswith("/api/routes/"):
                    route_id = int(path.split("/")[3])
                    route = db.get_route_by_id(route_id)
                    if not route:
                        self._send_json(404, {"error": "Route not found."})
                    else:
                        self._send_json(200, {"route": route})
                elif path.startswith("/api/driver/") and path.endswith("/route"):
                    driver_id = int(path.split("/")[3])
                    self._send_json(200, {"route": db.get_driver_route(driver_id)})
                elif path.startswith("/api/student/") and path.endswith("/status"):
                    student_id = int(path.split("/")[3])
                    self._send_json(200, db.get_student_status(student_id))
                elif path.startswith("/api/notifications/"):
                    user_id = int(path.split("/")[3])
                    unread_only = params.get("unread_only", ["0"])[0] == "1"
                    self._send_json(
                        200,
                        {"notifications": db.list_notifications(user_id, unread_only=unread_only)},
                    )
                else:
                    self._send_json(404, {"error": f"Unknown endpoint: {path}"})
            except Exception as exc:
                self._send_json(400, {"error": str(exc)})

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            path = parsed.path.rstrip("/")

            try:
                data = self._read_json_body()

                # Laptop Admin Actions
                if path == "/api/admin/seed-demo":
                    seed_demo_data(db_path=db_path)
                    self._send_json(200, {"status": "seeded"})
                elif path.startswith("/api/admin/users/") and path.endswith("/delete"):
                    user_id = int(path.split("/")[4])
                    db.delete_user(user_id)
                    self._send_json(200, {"status": "deleted"})

                # Mobile App REST API
                elif path == "/api/auth/register":
                    user = db.register_user(
                        name=data["name"],
                        email=data["email"],
                        password=data["password"],
                        role=data["role"],
                        phone=data.get("phone", ""),
                    )
                    self._send_json(201, {"user": user})

                elif path == "/api/auth/login":
                    user = db.login_user(
                        email=data["email"],
                        password=data["password"],
                        expected_role=data["role"],
                    )
                    self._send_json(200, {"user": user})

                elif path == "/api/routes":
                    route = db.create_route(
                        driver_id=int(data["driver_id"]),
                        bus_number=data["bus_number"],
                        route_name=data["route_name"],
                        destination_name=data.get("destination_name", "Campus Main Gate"),
                        destination_lat=float(data.get("destination_lat", 28.4744)),
                        destination_lon=float(data.get("destination_lon", 77.5040)),
                        departure_time=data.get("departure_time", "07:30 AM"),
                        arrival_time=data.get("arrival_time", "08:30 AM"),
                        capacity=int(data.get("capacity", 30)),
                    )
                    self._send_json(201, {"route": route})

                elif path.startswith("/api/routes/") and path.endswith("/schedule"):
                    route_id = int(path.split("/")[3])
                    route = db.update_route_schedule_and_destination(
                        route_id=route_id,
                        departure_time=data.get("departure_time"),
                        arrival_time=data.get("arrival_time"),
                        destination_name=data.get("destination_name"),
                        destination_lat=data.get("destination_lat"),
                        destination_lon=data.get("destination_lon"),
                    )
                    self._send_json(200, {"route": route})

                elif path.startswith("/api/routes/") and path.endswith("/stops"):
                    route_id = int(path.split("/")[3])
                    stop = db.add_stop(
                        route_id=route_id,
                        stop_name=data["stop_name"],
                        lat=float(data["lat"]),
                        lon=float(data["lon"]),
                        scheduled_time=data.get("scheduled_time", ""),
                    )
                    self._send_json(201, {"stop": stop})

                elif path.startswith("/api/routes/") and path.endswith("/location"):
                    route_id = int(path.split("/")[3])
                    result = db.update_bus_location(
                        route_id=route_id,
                        lat=float(data["lat"]),
                        lon=float(data["lon"]),
                        is_sharing=bool(data.get("is_sharing", True)),
                    )
                    self._send_json(200, result)

                elif path.startswith("/api/routes/") and path.endswith("/reset-trip"):
                    route_id = int(path.split("/")[3])
                    db.reset_trip_arrivals(route_id)
                    self._send_json(200, {"status": "trip_reset"})

                elif path == "/api/enrollments/request":
                    enrollment = db.request_route_enrollment(
                        student_id=int(data["student_id"]),
                        route_id=int(data["route_id"]),
                    )
                    self._send_json(201, {"enrollment": enrollment})

                elif path.startswith("/api/enrollments/") and path.endswith("/decision"):
                    enrollment_id = int(path.split("/")[3])
                    enrollment = db.decide_enrollment(
                        enrollment_id=enrollment_id,
                        decision=data["decision"],
                        pickup_stop_id=data.get("pickup_stop_id"),
                    )
                    self._send_json(200, {"enrollment": enrollment})

                elif path.startswith("/api/enrollments/") and path.endswith("/pickup"):
                    enrollment_id = int(path.split("/")[3])
                    enrollment = db.assign_student_pickup(
                        enrollment_id=enrollment_id,
                        pickup_stop_id=int(data["pickup_stop_id"]),
                    )
                    self._send_json(200, {"enrollment": enrollment})

                elif path.startswith("/api/student/") and path.endswith("/location"):
                    student_id = int(path.split("/")[3])
                    db.update_student_location(
                        student_id=student_id,
                        lat=float(data["lat"]),
                        lon=float(data["lon"]),
                    )
                    self._send_json(200, {"status": "updated"})

                elif path == "/api/wait-requests":
                    req = db.create_wait_request(
                        student_id=int(data["student_id"]),
                        route_id=int(data["route_id"]),
                        eta_message=data["eta_message"],
                    )
                    self._send_json(201, {"wait_request": req})

                elif path.startswith("/api/wait-requests/") and path.endswith("/respond"):
                    request_id = int(path.split("/")[3])
                    req = db.respond_wait_request(
                        request_id=request_id,
                        decision=data["decision"],
                    )
                    self._send_json(200, {"wait_request": req})

                elif path.startswith("/api/notifications/") and path.endswith("/read"):
                    user_id = int(path.split("/")[3])
                    db.mark_notifications_read(user_id)
                    self._send_json(200, {"status": "marked_read"})

                else:
                    self._send_json(404, {"error": f"Unknown endpoint: {path}"})
            except Exception as exc:
                self._send_json(400, {"error": str(exc)})

    return ThreadingHTTPServer((host, port), BusTrackerHandler)


def main() -> None:
    server = create_server(HOST, PORT, DB_PATH)
    lan = _detect_lan_url(PORT)
    print(f"Bus Tracking Server running at http://{HOST}:{PORT}")
    print(f"Laptop Admin Control Panel: http://127.0.0.1:{PORT}/admin")
    print(f"Instant Mobile App (Phone): {lan}/app")
    print(f"Mobile APK Download Page  : {lan}/download")
    print(f"Database file: {DB_PATH}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.server_close()


if __name__ == "__main__":
    main()
