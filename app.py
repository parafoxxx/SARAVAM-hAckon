"""Ek Awaaz - speak your language, they hear theirs, in your own voice (Streamlit app)."""

import hashlib
import html
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

import streamlit as st

# The Sarvam pipeline lives in api/_sarvam.py, shared with the serverless version.
sys.path.insert(0, str(Path(__file__).with_name("api")))
import _sarvam as sarvam  # noqa: E402

NATIVE = {
    "Hindi": "हिन्दी", "Tamil": "தமிழ்", "Telugu": "తెలుగు", "Kannada": "ಕನ್ನಡ", "Malayalam": "മലയാളം",
    "Bengali": "বাংলা", "Marathi": "मराठी", "Gujarati": "ગુજરાતી", "Punjabi": "ਪੰਜਾਬੀ", "Odia": "ଓଡ଼ିଆ",
    "Assamese": "অসমীয়া", "English": "English",
}
SCENARIOS = {"general": "💬 General", "doctor": "🏥 Doctor", "police": "👮 Police",
             "rent": "🏠 Renting", "bank": "🏦 Bank", "market": "🛒 Market"}
AUTO = "✨ Auto-detect"


def load_api_key():
    env_file = Path(__file__).with_name(".env")
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())
    if not os.environ.get("SARVAM_API_KEY"):
        try:  # Streamlit Cloud deployments keep the key in st.secrets.
            os.environ["SARVAM_API_KEY"] = st.secrets["SARVAM_API_KEY"]
        except Exception:
            return None
    return os.environ["SARVAM_API_KEY"]


@st.cache_resource
def get_client(_api_key):
    return sarvam.client()


COMMAND_LABELS = {"summarize": "summarize", "share": "summarize & share on WhatsApp",
                  "reset": "new conversation", "table_mode": "table mode"}


def reset_conversation():
    ss = st.session_state
    next_round = ss["round"] + 1
    for k in ("turns", "voices", "seen", "latest", "summary", "detected", "share_now"):
        ss.pop(k, None)
    ss["round"] = next_round
    st.rerun()


def esc(s):
    return html.escape(str(s))


def facts_html(facts):
    if not facts:
        return ""
    return '<div class="facts">' + "".join(f'<span class="fact">🚨 {esc(f)}</span>' for f in facts) + "</div>"


# ---------- Page ----------

st.set_page_config(page_title="Ek Awaaz · One Voice", page_icon="🗣️", layout="wide")
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;800&family=Noto+Sans:wght@400;600&display=swap');
    :root {
      --saffron: #ff7a1a; --saffron-soft: #fff3ea; --saffron-line: #ffd9bd;
      --indigo: #4f46e5; --indigo-soft: #eef0ff; --indigo-line: #d4d6ff;
      --ink: #1a1a2e; --muted: #6b7280; --line: #ececf3; --alert: #b42318; --alert-soft: #fff0ee;
    }
    html, body, [class*="css"], .stMarkdown { font-family: 'Plus Jakarta Sans', 'Noto Sans', sans-serif; }
    #MainMenu, footer, header [data-testid="stToolbar"] { visibility: hidden; }
    .block-container { padding-top: 1.4rem; max-width: 1100px; }

    .hero { text-align: center; padding: 28px 16px 22px; border-radius: 24px;
      background: radial-gradient(circle at 12% 20%, #ffe2cc 0, transparent 45%),
                  radial-gradient(circle at 88% 80%, #dcdcff 0, transparent 45%), #fffdfb;
      border: 1px solid var(--line); margin-bottom: 14px; }
    .hero h1 { font-size: clamp(2rem, 6vw, 2.8rem); font-weight: 800; margin: 0; color: var(--ink); letter-spacing: -1px; padding: 0; }
    .hero h1 .dev { background: linear-gradient(90deg, var(--saffron), var(--indigo));
      -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent; }
    .hero p { color: var(--muted); font-size: 1.08rem; margin: 8px 0 14px; }
    .chips { display: flex; gap: 8px; justify-content: center; flex-wrap: wrap; }
    .chip { font-size: 0.78rem; padding: 5px 12px; border-radius: 999px; background: white; border: 1px solid var(--line); color: var(--ink); }

    .st-key-card_A { border-top: 4px solid var(--saffron) !important; }
    .st-key-card_B { border-top: 4px solid var(--indigo) !important; transition: transform .5s; }
    .table-mode .st-key-card_B, body:has(.table-on) .st-key-card_B { transform: rotate(180deg); }
    .card-head { display: flex; align-items: center; gap: 12px; margin-bottom: 4px; }
    .avatar { width: 44px; height: 44px; border-radius: 14px; display: grid; place-items: center;
      color: white; font-weight: 800; font-size: 1.2rem; flex: none; }
    .avatar.a { background: linear-gradient(135deg, #ff9a4d, var(--saffron)); }
    .avatar.b { background: linear-gradient(135deg, #7c74ff, var(--indigo)); }
    .who { font-weight: 800; font-size: 1.05rem; color: var(--ink); }
    .native { color: var(--muted); font-size: 0.9rem; font-family: 'Noto Sans', sans-serif; }
    .pill { display: inline-block; font-size: 0.75rem; padding: 3px 10px; border-radius: 999px; margin: 2px 0; }
    .pill.on { background: #e7f8ee; color: #137a3f; }
    .pill.off { background: #f4f4f7; color: var(--muted); }

    .inbox { border-radius: 14px; padding: 12px 14px; margin: 6px 0; font-family: 'Noto Sans', sans-serif; }
    .inbox.a { background: var(--saffron-soft); } .inbox.b { background: var(--indigo-soft); }
    .inbox .from { font-size: .74rem; color: var(--muted); }
    .inbox .msg { font-size: 1.2rem; font-weight: 600; margin-top: 3px; line-height: 1.35; color: var(--ink); }

    .facts { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 8px; }
    .fact { font-size: .8rem; font-weight: 600; padding: 4px 10px; border-radius: 8px; background: var(--alert-soft);
      color: var(--alert); border: 1px solid #ffd0ca; font-family: 'Noto Sans', sans-serif; }
    .now .fact { background: rgba(255,255,255,.95); border-color: transparent; }

    .now { border-radius: 20px; padding: 20px 24px; margin: 14px 0 8px; color: white;
      background: linear-gradient(120deg, var(--saffron), #e0458f 50%, var(--indigo)); }
    .now .label { font-size: 0.76rem; opacity: 0.88; text-transform: uppercase; letter-spacing: 1px; }
    .now .text { font-size: clamp(1.3rem, 4vw, 1.6rem); font-weight: 600; line-height: 1.35; margin: 6px 0; font-family: 'Noto Sans', sans-serif; }
    .now .orig { font-size: 0.92rem; opacity: 0.88; font-family: 'Noto Sans', sans-serif; margin-top: 6px; }
    .now .en { font-size: 0.88rem; opacity: 0.9; font-style: italic; margin-top: 4px; }

    .row { display: flex; margin: 10px 0; } .row.b { justify-content: flex-end; }
    .bubble { max-width: 80%; padding: 12px 16px; border-radius: 18px; border: 1px solid var(--line); }
    .row.a .bubble { background: var(--saffron-soft); border-color: var(--saffron-line); border-top-left-radius: 4px; }
    .row.b .bubble { background: var(--indigo-soft); border-color: var(--indigo-line); border-top-right-radius: 4px; }
    .bubble .orig { font-size: 0.85rem; color: var(--muted); font-family: 'Noto Sans', sans-serif; }
    .bubble .trans { font-size: 1.1rem; color: var(--ink); margin-top: 4px; font-family: 'Noto Sans', sans-serif; }
    .bubble .en { font-size: .82rem; color: var(--muted); margin-top: 6px; font-style: italic; }
    .bubble .meta { font-size: 0.72rem; color: var(--muted); margin-top: 6px; }

    .voicecmd { font-size: .86rem; color: var(--ink); background: #fffaf3; border: 1px dashed var(--saffron-line);
      border-radius: 14px; padding: 10px 14px; margin: 4px 0 12px; line-height: 1.9; }
    .voicecmd span { display: inline-block; background: white; border: 1px solid var(--line); border-radius: 999px;
      padding: 1px 10px; margin: 0 4px; font-family: 'Noto Sans', sans-serif; }
    .empty { text-align: center; color: var(--muted); padding: 24px; border: 2px dashed var(--line); border-radius: 18px; margin-top: 10px; }
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
        <span class="chip">🎧 Saaras v3 · auto-detects language</span>
        <span class="chip">🧠 Sarvam-105B · context-aware interpreting</span>
        <span class="chip">🧬 Voice Cloning · cross-lingual</span>
        <span class="chip">🚨 Critical-fact alerts</span>
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
ss.setdefault("voices", {})  # person -> (first clip, its transcript), used as the cloning reference
ss.setdefault("seen", set())
ss.setdefault("latest", None)
ss.setdefault("round", 0)  # bumped on reset to clear the mic widgets
ss.setdefault("detected", {})  # person -> language detected while on auto

if ss.pop("_pending_table", False):  # set by the "table mode" voice command
    ss["table_mode"] = True

top_l, top_r = st.columns([3, 1], vertical_alignment="center")
with top_l:
    scenario = st.pills("Scenario", list(SCENARIOS), default="doctor", format_func=SCENARIOS.get,
                        label_visibility="collapsed", key="scenario") or "general"
with top_r:
    table_mode = st.toggle("📱 Face-to-face table mode", key="table_mode")
if table_mode:
    st.markdown('<span class="table-on"></span>', unsafe_allow_html=True)

st.markdown(
    """<div class="voicecmd">🎙️ <b>Voice commands</b>: tap any mic and say
    <span>“Ek Awaaz, summary banao”</span><span>“Ek Awaaz, WhatsApp pe bhejo”</span>
    <span>“Ek Awaaz, table mode”</span><span>“Ek Awaaz, naya conversation”</span>
    · 🚑 emergencies and 📅 📍 actions are detected automatically</div>""",
    unsafe_allow_html=True,
)

options = [AUTO] + list(NATIVE)
people = {}
cols = st.columns(1 if table_mode else 2, gap="large")
for i, (person, default) in enumerate((("A", AUTO), ("B", "Tamil"))):
    col = cols[0] if table_mode else cols[i]
    other = "B" if person == "A" else "A"
    with col, st.container(border=True, key=f"card_{person}"):
        choice = ss.get(f"lang_{person}", default)
        shown = ss.detected.get(person) if choice == AUTO else choice
        native = f"speaks {NATIVE[shown]}" if shown else "language auto-detected"
        st.markdown(
            f"""<div class="card-head"><div class="avatar {person.lower()}">{person}</div>
            <div><div class="who">Person {person}</div><div class="native">{native}</div></div></div>""",
            unsafe_allow_html=True,
        )
        choice = st.selectbox("Language", options, index=options.index(default), key=f"lang_{person}",
                              label_visibility="collapsed")
        if person in ss.voices:
            st.markdown('<span class="pill on">🧬 Voice captured · replies sound like you</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="pill off">Your first message becomes your voice (speak 5+ sec)</span>',
                        unsafe_allow_html=True)
        inbox = next((t for t in reversed(ss.turns) if t["who"] == other), None)
        if inbox:
            st.markdown(
                f"""<div class="inbox {person.lower()}"><div class="from">Person {other} said:</div>
                <div class="msg">{esc(inbox['translated'])}</div>{facts_html(inbox['facts'])}</div>""",
                unsafe_allow_html=True,
            )
        clip = st.audio_input("Tap to speak", key=f"mic_{person}_{ss['round']}", label_visibility="collapsed")
        lang = ss.detected.get(person, "Auto") if choice == AUTO else choice
        people[person] = (lang, clip)

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
    if other_lang == "Auto":
        st.warning(f"Pick Person {other}'s language first (or let them speak first), so we know what to translate into.")
        continue

    first_clip = person not in ss.voices
    label = f"Person {person}: {'detecting language' if lang == 'Auto' else lang} → {other_lang}"
    with st.status(label, expanded=True) as status:
        try:
            t0 = time.time()
            original, lang = sarvam.transcribe(client, audio, lang)
            t1 = time.time()
            if not original.strip():
                status.update(label="Didn't catch that. Try again a little louder.", state="error")
                continue
            st.write(f"🎧 Heard {lang} ({t1 - t0:.1f}s): {original}")
            spoken_command = sarvam.detect_command(original)
            if spoken_command:
                ss.pending_command = spoken_command
                status.update(label=f"🎙️ Voice command: {COMMAND_LABELS[spoken_command]}", state="complete",
                              expanded=False)
                continue
            translated, facts, english, extras = sarvam.translate(client, original, lang, other_lang, ss.turns, scenario)
            t2 = time.time()
            if extras["command"]:
                ss.pending_command = extras["command"]
                status.update(label=f"🎙️ Voice command: {COMMAND_LABELS[extras['command']]}", state="complete",
                              expanded=False)
                continue
            st.write(f"🧠 Interpreted ({t2 - t1:.1f}s): {translated}")
            ref_audio, ref_text = ss.voices.get(person, (audio, original))
            speech_b64, cloned = sarvam.speak(client, translated, other_lang, ref_audio, ref_text)
            t3 = time.time()
            st.write(f"{'🧬 Spoken in Person ' + person + chr(39) + 's voice' if cloned else '🔈 Spoken (standard voice)'} "
                     f"({t3 - t2:.1f}s)")
            status.update(label=f"{label.replace('detecting language', '✨ ' + lang)} · done in {t3 - t0:.1f}s",
                          state="complete", expanded=False)
        except Exception as e:
            status.update(label=f"Something went wrong: {e}", state="error")
            continue

    if first_clip:
        ss.voices[person] = (audio, original)
    if people[person][0] == "Auto" or ss.get(f"lang_{person}") == AUTO:
        ss.detected[person] = lang
    ss.turns.append({"who": person, "original": original, "translated": translated, "english": english,
                     "facts": facts, "src": lang, "tgt": other_lang, "cloned": cloned, "secs": t3 - t0,
                     "emergency": extras["emergency"], "actions": extras["actions"]})
    ss.latest = sarvam.b64decode(speech_b64)
    st.rerun()

# Voice commands ("Ek Awaaz, summary banao") run here, after the turn loop.
command = ss.pop("pending_command", None)
if command:
    st.toast(f"🎙️ Voice command: {COMMAND_LABELS[command]}")
    if command == "reset":
        reset_conversation()
    elif command == "table_mode":
        ss["_pending_table"] = True
        st.rerun()
    elif ss.turns:
        with st.spinner("Sarvam-105B is summarizing..."):
            langs = [people[p][0] if people[p][0] != "Auto" else "Hindi" for p in ("A", "B")]
            ss.summary = sarvam.summarize(client, ss.turns, langs[0], langs[1], scenario)
        ss.share_now = command == "share"

with st.expander("📄 Show a document: prescription, rent agreement, bank form", expanded=False):
    d1, d2, d3 = st.columns([1, 1, 1])
    giver = d1.radio("Who is handing it over?", ["A", "B"], index=1, horizontal=True,
                     format_func=lambda p: f"Person {p}", key="doc_giver")
    doc_lang = d2.selectbox("Document language", list(NATIVE), index=list(NATIVE).index("English"), key="doc_lang")
    receiver = "B" if giver == "A" else "A"
    receiver_lang = people[receiver][0]
    d3.markdown(f"<br>Explained to **Person {receiver}** in **{receiver_lang if receiver_lang != 'Auto' else '…'}**",
                unsafe_allow_html=True)
    doc = st.file_uploader("Photo or PDF of the document", type=["png", "jpg", "jpeg", "pdf"],
                           key=f"doc_{ss['round']}")
    if doc and st.button(f"🔍 Read & explain to Person {receiver}", type="primary", use_container_width=True):
        if receiver_lang == "Auto":
            st.warning(f"Pick Person {receiver}'s language first.")
        else:
            with st.status(f"📄 Reading document → {receiver_lang}", expanded=True) as status:
                try:
                    t0 = time.time()
                    text = sarvam.read_document(client, doc.getvalue(), doc.name, doc_lang)
                    t1 = time.time()
                    if not text:
                        raise ValueError("No text found in the document. Try a clearer photo.")
                    st.write(f"👁️ Sarvam Vision read the document ({t1 - t0:.1f}s)")
                    explanation, facts = sarvam.explain_document(client, text, receiver_lang, scenario)
                    t2 = time.time()
                    st.write(f"🧠 Explained in {receiver_lang} ({t2 - t1:.1f}s)")
                    ref_audio, ref_text = ss.voices.get(giver, (None, None))
                    if ref_audio:
                        speech_b64, cloned = sarvam.speak(client, explanation, receiver_lang, ref_audio, ref_text)
                    else:
                        res = client.text_to_speech.convert(text=explanation[:1500], language_code=sarvam.LANG_CODES[receiver_lang],
                                                            model="bulbul:v3")
                        speech_b64, cloned = res.audios[0], False
                    t3 = time.time()
                    status.update(label=f"📄 Document explained in {receiver_lang} · {t3 - t0:.1f}s", state="complete",
                                  expanded=False)
                except Exception as e:
                    status.update(label=f"Couldn't read the document: {e}", state="error")
                    st.stop()
            ss.turns.append({"who": giver, "original": "📄 " + text[:400] + ("…" if len(text) > 400 else ""),
                             "translated": explanation, "english": "", "facts": facts, "src": f"document ({doc_lang})",
                             "tgt": receiver_lang, "cloned": cloned, "secs": t3 - t0})
            ss.latest = sarvam.b64decode(speech_b64)
            st.rerun()

if ss.turns:
    last = ss.turns[-1]
    voice = f"in Person {last['who']}'s voice" if last["cloned"] else "standard voice"
    show_en = last["english"] and "English" not in (last["src"], last["tgt"])
    if not table_mode:
        st.markdown(
            f"""<div class="now"><div class="label">Now speaking · {last['tgt']} · {voice}</div>
            <div class="text">{esc(last['translated'])}</div>{facts_html(last['facts'])}
            <div class="orig">Person {last['who']} said in {last['src']}: {esc(last['original'])}</div>
            {f'<div class="en">🇬🇧 {esc(last["english"])}</div>' if show_en else ''}</div>""",
            unsafe_allow_html=True,
        )
    if last.get("emergency"):
        st.error(f"🚑 **Emergency detected** in what Person {last['who']} said. Get help now.", icon="🚨")
        e1, e2 = st.columns(2)
        e1.link_button("🚑 Call 108 · Ambulance", "tel:108", type="primary", use_container_width=True)
        e2.link_button("🆘 Call 112 · Emergency", "tel:112", use_container_width=True)
    links = [l for l in (sarvam.action_link(a) for a in last.get("actions", [])) if l]
    if links:
        st.markdown("**⚡ One-tap actions from what was said**")
        for col, (label, url) in zip(st.columns(len(links)), links):
            col.link_button(label, url, use_container_width=True)
    if ss.latest:
        st.audio(ss.latest, format="audio/wav", autoplay=True)

    st.markdown("#### Conversation")
    for t in reversed(ss.turns):
        side = t["who"].lower()
        voice = "🧬 cloned voice" if t["cloned"] else "🔈 standard voice"
        en = (f'<div class="en">🇬🇧 {esc(t["english"])}</div>'
              if t["english"] and "English" not in (t["src"], t["tgt"]) else "")
        st.markdown(
            f"""<div class="row {side}"><div class="bubble">
            <div class="orig">Person {t['who']} · {t['src']}: {esc(t['original'])}</div>
            <div class="trans">{esc(t['translated'])}</div>{facts_html(t['facts'])}{en}
            <div class="meta">→ {t['tgt']} · {voice} · {t['secs']:.1f}s</div></div></div>""",
            unsafe_allow_html=True,
        )

    c1, c2 = st.columns(2)
    if c1.button("📝 Summarize in both languages", use_container_width=True, type="primary"):
        with st.spinner("Sarvam-105B is summarizing..."):
            langs = [people[p][0] if people[p][0] != "Auto" else "Hindi" for p in ("A", "B")]
            ss.summary = sarvam.summarize(client, ss.turns, langs[0], langs[1], scenario)
    if c2.button("🔄 New conversation", use_container_width=True):
        reset_conversation()

    if ss.get("summary"):
        with st.container(border=True):
            st.markdown(f"##### 📝 {SCENARIOS[scenario]} · summary")
            st.markdown(ss.summary)
        lines = [f"Ek Awaaz · {SCENARIOS[scenario]} · {datetime.now():%d %b %Y %H:%M}", ""]
        for t in ss.turns:
            lines += [f"Person {t['who']} ({t['src']}): {t['original']}", f"  → {t['tgt']}: {t['translated']}"]
            if t["english"]:
                lines.append(f"  English: {t['english']}")
            if t["facts"]:
                lines.append(f"  Critical: {' | '.join(t['facts'])}")
            lines.append("")
        lines += ["Summary", ss.summary]
        if ss.get("share_now"):
            st.success("🎙️ Summary ready. Tap **📲 Send on WhatsApp** below.")
        s1, s2 = st.columns(2)
        s1.link_button("📲 Send on WhatsApp", use_container_width=True,
                       url="https://wa.me/?text=" + quote(f"Ek Awaaz · {SCENARIOS[scenario]} summary\n\n{ss.summary}"))
        s2.download_button("⬇️ Download transcript", "\n".join(lines), file_name="ek-awaaz-transcript.txt",
                           use_container_width=True)
else:
    st.markdown(
        """<div class="empty">👆 Pick a scenario and languages (or ✨ Auto-detect), tap the mic and speak.<br>
        The other person hears it in their language, <b>in your voice</b>.</div>""",
        unsafe_allow_html=True,
    )

st.markdown('<div class="foot">Built with Sarvam AI · Saaras · Sarvam-Translate · Sarvam-105B · Voice Cloning · Bulbul</div>',
            unsafe_allow_html=True)
