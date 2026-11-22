import json
import hashlib
import unittest
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

import struct
import subprocess
from PIL import Image, ImageDraw, ImageFont, ImageOps

from aml.calibration import FONT, InvalidImage
from aml.model import Analyzer, ModelUnavailable
from aml.service import analyze
from server import Handler, ROOT


RUNTIME_PARTS = (ROOT / "runtime/community.wasm.part1", ROOT / "runtime/community.wasm.part2")
BAR = [300, 197, 379, 197]
CELL = [80, 65, 144, 127]
MARKS = {"bar": BAR, "cell": CELL}


def sample(label="20 µm", with_bar=True, above=True):
    img = Image.new("RGB", (420, 234), "#fafafa")
    pen = ImageDraw.Draw(img)
    pen.ellipse((81,66,142,125), fill="#c19abf")
    pen.ellipse((96,77,128,110), fill="#774375")
    if with_bar:
        pen.rectangle((300,196,379,199), fill="#101010")
    if label:
        font = ImageFont.truetype(FONT, size=18)
        pen.text((340, 188 if above else 207), label, font=font, anchor="mb" if above else "mt", fill="black")
    return img


def encode(img, fmt="PNG", **opts):
    out = BytesIO()
    img.save(out, format=fmt, **opts)
    return out.getvalue()


class AppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.analyzer = Analyzer(ROOT / 'runtime')

    def test_complete_gate_and_measurements(self):
        for image in (sample(), ImageOps.invert(sample()), sample(above=False)):
            for fmt in ("PNG","JPEG"):
                with self.subTest(fmt=fmt):
                    data = analyze(encode(image, fmt), MARKS, self.analyzer)
                    self.assertEqual(data, {"bar_um":20,"bar_px":80,"um_per_pixel":.25,
                                             "box_width_um":16,"box_height_um":15.5})

    def test_two_different_lengths_use_image_evidence(self):
        for number in (5,10,20,25,50,100,150,200):
            self.assertEqual(analyze(encode(sample(f"{number} µm")), MARKS, self.analyzer)["bar_um"], number)

    def test_rejections_before_model(self):
        for image in (sample(with_bar=False), sample(""), sample("20"), sample("20 mm"),
                      sample("10 nm"), sample("sample"), sample("250 µm")):
            with self.subTest(), self.assertRaises(InvalidImage):
                analyze(encode(image), MARKS, self.analyzer, True)

    def test_forged_points_and_overlap(self):
        for marks in ({"bar":[40,60,120,60],"cell":CELL}, {"bar":[300,110,379,198],"cell":CELL},
                      {"bar":BAR,"cell":[295,175,385,205]}, {"bar":BAR,"cell":[-1,10,33,44]},
                      {"bar":[True,4,99,4],"cell":CELL}, {"bar":BAR,"cell":CELL,"um_per_pixel":1}):
            with self.subTest(), self.assertRaises(InvalidImage):
                analyze(encode(sample()), marks, self.analyzer, True)

    def test_unreadable_and_unsupported_images(self):
        animated = [sample(), ImageOps.invert(sample())]
        for data in (b"", b"hello", encode(sample(),"GIF"), encode(Image.new("RGBA",(50,50))),
                     encode(animated[0],save_all=True,append_images=animated[1:]),encode(Image.new("L",(25,25)))):
            with self.subTest(), self.assertRaises(InvalidImage):
                analyze(data, MARKS, self.analyzer)


    def test_compiled_component_directly(self):
        def invoke(image, marks, mode=1):
            packet = struct.pack("<11i", *image.size, *marks["bar"], *marks["cell"], mode)
            reply = subprocess.run([self.analyzer.node, str(ROOT/"runtime"/"run.cjs")],
                                   input=packet + image.tobytes(), capture_output=True, check=True)
            return int(reply.stdout)

        # Call the runner directly to check that it still requires the bar when the browser is out of the loop.
        self.assertGreater(invoke(sample(), MARKS), 0)
        for img in (sample(with_bar=False), sample(""), sample("20 mm")):
            self.assertLess(invoke(img, MARKS), 0)
        crop = sample().crop(CELL)
        self.assertLess(invoke(crop, {"bar": [2, 20, 42, 20], "cell": [3, 30, 30, 55]}), 0)
        self.assertLess(invoke(sample(), MARKS, mode=2), 0)

    def test_public_entry_point(self):
        audit = """const fs=require('node:fs');
        const bytes = Buffer.concat(process.argv.slice(1).map(name => fs.readFileSync(name)));
        const m = new WebAssembly.Module(bytes);
        console.log(JSON.stringify([WebAssembly.Module.exports(m), WebAssembly.Module.imports(m)]));"""
        check = subprocess.run([self.analyzer.node, "-e", audit, *map(str, RUNTIME_PARTS)],
                               capture_output=True, check=True)
        exports, imports = json.loads(check.stdout)
        self.assertEqual(exports, [{"name":"analyze", "kind":"function"}])
        self.assertEqual(imports, [{"module":"frame","name":"pixel","kind":"function"}])

    def test_required_component(self):
        with self.assertRaises(ModelUnavailable):
            Analyzer(ROOT / "missing-runtime")

class HTTPTests(unittest.TestCase):
    def request(self, method, route, body=None, *, model=None, **headers):
        body = body or b""
        headers = {"Host": "127.0.0.1:8787","Content-Length":str(len(body)),**headers}
        lines = [f"{method} {route} HTTP/1.0", *(f"{k}: {v}" for k,v in headers.items()), "", ""]
        raw = BytesIO("\r\n".join(lines).encode("ascii") + body)
        response = BytesIO()
        socket = SimpleNamespace(makefile=lambda *args: raw, sendall=response.write)
        server = SimpleNamespace(server_port=8787,model=model or Analyzer(ROOT / "runtime"))
        Handler(socket, ("127.0.0.1", 1234), server)
        heading, content = response.getvalue().split(b"\r\n\r\n",1)
        return int(heading.split(b" ",2)[1]), content

    def test_normal_ui_and_api(self):
        for path in ("/","/style.css","/app.js","/example.png","/api/status"):
            self.assertEqual(self.request("GET",path)[0],200)
        data = encode(sample())
        headers={"Content-Type":"image/png","X-Selection":json.dumps(MARKS)}
        status, measured=self.request("POST","/api/measure",data,**headers)
        self.assertEqual(status,200)
        self.assertEqual(json.loads(measured)["bar_um"],20)
        self.assertEqual(self.request("POST","/api/classify",data,**headers)[0],200)
        self.assertEqual(self.request("POST","/api/classify",encode(sample("")),**headers)[0],422)
        self.assertEqual(self.request("POST","/api/measure",data,**{**headers,"Origin":"http://outside.invalid"})[0],403)
        self.assertEqual(self.request("POST","/api/measure",data,**{"Content-Type":"text/plain"})[0],415)
        for part in RUNTIME_PARTS:
            self.assertEqual(self.request("GET", f"/runtime/{part.name}")[0], 404)

    def test_bundled_weights_and_both_outputs_over_http(self):
        for part in RUNTIME_PARTS:
            self.assertTrue(0 < part.stat().st_size < 25 * 1024 * 1024)
        digest = hashlib.sha256(b"".join(part.read_bytes() for part in RUNTIME_PARTS)).hexdigest()
        self.assertEqual(digest, "3e6869994305363c7d186b5578a93f746d78ab0ca0f5431fb4dd28f551b2dc3b")
        model = Analyzer(ROOT / "runtime")
        headers = {"Content-Type": "image/png", "X-Selection": json.dumps(MARKS)}
        # These two colors give repeatable outputs, so we can catch swapped labels in the API.
        for color, expected in (((120,120,120), "blast"), ((190,155,180), "non-blast")):
            image = sample()
            image.paste(color, tuple(CELL))
            status, data = self.request("POST", "/api/classify", encode(image), model=model, **headers)
            self.assertEqual(status, 200)
            self.assertEqual(json.loads(data)["cell_label"], expected)
        status, _ = self.request("POST", "/api/classify", encode(sample(with_bar=False)), model=model, **headers)
        self.assertEqual(status, 422)


if __name__=="__main__":
    unittest.main()
