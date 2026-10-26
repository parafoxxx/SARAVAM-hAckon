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

## Run locally

```bash
pip install -r requirements.txt
echo SARVAM_API_KEY=your_key_here > .env
streamlit run app.py
```

## Deploy (Streamlit Community Cloud)

1. Push this repo to GitHub. `.env` is git-ignored, so the key stays out.
2. On share.streamlit.io create an app from the repo, main file `app.py`.
3. Under **Settings → Secrets** add: `SARVAM_API_KEY = "your_key_here"`.
