#!/usr/bin/env python3
"""
Simple HTTP server for JEXI frontend
"""
import http.server
import socketserver
import os
import sys

# Change to the frontend directory
frontend_path = os.path.join(os.path.dirname(__file__), '..', 'frontend')
if os.path.exists(frontend_path):
    os.chdir(frontend_path)
else:
    print(f"❌ Frontend directory not found: {frontend_path}")
    print("Please ensure the frontend directory exists")
    sys.exit(1)

PORT = 8080

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

if __name__ == "__main__":
    Handler = MyHTTPRequestHandler
    
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"🚀 JEXI Frontend Server running on http://localhost:{PORT}")
        print(f"📁 Serving files from: {os.getcwd()}")
        print("🌐 Open your browser and navigate to http://localhost:8000")
        print("⚠️  Note: This is a development server. For production, use a proper web server.")
        print("🛑 Press Ctrl+C to stop the server")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n🛑 Server stopped by user")
            sys.exit(0)
