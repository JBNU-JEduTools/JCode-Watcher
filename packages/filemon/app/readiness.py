import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class ReadinessState:
    def __init__(self):
        self._ready = threading.Event()

    def mark_ready(self):
        self._ready.set()

    def mark_not_ready(self):
        self._ready.clear()

    @property
    def is_ready(self) -> bool:
        return self._ready.is_set()


def start_readiness_server(port: int, state: ReadinessState) -> ThreadingHTTPServer:
    class ReadinessHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path != "/ready":
                self.send_error(404)
                return
            status = 200 if state.is_ready else 503
            body = b"READY\n" if state.is_ready else b"STARTING\n"
            self.send_response(status)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, _format, *_args):
            return

    server = ThreadingHTTPServer(("0.0.0.0", port), ReadinessHandler)
    thread = threading.Thread(
        target=server.serve_forever, name="filemon-readiness", daemon=True
    )
    thread.start()
    return server
