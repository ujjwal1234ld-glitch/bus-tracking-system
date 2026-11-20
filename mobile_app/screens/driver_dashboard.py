"""Driver Dashboard Screen.

Features:
- Live count of approved students in the bus (e.g. 28 / 30)
- Toggle Live GPS location sharing (+ desktop stop simulator for easy testing)
- Automatic stop-arrival notification broadcast to all approved students
- Approve / Reject student route requests & assign pickup stops
- Set Arrival Time, Departure Time, Destination, and Pickup Stops
- Respond to late student 'Wait' requests with OK or Deny
"""

from typing import Any, Dict, List, Optional

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
from mobile_app.widgets.ui_components import (
    CardBox,
    StyledButton,
    StyledInput,
    make_label,
    show_message_popup,
)


class DriverDashboardScreen(Screen):
    """Main control panel for the Bus Driver."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.route: Optional[Dict[str, Any]] = None
        self.is_sharing = False
        self._poll_event = None
        self._seen_notif_ids = set()
        self._sim_stop_index = 0
        self.gps = LiveGPSService(on_location=self._on_real_gps)

        with self.canvas.before:
            Color(*COLORS["bg"])
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)

        root = BoxLayout(orientation="vertical", padding=dp(14), spacing=dp(10))

        # Top Bar
        top = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        self.header_lbl = Label(text="Driver Dashboard", font_size=dp(18), bold=True, color=COLORS["primary"])
        logout_btn = StyledButton(text="Sign Out", bg_color=COLORS["danger"], size_hint_x=None, width=dp(86), height=dp(40))
        logout_btn.bind(on_release=self._sign_out)
        top.add_widget(self.header_lbl)
        top.add_widget(logout_btn)
        root.add_widget(top)

        # Summary & Live Location Card
        summary = CardBox(orientation="vertical", padding=dp(12), spacing=dp(8), size_hint_y=None, height=dp(145))
        self.route_info_lbl = make_label("Loading bus route...", font_size=15, bold=True, color=COLORS["text"], height=22)
        self.student_count_lbl = make_label("Students in Bus: 0 / 30", font_size=14, bold=True, color=COLORS["success"], height=22)
        self.gps_status_lbl = make_label("Live Location: OFF", font_size=12, color=COLORS["muted"], height=18)

        gps_row = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(8))
        self.share_btn = StyledButton(text="Start Sharing Live Location", bg_color=COLORS["success"], height=dp(42))
        self.share_btn.bind(on_release=self._toggle_live_location)
        self.sim_btn = StyledButton(
            text="Simulate Next Stop",
            bg_color=COLORS["secondary"],
            size_hint_x=0.45,
            height=dp(42),
        )
        self.sim_btn.bind(on_release=self._simulate_next_stop)
        gps_row.add_widget(self.share_btn)
        gps_row.add_widget(self.sim_btn)

        summary.add_widget(self.route_info_lbl)
        summary.add_widget(self.student_count_lbl)
        summary.add_widget(self.gps_status_lbl)
        summary.add_widget(gps_row)
        root.add_widget(summary)

        # Navigation Tabs
        tab_row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(6))
        self.tab_students = StyledButton(text="Students", bg_color=COLORS["primary"], text_color=(0.08, 0.11, 0.17, 1), height=dp(38))
        self.tab_wait = StyledButton(text="Wait Requests", bg_color=COLORS["card"], height=dp(38))
        self.tab_route = StyledButton(text="Schedule & Stops", bg_color=COLORS["card"], height=dp(38))

        self.tab_students.bind(on_release=lambda *_: self._switch_tab("students"))
        self.tab_wait.bind(on_release=lambda *_: self._switch_tab("wait"))
        self.tab_route.bind(on_release=lambda *_: self._switch_tab("route"))
        tab_row.add_widget(self.tab_students)
        tab_row.add_widget(self.tab_wait)
        tab_row.add_widget(self.tab_route)
        root.add_widget(tab_row)

        # Scrollable Tab Content
        scroll = ScrollView()
        self.content_box = BoxLayout(orientation="vertical", spacing=dp(10), size_hint_y=None)
        self.content_box.bind(minimum_height=self.content_box.setter("height"))
        scroll.add_widget(self.content_box)
        root.add_widget(scroll)

        self.active_tab = "students"
        self.add_widget(root)

    def _update_bg(self, *_args):
        self._bg.pos = self.pos
        self._bg.size = self.size

    def on_enter(self, *_args):
        self.refresh_all()
        self._poll_event = Clock.schedule_interval(lambda _dt: self.refresh_all(), POLL_INTERVAL_SECONDS)

    def on_leave(self, *_args):
        if self._poll_event:
            self._poll_event.cancel()
            self._poll_event = None
        if self.is_sharing:
            self.gps.stop()
            self.is_sharing = False

    def _switch_tab(self, tab_name: str) -> None:
        self.active_tab = tab_name
        tabs = {
            "students": self.tab_students,
            "wait": self.tab_wait,
            "route": self.tab_route,
        }
        for name, btn in tabs.items():
            if name == tab_name:
                btn.set_bg_color(COLORS["primary"])
                btn.color = (0.08, 0.11, 0.17, 1)
            else:
                btn.set_bg_color(COLORS["card"])
                btn.color = COLORS["text"]
        self.refresh_all()

    def refresh_all(self) -> None:
        app = App.get_running_app()
        if not app.current_user:
            return
        driver = app.current_user
        self.header_lbl.text = f"Driver: {driver['name']}"

        try:
            self.route = app.api.get_driver_route(driver["id"])
            self._check_notifications(driver["id"])
        except RuntimeError as exc:
            self.route_info_lbl.text = f"Server error: {exc}"
            return

        if not self.route:
            self.route_info_lbl.text = "No bus route created yet."
            self.student_count_lbl.text = "Create your bus route below."
            self._render_create_route_form()
            return

        self.route_info_lbl.text = (
            f"{self.route['bus_number']} | {self.route['route_name']} -> {self.route['destination_name']}"
        )
        self.student_count_lbl.text = (
            f"Approved Students in Bus: {self.route['approved_student_count']} / {self.route['capacity']}  "
            f"| Dep: {self.route['departure_time']} | Arr: {self.route['arrival_time']}"
        )

        if self.active_tab == "students":
            self._render_students_tab()
        elif self.active_tab == "wait":
            self._render_wait_requests_tab()
        else:
            self._render_route_schedule_tab()

    def _check_notifications(self, driver_id: int) -> None:
        app = App.get_running_app()
        notifs = app.api.list_notifications(driver_id, unread_only=True)
        for n in notifs:
            if n["id"] not in self._seen_notif_ids:
                self._seen_notif_ids.add(n["id"])
                send_device_notification(n["title"], n["message"])

    # ------------------------------------------------------------------
    # Live Location Sharing & Stop Arrival Simulation
    # ------------------------------------------------------------------
    def _toggle_live_location(self, *_args) -> None:
        if not self.route:
            show_message_popup("No Route", "Please create your bus route first.")
            return
        app = App.get_running_app()
        self.is_sharing = not self.is_sharing

        if self.is_sharing:
            real_gps = self.gps.start()
            self.share_btn.text = "Stop Sharing Live Location"
            self.share_btn.set_bg_color(COLORS["danger"])
            mode_text = "Android GPS Active" if real_gps else "Desktop Mode (Use 'Simulate Next Stop')"
            self.gps_status_lbl.text = f"Live Location: ON ({mode_text})"
            self.gps_status_lbl.color = COLORS["success"]
            try:
                app.api.update_bus_location(
                    self.route["id"],
                    self.route["current_lat"],
                    self.route["current_lon"],
                    is_sharing=True,
                )
            except RuntimeError:
                pass
        else:
            self.gps.stop()
            self.share_btn.text = "Start Sharing Live Location"
            self.share_btn.set_bg_color(COLORS["success"])
            self.gps_status_lbl.text = "Live Location: OFF"
            self.gps_status_lbl.color = COLORS["muted"]
            try:
                app.api.update_bus_location(
                    self.route["id"],
                    self.route["current_lat"],
                    self.route["current_lon"],
                    is_sharing=False,
                )
            except RuntimeError:
                pass

    def _on_real_gps(self, lat: float, lon: float) -> None:
        if not self.route or not self.is_sharing:
            return
        app = App.get_running_app()
        try:
            res = app.api.update_bus_location(self.route["id"], lat, lon, is_sharing=True)
            self.gps_status_lbl.text = f"Live GPS: {lat:.5f}, {lon:.5f}"
            if res.get("arrived_stops_notified"):
                stops_str = ", ".join(res["arrived_stops_notified"])
                send_device_notification("Stop Reached", f"Notified all students: arrived at {stops_str}")
        except RuntimeError:
            pass

    def _simulate_next_stop(self, *_args) -> None:
        """Moves bus to the next stop on desktop so you can test auto-arrival notifications."""
        if not self.route:
            return
        stops = self.route.get("stops", [])
        if not stops:
            show_message_popup("No Stops", "Add at least one stop in the 'Schedule & Stops' tab.")
            return
        stop = stops[self._sim_stop_index % len(stops)]
        self._sim_stop_index += 1

        app = App.get_running_app()
        try:
            res = app.api.update_bus_location(self.route["id"], stop["lat"], stop["lon"], is_sharing=True)
            self.is_sharing = True
            self.share_btn.text = "Stop Sharing Live Location"
            self.share_btn.set_bg_color(COLORS["danger"])
            self.gps_status_lbl.text = f"Live Location: {stop['stop_name']} ({stop['lat']:.4f}, {stop['lon']:.4f})"
            self.gps_status_lbl.color = COLORS["success"]
            notified = res.get("arrived_stops_notified", [])
            if notified:
                show_message_popup(
                    "Auto-Notification Sent!",
                    f"Bus reached '{', '.join(notified)}'. All registered students were automatically notified.",
                )
        except RuntimeError as exc:
            show_message_popup("Error", str(exc))

    # ------------------------------------------------------------------
    # Tab 1: Student Approvals & Bus Roster (up to 30 students)
    # ------------------------------------------------------------------
    def _render_students_tab(self) -> None:
        app = App.get_running_app()
        self.content_box.clear_widgets()
        try:
            enrollments = app.api.list_enrollments(self.route["id"])
        except RuntimeError as exc:
            self.content_box.add_widget(make_label(f"Error: {exc}", color=COLORS["danger"]))
            return

        pending = [e for e in enrollments if e["status"] == "pending"]
        approved = [e for e in enrollments if e["status"] == "approved"]

        self.content_box.add_widget(make_label(f"Pending Approval Requests ({len(pending)})", font_size=15, bold=True, color=COLORS["primary"], height=26))
        if not pending:
            self.content_box.add_widget(make_label("No pending student requests.", font_size=13, color=COLORS["muted"], height=22))

        for enr in pending:
            card = CardBox(orientation="vertical", padding=dp(12), spacing=dp(6), size_hint_y=None, height=dp(102))
            card.add_widget(make_label(f"{enr['student_name']} ({enr['student_email']})", font_size=14, bold=True, height=22))
            btn_row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
            ok_btn = StyledButton(text="Approve", bg_color=COLORS["success"], height=dp(38))
            no_btn = StyledButton(text="Reject", bg_color=COLORS["danger"], height=dp(38))
            ok_btn.bind(on_release=lambda _b, eid=enr["id"]: self._decide_student(eid, "approved"))
            no_btn.bind(on_release=lambda _b, eid=enr["id"]: self._decide_student(eid, "rejected"))
            btn_row.add_widget(ok_btn)
            btn_row.add_widget(no_btn)
            card.add_widget(btn_row)
            self.content_box.add_widget(card)

        self.content_box.add_widget(
            make_label(
                f"Approved Students on Bus ({len(approved)} / {self.route['capacity']})",
                font_size=15,
                bold=True,
                color=COLORS["success"],
                height=28,
            )
        )
        for idx, enr in enumerate(approved, start=1):
            stop_label = enr.get("pickup_stop_name") or "Not assigned"
            card = CardBox(orientation="horizontal", padding=dp(10), spacing=dp(8), size_hint_y=None, height=dp(58))
            info = BoxLayout(orientation="vertical")
            info.add_widget(make_label(f"{idx}. {enr['student_name']}", font_size=14, bold=True, height=20))
            info.add_widget(make_label(f"Pickup: {stop_label}", font_size=12, color=COLORS["muted"], height=18))
            card.add_widget(info)

            if self.route.get("stops"):
                pickup_btn = StyledButton(
                    text="Set Pickup",
                    bg_color=COLORS["secondary"],
                    size_hint_x=None,
                    width=dp(95),
                    height=dp(36),
                )
                pickup_btn.bind(on_release=lambda _b, eid=enr["id"]: self._open_pickup_picker(eid))
                card.add_widget(pickup_btn)
            self.content_box.add_widget(card)

    def _decide_student(self, enrollment_id: int, decision: str) -> None:
        try:
            App.get_running_app().api.decide_enrollment(enrollment_id, decision)
            self.refresh_all()
        except RuntimeError as exc:
            show_message_popup("Error", str(exc))

    def _open_pickup_picker(self, enrollment_id: int) -> None:
        box = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(12))
        popup = Popup(title="Assign Pickup Stop", content=box, size_hint=(0.85, 0.55))
        for stop in self.route.get("stops", []):
            btn = StyledButton(text=f"{stop['stop_name']} ({stop['scheduled_time']})", bg_color=COLORS["secondary"], height=dp(42))

            def _assign(_b, sid=stop["id"]):
                try:
                    App.get_running_app().api.assign_pickup(enrollment_id, sid)
                    popup.dismiss()
                    self.refresh_all()
                except RuntimeError as exc:
                    show_message_popup("Error", str(exc))

            btn.bind(on_release=_assign)
            box.add_widget(btn)
        popup.open()

    # ------------------------------------------------------------------
    # Tab 2: Late Student "Wait" Requests (OK / Deny)
    # ------------------------------------------------------------------
    def _render_wait_requests_tab(self) -> None:
        app = App.get_running_app()
        self.content_box.clear_widgets()
        try:
            reqs = app.api.list_wait_requests(self.route["id"])
        except RuntimeError as exc:
            self.content_box.add_widget(make_label(f"Error: {exc}", color=COLORS["danger"]))
            return

        self.content_box.add_widget(make_label(f"Student Wait Requests ({len(reqs)})", font_size=15, bold=True, color=COLORS["primary"], height=26))
        if not reqs:
            self.content_box.add_widget(make_label("No wait requests right now.", color=COLORS["muted"], height=26))
            return

        for req in reqs:
            card = CardBox(orientation="vertical", padding=dp(12), spacing=dp(6), size_hint_y=None, height=dp(120 if req["status"] == "pending" else 76))
            card.add_widget(make_label(f"{req['student_name']}  [{req['status'].upper()}]", font_size=14, bold=True, height=22))
            card.add_widget(make_label(f"Message / Arrival ETA: {req['eta_message']}", font_size=13, color=COLORS["muted"], height=22))
            if req["status"] == "pending":
                row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
                ok_btn = StyledButton(text="OK (Will Wait)", bg_color=COLORS["success"], height=dp(38))
                deny_btn = StyledButton(text="Deny", bg_color=COLORS["danger"], height=dp(38))
                ok_btn.bind(on_release=lambda _b, rid=req["id"]: self._respond_wait(rid, "approved"))
                deny_btn.bind(on_release=lambda _b, rid=req["id"]: self._respond_wait(rid, "denied"))
                row.add_widget(ok_btn)
                row.add_widget(deny_btn)
                card.add_widget(row)
            self.content_box.add_widget(card)

    def _respond_wait(self, request_id: int, decision: str) -> None:
        try:
            App.get_running_app().api.respond_wait_request(request_id, decision)
            label = "OK (Wait Accepted)" if decision == "approved" else "Denied"
            show_message_popup("Response Sent", f"Notification sent to student: {label}.")
            self.refresh_all()
        except RuntimeError as exc:
            show_message_popup("Error", str(exc))

    # ------------------------------------------------------------------
    # Tab 3: Schedule (Departure / Arrival / Destination) & Pickup Stops
    # ------------------------------------------------------------------
    def _render_route_schedule_tab(self) -> None:
        self.content_box.clear_widgets()

        # Schedule & Destination Editor Card
        sched_card = CardBox(orientation="vertical", padding=dp(12), spacing=dp(8), size_hint_y=None, height=dp(295))
        sched_card.add_widget(make_label("Departure, Arrival & Destination", font_size=15, bold=True, color=COLORS["primary"], height=24))
        dep_in = StyledInput(text=self.route["departure_time"], hint_text="Departure Time (e.g. 07:30 AM)")
        arr_in = StyledInput(text=self.route["arrival_time"], hint_text="Arrival Time (e.g. 08:20 AM)")
        dest_in = StyledInput(text=self.route["destination_name"], hint_text="Destination Name")

        coord_row = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(8))
        dlat_in = StyledInput(text=str(self.route["destination_lat"]), hint_text="Dest Lat")
        dlon_in = StyledInput(text=str(self.route["destination_lon"]), hint_text="Dest Lon")
        coord_row.add_widget(dlat_in)
        coord_row.add_widget(dlon_in)

        save_btn = StyledButton(text="Save Schedule & Destination", bg_color=COLORS["success"], height=dp(42))

        def _save_schedule(*_a):
            try:
                App.get_running_app().api.update_schedule(
                    self.route["id"],
                    dep_in.text,
                    arr_in.text,
                    dest_in.text,
                    float(dlat_in.text),
                    float(dlon_in.text),
                )
                show_message_popup("Updated", "Schedule and destination saved.")
                self.refresh_all()
            except Exception as exc:
                show_message_popup("Error", str(exc))

        save_btn.bind(on_release=_save_schedule)
        sched_card.add_widget(dep_in)
        sched_card.add_widget(arr_in)
        sched_card.add_widget(dest_in)
        sched_card.add_widget(coord_row)
        sched_card.add_widget(save_btn)
        self.content_box.add_widget(sched_card)

        # Add Pickup Stop Card
        stop_card = CardBox(orientation="vertical", padding=dp(12), spacing=dp(8), size_hint_y=None, height=dp(245))
        stop_card.add_widget(make_label("Add Pickup Stop", font_size=15, bold=True, color=COLORS["primary"], height=24))
        sname_in = StyledInput(hint_text="Stop Name (e.g. Pari Chowk Stop)")
        stime_in = StyledInput(hint_text="Scheduled Time (e.g. 07:45 AM)")
        scoord = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(8))
        slat_in = StyledInput(hint_text="Latitude (e.g. 28.4671)")
        slon_in = StyledInput(hint_text="Longitude (e.g. 77.5138)")
        scoord.add_widget(slat_in)
        scoord.add_widget(slon_in)

        add_stop_btn = StyledButton(text="Add Pickup Stop", bg_color=COLORS["secondary"], height=dp(42))

        def _add_stop(*_a):
            try:
                App.get_running_app().api.add_stop(
                    self.route["id"],
                    sname_in.text,
                    float(slat_in.text),
                    float(slon_in.text),
                    stime_in.text,
                )
                show_message_popup("Stop Added", f"Added stop: {sname_in.text}")
                self.refresh_all()
            except Exception as exc:
                show_message_popup("Error", str(exc))

        add_stop_btn.bind(on_release=_add_stop)
        stop_card.add_widget(sname_in)
        stop_card.add_widget(stime_in)
        stop_card.add_widget(scoord)
        stop_card.add_widget(add_stop_btn)
        self.content_box.add_widget(stop_card)

        # Reset Trip Button (re-enables automatic stop arrival alerts for next trip)
        reset_btn = StyledButton(text="Start Fresh Trip (Reset Stop Alerts)", bg_color=COLORS["primary"], text_color=(0.08, 0.11, 0.17, 1), height=dp(42))

        def _reset(*_a):
            App.get_running_app().api.reset_trip(self.route["id"])
            self._sim_stop_index = 0
            show_message_popup("Trip Reset", "Stop arrival alerts reset for your new trip.")

        reset_btn.bind(on_release=_reset)
        self.content_box.add_widget(reset_btn)

    def _render_create_route_form(self) -> None:
        self.content_box.clear_widgets()
        card = CardBox(orientation="vertical", padding=dp(14), spacing=dp(8), size_hint_y=None, height=dp(340))
        card.add_widget(make_label("Create Your Bus Route", font_size=16, bold=True, color=COLORS["primary"], height=26))
        bus_in = StyledInput(hint_text="Bus Number (e.g. BUS-101)")
        rname_in = StyledInput(hint_text="Route Name (e.g. Route A - Campus)")
        dest_in = StyledInput(text="University Main Campus", hint_text="Destination Name")
        dep_in = StyledInput(text="07:30 AM", hint_text="Departure Time")
        arr_in = StyledInput(text="08:30 AM", hint_text="Arrival Time")
        btn = StyledButton(text="Create Route", bg_color=COLORS["success"], height=dp(44))

        def _create(*_a):
            app = App.get_running_app()
            try:
                app.api.create_route(
                    driver_id=app.current_user["id"],
                    bus_number=bus_in.text or "BUS-101",
                    route_name=rname_in.text or "Main Route",
                    destination_name=dest_in.text or "Campus",
                    destination_lat=28.4744,
                    destination_lon=77.5040,
                    departure_time=dep_in.text or "07:30 AM",
                    arrival_time=arr_in.text or "08:30 AM",
                    capacity=30,
                )
                self.refresh_all()
            except RuntimeError as exc:
                show_message_popup("Error", str(exc))

        btn.bind(on_release=_create)
        for w in (bus_in, rname_in, dest_in, dep_in, arr_in, btn):
            card.add_widget(w)
        self.content_box.add_widget(card)

    def _sign_out(self, *_args) -> None:
        App.get_running_app().current_user = None
        self.manager.current = "role_select"
