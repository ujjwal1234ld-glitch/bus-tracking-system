"""Root launcher required by Buildozer when packaging the Android APK.

You can run the mobile app on desktop with:
    python3 main.py
"""

from mobile_app.main import BusTrackingApp

if __name__ == "__main__":
    BusTrackingApp().run()
