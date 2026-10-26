"""POST /api/summary - bilingual summary of the conversation with Sarvam-105B."""

import os
import sys
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(__file__))
import _sarvam as s  # noqa: E402


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            body = s.read_json(self)
            summary = s.summarize(s.client(), body["turns"], body["langA"], body["langB"])
            s.send_json(self, 200, {"summary": summary})
        except Exception as e:
            s.send_json(self, 500, {"error": f"{type(e).__name__}: {e}"})
