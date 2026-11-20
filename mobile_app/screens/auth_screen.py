"""Separate Sign-In and Account Registration screen for Drivers and Students."""

from kivy.app import App
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen

from mobile_app.config import COLORS
from mobile_app.widgets.ui_components import (
    CardBox,
    StyledButton,
    StyledInput,
    make_label,
    show_message_popup,
)


class AuthScreen(Screen):
    """Handles login and new account registration for either Driver or Student."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.role = "student"
        self.mode = "login"  # 'login' or 'register'

        with self.canvas.before:
            Color(*COLORS["bg"])
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)

        root = BoxLayout(orientation="vertical", padding=dp(20), spacing=dp(14))

        top_bar = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(10))
        back_btn = StyledButton(
            text="< Back",
            bg_color=COLORS["card"],
            size_hint_x=None,
            width=dp(88),
            height=dp(40),
        )
        back_btn.bind(on_release=lambda *_: setattr(self.manager, "current", "role_select"))
        self.header_lbl = Label(text="Student Portal", font_size=dp(20), bold=True, color=COLORS["primary"])
        top_bar.add_widget(back_btn)
        top_bar.add_widget(self.header_lbl)
        root.add_widget(top_bar)

        # Toggle Login / Register
        toggle_row = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(8))
        self.login_tab_btn = StyledButton(text="Sign In", bg_color=COLORS["secondary"], height=dp(40))
        self.reg_tab_btn = StyledButton(text="Create Account", bg_color=COLORS["card"], height=dp(40))
        self.login_tab_btn.bind(on_release=lambda *_: self._set_mode("login"))
        self.reg_tab_btn.bind(on_release=lambda *_: self._set_mode("register"))
        toggle_row.add_widget(self.login_tab_btn)
        toggle_row.add_widget(self.reg_tab_btn)
        root.add_widget(toggle_row)

        # Form Card
        self.form_card = CardBox(orientation="vertical", padding=dp(16), spacing=dp(10), size_hint_y=None, height=dp(330))
        self.name_input = StyledInput(hint_text="Full Name")
        self.phone_input = StyledInput(hint_text="Phone Number (optional)")
        self.email_input = StyledInput(hint_text="Email Address (e.g. student1@bus.com)")
        self.password_input = StyledInput(hint_text="Password", password=True)
        self.submit_btn = StyledButton(
            text="Sign In",
            bg_color=COLORS["primary"],
            text_color=(0.08, 0.11, 0.17, 1),
            height=dp(48),
        )
        self.submit_btn.bind(on_release=self._submit)

        self.hint_lbl = make_label(
            "Demo: driver1@bus.com or student1@bus.com (password123)",
            font_size=11,
            color=COLORS["muted"],
            height=22,
        )

        self.form_card.add_widget(self.name_input)
        self.form_card.add_widget(self.phone_input)
        self.form_card.add_widget(self.email_input)
        self.form_card.add_widget(self.password_input)
        self.form_card.add_widget(self.submit_btn)
        self.form_card.add_widget(self.hint_lbl)
        root.add_widget(self.form_card)

        root.add_widget(BoxLayout())  # Spacer
        self.add_widget(root)
        self._set_mode("login")

    def _update_bg(self, *_args):
        self._bg.pos = self.pos
        self._bg.size = self.size

    def configure_role(self, role: str) -> None:
        self.role = role
        title = "Driver Sign In" if role == "driver" else "Student Sign In"
        self.header_lbl.text = title
        self.email_input.hint_text = (
            "Driver Email (e.g. driver1@bus.com)"
            if role == "driver"
            else "Student Email (e.g. student1@bus.com)"
        )
        self._set_mode("login")

    def _set_mode(self, mode: str) -> None:
        self.mode = mode
        is_reg = mode == "register"
        self.name_input.opacity = 1 if is_reg else 0
        self.name_input.height = dp(42) if is_reg else 0
        self.name_input.disabled = not is_reg

        self.phone_input.opacity = 1 if is_reg else 0
        self.phone_input.height = dp(42) if is_reg else 0
        self.phone_input.disabled = not is_reg

        self.login_tab_btn.set_bg_color(COLORS["secondary"] if not is_reg else COLORS["card"])
        self.reg_tab_btn.set_bg_color(COLORS["secondary"] if is_reg else COLORS["card"])
        self.submit_btn.text = f"Register as {self.role.title()}" if is_reg else f"Sign In as {self.role.title()}"
        self.form_card.height = dp(330 if is_reg else 235)

    def _submit(self, *_args) -> None:
        app = App.get_running_app()
        email = self.email_input.text.strip()
        password = self.password_input.text.strip()
        if not email or not password:
            show_message_popup("Missing Fields", "Please enter both email and password.")
            return

        try:
            if self.mode == "register":
                name = self.name_input.text.strip()
                if not name:
                    show_message_popup("Missing Name", "Please enter your full name.")
                    return
                user = app.api.register(
                    name=name,
                    email=email,
                    password=password,
                    role=self.role,
                    phone=self.phone_input.text.strip(),
                )
            else:
                user = app.api.login(email=email, password=password, role=self.role)
        except RuntimeError as exc:
            show_message_popup("Authentication Failed", str(exc))
            return

        app.current_user = user
        if user["role"] == "driver":
            self.manager.current = "driver_dashboard"
        else:
            # Check if student is already approved on a route
            try:
                status = app.api.get_student_status(user["id"])
                if status.get("enrolled") and status["enrollment"]["status"] == "approved":
                    self.manager.current = "student_dashboard"
                else:
                    self.manager.current = "student_route"
            except RuntimeError:
                self.manager.current = "student_route"
