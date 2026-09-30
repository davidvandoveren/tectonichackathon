# Demo video (Kate 2.0)

A ~2:24 animated product video: intro, problem, idea, the app's highlights in a phone frame
(Voor jou + "Waarom zie ik dit?", Just say it + Bevestigen, inheritance guidance, subscriptions,
consent), the jury dashboard at scale, quotes, vision and outro. Synthetic data only.

1. **Screens** – run the app with `PASSWORDLESS_LOGIN=true ADMIN_USERNAMES=jan`, then
   `node capture_app.mjs http://localhost:8080 <work>/shots`
2. **Picture** – copy `kate2-video.html` into `<work>`, then
   `node record_video.mjs <work> <path-to-ffmpeg>` → `kate2-demo-silent.mp4` (1920×1080, no audio)
3. **Voice** – `python make_voiceover.py --video kate2-demo-silent.mp4 [--voice male] [--music track.mp3]`
   uses your ElevenLabs key from `.env` and writes `kate2-demo.mp4`.

The scene texts and durations live in `window.SCENES` (`kate2-video.html`) and `SCENES`
(`make_voiceover.py`); keep both in sync when you change the script.
