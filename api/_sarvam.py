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

    Returns (translation, key_facts, english) where key_facts are short critical details in tgt."""
    english = english_reference(c, text, src)
    if tgt == "English" and english and not history:
        return english, [], english
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
        'Reply with JSON only: {"details": ["..."], "translation": "...", "key_facts": ["..."]}\n\n'
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
                return data["translation"].strip(), [str(f) for f in data.get("key_facts", [])][:4], english
        except Exception:
            if raw and "{" not in raw:
                return raw, [], english
    except Exception:
        pass
    res = c.text.translate(
        input=text,
        source_language_code=LANG_CODES[src],
        target_language_code=LANG_CODES[tgt],
        model="sarvam-translate:v1",
    )
    return res.translated_text, [], english


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
