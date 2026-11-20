"""Live GPS and native Android notification helpers using plyer.

Automatically falls back to a clean desktop mode when running on PC/Mac/Linux
so you can test the entire app before building the Android APK.
"""

from typing import Callable, Optional


def send_device_notification(title: str, message: str) -> None:
    """Show a native Android/desktop system notification if plyer is available."""
    try:
        from plyer import notification

        notification.notify(
            title=title,
            message=message,
            app_name="Bus Tracker",
            timeout=5,
        )
    except Exception:
        # Silently fall back to in-app notification banner
        pass


class LiveGPSService:
    """Manages live GPS updates on Android (via plyer.gps) with desktop fallback."""

    def __init__(self, on_location: Callable[[float, float], None]):
        self.on_location = on_location
        self.is_running = False
        self._using_plyer = False

    def request_android_permissions(self) -> None:
        """Request Android runtime location permissions when running as an APK."""
        try:
            from android.permissions import Permission, request_permissions

            request_permissions(
                [
                    Permission.ACCESS_FINE_LOCATION,
                    Permission.ACCESS_COARSE_LOCATION,
                ]
            )
        except Exception:
            # Not running on Android
            pass

    def start(self) -> bool:
        """Start receiving live GPS coordinates. Returns True if real GPS started."""
        self.request_android_permissions()
        self.is_running = True
        try:
            from plyer import gps

            gps.configure(on_location=self._handle_gps, on_status=self._handle_status)
            gps.start(minTime=3000, minDistance=5)
            self._using_plyer = True
            return True
        except Exception:
            # Running on desktop without hardware GPS
            self._using_plyer = False
            return False

    def stop(self) -> None:
        self.is_running = False
        if self._using_plyer:
            try:
                from plyer import gps

                gps.stop()
            except Exception:
                pass
            self._using_plyer = False

    def _handle_gps(self, **kwargs) -> None:
        lat: Optional[float] = kwargs.get("lat")
        lon: Optional[float] = kwargs.get("lon")
        if lat is not None and lon is not None:
            self.on_location(float(lat), float(lon))

    def _handle_status(self, stype: str, status: str) -> None:
        pass
