[app]
# Application name and package identity
title = Bus Tracking System
package.name = bustracker
package.domain = org.bustracker

# Source directory (contains root main.py and mobile_app/)
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
source.exclude_dirs = tests,server,downloads,bin,.buildozer
source.exclude_patterns = laptop_control_panel.py

# App version
version = 1.0.0

# Minimal requirements: zero requests/charset_normalizer/pillow wheel issues!
requirements = python3,kivy,plyer

# App branding assets
icon.filename = %(source.dir)s/assets/icons/app_icon.png
presplash.filename = %(source.dir)s/assets/icons/presplash.png

# Orientation & fullscreen
orientation = portrait
fullscreen = 0

# Android permissions for live GPS, network, and arrival notifications
android.permissions = INTERNET,ACCESS_FINE_LOCATION,ACCESS_COARSE_LOCATION,POST_NOTIFICATIONS
android.api = 33
android.minapi = 24
# Single modern 64-bit architecture cuts Buildozer build time in half!
android.archs = arm64-v8a
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
