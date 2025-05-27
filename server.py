import os
import sys
import urllib.parse
from http.server import HTTPServer, SimpleHTTPRequestHandler

PORT = 8000

class CustomHTTPRequestHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        if path.endswith('/'):
            path = path[:-1]
        
        file_path = self.translate_path(path)
        if file_path.endswith('/'):
            file_path = file_path[:-1]
        if not os.path.isfile(file_path) and not path.endswith('/'):
            html_path = self.translate_path(path + '.html')
            if os.path.isfile(html_path):
                self.path = path + '.html'
        
        return SimpleHTTPRequestHandler.do_GET(self)

def run_server(port):
    web_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(web_dir)
    
    server_address = ('', port)
    httpd = HTTPServer(server_address, CustomHTTPRequestHandler)
    
    print(f"Server started at http://localhost:{port}")
    print(f"Serving files from: {web_dir}")
    print("Press Ctrl+C to stop the server")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        httpd.server_close()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        try:
            PORT = int(sys.argv[1])
        except ValueError:
            print(f"Invalid port: {sys.argv[1]}")
            sys.exit(1)
    
    run_server(PORT)