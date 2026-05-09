from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")

from datetime import datetime
from typing import Callable, Optional

from gi.repository import Gtk, Pango

from ..models.event import Event


class EventCard(Gtk.Button):
    def __init__(
        self,
        event: Event,
        occ_start: datetime,
        occ_end: datetime,
        on_edit: Callable[[Event], None],
        mode: str = "tinted",   # tinted | live | past | solid
        on_resize: Optional[Callable[[Event, float], None]] = None,
    ) -> None:
        super().__init__()

        self.add_css_class("wp-event")
        self.add_css_class(f"color-{event.color}")

        if mode in ("live", "solid"):
            self.add_css_class("solid")
        if mode == "past":
            self.add_css_class("past")
        if mode == "live":
            self.add_css_class("live")

        self.set_hexpand(True)
        self.set_vexpand(True)
        self.set_halign(Gtk.Align.FILL)
        self.set_valign(Gtk.Align.FILL)
        self.set_margin_top(2)
        self.set_margin_bottom(2)
        self.set_margin_start(3)
        self.set_margin_end(3)

        duration_m = int((occ_end - occ_start).total_seconds() // 60)
        if duration_m < 45:
            self.add_css_class("short")

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        box.set_margin_start(8)
        box.set_margin_top(4)
        box.set_margin_bottom(4)
        box.set_margin_end(6)

        if mode == "live":
            dot_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
            dot_row.set_valign(Gtk.Align.CENTER)
            dot = Gtk.Box()
            dot.add_css_class("wp-live-dot")
            dot.set_valign(Gtk.Align.CENTER)
            title_lbl = Gtk.Label(label=event.title)
            title_lbl.set_halign(Gtk.Align.START)
            title_lbl.set_ellipsize(Pango.EllipsizeMode.END)
            title_lbl.add_css_class("wp-event-title")
            dot_row.append(dot)
            dot_row.append(title_lbl)
            box.append(dot_row)
        else:
            title_lbl = Gtk.Label(label=event.title)
            title_lbl.set_halign(Gtk.Align.START)
            title_lbl.set_ellipsize(Pango.EllipsizeMode.END)
            title_lbl.add_css_class("wp-event-title")
            box.append(title_lbl)

        if duration_m >= 45:
            time_lbl = Gtk.Label(
                label=f"{occ_start.strftime('%H:%M')} – {occ_end.strftime('%H:%M')}"
            )
            time_lbl.set_halign(Gtk.Align.START)
            time_lbl.add_css_class("wp-event-time")
            box.append(time_lbl)

        if on_resize is not None:
            overlay = Gtk.Overlay()
            overlay.set_child(box)

            handle = Gtk.Box()
            handle.add_css_class("wp-resize-handle")
            handle.set_valign(Gtk.Align.END)
            handle.set_halign(Gtk.Align.FILL)
            handle.set_can_target(True)
            overlay.add_overlay(handle)

            # Intercept clicks on the handle so they don't trigger the card edit
            click_blocker = Gtk.GestureClick()
            click_blocker.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
            click_blocker.connect(
                "pressed",
                lambda g, n, x, y: g.set_sequence_state(
                    g.get_current_sequence(), Gtk.EventSequenceState.CLAIMED
                ),
            )
            handle.add_controller(click_blocker)

            drag = Gtk.GestureDrag()
            drag.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
            drag.connect("drag-end", lambda g, ox, oy: on_resize(event, oy))
            handle.add_controller(drag)

            self.set_child(overlay)
        else:
            self.set_child(box)

        self.connect("clicked", lambda _: on_edit(event))
