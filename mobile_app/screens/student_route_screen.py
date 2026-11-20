"""Screen where a registered student selects their bus route and awaits driver approval."""

from kivy.app import App
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView

from mobile_app.config import COLORS
from mobile_app.widgets.ui_components import (
    CardBox,
    StyledButton,
    make_label,
    show_message_popup,
)


class StudentRouteScreen(Screen):
    """Lets a student choose their bus route and sends an approval request to the driver."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(*COLORS["bg"])
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)

        root = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(12))

        top_bar = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        self.title_lbl = Label(text="Select Your Bus Route", font_size=dp(18), bold=True, color=COLORS["primary"])
        refresh_btn = StyledButton(text="Refresh", bg_color=COLORS["secondary"], size_hint_x=None, width=dp(85), height=dp(40))
        refresh_btn.bind(on_release=lambda *_: self.refresh_data())
        logout_btn = StyledButton(text="Sign Out", bg_color=COLORS["danger"], size_hint_x=None, width=dp(85), height=dp(40))
        logout_btn.bind(on_release=self._sign_out)
        top_bar.add_widget(self.title_lbl)
        top_bar.add_widget(refresh_btn)
        top_bar.add_widget(logout_btn)
        root.add_widget(top_bar)

        self.status_banner = make_label(
            "Choose your bus route below. The driver will approve your request.",
            font_size=13,
            color=COLORS["muted"],
            height=36,
        )
        root.add_widget(self.status_banner)

        scroll = ScrollView()
        self.routes_box = BoxLayout(orientation="vertical", spacing=dp(10), size_hint_y=None)
        self.routes_box.bind(minimum_height=self.routes_box.setter("height"))
        scroll.add_widget(self.routes_box)
        root.add_widget(scroll)

        self.add_widget(root)

    def _update_bg(self, *_args):
        self._bg.pos = self.pos
        self._bg.size = self.size

    def on_enter(self, *_args):
        self.refresh_data()

    def refresh_data(self) -> None:
        app = App.get_running_app()
        if not app.current_user:
            return
        student_id = app.current_user["id"]

        try:
            status = app.api.get_student_status(student_id)
            if status.get("enrolled"):
                enr = status["enrollment"]
                if enr["status"] == "approved":
                    self.manager.current = "student_dashboard"
                    return
                if enr["status"] == "pending":
                    route = status["route"]
                    self.status_banner.text = (
                        f"Approval Pending: Waiting for {route['driver_name']} "
                        f"({route['bus_number']}) to accept your request. Tap Refresh to check."
                    )
                    self.status_banner.color = COLORS["primary"]
                elif enr["status"] == "rejected":
                    self.status_banner.text = "Your previous request was declined. You may choose another route."
                    self.status_banner.color = COLORS["danger"]

            routes = app.api.list_routes()
        except RuntimeError as exc:
            show_message_popup("Connection Error", str(exc))
            return

        self.routes_box.clear_widgets()
        if not routes:
            self.routes_box.add_widget(
                make_label("No bus routes available yet. Ask a driver to create a route.", color=COLORS["muted"], height=40)
            )
            return

        for route in routes:
            card = CardBox(orientation="vertical", padding=dp(14), spacing=dp(6), size_hint_y=None, height=dp(150))
            card.add_widget(
                make_label(
                    f"{route['bus_number']} - {route['route_name']}",
                    font_size=16,
                    bold=True,
                    color=COLORS["primary"],
                    height=24,
                )
            )
            card.add_widget(
                make_label(
                    f"Driver: {route['driver_name']}  |  Students: {route['approved_student_count']}/{route['capacity']}",
                    font_size=13,
                    height=20,
                )
            )
            card.add_widget(
                make_label(
                    f"Departure: {route['departure_time']}  ->  Arrival: {route['arrival_time']} ({route['destination_name']})",
                    font_size=12,
                    color=COLORS["muted"],
                    height=20,
                )
            )
            req_btn = StyledButton(
                text="Select Route & Send Request to Driver",
                bg_color=COLORS["success"],
                height=dp(42),
            )
            req_btn.bind(on_release=lambda _btn, rid=route["id"]: self._request_route(rid))
            card.add_widget(req_btn)
            self.routes_box.add_widget(card)

    def _request_route(self, route_id: int) -> None:
        app = App.get_running_app()
        try:
            app.api.request_enrollment(app.current_user["id"], route_id)
            show_message_popup(
                "Request Sent",
                "Your request has been sent to the bus driver for approval.",
            )
            self.refresh_data()
        except RuntimeError as exc:
            show_message_popup("Error", str(exc))

    def _sign_out(self, *_args) -> None:
        App.get_running_app().current_user = None
        self.manager.current = "role_select"
