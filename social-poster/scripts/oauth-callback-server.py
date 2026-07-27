#!/usr/bin/env python3
"""OAuth callback server — captures redirect code to secure path.
Usage: python3 oauth-callback-server.py <port>
       tailscale serve --bg --set-path /oauth-callback <port>
"""
import http.server, urllib.parse, sys, os, secrets

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 19876
# Write to user's .social-poster dir (chmod 600) instead of world-readable /tmp
OUT_DIR = os.path.join(os.path.expanduser("~"), ".social-poster")
os.makedirs(OUT_DIR, exist_ok=True)

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        code = params.get("code", [None])[0]
        if code:
            # Validate code format (alphanumeric + common OAuth chars)
            if len(code) > 2000 or not all(c.isalnum() or c in "-._~" for c in code):
                self.wfile.write(b"<h2>Invalid code format</h2>")
                print("\n⚠️  Rejected malformed code", flush=True)
                return
            # Atomic write: tempfile → rename
            tmp = os.path.join(OUT_DIR, f".code_{secrets.token_hex(4)}")
            with open(tmp, "w") as f:
                f.write(code)
            os.chmod(tmp, 0o600)
            os.replace(tmp, os.path.join(OUT_DIR, "last_code.txt"))
            self.wfile.write(f"<h2>✅ Code captured</h2><p><code>{code[:50]}...</code></p>".encode())
            print(f"\n✅ Code captured: {code[:50]}...", flush=True)
        else:
            self.wfile.write(b"<h2>No code found</h2>")
    def log_message(self, *a): pass

http.server.HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
