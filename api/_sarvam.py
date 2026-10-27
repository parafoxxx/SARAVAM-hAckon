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


CODE_LANGS = {v: k for k, v in LANG_CODES.items()}

SCENARIOS = {
    "general": "an everyday conversation",
    "doctor": "a doctor-patient consultation. Medicine names, doses, timings, symptoms and allergies must be exact",
    "police": "a citizen getting help at a police station. Names, places, times and incident details must be exact",
    "rent": "a tenant and landlord discussing renting a home. Rent, deposit, dates and conditions must be exact",
    "bank": "a customer at a bank. Amounts, account details, documents and deadlines must be exact",
    "market": "a customer and a shopkeeper. Items, quantities and prices must be exact",
}


def client():
    return SarvamAI(api_subscription_key=os.environ["SARVAM_API_KEY"])


def transcribe(c, audio_bytes, lang):
    """Returns (transcript, language name). lang "Auto" lets Saaras detect the language."""
    res = c.speech_to_text.transcribe(
        file=("speech.wav", audio_bytes, "audio/wav"),
        model="saaras:v3",
        language_code=LANG_CODES.get(lang, "unknown"),
    )
    detected = lang if lang in LANG_CODES else CODE_LANGS.get(res.language_code or "", "Hindi")
    return res.transcript, detected


def _parse_json(raw):
    start, end = raw.find("{"), raw.rfind("}")
    return json.loads(raw[start:end + 1])


def english_reference(c, text, src):
    """Sarvam-Translate's English rendering: very faithful on instructions, used to anchor 105B."""
    if src == "English":
        return text
    try:
        res = c.text.translate(input=text, source_language_code=LANG_CODES[src],
                               target_language_code="en-IN", model="sarvam-translate:v1")
        return res.translated_text
    except Exception:
        return ""


def translate(c, text, src, tgt, history, scenario="general"):
    """Interpretation in two passes: Sarvam-Translate gives a faithful English reference, then
    Sarvam-105B writes the final translation using it plus the conversation context (for gender
    and pronouns). In testing each model alone dropped details the pair keeps.

    Returns (translation, key_facts, english, extras) where key_facts are short critical details in tgt."""
    english = english_reference(c, text, src)
    if tgt == "English" and english and not history:
        return english, [], english, NO_EXTRAS
    context = "\n".join(f"Person {t['who']} ({t['src']}): {t['original']}" for t in history[-6:])
    system = (
        f"You are a live interpreter in {SCENARIOS.get(scenario, SCENARIOS['general'])}. "
        f"Translate the latest {src} message into {tgt} faithfully, the way a native speaker would say it "
        "aloud. The message is a raw speech transcript and may lack punctuation. An English reference "
        "translation is provided to help you get the meaning exactly right: every instruction, number, "
        "timing and condition in it must appear in your translation. Never add or drop anything. Use the "
        "earlier conversation to get gender and who 'he', 'she', 'it' refer to right.\n"
        "Work from the original message first (the reference can miss things too): before translating, "
        "list in English every separate detail it contains, including conditions like before/after food.\n"
        "Also list the critical facts in the message that must not be misunderstood (medicines, doses, "
        "amounts, prices, dates, times, places, warnings), each as a very short phrase in "
        f"{tgt}. Use an empty list if there are none.\n"
        "Also decide:\n"
        "- command: ONLY if the speaker is talking to the app itself by name, 'Ek Awaaz' (e.g. 'Ek Awaaz, "
        "summary banao'), one of \"summarize\", \"share\" (send on WhatsApp), \"reset\" (new conversation), "
        "\"table_mode\"; otherwise null.\n"
        "- emergency: true only if the message describes an emergency happening now (unconscious, chest "
        "pain, can't breathe, heavy bleeding, accident, fire, assault); else false.\n"
        "- actions: up to 3 one-tap actions the message implies, else []. Use "
        '{"type": "reminder", "title": "<short>", "details": "<what and when>"} for medicines, appointments '
        'or deadlines; {"type": "map", "label": "<short>", "query": "<place or address, in English>"} when a place is '
        'named; {"type": "call", "label": "<short>", "number": "<digits>"} only when a phone number is said. '
        f"Write title, details and label in {tgt}.\n"
        'Reply with JSON only: {"details": ["..."], "translation": "...", "key_facts": ["..."], '
        '"command": null, "emergency": false, "actions": []}\n\n'
        f"Earlier conversation:\n{context or '(none)'}"
    )
    user = f"{src} message: {text}" + (f"\nEnglish reference: {english}" if english else "")
    try:
        res = c.chat.completions(
            model="sarvam-105b-conversations",
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        )
        raw = (res.choices[0].message.content or "").strip()
        try:
            data = _parse_json(raw)
            if data.get("translation"):
                extras = {
                    "command": data.get("command") if data.get("command") in COMMANDS else None,
                    "emergency": data.get("emergency") is True,
                    "actions": [a for a in data.get("actions") or [] if isinstance(a, dict)][:3],
                }
                return data["translation"].strip(), [str(f) for f in data.get("key_facts", [])][:4], english, extras
        except Exception:
            if raw and "{" not in raw:
                return raw, [], english, NO_EXTRAS
    except Exception:
        pass
    res = c.text.translate(
        input=text,
        source_language_code=LANG_CODES[src],
        target_language_code=LANG_CODES[tgt],
        model="sarvam-translate:v1",
    )
    return res.translated_text, [], english, NO_EXTRAS


COMMANDS = ("summarize", "share", "reset", "table_mode")

WAKE_WORDS = ("आवाज", "अवाज", "awaaz", "awaz", "aawaz", "avaaz", "awaj", "आवाज़", "ஆவாஸ்", "ஆவாஜ்")
COMMAND_WORDS = [  # checked in order: "share" before "summarize", since "summary bhejo" means share
    ("share", ("whats", "wats", "watts", "वाट्स", "व्हाट्स", "वॉट्स", "व्हॉट्स", "वट्स", "ट्सऐप", "ट्सएप", "ट्सअप",
               "वाट्सप", "भेज", "bhej", "send", "share", "शेयर", "வாட்ஸ்", "அனுப்பு")),
    ("summarize", ("summary", "समरी", "सारांश", "सार", "summarize", "summarise", "சுருக்க")),
    ("table_mode", ("table", "टेबल", "டேபிள்")),
    ("reset", ("new conversation", "नया", "नई", "naya", "reset", "रीसेट", "शुरू से", "புதிய")),
]


def detect_command(transcript):
    """Wake-word voice commands ("Ek Awaaz, summary banao"), matched in code so they never get translated."""
    t = transcript.lower().replace("़", "")
    if not any(w.replace("़", "") in t for w in WAKE_WORDS):
        return None
    for command, words in COMMAND_WORDS:
        if any(w.lower() in t for w in words):
            return command
    return None
NO_EXTRAS = {"command": None, "emergency": False, "actions": []}


def action_link(a):
    """Turn a detected action into (button label, URL)."""
    from urllib.parse import quote, urlencode

    kind = a.get("type")
    if kind == "reminder":
        q = urlencode({"action": "TEMPLATE", "text": a.get("title", "Reminder"), "details": a.get("details", "")})
        return f"📅 {a.get('title', 'Add reminder')}", f"https://calendar.google.com/calendar/render?{q}"
    if kind == "map" and a.get("query"):
        return f"📍 {a.get('label') or a['query']}", f"https://www.google.com/maps/search/?api=1&query={quote(a['query'])}"
    if kind == "call" and a.get("number"):
        digits = "".join(ch for ch in str(a["number"]) if ch.isdigit() or ch == "+")
        return f"📞 {a.get('label') or digits}", f"tel:{digits}"
    return None


def speak(c, text, lang, ref_audio, ref_text=None):
    """Speak text in the speaker's cloned voice; fall back to a stock Bulbul voice.

    ref_text (the reference clip's transcript) saves the API from re-transcribing it.
    Returns (base64 wav, cloned?)."""
    try:
        extra = {"ref_text": ref_text[:500]} if ref_text else {}
        res = c.voice_cloning.convert(
            text=text[:1000],
            language_code=LANG_CODES[lang],
            ref_audio=("ref.wav", ref_audio, "audio/wav"),
            output_audio_codec="wav",
            **extra,
        )
        return res.audio_b64, True
    except Exception:
        res = c.text_to_speech.convert(text=text[:1500], language_code=LANG_CODES[lang], model="bulbul:v3")
        return res.audios[0], False


def read_document(c, file_bytes, filename, lang):
    """Sarvam Document Intelligence (Sarvam Vision): PDF/PNG/JPG -> markdown text."""
    import io
    import tempfile
    import zipfile

    doc_lang = "or-IN" if lang == "Odia" else LANG_CODES.get(lang, "en-IN")
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, os.path.basename(filename) or "document.png")
        with open(src, "wb") as f:
            f.write(file_bytes)
        job = c.document_intelligence.create_job(language=doc_lang, output_format="md")
        job.upload_file(src)
        job.start()
        job.wait_until_complete(poll_interval=1.0, timeout=120)
        out = job.download_output(os.path.join(tmp, "out.zip"))
        with open(out, "rb") as f:
            data = f.read()
    if data[:2] == b"PK":
        z = zipfile.ZipFile(io.BytesIO(data))
        return "\n".join(z.read(n).decode("utf-8", "replace") for n in z.namelist() if n.endswith(".md")).strip()
    return data.decode("utf-8", "replace").strip()


def explain_document(c, text, tgt, scenario="general"):
    """Sarvam-105B explains a document aloud to someone who can't read it. Returns (explanation, key_facts)."""
    system = (
        f"Someone in {SCENARIOS.get(scenario, SCENARIOS['general'])} has been handed the document below and "
        f"cannot read it. Explain it to them in {tgt}, in simple spoken words, as if reading it out and "
        "explaining it: what it is and exactly what they must do (every medicine, dose, timing, amount, date, "
        "condition and warning). Do not add anything that is not in the document. At most 6 short sentences.\n"
        f"Also list the critical facts as very short phrases in {tgt}.\n"
        'Reply with JSON only: {"explanation": "...", "key_facts": ["..."]}'
    )
    res = c.chat.completions(
        model="sarvam-105b-conversations",
        messages=[{"role": "system", "content": system}, {"role": "user", "content": text[:6000]}],
    )
    raw = (res.choices[0].message.content or "").strip()
    try:
        data = _parse_json(raw)
        return data["explanation"].strip(), [str(f) for f in data.get("key_facts", [])][:5]
    except Exception:
        return raw, []


SUMMARY_FOCUS = {
    "doctor": "Cover: symptoms, diagnosis, each medicine with dose and timing, warning signs, follow-up date.",
    "police": "Cover: what happened, when and where, people involved, what the police will do, reference numbers.",
    "rent": "Cover: rent, deposit, move-in date, rules and conditions, what each side agreed to do.",
    "bank": "Cover: what the customer wants, documents needed, amounts, deadlines, next steps.",
    "market": "Cover: items, quantities, agreed prices and total.",
}


def summarize(c, turns, lang_a, lang_b, scenario="general"):
    convo = "\n".join(f"Person {t['who']}: {t['original']}" for t in turns)
    prompt = (
        f"Below is {SCENARIOS.get(scenario, SCENARIOS['general']).split('.')[0]} between two people "
        "who don't share a language.\n"
        "Write a short summary of what was discussed and any decisions, numbers, dates "
        f"or next steps. {SUMMARY_FOCUS.get(scenario, '')} Write it twice: first in {lang_a}, then in {lang_b}. "
        "Use simple words and short bullet points. No preamble. Only include what was actually said: "
        "never invent medicines, doses or details. Skip any point that was not discussed.\n\n" + convo
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
