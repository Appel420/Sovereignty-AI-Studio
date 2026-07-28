from http.server import HTTPServer, SimpleHTTPRequestHandler
import os

class DashboardHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.path = '/index.html'  # your dashboard—rename if different
        try:
            filepath = os.getcwd() + self.path
            if os.path.isdir(filepath):
                self.send_response(301)
                self.send_header('Location', self.path + '/')
                self.end_headers()
                return
            with open(filepath, 'rb') as f:
                content = f.read()
            self.send_response(200)
            if self.path.endswith('.html'):
                self.send_header('Content-type', 'text/html')
            elif self.path.endswith('.js'):
                self.send_header('Content-type', 'text/javascript')
            elif self.path.endswith('.css'):
                self.send_header('Content-type', 'text/css')
            elif self.path.endswith('.json'):
                self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(content)
        except FileNotFoundError:
            self.send_error(404, 'File not found')
        except Exception as e:
            self.send_error(500, str(e))

if __name__ == '__main__':
    os.chdir(os.path.dirname(__file__))  # stay in current folder
    print("Final dashboard live: http://localhost:9898")
    print("Open Safari → localhost:9898")
    HTTPServer(('localhost', 9898), DashboardHandler).serve_forever()