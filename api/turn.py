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
            if (src != "Auto" and src not in s.LANG_CODES) or tgt not in s.LANG_CODES:
                return s.send_json(self, 400, {"error": "Unsupported language"})
            audio = s.b64decode(body["audio"])
            ref = s.b64decode(body["ref"]) if body.get("ref") else audio
            c = s.client()

            t0 = time.time()
            original, src = s.transcribe(c, audio, src)
            t1 = time.time()
            if not original.strip():
                return s.send_json(self, 200, {"empty": True})
            translated, key_facts, english, _extras = s.translate(c, original, src, tgt, body.get("history", []),
                                                body.get("scenario", "general"))
            t2 = time.time()
            # The first clip is its own reference, so its transcript is the reference text.
            ref_text = body.get("refText") or (original if not body.get("ref") or body["ref"] == body["audio"] else None)
            audio_b64, cloned = s.speak(c, translated, tgt, ref, ref_text)
            t3 = time.time()

            s.send_json(self, 200, {
                "original": original,
                "src": src,
                "translated": translated,
                "key_facts": key_facts,
                "english": english,
                "audio": audio_b64,
                "cloned": cloned,
                "timings": {"stt": t1 - t0, "translate": t2 - t1, "voice": t3 - t2, "total": t3 - t0},
            })
        except Exception as e:
            s.send_json(self, 500, {"error": f"{type(e).__name__}: {e}"})
