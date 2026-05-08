from __future__ import annotations

import json
from pathlib import Path
import tkinter as tk
from tkinter import ttk

from journal_reader import JournalReader
from navigation_math import calculate_marker
from overlay import PinOverlay
from status_reader import StatusReader

APP_DIR = Path(__file__).resolve().parent
CONFIG_PATH = APP_DIR / "config.json"


def load_config() -> dict:
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_config(cfg: dict) -> None:
    with CONFIG_PATH.open("w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


class PlanetPinApp:
    def __init__(self):
        self.cfg = load_config()

        self.root = tk.Tk()
        self.root.title("PlanetPin MVP")
        self.root.geometry("380x280")
        self.root.attributes("-topmost", True)

        detected_w = self.root.winfo_screenwidth()
        detected_h = self.root.winfo_screenheight()
        self.screen_w = int(self.cfg.get("screen_width") or detected_w)
        self.screen_h = int(self.cfg.get("screen_height") or detected_h)

        self.status_reader = StatusReader(self.cfg["journal_dir"])
        self.journal_reader = JournalReader(self.cfg["journal_dir"])
        self.overlay = PinOverlay(self.screen_w, self.screen_h, int(self.cfg.get("marker_radius", 16)))

        self.target_lat_var = tk.StringVar(value=str(self.cfg.get("target_lat", 0.0)))
        self.target_lon_var = tk.StringVar(value=str(self.cfg.get("target_lon", 0.0)))
        self.journal_dir_var = tk.StringVar(value=str(self.cfg.get("journal_dir", "")))
        self.fov_var = tk.StringVar(value=str(self.cfg.get("horizontal_fov", 70.0)))
        self.pitch_var = tk.StringVar(value=str(self.cfg.get("pitch_offset_deg", 0.0)))
        self.status_var = tk.StringVar(value="Starting...")

        self._build_controls()
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.after(100, self.update_loop)


    def _build_controls(self):
        pad = {"padx": 8, "pady": 4}
        frm = ttk.Frame(self.root)
        frm.pack(fill="both", expand=True, padx=8, pady=8)

        ttk.Label(frm, text="Target latitude").grid(row=0, column=0, sticky="w", **pad)
        ttk.Entry(frm, textvariable=self.target_lat_var).grid(row=0, column=1, sticky="ew", **pad)

        ttk.Label(frm, text="Target longitude").grid(row=1, column=0, sticky="w", **pad)
        ttk.Entry(frm, textvariable=self.target_lon_var).grid(row=1, column=1, sticky="ew", **pad)

        ttk.Label(frm, text="Journal folder").grid(row=2, column=0, sticky="w", **pad)
        ttk.Entry(frm, textvariable=self.journal_dir_var).grid(row=2, column=1, sticky="ew", **pad)

        ttk.Label(frm, text="Horizontal FOV").grid(row=3, column=0, sticky="w", **pad)
        ttk.Entry(frm, textvariable=self.fov_var).grid(row=3, column=1, sticky="ew", **pad)

        ttk.Label(frm, text="Pitch offset").grid(row=4, column=0, sticky="w", **pad)
        ttk.Entry(frm, textvariable=self.pitch_var).grid(row=4, column=1, sticky="ew", **pad)

        ttk.Button(frm, text="Save settings", command=self.save_settings).grid(row=5, column=0, sticky="ew", **pad)
        ttk.Button(frm, text="Quit", command=self.close).grid(row=5, column=1, sticky="ew", **pad)

        ttk.Label(frm, textvariable=self.status_var, wraplength=340).grid(row=6, column=0, columnspan=2, sticky="ew", **pad)
        frm.columnconfigure(1, weight=1)

    def save_settings(self):
        self.cfg["target_lat"] = float(self.target_lat_var.get())
        self.cfg["target_lon"] = float(self.target_lon_var.get())
        self.cfg["journal_dir"] = self.journal_dir_var.get().strip()
        self.cfg["horizontal_fov"] = float(self.fov_var.get())
        self.cfg["pitch_offset_deg"] = float(self.pitch_var.get())
        save_config(self.cfg)

        self.status_reader = StatusReader(self.cfg["journal_dir"])
        self.journal_reader = JournalReader(self.cfg["journal_dir"])
        self.status_var.set("Settings saved.")

    def update_loop(self):
        try:
            self.journal_reader.update()
            status = self.status_reader.read()

            if not StatusReader.has_planet_position(status):
                msg = "No planetary lat/lon/heading in Status.json yet. Get near a landable body."
                if self.cfg.get("hide_when_no_position", True):
                    self.overlay.hide_marker(None)
                else:
                    self.overlay.hide_marker(msg)
                self.status_var.set(msg)
                return

            current_lat = float(status["Latitude"])
            current_lon = float(status["Longitude"])
            heading = float(status["Heading"])
            altitude = float(status.get("Altitude", 0.0))
            body_name = status.get("BodyName")

            radius = StatusReader.planet_radius(status)
            if radius is None:
                radius = self.journal_reader.radius_for_body(body_name)

            if radius is None:
                msg = "Need PlanetRadius. Scan the body or wait for Status.json to include it."
                self.overlay.hide_marker(msg)
                self.status_var.set(msg)
                return

            target_lat = float(self.target_lat_var.get())
            target_lon = float(self.target_lon_var.get())
            h_fov = float(self.fov_var.get())
            pitch = float(self.pitch_var.get())
            v_fov = float(self.cfg.get("vertical_fov", 43.0))

            result = calculate_marker(
                current_lat=current_lat,
                current_lon=current_lon,
                heading_deg=heading,
                altitude_m=altitude,
                target_lat=target_lat,
                target_lon=target_lon,
                planet_radius_m=radius,
                screen_w=self.screen_w,
                screen_h=self.screen_h,
                horizontal_fov_deg=h_fov,
                vertical_fov_deg=v_fov,
                pitch_offset_deg=pitch,
            )

            if not result:
                self.overlay.hide_marker("Could not calculate marker.")
                return

            debug = None
            if self.cfg.get("show_debug_text", True):
                debug = (
                    f"Body: {body_name}\n"
                    f"Lat/Lon: {current_lat:.5f}, {current_lon:.5f}\n"
                    f"Target: {target_lat:.5f}, {target_lon:.5f}\n"
                    f"Distance: {result.distance_m/1000:.2f} km\n"
                    f"Visible side: {result.visible_side}\n"
                    f"In front: {result.in_front}"
                )

            self.overlay.draw_marker(result.x, result.y, solid=result.visible_side, clamped=result.clamped, debug=debug)
            self.status_var.set(f"Distance {result.distance_m/1000:.2f} km | marker {'solid' if result.visible_side else 'hollow'}")

        except Exception as e:
            self.overlay.hide_marker(f"Error: {e}")
            self.status_var.set(f"Error: {e}")
        finally:
            self.root.after(int(self.cfg.get("update_ms", 100)), self.update_loop)

    def close(self):
        try:
            self.overlay.win.destroy()
        except Exception:
            pass
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    PlanetPinApp().run()
