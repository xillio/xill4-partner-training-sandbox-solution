"""Stand-in for the Xill4 engine: HTTP on 8000, state in Mongo, files in /data/target.

Not Xill4. It exists so the provisioning and preflight harness can be exercised without
the private image; see README.md.
"""

import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

CONNECTION_STRING = os.environ["XILL4_DATABASE_CONNECTION_STRING"]
state = "no driver"

try:
    from pymongo import MongoClient
except ImportError:  # built with DEPS empty, for an air-gapped or proxied host
    pass
else:
    database = MongoClient(CONNECTION_STRING).get_default_database()
    database.projects.update_one({"_id": "standin"},
                                 {"$set": {"trainee": os.environ.get("TRAINEE", "")}},
                                 upsert=True)
    state = database.name

# Proves the mounted target is writable by whatever uid this image runs as -- the fact the
# preflight's volume check is really asking about.
Path("/data/target/.standin-started").write_text(f"{os.getuid()}\n", encoding="utf-8")


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200 if self.path in ("/", "/health") else 404)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(f"stand-in, not Xill4 (database: {state})\n".encode())

    def log_message(self, *args):
        pass


HTTPServer(("0.0.0.0", 8000), Handler).serve_forever()
