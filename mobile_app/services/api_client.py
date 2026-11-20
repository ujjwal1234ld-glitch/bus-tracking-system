"""Pure-Python HTTP client using only Python's standard library (urllib.request).

Zero third-party dependencies (no requests / charset_normalizer), which makes
Buildozer Android APK compilation much faster and avoids wheel errors.
"""

import json
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from mobile_app.config import DEFAULT_SERVER_URL


class BusTrackerAPI:
    """Clean wrapper around the Bus Tracking REST API."""

    def __init__(self, base_url: str = DEFAULT_SERVER_URL, timeout: float = 6.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def set_base_url(self, base_url: str) -> None:
        self.base_url = base_url.strip().rstrip("/")

    def _request(
        self, method: str, endpoint: str, payload: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        data_bytes = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {"Content-Type": "application/json"} if payload is not None else {}
        req = Request(url, data=data_bytes, headers=headers, method=method)

        try:
            with urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw)
        except HTTPError as exc:
            try:
                err_data = json.loads(exc.read().decode("utf-8"))
                msg = err_data.get("error", f"Server error ({exc.code})")
            except Exception:
                msg = f"Server error ({exc.code})"
            raise RuntimeError(msg) from exc
        except URLError as exc:
            raise RuntimeError(f"Cannot reach server at {self.base_url}: {exc.reason}") from exc
        except Exception as exc:
            raise RuntimeError(f"Request failed: {exc}") from exc

    # --- Auth ---
    def register(
        self, name: str, email: str, password: str, role: str, phone: str = ""
    ) -> Dict[str, Any]:
        return self._request(
            "POST",
            "/api/auth/register",
            {
                "name": name,
                "email": email,
                "password": password,
                "role": role,
                "phone": phone,
            },
        )["user"]

    def login(self, email: str, password: str, role: str) -> Dict[str, Any]:
        return self._request(
            "POST",
            "/api/auth/login",
            {"email": email, "password": password, "role": role},
        )["user"]

    # --- Routes & Stops ---
    def list_routes(self) -> List[Dict[str, Any]]:
        return self._request("GET", "/api/routes")["routes"]

    def get_driver_route(self, driver_id: int) -> Optional[Dict[str, Any]]:
        return self._request("GET", f"/api/driver/{driver_id}/route")["route"]

    def create_route(
        self,
        driver_id: int,
        bus_number: str,
        route_name: str,
        destination_name: str,
        destination_lat: float,
        destination_lon: float,
        departure_time: str,
        arrival_time: str,
        capacity: int = 30,
    ) -> Dict[str, Any]:
        return self._request(
            "POST",
            "/api/routes",
            {
                "driver_id": driver_id,
                "bus_number": bus_number,
                "route_name": route_name,
                "destination_name": destination_name,
                "destination_lat": destination_lat,
                "destination_lon": destination_lon,
                "departure_time": departure_time,
                "arrival_time": arrival_time,
                "capacity": capacity,
            },
        )["route"]

    def update_schedule(
        self,
        route_id: int,
        departure_time: str,
        arrival_time: str,
        destination_name: str,
        destination_lat: float,
        destination_lon: float,
    ) -> Dict[str, Any]:
        return self._request(
            "POST",
            f"/api/routes/{route_id}/schedule",
            {
                "departure_time": departure_time,
                "arrival_time": arrival_time,
                "destination_name": destination_name,
                "destination_lat": destination_lat,
                "destination_lon": destination_lon,
            },
        )["route"]

    def add_stop(
        self,
        route_id: int,
        stop_name: str,
        lat: float,
        lon: float,
        scheduled_time: str = "",
    ) -> Dict[str, Any]:
        return self._request(
            "POST",
            f"/api/routes/{route_id}/stops",
            {
                "stop_name": stop_name,
                "lat": lat,
                "lon": lon,
                "scheduled_time": scheduled_time,
            },
        )["stop"]

    def update_bus_location(
        self, route_id: int, lat: float, lon: float, is_sharing: bool = True
    ) -> Dict[str, Any]:
        return self._request(
            "POST",
            f"/api/routes/{route_id}/location",
            {"lat": lat, "lon": lon, "is_sharing": is_sharing},
        )

    def reset_trip(self, route_id: int) -> None:
        self._request("POST", f"/api/routes/{route_id}/reset-trip")

    # --- Student Enrollment & Approvals ---
    def request_enrollment(self, student_id: int, route_id: int) -> Dict[str, Any]:
        return self._request(
            "POST",
            "/api/enrollments/request",
            {"student_id": student_id, "route_id": route_id},
        )["enrollment"]

    def list_enrollments(self, route_id: int) -> List[Dict[str, Any]]:
        return self._request("GET", f"/api/routes/{route_id}/enrollments")["enrollments"]

    def decide_enrollment(
        self, enrollment_id: int, decision: str, pickup_stop_id: Optional[int] = None
    ) -> Dict[str, Any]:
        return self._request(
            "POST",
            f"/api/enrollments/{enrollment_id}/decision",
            {"decision": decision, "pickup_stop_id": pickup_stop_id},
        )["enrollment"]

    def assign_pickup(self, enrollment_id: int, pickup_stop_id: int) -> Dict[str, Any]:
        return self._request(
            "POST",
            f"/api/enrollments/{enrollment_id}/pickup",
            {"pickup_stop_id": pickup_stop_id},
        )["enrollment"]

    def update_student_location(self, student_id: int, lat: float, lon: float) -> None:
        self._request(
            "POST",
            f"/api/student/{student_id}/location",
            {"lat": lat, "lon": lon},
        )

    def get_student_status(self, student_id: int) -> Dict[str, Any]:
        return self._request("GET", f"/api/student/{student_id}/status")

    # --- Wait Requests ---
    def send_wait_request(
        self, student_id: int, route_id: int, eta_message: str
    ) -> Dict[str, Any]:
        return self._request(
            "POST",
            "/api/wait-requests",
            {
                "student_id": student_id,
                "route_id": route_id,
                "eta_message": eta_message,
            },
        )["wait_request"]

    def list_wait_requests(self, route_id: int) -> List[Dict[str, Any]]:
        return self._request("GET", f"/api/routes/{route_id}/wait-requests")["wait_requests"]

    def respond_wait_request(self, request_id: int, decision: str) -> Dict[str, Any]:
        return self._request(
            "POST",
            f"/api/wait-requests/{request_id}/respond",
            {"decision": decision},
        )["wait_request"]

    # --- Notifications ---
    def list_notifications(
        self, user_id: int, unread_only: bool = False
    ) -> List[Dict[str, Any]]:
        suffix = "?unread_only=1" if unread_only else ""
        return self._request("GET", f"/api/notifications/{user_id}{suffix}")["notifications"]

    def mark_notifications_read(self, user_id: int) -> None:
        self._request("POST", f"/api/notifications/{user_id}/read")
