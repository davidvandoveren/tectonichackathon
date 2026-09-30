"""Add Kate's ElevenLabs voice-over to the silent demo video.

    pip install imageio-ffmpeg          # only if you have no ffmpeg on your PATH
    python make_voiceover.py                              # female voice, kate2-demo-silent.mp4
    python make_voiceover.py --voice male
    python make_voiceover.py --music track.mp3            # optional royalty-free background music

Reads ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID_FEMALE / _MALE (or ELEVENLABS_VOICE_ID) from the
environment or from the nearest `.env` (this folder or any parent). Never prints the key.
Each scene's line starts at that scene's start; a line that is too long is sped up (max 1.25x)
so it never runs into the next scene. Output: kate2-demo.mp4.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent

# Same scenes and durations as kate2-video.html (window.SCENES).
SCENES = [
    ("intro", 7, "Stel je voor: een bank die je écht kent. Maak kennis met Kate twee punt nul!"),
    ("problem", 13, "Vandaag herkent Kate honderdveertig situaties. Allemaal met de hand geschreven. "
     "Maar hoe schrijf je een persoonlijke bankier voor twee komma drie miljoen klanten? "
     "Dat kan niet. Dus bouwden we iets beters."),
    ("idea", 13, "Kate twee punt nul leest signalen in je eigen data, en combineert ze tot momenten "
     "die niemand vooraf schreef. Dan beslist ze: wat zeg ik, wanneer, en via welk kanaal. "
     "Of: zeg ik beter niets?"),
    ("for-you", 11, "Elke suggestie op je startscherm is persoonlijk. En altijd met één tik: "
     "waarom zie ik dit? In jouw eigen cijfers."),
    ("just-say-it", 15, "Zeg gewoon wat je wil. Stuur Lucas vijfentwintig euro voor de pizza. "
     "Kate zet alles klaar, jij bevestigt. Kate betaalt nooit zelf. "
     "Eén zin in plaats van vijf schermen!"),
    ("inheritance", 15, "En bij de zwaarste momenten? Dan verkoopt Kate niets. Ze toont medeleven, "
     "biedt hulp aan, en geeft je door aan een echte adviseur. Met de context al klaar, "
     "zodat je je verhaal niet opnieuw hoeft te doen."),
    ("subscriptions", 12, "Kate spoort ook je abonnementen op. Dubbele streamingdiensten, "
     "prijsstijgingen, vergeten proefperiodes. En ze vraagt gewoon: gebruik je dit nog?"),
    ("trust", 11, "Jij houdt de controle. Jij kiest wat Kate mag weten, en wat ze mag doen. "
     "Gevoelige uitgaven? Die raakt ze nooit aan."),
    ("scale", 17, "En het schaalt! Hetzelfde brein, over tienduizend klanten. Vijfenveertig "
     "procent kreeg bewust niets. Nul komma zeven milliseconde per klant: heel KBC in een half "
     "uur rekenwerk. Zonder AI-model."),
    ("quote", 6, "Want niet spammen, dat is een feature."),
    ("vision", 15, "Onze visie: een bank die aanvoelt als je persoonlijke bankier. Die spreekt op "
     "het juiste moment, via het juiste kanaal, en zwijgt als er niets te zeggen valt. "
     "De grote beslissingen? Die blijven altijd bij een mens."),
    ("outro", 9, "Kate twee punt nul. Een bank die je durft te vertrouwen."),
]
LEAD_IN = 0.35  # seconds between a scene appearing and its line starting
MAX_SPEEDUP = 1.25

# Energetic, expressive delivery ("tryhard" presenter): low stability, high style.
VOICE_SETTINGS = {"stability": 0.3, "similarity_boost": 0.8, "style": 0.75, "use_speaker_boost": True}


def load_env() -> None:
    for folder in [Path.cwd(), *Path.cwd().parents, HERE, *HERE.parents]:
        env = folder / ".env"
        if env.is_file():
            for line in env.read_text(encoding="utf-8").splitlines():
                m = re.match(r"^\s*([A-Z0-9_]+)\s*=\s*(.*?)\s*$", line)
                if m and not line.lstrip().startswith("#"):
                    os.environ.setdefault(m.group(1), m.group(2).strip("'\""))
            print(f"Keys gelezen uit {env}")
            return


def ffmpeg_path() -> str:
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg  # type: ignore[import-not-found]

        return str(imageio_ffmpeg.get_ffmpeg_exe())
    except ImportError:
        sys.exit("ffmpeg niet gevonden. Installeer het of doe: pip install imageio-ffmpeg")


def tts(text: str, voice_id: str, key: str, model: str, out: Path) -> None:
    body = json.dumps({"text": text, "model_id": model, "voice_settings": VOICE_SETTINGS}).encode()
    req = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?output_format=mp3_44100_192",
        data=body,
        headers={"xi-api-key": key, "Content-Type": "application/json", "Accept": "audio/mpeg"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310 - fixed https URL
            out.write_bytes(resp.read())
    except urllib.error.HTTPError as exc:
        sys.exit(f"ElevenLabs gaf HTTP {exc.code}: {exc.read()[:300]!r}")


def duration(ffmpeg: str, file: Path) -> float:
    probe = subprocess.run([ffmpeg, "-i", str(file)], capture_output=True, text=True)
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", probe.stderr)
    if not m:
        sys.exit(f"Kon de duur van {file} niet lezen")
    h, mnt, s = m.groups()
    return int(h) * 3600 + int(mnt) * 60 + float(s)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", default=str(HERE / "kate2-demo-silent.mp4"))
    parser.add_argument("--out", default=str(HERE / "kate2-demo.mp4"))
    parser.add_argument("--voice", choices=["female", "male"], default="female")
    parser.add_argument("--model", default="eleven_multilingual_v2")
    parser.add_argument("--music", help="optional background music file (royalty free)")
    parser.add_argument("--music-volume", type=float, default=0.12)
    args = parser.parse_args()

    load_env()
    key = os.environ.get("ELEVENLABS_API_KEY", "")
    voice_id = os.environ.get(f"ELEVENLABS_VOICE_ID_{args.voice.upper()}") or os.environ.get(
        "ELEVENLABS_VOICE_ID", ""
    )
    if not key or not voice_id:
        sys.exit("ELEVENLABS_API_KEY en ELEVENLABS_VOICE_ID_FEMALE/_MALE ontbreken (.env).")
    if not Path(args.video).is_file():
        sys.exit(f"Video niet gevonden: {args.video}")
    ffmpeg = ffmpeg_path()

    with tempfile.TemporaryDirectory() as tmp:
        inputs: list[str] = []
        filters: list[str] = []
        start = 0.0
        for index, (scene, slot, text) in enumerate(SCENES):
            clip = Path(tmp) / f"{index:02d}-{scene}.mp3"
            print(f"🎙️  {scene:14s} …", end=" ", flush=True)
            tts(text, voice_id, key, args.model, clip)
            length = duration(ffmpeg, clip)
            room = slot - LEAD_IN - 0.25
            tempo = min(MAX_SPEEDUP, max(1.0, length / room))
            print(f"{length:4.1f}s" + (f" → {tempo:.2f}x sneller" if tempo > 1 else ""))
            if length / tempo > room + 0.01:
                print(f"   ⚠️  {scene}: tekst blijft {length / tempo - room:.1f}s te lang, overweeg korter")
            delay = int((start + LEAD_IN) * 1000)
            inputs += ["-i", str(clip)]
            filters.append(f"[{index + 1}:a]atempo={tempo:.3f},adelay={delay}|{delay}[v{index}]")
            start += slot
        voices = "".join(f"[v{i}]" for i in range(len(SCENES)))
        mix = f"{voices}amix=inputs={len(SCENES)}:normalize=0,alimiter=limit=0.95[vo]"
        extra: list[str] = []
        final = "[vo]"
        if args.music:
            extra = ["-stream_loop", "-1", "-i", args.music]
            music_index = len(SCENES) + 1
            filters.append(f"[{music_index}:a]volume={args.music_volume},afade=t=out:st={start - 3}:d=3[m]")
            mix += f";[vo][m]amix=inputs=2:normalize=0[mix]"
            final = "[mix]"
        cmd = [ffmpeg, "-y", "-loglevel", "error", "-i", args.video, *inputs, *extra,
               "-filter_complex", ";".join([*filters, mix]),
               "-map", "0:v", "-map", final, "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
               "-t", str(start), "-movflags", "+faststart", args.out]
        subprocess.run(cmd, check=True)
    print(f"\n✅ Klaar: {args.out}")


if __name__ == "__main__":
    main()
