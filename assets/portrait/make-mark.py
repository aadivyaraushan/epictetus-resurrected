"""Build the browser-tab icon from the approved Epictetus portrait.

Run: .venv/bin/python assets/portrait/make-mark.py
"""

from pathlib import Path

from PIL import Image

WEB = Path(__file__).parents[2] / "web"
PORTRAIT = WEB / "public" / "epictetus.png"
ICON = WEB / "app" / "icon.png"


def main():
    portrait = Image.open(PORTRAIT).convert("RGBA")
    icon = portrait.resize((256, 256), Image.LANCZOS)
    icon.save(ICON, optimize=True)
    print(f"icon {icon.width}x{icon.height}")


main()
