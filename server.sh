#!/home/tomh/sfs-it-console/venv/bin/python3

from http.server import HTTPServer, CGIHTTPRequestHandler

server_address = ("0.0.0.0", 8000)
httpd = HTTPServer(server_address, CGIHTTPRequestHandler)
httpd.serve_forever()

