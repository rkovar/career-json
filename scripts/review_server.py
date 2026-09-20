"""A temporary loopback connection for the career review page; no hosted service."""
import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import secrets
import time
import webbrowser

from career_review import correct, save, state_token
from pack_io import local
import pack_review
from review_html import render_review

MAX_BODY = 1024 * 1024


def create_server(session, port=0):
    session = local(session)
    pack_review.load_session(session)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass  # Never log the private URL or career content.

        def send(self, code, content, kind='application/json; charset=utf-8'):
            payload = content.encode('utf-8')
            self.send_response(code)
            self.send_header('Content-Type', kind)
            self.send_header('Content-Length', str(len(payload)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; img-src data:; base-uri 'none'; frame-ancestors 'none'; form-action 'none'")
            self.end_headers()
            self.wfile.write(payload)

        def allowed(self, mutation=False):
            if self.headers.get('Host') != self.server.authority:
                return False
            if self.path not in (self.server.route, self.server.route + '/save',
                                 self.server.route + '/correct', self.server.route + '/reading'):
                return False
            if mutation and (self.headers.get('Origin') != self.server.origin or
                             self.headers.get('X-Career-Review') != self.server.token or
                             self.headers.get_content_type() != 'application/json'):
                return False
            self.server.last_active = time.monotonic()
            return True

        def do_GET(self):
            if not self.allowed() or self.path.endswith(('/save', '/correct')):
                self.send(404, json.dumps({'error': 'Review not found.'})); return
            try:
                if self.path.endswith('/reading'):
                    from career_page import build
                    from pack_io import read
                    current = pack_review.resolve()
                    if current is None:
                        raise ValueError('No career facts have been saved yet.')
                    page = build(read(current), str(local(current).relative_to(pack_review.ROOT.resolve())))
                else:
                    state = pack_review.status(self.server.session)
                    state['connection'] = {'url': self.server.route, 'token': self.server.token,
                                           'state_token': state_token(state)}
                    page = render_review(state)
                self.send(200, page, 'text/html; charset=utf-8')
            except (ValueError, KeyError, OSError, SystemExit) as exc:
                self.send(409, json.dumps({'error': str(exc)}))

        def do_POST(self):
            if not self.allowed(mutation=True) or not self.path.endswith(('/save', '/correct')):
                self.send(403, json.dumps({'error': 'Use the review page opened by this career session.'})); return
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= MAX_BODY:
                    raise ValueError('Review request is empty or too large.')
                self.connection.settimeout(15)
                request = json.loads(self.rfile.read(length))
                if not isinstance(request, dict) or set(request) - {'state_token', 'decisions', 'edits'}:
                    raise ValueError('Invalid review request.')
                if not isinstance(request.get('state_token'), str):
                    raise ValueError('Reload the current review before saving.')
                if self.path.endswith('/correct'):
                    self.server.session = correct(self.server.session, request['decisions'], request.get('edits'), request['state_token'])
                    response = {'message': 'Revised wording is ready. Review and confirm it before saving.', 'reload': True}
                else:
                    state = save(self.server.session, request['decisions'], request['state_token'])
                    response = {key: state[key] for key in ('saved_pack', 'save_blocked', 'reading_page',
                                'reading_page_error', 'state_token', 'message', 'summary')}
                    response['items'] = [{'key': r['key'], 'review_status': r['review_status']} for r in state['items']]
                self.send(200, json.dumps(response))
            except (ValueError, KeyError, TypeError, OSError, SystemExit) as exc:
                self.send(409, json.dumps({'error': str(exc)}))

    server = HTTPServer(('127.0.0.1', port), Handler)
    server.timeout = 1
    server.token = secrets.token_urlsafe(32)
    server.authority = '127.0.0.1:' + str(server.server_port)
    server.origin = 'http://' + server.authority
    server.route = '/review/' + server.token
    server.session = session
    server.last_active = time.monotonic()
    return server


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', required=True)
    parser.add_argument('--port', type=int, default=0)
    parser.add_argument('--open', action='store_true', help='open the local review in your browser')
    parser.add_argument('--idle-minutes', type=float, default=60)
    args = parser.parse_args(argv)
    if args.idle_minutes <= 0:
        parser.error('idle-minutes must be positive')
    try:
        with create_server(args.session, args.port) as server:
            url = server.origin + server.route
            print(url, flush=True)
            print('Private local review. Save reviewed changes here; Ctrl-C closes the connection. GitHub backup is separate.', flush=True)
            if args.open:
                webbrowser.open(url)
            while time.monotonic() - server.last_active < args.idle_minutes * 60:
                server.handle_request()
        return 0
    except KeyboardInterrupt:
        print('\nReview connection closed. Saved career facts and recorded decisions remain available.')
        return 0
    except (ValueError, OSError, KeyError) as exc:
        parser.exit(1, 'review: ' + str(exc) + '\n')


if __name__ == '__main__':
    main()
