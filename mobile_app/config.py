"""Configuration for the Bus Tracking Kivy mobile app."""

import os

# Default backend server URL.
# When running on an Android phone on the same Wi-Fi as your PC, change this to
# your PC's local IP address (e.g., "http://192.168.1.10:5000") on the Welcome screen.
DEFAULT_SERVER_URL = os.environ.get("BUS_TRACKER_SERVER_URL", "http://127.0.0.1:5000")

# How often (in seconds) the app refreshes live location and notifications
POLL_INTERVAL_SECONDS = 3.0

# Asset paths
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")
ICONS_DIR = os.path.join(ASSETS_DIR, "icons")
IMAGES_DIR = os.path.join(ASSETS_DIR, "images")

# App color palette (RGBA 0..1)
COLORS = {
    "bg": (0.08, 0.11, 0.17, 1),          # Deep Navy
    "card": (0.13, 0.17, 0.25, 1),        # Slate Card
    "primary": (0.96, 0.65, 0.14, 1),     # School Bus Amber
    "secondary": (0.20, 0.56, 0.90, 1),   # Sky Blue
    "success": (0.16, 0.68, 0.42, 1),     # Emerald Green
    "danger": (0.86, 0.26, 0.27, 1),      # Coral Red
    "text": (0.95, 0.97, 1.00, 1),        # Off-white
    "muted": (0.65, 0.72, 0.82, 1),       # Soft Slate
}
