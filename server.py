"""Start AML Cell Lab locally with python server.py."""

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from aml.calibration import InvalidImage
from aml.model import Analyzer, ModelUnavailable
from aml.service import analyze


ROOT = Path(__file__).resolve().parent
MAX_BYTES = 8 * 1024 * 1024
ASSETS = {"/": ("web/index.html", "text/html; charset=utf-8"),
          "/app.js": ("web/app.js", "text/javascript; charset=utf-8"),
          "/style.css": ("web/style.css", "text/css"),
          "/example.png": ("examples/scale-practice.png", "image/png")}


class Handler(BaseHTTPRequestHandler):
    def reply(self, status, mime, body):
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; img-src 'self' blob:; frame-ancestors 'none'; form-action 'none'")
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, status, content):
        self.reply(status, "application/json", json.dumps(content).encode())

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/api/status":
            return self.send_json(200, {"classification_available": True})
        if path not in ASSETS:
            return self.send_json(404, {"error": "This address isn’t part of AML Cell Lab."})
        file, mime = ASSETS[path]
        self.reply(200, mime, (ROOT / file).read_bytes())

    def do_POST(self):
        if self.path not in ("/api/measure", "/api/classify"):
            return self.send_json(404, {"error": "This address isn’t part of AML Cell Lab."})
        port = self.server.server_port
        hosts = (f"127.0.0.1:{port}", f"localhost:{port}")
        origin = self.headers.get("Origin")
        if self.headers.get("Host") not in hosts or (origin and origin not in [f"http://{h}" for h in hosts]):
            return self.send_json(403, {"error": "Open the app at the local address printed in your terminal and try again."})
        if self.headers.get_content_type() not in ("image/png", "image/jpeg"):
            return self.send_json(415, {"error": "Send one PNG or JPEG image per request."})
        try:
            size = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            size = 0
        if not 0 < size <= MAX_BYTES:
            return self.send_json(413, {"error": "Choose a nonempty image file no larger than 8 MiB."})
        try:
            selection = json.loads(self.headers.get("X-Selection", "{}"))
            data = self.rfile.read(size)
            if len(data) != size:
                raise InvalidImage("Only part of the image came through. Open the file and try again.")
            result = analyze(data, selection, self.server.model, classify=self.path == "/api/classify")
        except (InvalidImage, json.JSONDecodeError, RecursionError) as exc:
            return self.send_json(422, {"error": str(exc)})
        except ModelUnavailable as exc:
            return self.send_json(503, {"error": str(exc)})
        self.send_json(200, result)

    def log_message(self, fmt, *args):
        pass


class LocalServer(ThreadingHTTPServer):
    def get_request(self):
        connection, address = super().get_request()
        connection.settimeout(15)
        return connection, address


def make_server(port, model=None):
    if model is None:
        model = Analyzer(ROOT / "runtime")
    server = LocalServer(("127.0.0.1", port), Handler)
    server.model = model
    return server


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8787)
    with make_server(parser.parse_args().port) as server:
        print(f"Open http://127.0.0.1:{server.server_port}  (press Ctrl+C here to stop)", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
