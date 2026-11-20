"""Seed the SQLite database with 1 driver, 1 bus route, stops, and 30 sample students."""

import os
import sys

# Allow running directly as: python3 server/seed_demo_data.py
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from server.database import BusDatabase


def seed_demo_data(db_path: str = None) -> None:
    db = BusDatabase(db_path=db_path) if db_path else BusDatabase()

    # 1. Create 1 Driver account
    try:
        driver = db.register_user(
            name="Rajesh Kumar",
            email="driver1@bus.com",
            password="password123",
            role="driver",
            phone="+91-9876543210",
        )
        print(f"Created driver: {driver['email']} / password123")
    except ValueError:
        driver = db.login_user("driver1@bus.com", "password123", "driver")
        print("Driver already exists.")

    # 2. Create 1 Bus Route (30-student capacity) with 3 pickup stops
    route = db.get_driver_route(driver["id"])
    if not route:
        route = db.create_route(
            driver_id=driver["id"],
            bus_number="BUS-101",
            route_name="Route A - Knowledge Park Express",
            destination_name="University Main Campus",
            destination_lat=28.4744,
            destination_lon=77.5040,
            departure_time="07:30 AM",
            arrival_time="08:20 AM",
            capacity=30,
        )
        stop1 = db.add_stop(route["id"], "Pari Chowk Stop", 28.4671, 77.5138, "07:35 AM")
        stop2 = db.add_stop(route["id"], "Alpha 1 Metro Stop", 28.4712, 77.5101, "07:50 AM")
        stop3 = db.add_stop(route["id"], "Knowledge Park II Stop", 28.4730, 77.5065, "08:05 AM")
        stops = [stop1, stop2, stop3]
        print(f"Created route: {route['route_name']} ({route['bus_number']}) with 3 stops.")
    else:
        stops = route["stops"]
        print("Route already exists.")

    # 3. Register 30 students (approve 28, leave 2 pending so you can test driver approval)
    for i in range(1, 31):
        email = f"student{i}@bus.com"
        try:
            student = db.register_user(
                name=f"Student {i:02d}",
                email=email,
                password="password123",
                role="student",
                phone=f"+91-90000000{i:02d}",
            )
        except ValueError:
            student = db.login_user(email, "password123", "student")

        enrollment = db.request_route_enrollment(student["id"], route["id"])
        if i <= 28:
            assigned_stop = stops[(i - 1) % len(stops)]
            db.decide_enrollment(enrollment["id"], "approved", pickup_stop_id=assigned_stop["id"])
            db.update_student_location(
                student["id"],
                assigned_stop["lat"] + 0.0005,
                assigned_stop["lon"] - 0.0004,
            )

    print("Seeded 30 students (student1@bus.com .. student30@bus.com, password: password123).")
    print("28 students are approved; student29 & student30 are pending driver approval.")


if __name__ == "__main__":
    seed_demo_data()
