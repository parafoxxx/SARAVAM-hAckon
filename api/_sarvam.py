"""Shared Sarvam pipeline for the Vercel functions. Files starting with _ are not exposed as routes."""

import base64
import json
import os

from sarvamai import SarvamAI

LANG_CODES = {
    "Hindi": "hi-IN", "Tamil": "ta-IN", "Telugu": "te-IN", "Kannada": "kn-IN",
    "Malayalam": "ml-IN", "Bengali": "bn-IN", "Marathi": "mr-IN", "Gujarati": "gu-IN",
    "Punjabi": "pa-IN", "Odia": "od-IN", "Assamese": "as-IN", "English": "en-IN",
}


def client():
    return SarvamAI(api_subscription_key=os.environ["SARVAM_API_KEY"])


def transcribe(c, audio_bytes, lang):
    res = c.speech_to_text.transcribe(
        file=("speech.wav", audio_bytes, "audio/wav"),
        model="saaras:v3",
        language_code=LANG_CODES[lang],
    )
    return res.transcript


def translate(c, text, src, tgt, history):
    """Context-aware interpretation with Sarvam-105B; Sarvam-Translate as fallback."""
    context = "\n".join(f"Person {t['who']} ({t['src']}): {t['original']}" for t in history[-6:])
    system = (
        f"You are a live interpreter between two people. Translate the latest message from {src} "
        f"to {tgt} exactly, the way a native speaker would say it aloud. Keep meaning, gender, "
        "names, numbers and tone. Use the earlier conversation only to resolve who 'he', 'she', "
        f"'it' etc. refer to. Output only the {tgt} translation.\n\n"
        f"Earlier conversation:\n{context or '(none)'}"
    )
    try:
        res = c.chat.completions(
            model="sarvam-105b-conversations",
            messages=[{"role": "system", "content": system}, {"role": "user", "content": text}],
        )
        out = (res.choices[0].message.content or "").strip()
        if out:
            return out
    except Exception:
        pass
    res = c.text.translate(
        input=text,
        source_language_code=LANG_CODES[src],
        target_language_code=LANG_CODES[tgt],
        model="sarvam-translate:v1",
    )
    return res.translated_text


def speak(c, text, lang, ref_audio):
    """Speak text in the speaker's cloned voice; fall back to a stock Bulbul voice.

    Returns (base64 wav, cloned?)."""
    try:
        res = c.voice_cloning.convert(
            text=text[:1000],
            language_code=LANG_CODES[lang],
            ref_audio=("ref.wav", ref_audio, "audio/wav"),
            output_audio_codec="wav",
        )
        return res.audio_b64, True
    except Exception:
        res = c.text_to_speech.convert(text=text[:1500], language_code=LANG_CODES[lang], model="bulbul:v3")
        return res.audios[0], False


def summarize(c, turns, lang_a, lang_b):
    convo = "\n".join(f"Person {t['who']}: {t['original']}" for t in turns)
    prompt = (
        "Below is a conversation between two people who don't share a language.\n"
        "Write a short summary of what was discussed and any decisions, numbers, dates "
        f"or next steps. Write it twice: first in {lang_a}, then in {lang_b}. "
        "Use simple words and short bullet points. No preamble.\n\n" + convo
    )
    res = c.chat.completions(
        model="sarvam-105b-conversations",
        messages=[{"role": "user", "content": prompt}],
    )
    return res.choices[0].message.content


def b64decode(s):
    return base64.b64decode(s)


def read_json(handler):
    length = int(handler.headers.get("Content-Length", 0))
    return json.loads(handler.rfile.read(length) or b"{}")


def send_json(handler, status, payload):
    body = json.dumps(payload, ensure_ascii=False).encode()
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)
