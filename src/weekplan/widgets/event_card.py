from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")

from datetime import datetime
from typing import Callable

from gi.repository import Gtk, Pango

from ..models.event import Event


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


class EventCard(Gtk.Button):
    def __init__(
        self,
        event: Event,
        occ_start: datetime,
        occ_end: datetime,
        on_edit: Callable[[Event], None],
    ) -> None:
        super().__init__()

        self.add_css_class("event-card")
        self.set_hexpand(True)
        self.set_vexpand(True)
        self.set_halign(Gtk.Align.FILL)
        self.set_valign(Gtk.Align.FILL)
        self.set_margin_top(1)
        self.set_margin_bottom(1)
        self.set_margin_start(2)
        self.set_margin_end(2)

        # Dynamic colour: gradient left-bar + light background tint
        r, g, b = _hex_to_rgb(event.color)
        css_class = f"ec-{event.id}"
        self.add_css_class(css_class)
        provider = Gtk.CssProvider()
        provider.load_from_string(
            f".{css_class} {{"
            f"  background-image: linear-gradient("
            f"    to right, {event.color} 4px, rgba({r},{g},{b},0.18) 4px);"
            f"  border-radius: 4px;"
            f"}}"
        )
        self.get_style_context().add_provider(
            provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        # Content: title + occurrence time subtitle
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        box.set_margin_start(8)
        box.set_margin_top(2)
        box.set_margin_bottom(2)
        box.set_margin_end(4)

        title_lbl = Gtk.Label(label=event.title)
        title_lbl.set_halign(Gtk.Align.START)
        title_lbl.set_ellipsize(Pango.EllipsizeMode.END)
        title_lbl.add_css_class("caption-heading")

        time_lbl = Gtk.Label(
            label=f"{occ_start.strftime('%H:%M')} – {occ_end.strftime('%H:%M')}"
        )
        time_lbl.set_halign(Gtk.Align.START)
        time_lbl.add_css_class("caption")

        box.append(title_lbl)
        box.append(time_lbl)
        self.set_child(box)

        self.connect("clicked", lambda _: on_edit(event))
