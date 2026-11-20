# Bus Tracking System (Laptop Server Control Panel + Mobile Android APK)

A clean, modular, 100% Python **Bus Tracking System** designed with two parts:
1. **Laptop Control Center (`laptop_control_panel.py` + `server/`)**: Runs the server and SQLite database on your laptop, gives you a visual **Admin Control Panel** in your browser (`http://127.0.0.1:5000/admin`), lets you back up the database, manage drivers/students/routes/approvals/wait alerts, and hosts a **Phone APK Download Page** (`http://<YOUR-LAPTOP-IP>:5000/download`) so drivers and students can download the app directly from your laptop.
2. **Mobile App for Drivers & Students (`main.py` + `mobile_app/` + `buildozer.spec`)**: Python Kivy mobile app compiled into an Android `.apk` with separate **Sign in as Driver** and **Sign in as Student** portals.

## How Laptop + Mobile Work Together

```text
   [ Your Laptop ]  <--- Wi-Fi / Internet --->  [ Driver's Phone (APK) ]
   - Runs Python Server + SQLite DB             - Shares Live GPS
   - Laptop Admin Panel (/admin)                - Approves 30 Students
   - Hosts APK Download Page (/download)        - Clicks OK / Deny on Wait alerts
                         ^
                         |
                         v
                [ Students' Phones (APK) ]
                - Download APK from your laptop
                - Track Live Bus + Pickup + Destination
                - Auto "Bus Has Arrived!" Alerts
                - 1-Tap "WAIT (I'm Late)" Button
```

## Folder Structure

```text
bus_tracking_system/
├── laptop_control_panel.py         # Run on your LAPTOP: starts server + opens Admin Panel
├── main.py                         # Mobile app entry point (desktop test & Buildozer APK)
├── buildozer.spec                  # Android APK build configuration
├── requirements.txt                # Mobile app Python dependencies
├── downloads/
│   └── PLACE_APK_HERE.txt          # Put your compiled bustracker.apk here for phone downloads
├── assets/
│   ├── icons/                      # App icon, splash screen, bus/student/pickup/dest markers
│   └── images/                     # Welcome screen banner
├── server/
│   ├── config.py                   # Host, port, arrival radius (100m), capacity (30)
│   ├── geo_utils.py                # Haversine GPS distance calculator
│   ├── database.py                 # SQLite schema & queries
│   ├── admin_ui.py                 # Laptop Admin Control Panel & Mobile APK Download page
│   ├── app.py                      # Pure-Python HTTP JSON API + Admin web server
│   └── seed_demo_data.py           # Optional demo seeder (1 driver + 30 students)
├── mobile_app/
│   ├── main.py                     # Kivy App & ScreenManager
│   ├── config.py                   # Default server URL, poll interval, colors
│   ├── services/                   # api_client.py (REST) & gps_service.py (Android GPS/Alerts)
│   ├── widgets/                    # map_widget.py (OpenStreetMap + fallback) & ui_components.py
│   └── screens/                    # Separate Driver & Student Sign-In, Route Select, Dashboards
└── tests/
    └── test_bus_tracking_e2e.py    # Automated end-to-end tests
```

## Step 1: Run the Server & Admin Control Panel on Your Laptop

No `pip install` is needed for the laptop server—it uses only Python's built-in standard library (`http.server` + `sqlite3`):

```bash
python3 laptop_control_panel.py
```

This automatically:
- Starts the server and SQLite database (`server/bus_tracker.db`).
- Opens the **Laptop Admin Control Panel** in your browser at `http://127.0.0.1:5000/admin`.
- Prints your laptop's **Mobile Server URL** (e.g. `http://192.168.1.10:5000`) and **Phone APK Download URL** (e.g. `http://192.168.1.10:5000/download`).

From the **Laptop Admin Control Panel**, you can:
- Click **Seed Demo (1 Driver + 30 Students)** to populate sample accounts instantly.
- Add or delete **Drivers** and **Students** in the SQLite database.
- Create **Bus Routes**, monitor **Live GPS coordinates**, approve/reject student enrollments, and respond to **Wait Requests**.
- Click **Download DB Backup** at any time to save a copy of `bus_tracker.db`.

## Step 2: Build the Mobile APK (for Drivers & Students)

Buildozer compiles Python + Kivy into an Android `.apk` on Linux, Windows WSL2, or Google Colab:

```bash
sudo apt update
sudo apt install -y git zip unzip openjdk-17-jdk python3-pip autoconf libtool pkg-config zlib1g-dev libncurses-dev cmake libffi-dev libssl-dev
pip install buildozer cython

# Run inside the bus_tracking_system/ folder:
buildozer -v android debug
```

Copy the compiled `.apk` from `bin/` into `downloads/bustracker.apk` on your laptop.

## Step 3: Download & Connect on Driver and Student Phones

1. Connect your laptop and phones to the same Wi-Fi (or host `server/app.py` on a cloud VPS/Render/PythonAnywhere for mobile data over the internet).
2. On any Android phone, open the browser and visit `http://<YOUR-LAPTOP-IP>:5000/download` to download and install `bustracker.apk`.
3. Open the app, enter `http://<YOUR-LAPTOP-IP>:5000` in the **Backend Server URL** box on the Welcome screen, and tap **Sign in as Driver** or **Sign in as Student**.

## Desktop Testing & Automated Verification

```bash
# Test the mobile UI on your laptop (optional):
pip install -r requirements.txt
python3 main.py

# Run automated end-to-end tests:
python3 -m unittest discover -s tests -v
```
