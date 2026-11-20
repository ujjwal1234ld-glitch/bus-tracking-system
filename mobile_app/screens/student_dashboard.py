"""Student Dashboard Screen.

Features:
- Displays Bus Driver name, phone, bus number, and live sharing status
- Live Map showing Bus Live Location, Student Location, Pickup Point, and Destination
- Displays Departure Time and Arrival Time set by the driver
- Single prominent 'WAIT (I'm Late)' button to send arrival ETA message to the driver
- Live Notification feed (Bus Arrived at stop, Wait Request OK/Denied)
"""

from typing import Any, Dict, Optional

from kivy.app import App
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView

from mobile_app.config import COLORS, POLL_INTERVAL_SECONDS
from mobile_app.services.gps_service import LiveGPSService, send_device_notification
from mobile_app.widgets.map_widget import BusMapWidget
from mobile_app.widgets.ui_components import (
    CardBox,
    StyledButton,
    StyledInput,
    make_label,
    show_message_popup,
)


class StudentDashboardScreen(Screen):
    """Live tracking & wait-request screen for an approved student."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.route: Optional[Dict[str, Any]] = None
        self.enrollment: Optional[Dict[str, Any]] = None
        self._poll_event = None
        self._seen_notif_ids = set()
        self.gps = LiveGPSService(on_location=self._on_student_gps)

        with self.canvas.before:
            Color(*COLORS["bg"])
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)

        root = BoxLayout(orientation="vertical", padding=dp(14), spacing=dp(10))

        # Top Bar
        top = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        self.header_lbl = Label(text="Live Bus Tracker", font_size=dp(18), bold=True, color=COLORS["primary"])
        logout_btn = StyledButton(text="Sign Out", bg_color=COLORS["danger"], size_hint_x=None, width=dp(86), height=dp(40))
        logout_btn.bind(on_release=self._sign_out)
        top.add_widget(self.header_lbl)
        top.add_widget(logout_btn)
        root.add_widget(top)

        # Driver & Schedule Info Card
        info_card = CardBox(orientation="vertical", padding=dp(12), spacing=dp(4), size_hint_y=None, height=dp(116))
        self.driver_lbl = make_label("Driver: Loading...", font_size=14, bold=True, color=COLORS["text"], height=22)
        self.schedule_lbl = make_label("Departure: --  |  Arrival: --", font_size=13, color=COLORS["primary"], height=20)
        self.pickup_lbl = make_label("Pickup Point: --", font_size=12, color=COLORS["success"], height=20)
        self.dest_lbl = make_label("Destination: --", font_size=12, color=COLORS["muted"], height=20)
        info_card.add_widget(self.driver_lbl)
        info_card.add_widget(self.schedule_lbl)
        info_card.add_widget(self.pickup_lbl)
        info_card.add_widget(self.dest_lbl)
        root.add_widget(info_card)

        # Live Map Widget
        self.map_widget = BusMapWidget(size_hint_y=0.44)
        root.add_widget(self.map_widget)

        # Single "WAIT" Button for Late Students
        self.wait_btn = StyledButton(
            text="WAIT! I'm Late - Tell Driver My Time",
            bg_color=COLORS["primary"],
            text_color=(0.08, 0.11, 0.17, 1),
            height=dp(48),
        )
        self.wait_btn.bind(on_release=self._open_wait_popup)
        root.add_widget(self.wait_btn)

        # Live Notifications Feed
        root.add_widget(make_label("Live Notifications", font_size=14, bold=True, color=COLORS["secondary"], height=22))
        scroll = ScrollView(size_hint_y=0.28)
        self.notif_box = BoxLayout(orientation="vertical", spacing=dp(6), size_hint_y=None)
        self.notif_box.bind(minimum_height=self.notif_box.setter("height"))
        scroll.add_widget(self.notif_box)
        root.add_widget(scroll)

        self.add_widget(root)

    def _update_bg(self, *_args):
        self._bg.pos = self.pos
        self._bg.size = self.size

    def on_enter(self, *_args):
        self.gps.start()
        self.refresh_all()
        self._poll_event = Clock.schedule_interval(lambda _dt: self.refresh_all(), POLL_INTERVAL_SECONDS)

    def on_leave(self, *_args):
        if self._poll_event:
            self._poll_event.cancel()
            self._poll_event = None
        self.gps.stop()

    def _on_student_gps(self, lat: float, lon: float) -> None:
        app = App.get_running_app()
        if app.current_user:
            try:
                app.api.update_student_location(app.current_user["id"], lat, lon)
            except RuntimeError:
                pass

    def refresh_all(self) -> None:
        app = App.get_running_app()
        if not app.current_user:
            return
        student = app.current_user
        self.header_lbl.text = f"Hi, {student['name']}"

        try:
            status = app.api.get_student_status(student["id"])
            notifs = app.api.list_notifications(student["id"])
        except RuntimeError as exc:
            self.driver_lbl.text = f"Connection error: {exc}"
            return

        if not status.get("enrolled") or status["enrollment"]["status"] != "approved":
            self.manager.current = "student_route"
            return

        self.enrollment = status["enrollment"]
        self.route = status["route"]

        live_tag = "LIVE" if self.route["is_sharing_location"] else "OFFLINE"
        self.driver_lbl.text = (
            f"Driver: {self.route['driver_name']} ({self.route['driver_phone'] or 'N/A'})  |  "
            f"{self.route['bus_number']} [{live_tag}]"
        )
        self.schedule_lbl.text = (
            f"Departure: {self.route['departure_time']}   |   Arrival: {self.route['arrival_time']}"
        )
        pickup_name = self.enrollment.get("pickup_stop_name") or "Assigned by driver soon"
        pickup_time = self.enrollment.get("pickup_time") or ""
        self.pickup_lbl.text = f"Your Pickup Point: {pickup_name} {f'({pickup_time})' if pickup_time else ''}"
        self.dest_lbl.text = f"Destination: {self.route['destination_name']}"

        # Update Live Map with Bus, Student, Pickup Point, and Destination
        bus_pos = (self.route["current_lat"], self.route["current_lon"])
        dest_pos = (self.route["destination_lat"], self.route["destination_lon"])
        pickup_pos = (
            (self.enrollment["pickup_lat"], self.enrollment["pickup_lon"])
            if self.enrollment.get("pickup_lat") is not None
            else None
        )
        student_pos = (
            (self.enrollment["student_lat"], self.enrollment["student_lon"])
            if self.enrollment.get("student_lat") is not None
            else pickup_pos
        )
        self.map_widget.update_markers(
            bus_pos=bus_pos,
            student_pos=student_pos,
            pickup_pos=pickup_pos,
            destination_pos=dest_pos,
        )

        # Render notifications & trigger native device alerts for new ones
        self.notif_box.clear_widgets()
        if not notifs:
            self.notif_box.add_widget(make_label("No notifications yet.", font_size=12, color=COLORS["muted"], height=22))
        else:
            for n in notifs[:10]:
                if not n["is_read"] and n["id"] not in self._seen_notif_ids:
                    self._seen_notif_ids.add(n["id"])
                    send_device_notification(n["title"], n["message"])

                card = CardBox(orientation="vertical", padding=dp(8), spacing=dp(2), size_hint_y=None, height=dp(54))
                card.add_widget(make_label(n["title"], font_size=13, bold=True, color=COLORS["primary"], height=18))
                card.add_widget(make_label(n["message"], font_size=12, color=COLORS["text"], height=18))
                self.notif_box.add_widget(card)

    def _open_wait_popup(self, *_args) -> None:
        if not self.route:
            return
        box = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(14))
        box.add_widget(make_label("What time will you reach the bus?", font_size=14, bold=True, height=24))
        eta_input = StyledInput(hint_text="e.g., 5 mins (reaching by 07:55 AM)")
        row = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(8))
        send_btn = StyledButton(text="Send to Driver", bg_color=COLORS["success"], height=dp(42))
        cancel_btn = StyledButton(text="Cancel", bg_color=COLORS["card"], height=dp(42))
        row.add_widget(send_btn)
        row.add_widget(cancel_btn)
        box.add_widget(eta_input)
        box.add_widget(row)

        popup = Popup(title="Ask Driver to Wait", content=box, size_hint=(0.88, 0.36))

        def _send(*_a):
            msg = eta_input.text.strip() or "Will reach in 5 minutes"
            try:
                App.get_running_app().api.send_wait_request(
                    App.get_running_app().current_user["id"],
                    self.route["id"],
                    msg,
                )
                popup.dismiss()
                show_message_popup(
                    "Wait Request Sent",
                    "Sent to your driver. You will be notified as soon as they tap OK or Deny.",
                )
            except RuntimeError as exc:
                show_message_popup("Error", str(exc))

        send_btn.bind(on_release=_send)
        cancel_btn.bind(on_release=popup.dismiss)
        popup.open()

    def _sign_out(self, *_args) -> None:
        App.get_running_app().current_user = None
        self.manager.current = "role_select"
