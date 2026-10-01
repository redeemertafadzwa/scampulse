# Known limitations (honest)

Measured on synthetic data (Stage 1). Numbers will change as real, Confirmed
reports are added in later stages.

## Current failures
- **~0.8% of scams wrongly cleared** on the combined test+disguised scams
  (about 1 message). Typically a short scam with no trigger words and no link.
- **~2.4% of disguised scams missed** — very heavy leetspeak that also strips
  the link can slip past both layers.
- These are the two numbers we most want to drive down; they are re-measured by
  `ml/evaluate.py` on every change and must not get worse before a model ships.

## By design
- **No deepfake/audio/video detection.** For voice-note/video claims the engine
  reacts only to what the *text* says and tells the user: "We can't check audio
  or video. Confirm it's really them another way." It never claims to detect a
  deepfake.
- **Name redaction is partial.** We reliably redact +263/07x phone numbers,
  links, amounts and long account numbers, plus names right after a greeting
  ("Dear Tapiwa"). Free-standing names mid-sentence may remain; the user always
  sees exactly what will be sent before anything uploads (Stage 3/4).
- **Synthetic data.** The supplied `Cyber_Shield_Training_Dataset.csv` has only
  12 unique messages, so we built four separate synthetic sets instead. Real
  accuracy in the field is unknown until community reports arrive.

## Remaining polish (functionality complete)
- **Self-host the fonts.** Bricolage Grotesque + Source Sans 3 currently load
  from Google Fonts (cached by the service worker after first load); the spec
  asks for self-hosted woff2. System-font fallback means it still works offline.
- **Formal device testing.** Run Lighthouse (PWA/perf/accessibility) and test on
  two real Android phones (one low-end) before judging.
- **Name redaction** remains partial (see "By design" above).

## Built (Stages 2-6)
- On-device JS inference + Python/JS parity test (948 checks, 0 mismatches).
- Check / Verdict+Why / Feed / Before-you-send / Report screens, EN+partial
  Shona/Ndebele, voice read-out, opt-in redacted reporting.
- Reports API, fingerprint family matching, confirm-threshold + admin moderation,
  `retrain` (gated publish), PWA (manifest + service worker + share_target),
  offline, privacy page, `/health`, prod security headers.
