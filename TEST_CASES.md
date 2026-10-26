# Ek Awaaz: Test Cases & Demo Script

Default setup unless a test says otherwise: **🏥 Doctor** scenario, **Person A = ✨ Auto-detect**, **Person B = Tamil**.
Speak clearly, phone close, **6–8 seconds for each person's first message** (it becomes their cloned voice).
Hindi lines are written in Roman script so anyone can read them aloud.

---

## Part 1: Must-pass tests (run these before presenting)

| ID | Feature | Steps | Expected result | Pass |
|---|---|---|---|---|
| TC-01 | App loads | Open the Streamlit link | Header, scenario pills, two speaker cards. No red "API key" error | ☐ |
| TC-02 | ✨ Auto-detect + voice capture | Person A speaks: *"Namaste doctor sahab, mera naam Ravi hai. Mere bete ko kal raat se bahut tez bukhar hai aur woh kuch kha nahi raha."* | Status shows **✨ Hindi**. Tamil audio plays automatically. Card A shows **🧬 Voice captured** | ☐ |
| TC-03 | 🧬 Cloned voice | Listen to the Tamil audio from TC-02 | Sounds like **Person A**. Bubble tag says **🧬 cloned voice** | ☐ |
| TC-04 | 🧠 Two-pass translation | Switch Person B to **English**. B says: *"Give him paracetamol 250 mg after food, three times a day."* | Hindi contains **"खाने के बाद"** (after food) and refers to the boy as **him** (उसे / लड़के), not her | ☐ |
| TC-05 | 🚨 Critical-fact alerts | Same turn, B adds: *"If fever goes above 102, come back immediately."* | Red chips: medicine + dose, three times a day, 102 degrees | ☐ |
| TC-06 | 📝 Bilingual summary | Tap **📝 Summarize in both languages** | Summary in both languages (symptoms, medicine, warning signs, follow-up). Contains **only what was actually said** | ☐ |
| TC-07 | 📲 WhatsApp share | Tap **📲 Send on WhatsApp** | WhatsApp opens with the summary already filled in | ☐ |

## Part 2: Good-to-check tests

| ID | Feature | Steps | Expected result | Pass |
|---|---|---|---|---|
| TC-08 | 📱 Table mode | Turn on **📱 Face-to-face table mode** | Cards stack. **Person B's card is upside down**. Each card shows the last message it received, in large text | ☐ |
| TC-09 | 🇬🇧 English line | Look under a Hindi ↔ Tamil bubble | An italic 🇬🇧 English translation is shown | ☐ |
| TC-10 | ⏱️ Live pipeline | Watch the status box during a turn | 🎧 Heard → 🧠 Interpreted → 🧬 Spoken, each with seconds. Total about 5–8 s | ☐ |
| TC-11 | 🎭 Scenario: Renting | Pick **🏠 Renting**. A (Hindi): *"Kiraya kitna hai aur deposit kitna dena padega?"* B (English): *"Rent is 12,000 a month, deposit is 3 months, move in on the 1st."* | Chips show 12,000 / 3 months / 1st. The summary lists rent, deposit, move-in date | ☐ |
| TC-12 | 🎭 Scenario: Market | Pick **🛒 Market**. A: *"Do kilo tamatar kitne ka hai?"* | The translation keeps "2 kilo" | ☐ |
| TC-13 | ⬇️ Download transcript | After summarizing, tap **⬇️ Download transcript** | A `.txt` file with every turn, English lines, critical facts and the summary | ☐ |
| TC-14 | 🔄 Reset | Tap **🔄 New conversation** | Conversation, voice badges and mics all cleared | ☐ |
| TC-15 | ✨ Auto-detect, other language | A judge speaks Bengali/Marathi/Telugu, e.g. Bengali *"Amar matha byatha korche"* (I have a headache) | Card shows that language in its own script. Translation plays | ☐ |

## Part 3: Edge cases

| ID | Case | Steps | Expected result | Pass |
|---|---|---|---|---|
| TC-16 | Both on Auto-detect | Set A and B to ✨ Auto-detect, then speak | Yellow warning: "Pick Person X's language first". No crash | ☐ |
| TC-17 | Silence / too short | Record about 1 s of silence | "Didn't catch that. Try again a little louder." | ☐ |
| TC-18 | Clone fallback | (Happens only if cloning fails) | Audio still plays in a standard Bulbul voice. Tag shows **🔈 standard voice** | ☐ |
| TC-19 | Noisy room | Speak with background noise | Still transcribes. Hold the phone closer if not | ☐ |

## Troubleshooting

| Symptom | Fix |
|---|---|
| No audio plays | Tap ▶ on the audio bar (the browser blocked autoplay) |
| 🔈 standard voice instead of 🧬 | Start a new conversation. Make the first message a clear 6–8 s |
| "Something went wrong: 402" | Sarvam account is out of credits |
| Mic doesn't respond | Use the **https** link and allow microphone access in the browser |
| App shows API key error | Streamlit → Settings → Secrets: `SARVAM_API_KEY = "your_key"` |

---

# Demo Script: one example per feature

| # | Feature | Do / say | What judges see | Line to say |
|---|---|---|---|---|
| 1 | 🧬 Voice cloning | Judge as Person A (Auto), says TC-02 line | Tamil plays **in the judge's voice** | "You don't speak Tamil, but that was **your voice** speaking it, cloned from one sentence." |
| 2 | ✨ Auto-detect | Judge speaks Bengali / Marathi / Telugu | Card switches to that language | "Nobody chose a language. If you can't read a dropdown, you can still use it by talking." |
| 3 | 🧠 Two-pass translation | TC-04 dose line | **खाने के बाद** and **him** kept | "105B alone dropped 'after food'. Sarvam-Translate alone turned the boy into a girl. Our two-pass pipeline got both right every time." |
| 4 | 🚨 Critical facts | TC-05 line | Red chips with dose, frequency, 102° | "We show the dose, the timing and the warning in red, in the listener's language." |
| 5 | 🎭 Scenarios | TC-11 renting | Chips: 12,000 / 3 months / 1st | "A newcomer in Chennai, a landlord who speaks only Tamil, a ₹36,000 deposit. Every number comes through." |
| 6 | 📱 Table mode | Toggle, phone flat between two judges | B's half flips toward them | "One phone between two people, and each reads their own side." |
| 7 | 🇬🇧 English line | Point at any bubble | Italic English line | "You can't read both Tamil and Hindi, but you can check every word here." |
| 8 | ⏱️ Live pipeline | Point at the status box mid-turn | Step-by-step timings | "Speech-to-text, a translation that checks itself, and voice cloning, live in about 5 seconds." |
| 9 | 📝 Summary | Tap Summarize | Structured, in both languages | "Patients forget most of what a doctor says. Ravi leaves with it in his own language." |
| 10 | 📲 WhatsApp | Tap Send on WhatsApp | WhatsApp opens, already filled in | "His wife back in the village gets the instructions in Hindi." |
| 11 | 🛡️ Fallbacks | Only if asked about reliability | 🧬 / 🔈 tag | "Every step has a backup, so it doesn't break on stage." |

## 90-second run

1. **🏥 Doctor.** Judge speaks Hindi → Tamil plays in **their voice** (1, 2)
2. You give the dose in English → **"after food" kept + 🚨 chips** (3, 4)
3. **📱 Table mode** flip (6)
4. **📝 Summarize → 📲 WhatsApp** (9, 10)
5. Close: *"India has 22 official languages. Ek Awaaz lets two people talk, each in their own voice."*
