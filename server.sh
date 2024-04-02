#!/home/tomh/sfs-it-console/venv/bin/python3
import os,sys
from http.server import HTTPServer, CGIHTTPRequestHandler

os.chdir(os.path.dirname(sys.argv[0]))


server_address = ("0.0.0.0", 8000)
httpd = HTTPServer(server_address, CGIHTTPRequestHandler)
httpd.serve_forever()

