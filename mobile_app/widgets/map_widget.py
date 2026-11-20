"""Live Map Widget for displaying Bus, Student, Pickup Point, and Destination.

Uses `kivy_garden.mapview` (real OpenStreetMap tiles) when installed (including
in the Android APK), and automatically falls back to a clean built-in Kivy
coordinate radar map so it always works out of the box.
"""

import os
from typing import Dict, Optional, Tuple

from kivy.graphics import Color, Ellipse, Line, Rectangle
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget

from mobile_app.config import COLORS, ICONS_DIR

try:
    from kivy_garden.mapview import MapMarker, MapView

    HAS_MAPVIEW = True
except Exception:
    HAS_MAPVIEW = False


class _FallbackCanvasMap(Widget):
    """Lightweight coordinate plot fallback when kivy_garden.mapview is unavailable."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.points: Dict[str, Tuple[float, float, Tuple[float, float, float, float], str]] = {}
        self.bind(pos=self._redraw, size=self._redraw)

    def set_points(self, points: Dict[str, Tuple[float, float, Tuple[float, float, float, float], str]]):
        self.points = points
        self._redraw()

    def _redraw(self, *_args):
        self.canvas.clear()
        with self.canvas:
            # Map background
            Color(0.10, 0.15, 0.22, 1)
            Rectangle(pos=self.pos, size=self.size)

            # Subtle coordinate grid
            Color(0.18, 0.25, 0.35, 1)
            for i in range(1, 5):
                gx = self.x + (self.width * i / 5.0)
                gy = self.y + (self.height * i / 5.0)
                Line(points=[gx, self.y, gx, self.top], width=1)
                Line(points=[self.x, gy, self.right, gy], width=1)

            if not self.points:
                return

            lats = [p[0] for p in self.points.values()]
            lons = [p[1] for p in self.points.values()]
            min_lat, max_lat = min(lats), max(lats)
            min_lon, max_lon = min(lons), max(lons)

            lat_span = max(max_lat - min_lat, 0.004)
            lon_span = max(max_lon - min_lon, 0.004)
            pad = dp(26)
            usable_w = max(self.width - 2 * pad, 10)
            usable_h = max(self.height - 2 * pad, 10)

            def to_xy(lat: float, lon: float):
                px = self.x + pad + ((lon - min_lon) / lon_span) * usable_w
                py = self.y + pad + ((lat - min_lat) / lat_span) * usable_h
                return px, py

            # Connect bus -> pickup -> destination with a dashed-style route line
            route_keys = [k for k in ("bus", "pickup", "destination") if k in self.points]
            if len(route_keys) >= 2:
                Color(0.96, 0.65, 0.14, 0.65)
                pts = []
                for k in route_keys:
                    pts.extend(to_xy(self.points[k][0], self.points[k][1]))
                Line(points=pts, width=dp(2))

            # Draw markers
            for _key, (lat, lon, color, _label) in self.points.items():
                px, py = to_xy(lat, lon)
                r = dp(8)
                Color(*color)
                Ellipse(pos=(px - r, py - r), size=(2 * r, 2 * r))


class BusMapWidget(BoxLayout):
    """Unified map widget showing Bus, Student, Pickup Point, and Destination."""

    def __init__(self, **kwargs):
        kwargs.setdefault("orientation", "vertical")
        kwargs.setdefault("spacing", dp(4))
        super().__init__(**kwargs)

        self._markers: Dict[str, object] = {}
        if HAS_MAPVIEW:
            self._mapview = MapView(zoom=14, lat=28.4700, lon=77.5080)
            self.add_widget(self._mapview)
            self._fallback = None
        else:
            self._mapview = None
            self._fallback = _FallbackCanvasMap()
            self.add_widget(self._fallback)

        # Compact legend bar below map
        self._legend = Label(
            text="[Bus: Amber]  [You: Blue]  [Pickup: Green]  [Destination: Red]",
            font_size=dp(12),
            color=COLORS["muted"],
            size_hint_y=None,
            height=dp(22),
        )
        self.add_widget(self._legend)

    def update_markers(
        self,
        bus_pos: Optional[Tuple[float, float]] = None,
        student_pos: Optional[Tuple[float, float]] = None,
        pickup_pos: Optional[Tuple[float, float]] = None,
        destination_pos: Optional[Tuple[float, float]] = None,
    ) -> None:
        """Update all live markers on the map."""
        icon_map = {
            "bus": (bus_pos, os.path.join(ICONS_DIR, "bus_marker.png"), COLORS["primary"], "Bus"),
            "student": (student_pos, os.path.join(ICONS_DIR, "student_marker.png"), COLORS["secondary"], "You"),
            "pickup": (pickup_pos, os.path.join(ICONS_DIR, "pickup_marker.png"), COLORS["success"], "Pickup"),
            "destination": (destination_pos, os.path.join(ICONS_DIR, "dest_marker.png"), COLORS["danger"], "Destination"),
        }

        if HAS_MAPVIEW and self._mapview is not None:
            for key, (pos, icon_path, _color, _label) in icon_map.items():
                if pos is None:
                    continue
                lat, lon = pos
                if key in self._markers:
                    marker = self._markers[key]
                    marker.lat = lat
                    marker.lon = lon
                else:
                    kwargs = {"lat": lat, "lon": lon}
                    if os.path.exists(icon_path):
                        kwargs["source"] = icon_path
                    marker = MapMarker(**kwargs)
                    self._mapview.add_marker(marker)
                    self._markers[key] = marker

            center = bus_pos or pickup_pos or destination_pos
            if center:
                self._mapview.center_on(center[0], center[1])
        elif self._fallback is not None:
            points = {}
            for key, (pos, _icon_path, color, label) in icon_map.items():
                if pos is not None:
                    points[key] = (pos[0], pos[1], color, label)
            self._fallback.set_points(points)
