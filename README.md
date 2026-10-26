# 🗣️ Ek Awaaz

**Speak your language. They hear theirs, in your own voice.**

A live two-way interpreter for people who don't share a language: a migrant worker and a doctor, a tenant and a landlord, a nurse and a patient's family. Each person speaks in their own language, and the other hears the translation **in the speaker's cloned voice**. No setup: your first message becomes your voice sample.

## How it works

| Step | Sarvam API |
|---|---|
| Speech → text | Saaras v3 (speech-to-text) |
| Context-aware translation (keeps gender, numbers, tone; resolves "he/she" from earlier turns) | Sarvam-105B, with Sarvam-Translate as fallback |
| Text → speech in the speaker's own voice, cross-lingual | Voice Cloning, with Bulbul v3 as fallback |
| Summary of the conversation in both languages | Sarvam-105B |

Supports 12 languages: Hindi, Tamil, Telugu, Kannada, Malayalam, Bengali, Marathi, Gujarati, Punjabi, Odia, Assamese, English.

## Project layout

| Path | What it is |
|---|---|
| `index.html` | Web frontend (Vercel). Records the mic in the browser and converts it to 16 kHz WAV |
| `api/turn.py` | Serverless function: one turn (speech → text → translation → cloned speech) |
| `api/summary.py` | Serverless function: bilingual conversation summary |
| `api/_sarvam.py` | Shared Sarvam pipeline |
| `app.py` | The same app as a Streamlit version (backup / local demo) |

## Deploy on Vercel

1. On vercel.com → **Add New → Project**, import this GitHub repo. Framework preset: **Other**, with no build command.
2. Under **Environment Variables** add `SARVAM_API_KEY` = your key.
3. Deploy. The HTTPS link works with the mic on phones too.

## Run the Streamlit version locally

```bash
pip install -r requirements.txt streamlit
echo SARVAM_API_KEY=your_key_here > .env
streamlit run app.py
```

`.env` is git-ignored, so the key never reaches the repo.
