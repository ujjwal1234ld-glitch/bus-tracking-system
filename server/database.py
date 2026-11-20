"""SQLite database layer for the Bus Tracking System.

Handles users (drivers and students), bus routes, pickup stops, student enrollment
approvals, live GPS bus locations, student wait requests, and notifications.
"""

from datetime import datetime
import hashlib
import secrets
import sqlite3
from typing import Any, Dict, List, Optional

from server.config import DB_PATH, DEFAULT_BUS_CAPACITY, STOP_ARRIVAL_RADIUS_METERS
from server.geo_utils import haversine_distance_meters


def _utc_now() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


def _hash_password(password: str, salt: Optional[str] = None) -> str:
    if salt is None:
        salt = secrets.token_hex(8)
    digest = hashlib.sha256(f"{salt}:{password}".encode("utf-8")).hexdigest()
    return f"{salt}${digest}"


def _verify_password(password: str, stored_hash: str) -> bool:
    if "$" not in stored_hash:
        return False
    salt, _ = stored_hash.split("$", 1)
    return _hash_password(password, salt) == stored_hash


class BusDatabase:
    """Simple, clean SQLite wrapper for all Bus Tracking System data."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def init_db(self) -> None:
        """Create all tables if they do not exist."""
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    phone TEXT DEFAULT '',
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('driver', 'student')),
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS routes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    driver_id INTEGER NOT NULL,
                    bus_number TEXT NOT NULL,
                    route_name TEXT NOT NULL,
                    capacity INTEGER NOT NULL DEFAULT 30,
                    destination_name TEXT DEFAULT 'Campus Main Gate',
                    destination_lat REAL DEFAULT 28.4744,
                    destination_lon REAL DEFAULT 77.5040,
                    departure_time TEXT DEFAULT '07:30 AM',
                    arrival_time TEXT DEFAULT '08:30 AM',
                    is_sharing_location INTEGER NOT NULL DEFAULT 0,
                    current_lat REAL DEFAULT 28.4700,
                    current_lon REAL DEFAULT 77.5000,
                    last_location_update TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (driver_id) REFERENCES users(id)
                );

                CREATE TABLE IF NOT EXISTS stops (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    route_id INTEGER NOT NULL,
                    stop_name TEXT NOT NULL,
                    lat REAL NOT NULL,
                    lon REAL NOT NULL,
                    stop_order INTEGER NOT NULL DEFAULT 1,
                    scheduled_time TEXT DEFAULT '',
                    arrived_notified INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY (route_id) REFERENCES routes(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS enrollments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id INTEGER NOT NULL,
                    route_id INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending'
                        CHECK(status IN ('pending', 'approved', 'rejected')),
                    pickup_stop_id INTEGER DEFAULT NULL,
                    student_lat REAL DEFAULT NULL,
                    student_lon REAL DEFAULT NULL,
                    requested_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(student_id, route_id),
                    FOREIGN KEY (student_id) REFERENCES users(id),
                    FOREIGN KEY (route_id) REFERENCES routes(id) ON DELETE CASCADE,
                    FOREIGN KEY (pickup_stop_id) REFERENCES stops(id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS wait_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id INTEGER NOT NULL,
                    route_id INTEGER NOT NULL,
                    eta_message TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending'
                        CHECK(status IN ('pending', 'approved', 'denied')),
                    created_at TEXT NOT NULL,
                    responded_at TEXT DEFAULT '',
                    FOREIGN KEY (student_id) REFERENCES users(id),
                    FOREIGN KEY (route_id) REFERENCES routes(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    message TEXT NOT NULL,
                    notif_type TEXT NOT NULL DEFAULT 'info',
                    is_read INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                );
                """
            )

    # ------------------------------------------------------------------
    # Authentication (Separate Driver & Student Sign-in / Registration)
    # ------------------------------------------------------------------
    def register_user(
        self, name: str, email: str, password: str, role: str, phone: str = ""
    ) -> Dict[str, Any]:
        if role not in ("driver", "student"):
            raise ValueError("Role must be 'driver' or 'student'.")
        clean_email = email.strip().lower()
        now = _utc_now()
        with self._connect() as conn:
            existing = conn.execute(
                "SELECT id FROM users WHERE email = ?", (clean_email,)
            ).fetchone()
            if existing:
                raise ValueError("An account with this email already exists.")
            cursor = conn.execute(
                """
                INSERT INTO users (name, email, phone, password_hash, role, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (name.strip(), clean_email, phone.strip(), _hash_password(password), role, now),
            )
            user_id = cursor.lastrowid
        return {
            "id": user_id,
            "name": name.strip(),
            "email": clean_email,
            "phone": phone.strip(),
            "role": role,
        }

    def login_user(self, email: str, password: str, expected_role: str) -> Dict[str, Any]:
        clean_email = email.strip().lower()
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE email = ?", (clean_email,)
            ).fetchone()
        if not row:
            raise ValueError("Account not found.")
        if row["role"] != expected_role:
            raise ValueError(
                f"This account is registered as a {row['role']}. "
                f"Please use 'Sign in as {row['role'].title()}'."
            )
        if not _verify_password(password, row["password_hash"]):
            raise ValueError("Incorrect password.")
        return {
            "id": row["id"],
            "name": row["name"],
            "email": row["email"],
            "phone": row["phone"],
            "role": row["role"],
        }

    # ------------------------------------------------------------------
    # Routes & Stops (Managed by Driver)
    # ------------------------------------------------------------------
    def create_route(
        self,
        driver_id: int,
        bus_number: str,
        route_name: str,
        destination_name: str = "Campus Main Gate",
        destination_lat: float = 28.4744,
        destination_lon: float = 77.5040,
        departure_time: str = "07:30 AM",
        arrival_time: str = "08:30 AM",
        capacity: int = DEFAULT_BUS_CAPACITY,
    ) -> Dict[str, Any]:
        now = _utc_now()
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO routes (
                    driver_id, bus_number, route_name, capacity,
                    destination_name, destination_lat, destination_lon,
                    departure_time, arrival_time, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    driver_id,
                    bus_number.strip(),
                    route_name.strip(),
                    int(capacity),
                    destination_name.strip(),
                    float(destination_lat),
                    float(destination_lon),
                    departure_time.strip(),
                    arrival_time.strip(),
                    now,
                ),
            )
            route_id = cursor.lastrowid
        return self.get_route_by_id(route_id)

    def get_route_by_id(self, route_id: int) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT r.*, u.name AS driver_name, u.phone AS driver_phone, u.email AS driver_email
                FROM routes r
                JOIN users u ON u.id = r.driver_id
                WHERE r.id = ?
                """,
                (route_id,),
            ).fetchone()
            if not row:
                return None
            stops = conn.execute(
                "SELECT * FROM stops WHERE route_id = ? ORDER BY stop_order ASC, id ASC",
                (route_id,),
            ).fetchall()
            approved_count = conn.execute(
                "SELECT COUNT(*) AS cnt FROM enrollments WHERE route_id = ? AND status = 'approved'",
                (route_id,),
            ).fetchone()["cnt"]
        result = dict(row)
        result["is_sharing_location"] = bool(result["is_sharing_location"])
        result["approved_student_count"] = approved_count
        result["stops"] = [dict(s) for s in stops]
        return result

    def get_driver_route(self, driver_id: int) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id FROM routes WHERE driver_id = ? ORDER BY id DESC LIMIT 1",
                (driver_id,),
            ).fetchone()
        if not row:
            return None
        return self.get_route_by_id(row["id"])

    def list_routes(self) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT id FROM routes ORDER BY id ASC").fetchall()
        return [self.get_route_by_id(r["id"]) for r in rows]

    def update_route_schedule_and_destination(
        self,
        route_id: int,
        departure_time: Optional[str] = None,
        arrival_time: Optional[str] = None,
        destination_name: Optional[str] = None,
        destination_lat: Optional[float] = None,
        destination_lon: Optional[float] = None,
    ) -> Dict[str, Any]:
        fields = []
        values: List[Any] = []
        if departure_time is not None:
            fields.append("departure_time = ?")
            values.append(departure_time.strip())
        if arrival_time is not None:
            fields.append("arrival_time = ?")
            values.append(arrival_time.strip())
        if destination_name is not None:
            fields.append("destination_name = ?")
            values.append(destination_name.strip())
        if destination_lat is not None:
            fields.append("destination_lat = ?")
            values.append(float(destination_lat))
        if destination_lon is not None:
            fields.append("destination_lon = ?")
            values.append(float(destination_lon))

        if fields:
            values.append(route_id)
            with self._connect() as conn:
                conn.execute(
                    f"UPDATE routes SET {', '.join(fields)} WHERE id = ?",
                    tuple(values),
                )
        route = self.get_route_by_id(route_id)
        if not route:
            raise ValueError("Route not found.")
        return route

    def add_stop(
        self,
        route_id: int,
        stop_name: str,
        lat: float,
        lon: float,
        scheduled_time: str = "",
    ) -> Dict[str, Any]:
        with self._connect() as conn:
            max_order = conn.execute(
                "SELECT COALESCE(MAX(stop_order), 0) AS m FROM stops WHERE route_id = ?",
                (route_id,),
            ).fetchone()["m"]
            cursor = conn.execute(
                """
                INSERT INTO stops (route_id, stop_name, lat, lon, stop_order, scheduled_time)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (route_id, stop_name.strip(), float(lat), float(lon), max_order + 1, scheduled_time.strip()),
            )
            stop_id = cursor.lastrowid
            row = conn.execute("SELECT * FROM stops WHERE id = ?", (stop_id,)).fetchone()
        return dict(row)

    def reset_trip_arrivals(self, route_id: int) -> None:
        """Reset stop arrival notification flags for a fresh bus trip."""
        with self._connect() as conn:
            conn.execute(
                "UPDATE stops SET arrived_notified = 0 WHERE route_id = ?",
                (route_id,),
            )

    # ------------------------------------------------------------------
    # Student Route Selection & Driver Approval Workflow
    # ------------------------------------------------------------------
    def request_route_enrollment(self, student_id: int, route_id: int) -> Dict[str, Any]:
        now = _utc_now()
        with self._connect() as conn:
            route = conn.execute("SELECT * FROM routes WHERE id = ?", (route_id,)).fetchone()
            if not route:
                raise ValueError("Selected bus route does not exist.")

            student = conn.execute("SELECT name FROM users WHERE id = ?", (student_id,)).fetchone()
            if not student:
                raise ValueError("Student account not found.")

            existing = conn.execute(
                "SELECT id, status FROM enrollments WHERE student_id = ? AND route_id = ?",
                (student_id, route_id),
            ).fetchone()
            if existing:
                conn.execute(
                    "UPDATE enrollments SET status = 'pending', updated_at = ? WHERE id = ?",
                    (now, existing["id"]),
                )
                enrollment_id = existing["id"]
            else:
                cursor = conn.execute(
                    """
                    INSERT INTO enrollments (student_id, route_id, status, requested_at, updated_at)
                    VALUES (?, ?, 'pending', ?, ?)
                    """,
                    (student_id, route_id, now, now),
                )
                enrollment_id = cursor.lastrowid

            # Notify the driver about the new approval request
            conn.execute(
                """
                INSERT INTO notifications (user_id, title, message, notif_type, created_at)
                VALUES (?, ?, ?, 'enrollment_request', ?)
                """,
                (
                    route["driver_id"],
                    "New Student Bus Request",
                    f"{student['name']} requested to join {route['route_name']} ({route['bus_number']}).",
                    now,
                ),
            )
            row = conn.execute("SELECT * FROM enrollments WHERE id = ?", (enrollment_id,)).fetchone()
        return dict(row)

    def list_route_enrollments(self, route_id: int) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT e.*, u.name AS student_name, u.email AS student_email, u.phone AS student_phone,
                       s.stop_name AS pickup_stop_name, s.lat AS pickup_lat, s.lon AS pickup_lon
                FROM enrollments e
                JOIN users u ON u.id = e.student_id
                LEFT JOIN stops s ON s.id = e.pickup_stop_id
                WHERE e.route_id = ?
                ORDER BY
                    CASE e.status WHEN 'pending' THEN 0 WHEN 'approved' THEN 1 ELSE 2 END,
                    e.id ASC
                """,
                (route_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def decide_enrollment(
        self,
        enrollment_id: int,
        decision: str,
        pickup_stop_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        if decision not in ("approved", "rejected"):
            raise ValueError("Decision must be 'approved' or 'rejected'.")
        now = _utc_now()
        with self._connect() as conn:
            enrollment = conn.execute(
                """
                SELECT e.*, r.route_name, r.bus_number, r.capacity
                FROM enrollments e
                JOIN routes r ON r.id = e.route_id
                WHERE e.id = ?
                """,
                (enrollment_id,),
            ).fetchone()
            if not enrollment:
                raise ValueError("Enrollment request not found.")

            if decision == "approved" and enrollment["status"] != "approved":
                current_count = conn.execute(
                    "SELECT COUNT(*) AS cnt FROM enrollments WHERE route_id = ? AND status = 'approved'",
                    (enrollment["route_id"],),
                ).fetchone()["cnt"]
                if current_count >= enrollment["capacity"]:
                    raise ValueError(
                        f"Bus is already full ({enrollment['capacity']} students max)."
                    )

            # Auto-assign first stop if driver approves without picking a specific stop
            assigned_stop_id = pickup_stop_id
            if decision == "approved" and assigned_stop_id is None:
                first_stop = conn.execute(
                    "SELECT id FROM stops WHERE route_id = ? ORDER BY stop_order ASC LIMIT 1",
                    (enrollment["route_id"],),
                ).fetchone()
                if first_stop:
                    assigned_stop_id = first_stop["id"]

            conn.execute(
                """
                UPDATE enrollments
                SET status = ?, pickup_stop_id = COALESCE(?, pickup_stop_id), updated_at = ?
                WHERE id = ?
                """,
                (decision, assigned_stop_id, now, enrollment_id),
            )

            title = "Bus Request Approved" if decision == "approved" else "Bus Request Rejected"
            msg = (
                f"You have been approved for {enrollment['route_name']} ({enrollment['bus_number']})."
                if decision == "approved"
                else f"Your request for {enrollment['route_name']} ({enrollment['bus_number']}) was declined."
            )
            conn.execute(
                """
                INSERT INTO notifications (user_id, title, message, notif_type, created_at)
                VALUES (?, ?, ?, 'enrollment_decision', ?)
                """,
                (enrollment["student_id"], title, msg, now),
            )
            updated = conn.execute(
                "SELECT * FROM enrollments WHERE id = ?", (enrollment_id,)
            ).fetchone()
        return dict(updated)

    def assign_student_pickup(self, enrollment_id: int, pickup_stop_id: int) -> Dict[str, Any]:
        now = _utc_now()
        with self._connect() as conn:
            conn.execute(
                "UPDATE enrollments SET pickup_stop_id = ?, updated_at = ? WHERE id = ?",
                (pickup_stop_id, now, enrollment_id),
            )
            row = conn.execute("SELECT * FROM enrollments WHERE id = ?", (enrollment_id,)).fetchone()
        if not row:
            raise ValueError("Enrollment not found.")
        return dict(row)

    def update_student_location(self, student_id: int, lat: float, lon: float) -> None:
        now = _utc_now()
        with self._connect() as conn:
            conn.execute(
                "UPDATE enrollments SET student_lat = ?, student_lon = ?, updated_at = ? WHERE student_id = ?",
                (float(lat), float(lon), now, student_id),
            )

    def get_student_status(self, student_id: int) -> Dict[str, Any]:
        """Return the student's active enrollment, driver details, route, stops, and pickup."""
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT e.*, s.stop_name AS pickup_stop_name, s.lat AS pickup_lat,
                       s.lon AS pickup_lon, s.scheduled_time AS pickup_time
                FROM enrollments e
                LEFT JOIN stops s ON s.id = e.pickup_stop_id
                WHERE e.student_id = ?
                ORDER BY
                    CASE e.status WHEN 'approved' THEN 0 WHEN 'pending' THEN 1 ELSE 2 END,
                    e.updated_at DESC
                LIMIT 1
                """,
                (student_id,),
            ).fetchone()
        if not row:
            return {"enrolled": False, "enrollment": None, "route": None}
        enrollment = dict(row)
        route = self.get_route_by_id(enrollment["route_id"])
        return {
            "enrolled": True,
            "enrollment": enrollment,
            "route": route,
        }

    # ------------------------------------------------------------------
    # Live Bus Location Sharing & Automatic Stop Arrival Notifications
    # ------------------------------------------------------------------
    def update_bus_location(
        self,
        route_id: int,
        lat: float,
        lon: float,
        is_sharing: bool = True,
    ) -> Dict[str, Any]:
        now = _utc_now()
        arrived_stops: List[str] = []

        with self._connect() as conn:
            conn.execute(
                """
                UPDATE routes
                SET current_lat = ?, current_lon = ?, is_sharing_location = ?, last_location_update = ?
                WHERE id = ?
                """,
                (float(lat), float(lon), 1 if is_sharing else 0, now, route_id),
            )

            if is_sharing:
                stops = conn.execute(
                    "SELECT * FROM stops WHERE route_id = ? AND arrived_notified = 0",
                    (route_id,),
                ).fetchall()
                approved_students = conn.execute(
                    "SELECT student_id FROM enrollments WHERE route_id = ? AND status = 'approved'",
                    (route_id,),
                ).fetchall()

                for stop in stops:
                    dist = haversine_distance_meters(
                        float(lat), float(lon), stop["lat"], stop["lon"]
                    )
                    if dist <= STOP_ARRIVAL_RADIUS_METERS:
                        conn.execute(
                            "UPDATE stops SET arrived_notified = 1 WHERE id = ?",
                            (stop["id"],),
                        )
                        arrived_stops.append(stop["stop_name"])
                        for st in approved_students:
                            conn.execute(
                                """
                                INSERT INTO notifications (user_id, title, message, notif_type, created_at)
                                VALUES (?, ?, ?, 'bus_arrived', ?)
                                """,
                                (
                                    st["student_id"],
                                    "Bus Has Arrived!",
                                    f"The bus has arrived at stop: {stop['stop_name']}.",
                                    now,
                                ),
                            )

        return {
            "route_id": route_id,
            "lat": float(lat),
            "lon": float(lon),
            "is_sharing_location": is_sharing,
            "last_location_update": now,
            "arrived_stops_notified": arrived_stops,
        }

    # ------------------------------------------------------------------
    # Late Student "Wait" Request -> Driver OK / Deny -> Notification
    # ------------------------------------------------------------------
    def create_wait_request(
        self, student_id: int, route_id: int, eta_message: str
    ) -> Dict[str, Any]:
        now = _utc_now()
        clean_msg = eta_message.strip() or "I will be there in 5 minutes."
        with self._connect() as conn:
            route = conn.execute("SELECT * FROM routes WHERE id = ?", (route_id,)).fetchone()
            if not route:
                raise ValueError("Route not found.")
            student = conn.execute("SELECT name FROM users WHERE id = ?", (student_id,)).fetchone()
            if not student:
                raise ValueError("Student not found.")

            cursor = conn.execute(
                """
                INSERT INTO wait_requests (student_id, route_id, eta_message, status, created_at)
                VALUES (?, ?, ?, 'pending', ?)
                """,
                (student_id, route_id, clean_msg, now),
            )
            req_id = cursor.lastrowid

            conn.execute(
                """
                INSERT INTO notifications (user_id, title, message, notif_type, created_at)
                VALUES (?, ?, ?, 'wait_request', ?)
                """,
                (
                    route["driver_id"],
                    "Student Wait Request",
                    f"{student['name']} is late and asked to wait: {clean_msg}",
                    now,
                ),
            )
            row = conn.execute("SELECT * FROM wait_requests WHERE id = ?", (req_id,)).fetchone()
        return dict(row)

    def list_wait_requests(self, route_id: int) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT w.*, u.name AS student_name, u.phone AS student_phone
                FROM wait_requests w
                JOIN users u ON u.id = w.student_id
                WHERE w.route_id = ?
                ORDER BY
                    CASE w.status WHEN 'pending' THEN 0 ELSE 1 END,
                    w.id DESC
                """,
                (route_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def respond_wait_request(self, request_id: int, decision: str) -> Dict[str, Any]:
        if decision not in ("approved", "denied"):
            raise ValueError("Decision must be 'approved' (OK) or 'denied' (Deny).")
        now = _utc_now()
        with self._connect() as conn:
            req = conn.execute(
                "SELECT * FROM wait_requests WHERE id = ?", (request_id,)
            ).fetchone()
            if not req:
                raise ValueError("Wait request not found.")

            conn.execute(
                "UPDATE wait_requests SET status = ?, responded_at = ? WHERE id = ?",
                (decision, now, request_id),
            )

            if decision == "approved":
                title = "Wait Request Accepted (OK)"
                msg = f"Driver clicked OK for your request ('{req['eta_message']}'). The bus will wait for you!"
            else:
                title = "Wait Request Denied"
                msg = f"Driver denied your wait request ('{req['eta_message']}'). The bus cannot wait."

            conn.execute(
                """
                INSERT INTO notifications (user_id, title, message, notif_type, created_at)
                VALUES (?, ?, ?, 'wait_response', ?)
                """,
                (req["student_id"], title, msg, now),
            )
            updated = conn.execute(
                "SELECT * FROM wait_requests WHERE id = ?", (request_id,)
            ).fetchone()
        return dict(updated)

    # ------------------------------------------------------------------
    # Notifications
    # ------------------------------------------------------------------
    def list_notifications(self, user_id: int, unread_only: bool = False) -> List[Dict[str, Any]]:
        query = "SELECT * FROM notifications WHERE user_id = ?"
        if unread_only:
            query += " AND is_read = 0"
        query += " ORDER BY id DESC LIMIT 50"
        with self._connect() as conn:
            rows = conn.execute(query, (user_id,)).fetchall()
        return [dict(r) for r in rows]

    def mark_notifications_read(self, user_id: int) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE notifications SET is_read = 1 WHERE user_id = ?",
                (user_id,),
            )

    # ------------------------------------------------------------------
    # Laptop Admin Control Panel Queries
    # ------------------------------------------------------------------
    def list_users(self) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, name, email, phone, role, created_at FROM users ORDER BY role ASC, id ASC"
            ).fetchall()
        return [dict(r) for r in rows]

    def delete_user(self, user_id: int) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM notifications WHERE user_id = ?", (user_id,))
            conn.execute("DELETE FROM wait_requests WHERE student_id = ?", (user_id,))
            conn.execute("DELETE FROM enrollments WHERE student_id = ?", (user_id,))
            conn.execute("DELETE FROM routes WHERE driver_id = ?", (user_id,))
            conn.execute("DELETE FROM users WHERE id = ?", (user_id,))

    def get_admin_overview(self) -> Dict[str, Any]:
        with self._connect() as conn:
            drivers = conn.execute("SELECT COUNT(*) AS c FROM users WHERE role = 'driver'").fetchone()["c"]
            students = conn.execute("SELECT COUNT(*) AS c FROM users WHERE role = 'student'").fetchone()["c"]
            routes_cnt = conn.execute("SELECT COUNT(*) AS c FROM routes").fetchone()["c"]
            approved = conn.execute("SELECT COUNT(*) AS c FROM enrollments WHERE status = 'approved'").fetchone()["c"]
            pending = conn.execute("SELECT COUNT(*) AS c FROM enrollments WHERE status = 'pending'").fetchone()["c"]
            waits = conn.execute("SELECT COUNT(*) AS c FROM wait_requests WHERE status = 'pending'").fetchone()["c"]
            recent_notifs = conn.execute(
                """
                SELECT n.id, n.title, n.message, n.notif_type, n.created_at,
                       u.name AS user_name, u.role AS user_role
                FROM notifications n
                JOIN users u ON u.id = n.user_id
                ORDER BY n.id DESC LIMIT 25
                """
            ).fetchall()
        return {
            "stats": {
                "drivers": drivers,
                "students": students,
                "routes": routes_cnt,
                "approved_enrollments": approved,
                "pending_enrollments": pending,
                "pending_wait_requests": waits,
            },
            "users": self.list_users(),
            "routes": self.list_routes(),
            "recent_notifications": [dict(r) for r in recent_notifs],
        }
