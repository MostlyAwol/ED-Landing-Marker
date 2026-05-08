# overlay.py
import sys
import tkinter as tk

IS_WINDOWS = sys.platform.startswith("win")


class PinOverlay:
    def __init__(self, width, height, marker_size=28):
        self.width = width
        self.height = height
        self.marker_size = marker_size

        self.transparent_color = "#ff00ff"

        self.root = tk.Toplevel()
        self.root.title("PlanetPin Overlay")
        self.root.geometry(f"{width}x{height}+0+0")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)

        # Color-key transparency.
        self.root.configure(bg=self.transparent_color)

        try:
            self.root.attributes("-transparentcolor", self.transparent_color)
        except tk.TclError:
            pass

        self.canvas = tk.Canvas(
            self.root,
            width=width,
            height=height,
            bg=self.transparent_color,
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack(fill="both", expand=True)

        self.root.after(250, self.make_clickthrough)
        self.root.after(1000, self.make_clickthrough)
        self.root.after(500, self.keep_overlay_on_top)

    def keep_overlay_on_top(self):
        self.force_topmost()
        self.root.after(500, self.keep_overlay_on_top)

    def make_clickthrough(self):
        if not IS_WINDOWS:
            return

        try:
            import ctypes

            user32 = ctypes.windll.user32

            # Tk can have a wrapper window, so try both.
            hwnd = self.root.winfo_id()
            parent = user32.GetParent(hwnd)
            if parent:
                hwnd = parent

            self.hwnd = hwnd

            GWL_EXSTYLE = -20
            WS_EX_LAYERED = 0x00080000
            WS_EX_TRANSPARENT = 0x00000020
            WS_EX_NOACTIVATE = 0x08000000
            WS_EX_TOOLWINDOW = 0x00000080

            style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            style |= WS_EX_LAYERED
            style |= WS_EX_TRANSPARENT
            style |= WS_EX_NOACTIVATE
            style |= WS_EX_TOOLWINDOW

            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)

            self.force_topmost()

        except Exception as e:
            print(f"Could not enable click-through overlay: {e}")

    def clear(self):
        self.canvas.delete("all")

    def draw_marker(
        self,
        x,
        y,
        solid=True,
        edge=False,
        clamped=False,
        text=None,
        **kwargs
    ):
        """
        Draws the landing marker.

        Accepts both:
          edge=True
        and:
          clamped=True

        because main.py may use either name.
        """
        #print(f"DRAW_MARKER called: x={x}, y={y}")
        #print(f"Overlay size: {self.width}x{self.height}")
        #print(f"Drawing at visible coords: {x}, {y}")        
        self.clear()

        edge = edge or clamped

        r = self.marker_size / 2

        x = max(r, min(self.width - r, float(x)))
        y = max(r, min(self.height - r, float(y)))

        outline = "lime"

        # Main ring
        self.canvas.create_oval(
            x - r,
            y - r,
            x + r,
            y + r,
            outline=outline,
            fill="",
            width=5,
        )

        # Solid marker indicator: draw an inner ring and crosshair instead of filling
        if solid:
            self.canvas.create_oval(
                x - r + 8,
                y - r + 8,
                x + r - 8,
                y + r - 8,
                outline=outline,
                fill="",
                width=3,
            )

        # Big crosshair so it is impossible to miss
        self.canvas.create_line(
            x - 20,
            y,
            x + 20,
            y,
            fill=outline,
            width=2,
        )

        self.canvas.create_line(
            x,
            y - 20,
            x,
            y + 20,
            fill=outline,
            width=2,
        )

        if edge:
            self.canvas.create_text(
                x,
                y - r - 14,
                text="EDGE",
                fill="lime",
                font=("Segoe UI", 10, "bold"),
            )

        if text:
            self.canvas.create_text(
                x,
                y + r + 32,
                text=str(text),
                fill="lime",
                font=("Segoe UI", 10, "bold"),
            )

    def debug_test_marker(self):
        self.draw_marker(
            self.width / 2,
            self.height / 2,
            solid=True,
            edge=False,
            text="TEST MARKER"
        )

    def force_topmost(self):
        if not IS_WINDOWS:
            return

        try:
            import ctypes

            user32 = ctypes.windll.user32

            hwnd = getattr(self, "hwnd", None)
            if not hwnd:
                hwnd = self.root.winfo_id()
                parent = user32.GetParent(hwnd)
                if parent:
                    hwnd = parent
                self.hwnd = hwnd

            HWND_TOPMOST = -1
            SWP_NOMOVE = 0x0002
            SWP_NOSIZE = 0x0001
            SWP_NOACTIVATE = 0x0010
            SWP_SHOWWINDOW = 0x0040

            user32.SetWindowPos(
                hwnd,
                HWND_TOPMOST,
                0,
                0,
                0,
                0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW,
            )

            self.root.lift()
            self.root.attributes("-topmost", True)

        except Exception as e:
            print(f"Could not force overlay topmost: {e}")

    def hide_marker(self, message=None):
        #self.clear()

        text = str(message) if message else "MARKER HIDDEN"

        self.canvas.create_text(
            self.width / 2,
            self.height / 2,
            text=text,
            fill="lime",
            font=("Segoe UI", 18, "bold"),
        )

    def update(self):
        self.root.update_idletasks()
        self.root.update()


# Backwards-compatible alias in case main.py imports PlanetPinOverlay.
PlanetPinOverlay = PinOverlay