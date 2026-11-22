"""Send the image and the user’s marks to the local runtime in one request."""
import shutil
import struct
import subprocess
import threading
from pathlib import Path

from .calibration import InvalidImage


class ModelUnavailable(RuntimeError):
    pass


class Analyzer:
    _slots = threading.BoundedSemaphore(2)

    def __init__(self, runtime_dir):
        self.directory = Path(runtime_dir).resolve()
        self.node = shutil.which("node")
        if self.node is None:
            raise ModelUnavailable("Install Node.js 18 or later, then restart the app.")
        for name in ("run.cjs", "community.wasm.part1", "community.wasm.part2"):
            if not (self.directory / name).is_file():
                raise ModelUnavailable(f"Couldn’t find runtime/{name}. Copy it back from the release and restart the app.")

    def analyze_frame(self, image, bar, cell, classify):
        header = struct.pack("<11i", *image.size, *bar, *cell, int(classify))
        with self._slots:
            try:
                result = subprocess.run(
                    [self.node, str(self.directory / "run.cjs")],
                    input=header + image.tobytes(),
                    capture_output=True,
                    timeout=60,
                    check=True,
                )
                packed = int(result.stdout)
            except (OSError, ValueError, subprocess.SubprocessError) as exc:
                raise ModelUnavailable("The local runtime couldn’t finish analyzing this image.") from exc
        errors = {
            -1: "Keep all four marks inside the image. Check the bar endpoints and the size of the cell box.",
            -2: "Move the cell box clear of the bar and its label.",
            -3: "Check the printed length. It should be centered just above or below the bar, in µm.",
            -4: "Couldn’t find a solid horizontal bar at those marks. Click directly on each end.",
        }
        if packed in errors:
            raise InvalidImage(errors[packed])
        pixels = packed & 4095
        length = (packed >> 12) & 255
        decision = packed >> 20
        if pixels < 20 or length not in (5, 10, 20, 25, 50, 100, 150, 200):
            raise ModelUnavailable("The runtime returned a scale measurement outside the supported range.")
        if decision not in ((1, 2) if classify else (0,)):
            raise ModelUnavailable("The runtime returned an unexpected result for this request.")
        # A 20 µm bar spanning 80 pixels gives us 0.25 µm per pixel for this image.
        pitch = length / pixels
        left, top, right, bottom = cell
        output = {
            "bar_um": length,
            "bar_px": pixels,
            "um_per_pixel": round(pitch, 6),
            "box_width_um": round((right-left)*pitch, 2),
            "box_height_um": round((bottom-top)*pitch, 2),
        }
        if classify:
            output["cell_label"] = ("non-blast", "blast")[decision-1]
        return output

