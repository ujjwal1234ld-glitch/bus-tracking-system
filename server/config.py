"""Configuration settings for the Bus Tracking System backend server."""

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Server network settings.
# Reads cloud platform PORT automatically (Render, Railway, Fly.io) or defaults to 5000.
HOST = os.environ.get("BUS_TRACKER_HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", os.environ.get("BUS_TRACKER_PORT", "5000")))

# SQLite database path
DB_PATH = os.environ.get(
    "BUS_TRACKER_DB",
    os.path.join(BASE_DIR, "bus_tracker.db"),
)

# Distance threshold (in meters) to automatically trigger "Bus has arrived" notification
STOP_ARRIVAL_RADIUS_METERS = float(
    os.environ.get("STOP_ARRIVAL_RADIUS_METERS", "100.0")
)

# Default maximum students per bus
DEFAULT_BUS_CAPACITY = 30
