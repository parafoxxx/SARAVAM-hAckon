"""Ek Awaaz - speak your language, they hear theirs, in your own voice."""

import base64
import hashlib
import html
import os
import time
from pathlib import Path

import streamlit as st
from sarvamai import SarvamAI

# Languages supported end to end: STT, translation and voice cloning.
LANGUAGES = {
    "Hindi": ("hi-IN", "हिन्दी"),
    "Tamil": ("ta-IN", "தமிழ்"),
    "Telugu": ("te-IN", "తెలుగు"),
    "Kannada": ("kn-IN", "ಕನ್ನಡ"),
    "Malayalam": ("ml-IN", "മലയാളം"),
    "Bengali": ("bn-IN", "বাংলা"),
    "Marathi": ("mr-IN", "मराठी"),
    "Gujarati": ("gu-IN", "ગુજરાતી"),
    "Punjabi": ("pa-IN", "ਪੰਜਾਬੀ"),
    "Odia": ("od-IN", "ଓଡ଼ିଆ"),
    "Assamese": ("as-IN", "অসমীয়া"),
    "English": ("en-IN", "English"),
}


def code(lang):
    return LANGUAGES[lang][0]


def load_api_key():
    env_file = Path(__file__).with_name(".env")
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())
    if os.environ.get("SARVAM_API_KEY"):
        return os.environ["SARVAM_API_KEY"]
    try:  # Streamlit Cloud deployments keep the key in st.secrets.
        return st.secrets["SARVAM_API_KEY"]
    except Exception:
        return None


@st.cache_resource
def get_client(api_key):
    return SarvamAI(api_subscription_key=api_key)


def transcribe(client, audio_bytes, lang):
    res = client.speech_to_text.transcribe(
        file=("speech.wav", audio_bytes, "audio/wav"),
        model="saaras:v3",
        language_code=code(lang),
    )
    return res.transcript


def translate(client, text, src, tgt, history):
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
        res = client.chat.completions(
            model="sarvam-105b-conversations",
            messages=[{"role": "system", "content": system}, {"role": "user", "content": text}],
        )
        out = (res.choices[0].message.content or "").strip()
        if out:
            return out
    except Exception:
        pass
    res = client.text.translate(
        input=text,
        source_language_code=code(src),
        target_language_code=code(tgt),
        model="sarvam-translate:v1",
    )
    return res.translated_text


def speak(client, text, lang, ref_audio):
    """Speak text in the speaker's cloned voice; fall back to a stock Bulbul voice."""
    try:
        res = client.voice_cloning.convert(
            text=text[:1000],
            language_code=code(lang),
            ref_audio=("ref.wav", ref_audio, "audio/wav"),
            output_audio_codec="wav",
        )
        return base64.b64decode(res.audio_b64), True
    except Exception:
        res = client.text_to_speech.convert(text=text[:1500], language_code=code(lang), model="bulbul:v3")
        return base64.b64decode(res.audios[0]), False


def summarize(client, turns, lang_a, lang_b):
    convo = "\n".join(f"Person {t['who']}: {t['original']}" for t in turns)
    prompt = (
        "Below is a conversation between two people who don't share a language.\n"
        "Write a short summary of what was discussed and any decisions, numbers, dates "
        f"or next steps. Write it twice: first in {lang_a}, then in {lang_b}. "
        "Use simple words and short bullet points. No preamble.\n\n" + convo
    )
    res = client.chat.completions(
        model="sarvam-105b-conversations",
        messages=[{"role": "user", "content": prompt}],
    )
    return res.choices[0].message.content


# ---------- Page ----------

st.set_page_config(page_title="Ek Awaaz · One Voice", page_icon="🗣️", layout="wide")
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;800&family=Noto+Sans:wght@400;600&display=swap');
    :root {
      --saffron: #ff7a1a; --saffron-soft: #fff3ea;
      --indigo: #4f46e5; --indigo-soft: #eef0ff;
      --ink: #1a1a2e; --muted: #6b7280; --line: #ececf3;
    }
    html, body, [class*="css"], .stMarkdown { font-family: 'Plus Jakarta Sans', 'Noto Sans', sans-serif; }
    #MainMenu, footer, header [data-testid="stToolbar"] { visibility: hidden; }
    .block-container { padding-top: 1.6rem; max-width: 1100px; }

    .hero { text-align: center; padding: 28px 16px 22px; border-radius: 24px;
      background: radial-gradient(circle at 15% 20%, #ffe2cc 0, transparent 45%),
                  radial-gradient(circle at 85% 80%, #dcdcff 0, transparent 45%), #fffdfb;
      border: 1px solid var(--line); margin-bottom: 22px; }
    .hero h1 { font-size: 2.7rem; font-weight: 800; margin: 0; color: var(--ink); letter-spacing: -1px; }
    .hero h1 .dev { background: linear-gradient(90deg, var(--saffron), var(--indigo));
      -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    .hero p { color: var(--muted); font-size: 1.08rem; margin: 8px 0 14px; }
    .chips { display: flex; gap: 8px; justify-content: center; flex-wrap: wrap; }
    .chip { font-size: 0.78rem; padding: 5px 12px; border-radius: 999px; background: white;
      border: 1px solid var(--line); color: var(--ink); }

    .card-head { display: flex; align-items: center; gap: 12px; margin-bottom: 6px; }
    .avatar { width: 44px; height: 44px; border-radius: 14px; display: grid; place-items: center;
      color: white; font-weight: 800; font-size: 1.2rem; }
    .avatar.a { background: linear-gradient(135deg, #ff9a4d, var(--saffron)); }
    .avatar.b { background: linear-gradient(135deg, #7c74ff, var(--indigo)); }
    .who { font-weight: 800; font-size: 1.05rem; color: var(--ink); }
    .native { color: var(--muted); font-size: 0.9rem; }
    .pill { display: inline-block; font-size: 0.75rem; padding: 3px 10px; border-radius: 999px; margin: 4px 0 2px; }
    .pill.on { background: #e7f8ee; color: #137a3f; }
    .pill.off { background: #f4f4f7; color: var(--muted); }

    .now { border-radius: 20px; padding: 20px 24px; margin: 18px 0 8px; color: white;
      background: linear-gradient(120deg, var(--saffron), #e0458f 50%, var(--indigo)); }
    .now .label { font-size: 0.78rem; opacity: 0.85; text-transform: uppercase; letter-spacing: 1px; }
    .now .text { font-size: 1.6rem; font-weight: 600; line-height: 1.35; margin: 6px 0; font-family: 'Noto Sans', sans-serif; }
    .now .orig { font-size: 0.92rem; opacity: 0.85; }

    .row { display: flex; margin: 10px 0; }
    .row.b { justify-content: flex-end; }
    .bubble { max-width: 78%; padding: 12px 16px; border-radius: 18px; border: 1px solid var(--line); }
    .row.a .bubble { background: var(--saffron-soft); border-top-left-radius: 4px; }
    .row.b .bubble { background: var(--indigo-soft); border-top-right-radius: 4px; }
    .bubble .orig { font-size: 0.85rem; color: var(--muted); }
    .bubble .trans { font-size: 1.12rem; color: var(--ink); margin-top: 4px; font-family: 'Noto Sans', sans-serif; }
    .bubble .meta { font-size: 0.72rem; color: var(--muted); margin-top: 6px; }

    .empty { text-align: center; color: var(--muted); padding: 26px; border: 2px dashed var(--line); border-radius: 18px; }
    .foot { text-align: center; color: var(--muted); font-size: 0.8rem; margin-top: 30px; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero">
      <h1><span class="dev">एक आवाज़</span> · Ek Awaaz</h1>
      <p>Speak your language. They hear theirs, <b>in your own voice.</b></p>
      <div class="chips">
        <span class="chip">🎧 Saaras v3 · speech-to-text</span>
        <span class="chip">🧠 Sarvam-105B · context-aware interpreting</span>
        <span class="chip">🧬 Voice Cloning · cross-lingual</span>
        <span class="chip">🌏 12 Indian languages</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

api_key = load_api_key()
if not api_key:
    st.error("SARVAM_API_KEY is not set. Add it to .env (local) or Streamlit secrets (cloud).")
    st.stop()
client = get_client(api_key)

ss = st.session_state
ss.setdefault("turns", [])
ss.setdefault("voices", {})  # person -> first clip, used as the cloning reference
ss.setdefault("seen", set())
ss.setdefault("latest", None)
ss.setdefault("round", 0)  # bumped on reset to clear the mic widgets

names = list(LANGUAGES)
people = {}
col_a, col_b = st.columns(2, gap="large")
for person, col, default in (("A", col_a, "Hindi"), ("B", col_b, "Tamil")):
    with col, st.container(border=True):
        lang = ss.get(f"lang_{person}", default)
        st.markdown(
            f"""<div class="card-head"><div class="avatar {person.lower()}">{person}</div>
            <div><div class="who">Person {person}</div>
            <div class="native">speaks {LANGUAGES[lang][1]}</div></div></div>""",
            unsafe_allow_html=True,
        )
        lang = st.selectbox("Language", names, index=names.index(default), key=f"lang_{person}",
                            label_visibility="collapsed")
        if person in ss.voices:
            st.markdown('<span class="pill on">🧬 Voice captured · replies sound like you</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="pill off">Your first message becomes your voice (speak 5+ sec)</span>',
                        unsafe_allow_html=True)
        clip = st.audio_input(f"Tap to speak", key=f"mic_{person}_{ss['round']}", label_visibility="collapsed")
        people[person] = (lang, clip)

lang_a, lang_b = people["A"][0], people["B"][0]

for person, (lang, clip) in people.items():
    if clip is None:
        continue
    audio = clip.getvalue()
    digest = hashlib.md5(audio).hexdigest()
    if digest in ss.seen:
        continue
    ss.seen.add(digest)

    other = "B" if person == "A" else "A"
    other_lang = people[other][0]
    ss.voices.setdefault(person, audio)

    with st.status(f"Person {person}: {lang} → {other_lang}", expanded=True) as status:
        try:
            t0 = time.time()
            original = transcribe(client, audio, lang)
            t1 = time.time()
            if not original.strip():
                status.update(label="Didn't catch that. Try again a little louder.", state="error")
                continue
            st.write(f"🎧 Heard ({t1 - t0:.1f}s): {original}")
            translated = translate(client, original, lang, other_lang, ss.turns)
            t2 = time.time()
            st.write(f"🧠 Interpreted ({t2 - t1:.1f}s): {translated}")
            speech, cloned = speak(client, translated, other_lang, ss.voices[person])
            t3 = time.time()
            st.write(f"{'🧬 Spoken in Person ' + person + chr(39) + 's voice' if cloned else '🔈 Spoken (standard voice)'} ({t3 - t2:.1f}s)")
            status.update(label=f"Person {person}: {lang} → {other_lang} · done in {t3 - t0:.1f}s",
                          state="complete", expanded=False)
        except Exception as e:
            status.update(label=f"Something went wrong: {e}", state="error")
            continue

    ss.turns.append({"who": person, "original": original, "translated": translated, "src": lang,
                     "tgt": other_lang, "cloned": cloned, "secs": t3 - t0})
    ss.latest = speech

if ss.turns:
    last = ss.turns[-1]
    voice = f"in Person {last['who']}'s voice" if last["cloned"] else "standard voice"
    st.markdown(
        f"""<div class="now"><div class="label">Now speaking · {last['tgt']} · {voice}</div>
        <div class="text">{html.escape(last['translated'])}</div>
        <div class="orig">Person {last['who']} said in {last['src']}: {html.escape(last['original'])}</div></div>""",
        unsafe_allow_html=True,
    )
    if ss.latest:
        st.audio(ss.latest, format="audio/wav", autoplay=True)

    st.markdown("#### Conversation")
    for t in reversed(ss.turns):
        side = t["who"].lower()
        voice = "🧬 cloned voice" if t["cloned"] else "🔈 standard voice"
        st.markdown(
            f"""<div class="row {side}"><div class="bubble">
            <div class="orig">Person {t['who']} · {t['src']}: {html.escape(t['original'])}</div>
            <div class="trans">{html.escape(t['translated'])}</div>
            <div class="meta">→ {t['tgt']} · {voice} · {t['secs']:.1f}s</div></div></div>""",
            unsafe_allow_html=True,
        )

    c1, c2 = st.columns(2)
    if c1.button("📝 Summarize in both languages", use_container_width=True, type="primary"):
        with st.spinner("Sarvam-105B is summarizing..."):
            ss.summary = summarize(client, ss.turns, lang_a, lang_b)
    if c2.button("🔄 New conversation", use_container_width=True):
        next_round = ss["round"] + 1
        for k in ("turns", "voices", "seen", "latest", "summary"):
            ss.pop(k, None)
        ss["round"] = next_round
        st.rerun()
    if ss.get("summary"):
        with st.container(border=True):
            st.markdown("##### 📝 Conversation summary")
            st.markdown(ss.summary)
else:
    st.markdown(
        """<div class="empty">👆 Pick a language for each person, then tap the mic and speak.<br>
        The other person hears it in their language, <b>in your voice</b>.</div>""",
        unsafe_allow_html=True,
    )

st.markdown('<div class="foot">Built with Sarvam AI · Saaras · Sarvam-105B · Voice Cloning · Bulbul</div>',
            unsafe_allow_html=True)
