"""Local, allowlisted HTTP player for PD musicus. Python standard library only."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
from pathlib import Path
import re
from urllib.parse import urlsplit
import webbrowser

ROOT = Path(__file__).resolve().parent
SAMPLES = ("avs_0p5a", "avs_5a")


def make_handler(root=ROOT):
    root = Path(root)
    class Handler(BaseHTTPRequestHandler):
        def do_HEAD(self):
            self.serve(head=True)

        def do_GET(self):
            self.serve()

        def serve(self, head=False):
            path = urlsplit(self.path).path
            if path.startswith('/samples/') and path.removeprefix('/samples/').removesuffix('.json') in SAMPLES and path.endswith('.json'):
                name = path.removeprefix('/samples/').removesuffix('.json')
                try:
                    from pd_musicus import build_plan
                    plan = build_plan(root/'examples'/f'{name}_pd.csv', asd=root/'examples'/f'{name}_asd.csv')
                    plan['audio'] = f'{name}.wav'
                    # Only the information needed for playback leaves this endpoint.
                    for item in plan['inputs']:
                        item['path'] = Path(item['path']).name
                    payload = json.dumps(plan, allow_nan=False).encode('utf-8')
                except (OSError, ValueError, KeyError):
                    self.send_error(500, 'Could not prepare sample score')
                    return
                self.send_payload(payload, 'application/json', head)
                return
            routes = {'/': root/'player/index.html', '/index.html': root/'player/index.html'}
            routes.update({f'/{name}': root/'player'/name for name in ('style.css','app.js','timeline.js')})
            routes.update({f'/examples/{name}.wav': root/'examples'/f'{name}.wav' for name in SAMPLES})
            target = routes.get(path)
            if target is None or not target.is_file():
                self.send_error(404)
                return
            payload = target.read_bytes()
            self.send_payload(payload, mimetypes.guess_type(target.name)[0] or 'application/octet-stream', head)

        def send_payload(self, payload, content_type, head):
            length = len(payload)
            start, end, partial = 0, length-1, False
            requested = self.headers.get('Range')
            if requested:
                match = re.fullmatch(r'bytes=(\d*)-(\d*)', requested)
                try:
                    if not match or not any(match.groups()):
                        raise ValueError()
                    a, b = match.groups()
                    if not a:
                        suffix = int(b)
                        if suffix <= 0:
                            raise ValueError()
                        start = max(0, length-suffix)
                    else:
                        start = int(a)
                        end = min(int(b), length-1) if b else length-1
                    if start > end or start >= length:
                        raise ValueError()
                    partial = True
                except ValueError:
                    self.send_response(416)
                    self.send_header('Content-Range', f'bytes */{length}')
                    self.send_header('Content-Length', '0')
                    self.end_headers()
                    return
            self.send_response(206 if partial else 200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(end-start+1))
            self.send_header('Accept-Ranges', 'bytes')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('X-Content-Type-Options', 'nosniff')
            if partial:
                self.send_header('Content-Range', f'bytes {start}-{end}/{length}')
            self.end_headers()
            if not head:
                try:
                    self.wfile.write(payload[start:end+1])
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                    pass

        def log_message(self, *_):
            pass
    return Handler


def run(port=8765, open_browser=True):
    try:
        server = ThreadingHTTPServer(('127.0.0.1', port), make_handler())
    except OSError:
        server = ThreadingHTTPServer(('127.0.0.1', 0), make_handler())
        print('Requested port unavailable; using an available local port.', flush=True)
    with server:
        url = f'http://127.0.0.1:{server.server_port}/'
        print(f'PD musicus player: {url}\nPress Ctrl+C to stop.', flush=True)
        if open_browser:
            webbrowser.open(url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    run(args.port, not args.no_browser)
