"""POST /api/turn - one spoken turn: speech -> text -> translation -> speech in the speaker's voice."""

import os
import sys
import time
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(__file__))
import _sarvam as s  # noqa: E402


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            body = s.read_json(self)
            src, tgt = body["src"], body["tgt"]
            if src not in s.LANG_CODES or tgt not in s.LANG_CODES:
                return s.send_json(self, 400, {"error": "Unsupported language"})
            audio = s.b64decode(body["audio"])
            ref = s.b64decode(body["ref"]) if body.get("ref") else audio
            c = s.client()

            t0 = time.time()
            original = s.transcribe(c, audio, src)
            t1 = time.time()
            if not original.strip():
                return s.send_json(self, 200, {"empty": True})
            translated = s.translate(c, original, src, tgt, body.get("history", []))
            t2 = time.time()
            audio_b64, cloned = s.speak(c, translated, tgt, ref)
            t3 = time.time()

            s.send_json(self, 200, {
                "original": original,
                "translated": translated,
                "audio": audio_b64,
                "cloned": cloned,
                "timings": {"stt": t1 - t0, "translate": t2 - t1, "voice": t3 - t2, "total": t3 - t0},
            })
        except Exception as e:
            s.send_json(self, 500, {"error": f"{type(e).__name__}: {e}"})
