"""Reusable styled buttons, cards, inputs, and popups for a clean Kivy UI."""

from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput

from mobile_app.config import COLORS


class CardBox(BoxLayout):
    """A rounded dark card container with padding."""

    def __init__(self, bg_color=None, radius=12, **kwargs):
        super().__init__(**kwargs)
        self._bg_color = bg_color or COLORS["card"]
        self._radius = radius
        with self.canvas.before:
            self._color_instr = Color(*self._bg_color)
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(self._radius)])
        self.bind(pos=self._update_rect, size=self._update_rect)

    def _update_rect(self, *_args):
        self._rect.pos = self.pos
        self._rect.size = self.size


class StyledButton(Button):
    """Flat rounded button with consistent typography."""

    def __init__(self, bg_color=None, text_color=None, **kwargs):
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", dp(44))
        kwargs.setdefault("bold", True)
        kwargs.setdefault("font_size", dp(15))
        super().__init__(**kwargs)
        self.background_normal = ""
        self.background_down = ""
        self.background_color = (0, 0, 0, 0)
        self.color = text_color or COLORS["text"]
        self._bg_color = bg_color or COLORS["primary"]

        with self.canvas.before:
            self._color_instr = Color(*self._bg_color)
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(10)])
        self.bind(pos=self._update_rect, size=self._update_rect)

    def set_bg_color(self, rgba):
        self._bg_color = rgba
        self._color_instr.rgba = rgba

    def _update_rect(self, *_args):
        self._rect.pos = self.pos
        self._rect.size = self.size


class StyledInput(TextInput):
    """Clean single-line dark text input."""

    def __init__(self, **kwargs):
        kwargs.setdefault("multiline", False)
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", dp(42))
        kwargs.setdefault("padding", [dp(12), dp(10)])
        kwargs.setdefault("font_size", dp(14))
        kwargs.setdefault("background_color", (0.18, 0.23, 0.33, 1))
        kwargs.setdefault("foreground_color", COLORS["text"])
        kwargs.setdefault("hint_text_color", COLORS["muted"])
        kwargs.setdefault("cursor_color", COLORS["primary"])
        super().__init__(**kwargs)


def make_label(text: str, font_size: int = 14, bold: bool = False, color=None, height: int = 24):
    """Helper to create a left-aligned Kivy Label that wraps cleanly."""
    lbl = Label(
        text=text,
        font_size=dp(font_size),
        bold=bold,
        color=color or COLORS["text"],
        size_hint_y=None,
        height=dp(height),
        halign="left",
        valign="middle",
    )
    lbl.bind(size=lambda instance, val: setattr(instance, "text_size", (val[0], None)))
    return lbl


def show_message_popup(title: str, message: str) -> None:
    """Display a simple modal alert popup."""
    box = BoxLayout(orientation="vertical", spacing=dp(12), padding=dp(14))
    lbl = Label(text=message, color=COLORS["text"], halign="center", valign="middle")
    lbl.bind(size=lambda inst, val: setattr(inst, "text_size", (val[0], None)))
    btn = StyledButton(text="OK", bg_color=COLORS["primary"], text_color=(0.08, 0.11, 0.17, 1))
    box.add_widget(lbl)
    box.add_widget(btn)

    popup = Popup(title=title, content=box, size_hint=(0.85, 0.35))
    btn.bind(on_release=popup.dismiss)
    popup.open()
