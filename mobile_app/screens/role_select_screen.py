"""Welcome screen with separate 'Sign in as Driver' and 'Sign in as Student' options."""

import os

from kivy.app import App
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen

from mobile_app.config import COLORS, DEFAULT_SERVER_URL, IMAGES_DIR
from mobile_app.widgets.ui_components import CardBox, StyledButton, StyledInput, make_label


class RoleSelectScreen(Screen):
    """Entry screen allowing users to choose Driver or Student portal."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(*COLORS["bg"])
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)

        root = BoxLayout(orientation="vertical", padding=dp(20), spacing=dp(16))

        banner_path = os.path.join(IMAGES_DIR, "banner.png")
        if os.path.exists(banner_path):
            root.add_widget(Image(source=banner_path, size_hint_y=None, height=dp(150), allow_stretch=True))

        title = Label(
            text="Bus Tracking System",
            font_size=dp(26),
            bold=True,
            color=COLORS["primary"],
            size_hint_y=None,
            height=dp(36),
        )
        subtitle = Label(
            text="Live GPS Tracking, Route Approvals & Instant Alerts",
            font_size=dp(13),
            color=COLORS["muted"],
            size_hint_y=None,
            height=dp(22),
        )
        root.add_widget(title)
        root.add_widget(subtitle)

        # Separate Role Sign-In Card
        card = CardBox(orientation="vertical", padding=dp(16), spacing=dp(12), size_hint_y=None, height=dp(195))
        card.add_widget(make_label("Choose Your Portal", font_size=16, bold=True, height=26))

        driver_btn = StyledButton(
            text="Sign in as Driver",
            bg_color=COLORS["primary"],
            text_color=(0.08, 0.11, 0.17, 1),
            height=dp(50),
        )
        driver_btn.bind(on_release=lambda *_: self._open_auth("driver"))

        student_btn = StyledButton(
            text="Sign in as Student",
            bg_color=COLORS["secondary"],
            text_color=COLORS["text"],
            height=dp(50),
        )
        student_btn.bind(on_release=lambda *_: self._open_auth("student"))

        card.add_widget(driver_btn)
        card.add_widget(student_btn)
        root.add_widget(card)

        # Server URL setting (handy when running APK on a real phone over Wi-Fi)
        server_card = CardBox(orientation="vertical", padding=dp(14), spacing=dp(8), size_hint_y=None, height=dp(100))
        server_card.add_widget(make_label("Backend Server URL (PC IP for APK)", font_size=12, color=COLORS["muted"], height=18))
        self.server_input = StyledInput(text=DEFAULT_SERVER_URL, hint_text="http://192.168.1.5:5000")
        server_card.add_widget(self.server_input)
        root.add_widget(server_card)

        root.add_widget(BoxLayout())  # Spacer
        self.add_widget(root)

    def _update_bg(self, *_args):
        self._bg.pos = self.pos
        self._bg.size = self.size

    def _open_auth(self, role: str) -> None:
        app = App.get_running_app()
        app.api.set_base_url(self.server_input.text)
        auth_screen = self.manager.get_screen("auth")
        auth_screen.configure_role(role)
        self.manager.current = "auth"
