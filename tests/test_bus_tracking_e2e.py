"""End-to-end automated tests for the Bus Tracking System.

Verifies:
1. Separate driver & student registration/sign-in with role enforcement.
2. 30-student route selection, driver approval workflow, and 30-student capacity limit.
3. Driver setting pickup stops, destination, departure time, and arrival time.
4. Live bus GPS updates triggering automatic "Bus Has Arrived!" notifications to all 30 students.
5. Late student Wait request -> Driver OK / Deny -> Student receives exact decision notification.
"""

import os
import tempfile
import threading
import unittest

from mobile_app.services.api_client import BusTrackerAPI
from server.app import create_server


class TestBusTrackingEndToEnd(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp_dir.name, "test_bus.db")
        # Bind to port 0 so OS picks a free port automatically
        self.server = create_server(host="127.0.0.1", port=0, db_path=self.db_path)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.api = BusTrackerAPI(base_url=f"http://127.0.0.1:{self.port}")

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)
        self.tmp_dir.cleanup()

    def test_full_30_student_bus_workflow(self) -> None:
        # 1. Separate Driver & Student Registration + Role Enforcement
        driver = self.api.register("Rajesh Driver", "driver@test.com", "pass123", "driver", "9999999999")
        logged_driver = self.api.login("driver@test.com", "pass123", "driver")
        self.assertEqual(logged_driver["id"], driver["id"])

        # Driver cannot sign in through Student portal
        with self.assertRaises(RuntimeError):
            self.api.login("driver@test.com", "pass123", "student")

        # 2. Driver creates bus route (capacity 30) & sets schedule, destination, and stops
        route = self.api.create_route(
            driver_id=driver["id"],
            bus_number="BUS-01",
            route_name="North Campus Route",
            destination_name="Engineering Block",
            destination_lat=28.4744,
            destination_lon=77.5040,
            departure_time="07:30 AM",
            arrival_time="08:15 AM",
            capacity=30,
        )
        stop1 = self.api.add_stop(route["id"], "Pari Chowk", 28.4671, 77.5138, "07:40 AM")
        stop2 = self.api.add_stop(route["id"], "Alpha 1", 28.4712, 77.5101, "07:55 AM")

        # 3. 30 Students register, pick the bus route, and get approved by the driver
        students = []
        for i in range(1, 31):
            st = self.api.register(f"Student {i}", f"student{i}@test.com", "pass123", "student")
            students.append(st)
            enr = self.api.request_enrollment(st["id"], route["id"])
            self.assertEqual(enr["status"], "pending")
            assigned_stop = stop1 if i <= 15 else stop2
            decided = self.api.decide_enrollment(enr["id"], "approved", pickup_stop_id=assigned_stop["id"])
            self.assertEqual(decided["status"], "approved")

        # Verify driver sees exact count of 30 approved students
        driver_route = self.api.get_driver_route(driver["id"])
        self.assertEqual(driver_route["approved_student_count"], 30)

        # Verify 31st student cannot exceed capacity of 30
        st31 = self.api.register("Student 31", "student31@test.com", "pass123", "student")
        enr31 = self.api.request_enrollment(st31["id"], route["id"])
        with self.assertRaises(RuntimeError):
            self.api.decide_enrollment(enr31["id"], "approved")

        # Verify approved student sees driver, pickup point, destination, departure & arrival times
        st1_status = self.api.get_student_status(students[0]["id"])
        self.assertTrue(st1_status["enrolled"])
        self.assertEqual(st1_status["route"]["driver_name"], "Rajesh Driver")
        self.assertEqual(st1_status["route"]["departure_time"], "07:30 AM")
        self.assertEqual(st1_status["route"]["arrival_time"], "08:15 AM")
        self.assertEqual(st1_status["enrollment"]["pickup_stop_name"], "Pari Chowk")
        self.assertEqual(st1_status["route"]["destination_name"], "Engineering Block")

        # 4. Driver shares live location & reaches Stop 1 -> auto-notifies all 30 students
        loc_res = self.api.update_bus_location(route["id"], 28.4671, 77.5138, is_sharing=True)
        self.assertIn("Pari Chowk", loc_res["arrived_stops_notified"])

        for st in students:
            notifs = self.api.list_notifications(st["id"])
            arrived_msgs = [n for n in notifs if n["notif_type"] == "bus_arrived"]
            self.assertEqual(len(arrived_msgs), 1)
            self.assertIn("Pari Chowk", arrived_msgs[0]["message"])

        # 5. Late student Wait requests: Student 1 -> OK, Student 2 -> Deny
        w1 = self.api.send_wait_request(students[0]["id"], route["id"], "Reaching in 4 mins (07:44 AM)")
        w2 = self.api.send_wait_request(students[1]["id"], route["id"], "Reaching in 20 mins (08:00 AM)")

        self.api.respond_wait_request(w1["id"], "approved")
        self.api.respond_wait_request(w2["id"], "denied")

        st1_wait_notifs = [
            n for n in self.api.list_notifications(students[0]["id"]) if n["notif_type"] == "wait_response"
        ]
        st2_wait_notifs = [
            n for n in self.api.list_notifications(students[1]["id"]) if n["notif_type"] == "wait_response"
        ]
        self.assertEqual(len(st1_wait_notifs), 1)
        self.assertIn("OK", st1_wait_notifs[0]["title"])
        self.assertEqual(len(st2_wait_notifs), 1)
        self.assertIn("Denied", st2_wait_notifs[0]["title"])



    def test_laptop_admin_control_panel_and_download_page(self) -> None:
        import requests

        base = f"http://127.0.0.1:{self.port}"
        # Admin HTML page loads cleanly
        admin_res = requests.get(f"{base}/admin", timeout=5)
        self.assertEqual(admin_res.status_code, 200)
        self.assertIn("Laptop Admin Control Panel", admin_res.text)

        # Mobile APK download page loads cleanly
        dl_res = requests.get(f"{base}/download", timeout=5)
        self.assertEqual(dl_res.status_code, 200)
        self.assertIn("Bus Tracking System", dl_res.text)

        # Seed demo data from admin API & verify overview counts
        seed_res = requests.post(f"{base}/api/admin/seed-demo", timeout=10)
        self.assertEqual(seed_res.status_code, 200)

        ov = requests.get(f"{base}/api/admin/overview", timeout=5).json()
        self.assertEqual(ov["stats"]["drivers"], 1)
        self.assertEqual(ov["stats"]["students"], 30)
        self.assertEqual(ov["stats"]["approved_enrollments"], 28)
        self.assertEqual(ov["stats"]["pending_enrollments"], 2)

        # DB backup endpoint returns SQLite file bytes
        bak_res = requests.get(f"{base}/api/admin/backup-db", timeout=5)
        self.assertEqual(bak_res.status_code, 200)
        self.assertTrue(bak_res.content.startswith(b"SQLite format 3"))


if __name__ == "__main__":
    unittest.main()
