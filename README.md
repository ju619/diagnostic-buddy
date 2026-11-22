# diagnostic-buddy

# by NanoCure AI, a Jackie White Lab company

I wanted researchers to be able to download our AML model (public version), run it on their own machine, and see what it calls on a cell they pick. Start with a de-identified image of a stained smear. Mark the scale bar, draw a box around one cell, and the model will give you a **blast** or **non-blast** call.

## Run it locally

You’ll need Python 3.11–3.13 and Node.js 18 or later. Python serves the app and Node runs the classifier. The weights come with the project, and a CPU is enough. Your images stay on your machine.

Extract the ZIP and open a terminal in the folder with `server.py`. Run the tests, then start the app.

**Windows PowerShell**

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe server.py
```

**macOS or Linux**

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python server.py
```

Leave the terminal open while you work. Press Ctrl+C there when you’re done. [Open AML Cell Lab](http://127.0.0.1:8787)

## Check the scale first

Choose **Practice image**. The dark bar near the bottom right is labeled **20 µm**. Click its two ends, then click opposite corners of a box around the purple shape. Choose **Measure box**.

For an exact check, open **Enter pixel coordinates** and use these marks.

| Field | Coordinates |
| --- | --- |
| Bar endpoints | `300, 197, 379, 197` |
| Cell box | `80, 65, 144, 127` |

Choose **Apply coordinates**, then **Measure box**. The bar spans 80 pixels, so each pixel represents **0.25 µm**. The box is 64 × 62 pixels and should read **16 × 15.5 µm**. Those numbers describe the box you drew. The practice shape is there to help you check the measurement.

## Try a smear image

1. Choose **Open image** and select a de-identified PNG or JPEG.
2. Click the two ends of the scale bar. Either end can go first.
3. Draw a roughly square box around one whole cell. Leave a little smear around it and keep the bar, its label, and neighboring cells outside the box.
4. Choose **Classify cell**. You’ll see the box dimensions and the model’s call for that cell.

### What the scale reader accepts

| Item | What to use |
| --- | --- |
| Image | One grayscale or RGB still image, at least 48 pixels on each side, up to 8 MiB and 12 megapixels |
| Bar | A solid horizontal rectangle, 20–1600 pixels long, with clear contrast against its background |
| Label | One printed length centered just above or below the bar, in supported sans-serif lettering |
| Length | 5, 10, 20, 25, 50, 100, 150, or 200 µm. The reader accepts both `µm` and `um`. |
| Cell box | 12–1024 pixels on each side, clear of the bar and its label |

If the app rejects a bar you can see, check where you clicked and whether the printed length is on the list. Faint bars, text touching the bar, and unfamiliar fonts can also be hard for the reader to recognize. Measurements depend on the scale printed on the original image.

## Interpreting a call

You pick the cell. The model can still return a label if your box contains only background, several cells, or an out-of-focus region. Look back at the selected pixels when you review the call. We built this release for education and research. We haven’t established clinical performance for this workflow or its use in diagnosing a patient.

## Where the code lives

| Path | What it does |
| --- | --- |
| `web/` | Displays the image and records where you click |
| `server.py` | Serves the browser app and handles local requests |
| `aml/calibration.py` | Opens the image and checks the coordinates |
| `aml/model.py` | Sends the full image and your marks to the runtime |
| `runtime/community.wasm.part1` and `runtime/community.wasm.part2` | Reads the scale bar, measures the box, and classifies the selected cell |
| `tests/` | Checks which images the app accepts, how it measures them, and the labels returned by the API |

## Licenses

© 2026 Jackie White Lab. The app code and practice image use the BSD 3-Clause license. The compiled runtime and its weights have separate noncommercial terms. The bundled font has its own license. [App code](LICENSE) · [Runtime and weights](runtime/LICENSE.txt) · [Font](aml/fonts/bitstream-vera-license.txt)
