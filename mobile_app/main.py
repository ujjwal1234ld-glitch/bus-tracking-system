"""Kivy application entry point for the Bus Tracking System."""

from typing import Any, Dict, Optional

from kivy.app import App
from kivy.core.window import Window
from kivy.uix.screenmanager import ScreenManager

from mobile_app.screens.auth_screen import AuthScreen
from mobile_app.screens.driver_dashboard import DriverDashboardScreen
from mobile_app.screens.role_select_screen import RoleSelectScreen
from mobile_app.screens.student_dashboard import StudentDashboardScreen
from mobile_app.screens.student_route_screen import StudentRouteScreen
from mobile_app.services.api_client import BusTrackerAPI

# Set a phone-like window size when testing on desktop (ignored on Android)
try:
    from kivy.utils import platform

    if platform not in ("android", "ios"):
        Window.size = (410, 740)
except Exception:
    pass


class BusTrackingApp(App):
    """Main Kivy application class."""

    title = "Bus Tracking System"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.api = BusTrackerAPI()
        self.current_user: Optional[Dict[str, Any]] = None

    def build(self) -> ScreenManager:
        sm = ScreenManager()
        sm.add_widget(RoleSelectScreen(name="role_select"))
        sm.add_widget(AuthScreen(name="auth"))
        sm.add_widget(StudentRouteScreen(name="student_route"))
        sm.add_widget(DriverDashboardScreen(name="driver_dashboard"))
        sm.add_widget(StudentDashboardScreen(name="student_dashboard"))
        sm.current = "role_select"
        return sm


if __name__ == "__main__":
    BusTrackingApp().run()
