#!/usr/bin/env python3
"""Con Files production pipeline: script -> ElevenLabs voice -> Higgsfield images -> MP4.

Env vars (set in the environment's settings, never in chat or in git):
  ELEVENLABS_API_KEY   required for voice
  ELEVENLABS_VOICE_ID  required (pick a calm, deep narrator voice in your ElevenLabs library)
  HIGGSFIELD_API_KEY   optional; HIGGSFIELD_API_SECRET if your plan uses key+secret
Usage:
  python3 produce.py plan               # parse script, print scenes/shots/word counts (offline)
  python3 produce.py voice              # ElevenLabs TTS per scene -> assets/voice/NN.mp3
  python3 produce.py images             # Higgsfield (see higgsfield_generate) -> assets/images/NN_k.png
  python3 produce.py render             # assemble final MP4 from assets/ (missing images -> placeholder cards)
Images can also be made by hand in Higgsfield's web app with the prompts in shotlist.json:
save them as assets/images/<scene#>_<shot#>.png (e.g. 01_1.png) and run `render`.
"""
import json, os, re, subprocess, sys, shutil
from pathlib import Path
import urllib.request

ROOT = Path(__file__).parent
SCRIPT = ROOT.parent / "02-script.md"
ASSETS = ROOT / "assets"; (ASSETS / "voice").mkdir(parents=True, exist_ok=True); (ASSETS / "images").mkdir(exist_ok=True)
SHOTS = json.loads((ROOT / "shotlist.json").read_text())
W, H, FPS = 1920, 1080, 30

def parse_scenes():
    scenes, cur = [], None
    for raw in SCRIPT.read_text().splitlines():
        s = raw.strip()
        if s.startswith("## "):
            cur = {"title": re.sub(r"\s*\(.*?\)\s*$", "", s[3:]).strip(), "text": []}; scenes.append(cur); continue
        if cur is None or not s or s == "---" or s.startswith(("#", "(Facts", "Target", "[VISUAL", "[SFX")): continue
        t = re.sub(r"\*\*|⚠.*$|\[.*?\]", "", s).strip()
        if t: cur["text"].append(t)
    for i, sc in enumerate(scenes, 1):
        sc["n"] = i; sc["narration"] = " ".join(sc["text"])
    return scenes

def dur(p):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)]))

def eleven_tts(text, out):
    key, voice = os.environ.get("ELEVENLABS_API_KEY"), os.environ.get("ELEVENLABS_VOICE_ID")
    if not key or not voice: sys.exit("Set ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID")
    req = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice}?output_format=mp3_44100_128",
        data=json.dumps({"text": text, "model_id": "eleven_multilingual_v2",
                         "voice_settings": {"stability": 0.55, "similarity_boost": 0.8, "style": 0.25}}).encode(),
        headers={"xi-api-key": key, "Content-Type": "application/json", "Accept": "audio/mpeg"})
    out.write_bytes(urllib.request.urlopen(req, timeout=120).read())

def higgsfield_generate(prompt, out):
    """Higgsfield's API contract must be confirmed against your account's API docs
    (endpoint, auth header, model id, async polling). Fill this in once credentials/docs are available.
    Until then, generate with the prompts in shotlist.json in the Higgsfield web app and save by hand."""
    raise NotImplementedError("Higgsfield API adapter not configured; see docstring")

def cmd_plan():
    total = 0
    for sc in parse_scenes():
        words = len(sc["narration"].split()); total += words
        print(f"{sc['n']:02d} {sc['title']:<32} {words:>4} words  ~{words/150*60:>4.0f}s  shots={len(SHOTS['scenes'].get(sc['title'], []))}")
    print(f"TOTAL {total} words ~ {total/150:.1f} min @150wpm")

def cmd_voice():
    for sc in parse_scenes():
        out = ASSETS / "voice" / f"{sc['n']:02d}.mp3"
        if out.exists(): continue
        print("TTS", sc["title"]); eleven_tts(sc["narration"], out)

def cmd_images():
    for sc in parse_scenes():
        for k, p in enumerate(SHOTS["scenes"][sc["title"]], 1):
            out = ASSETS / "images" / f"{sc['n']:02d}_{k}.png"
            if out.exists(): continue
            higgsfield_generate(f"{p}. Style: {SHOTS['style']}", out)

def cmd_render():
    work = ROOT / ".work"; shutil.rmtree(work, ignore_errors=True); work.mkdir()
    parts, srt, t = [], [], 0.0
    ts = lambda x: f"{int(x//3600):02}:{int(x%3600//60):02}:{int(x%60):02},{int(x%1*1000):03}"
    for sc in parse_scenes():
        voice = ASSETS / "voice" / f"{sc['n']:02d}.mp3"
        if not voice.exists(): sys.exit(f"missing {voice} (run `voice`)")
        d = dur(voice) + 0.6; shots = SHOTS["scenes"][sc["title"]]; per = d / len(shots)
        imgs = []
        for k in range(1, len(shots) + 1):
            p = ASSETS / "images" / f"{sc['n']:02d}_{k}.png"
            if not p.exists():
                p = work / f"ph_{sc['n']:02d}_{k}.png"
                subprocess.run(["convert", "-size", f"{W}x{H}", "xc:#0B0B0F", "-fill", "#D7263D", "-pointsize", "48",
                                "-gravity", "center", "-annotate", "0", f"PLACEHOLDER\n{sc['title']} #{k}", str(p)], check=True)
            imgs.append(p)
        seg = []
        for k, p in enumerate(imgs, 1):
            o = work / f"s{sc['n']:02d}_{k}.mp4"; n = int(per * FPS)
            zoom = "min(zoom+0.0007,1.15)" if k % 2 else "max(1.15-0.0007*on,1.0)"
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", str(p), "-t", f"{per:.3f}",
                "-vf", f"scale=3840:-1,zoompan=z='{zoom}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={n}:s={W}x{H}:fps={FPS},"
                       "eq=contrast=1.08:saturation=0.9,noise=alls=8:allf=t,fade=t=in:d=0.4",
                "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", str(o)], check=True)
            seg.append(o)
        (work / f"l{sc['n']}.txt").write_text("".join(f"file '{s}'\n" for s in seg))
        v = work / f"v{sc['n']:02d}.mp4"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(work / f"l{sc['n']}.txt"),
                        "-i", str(voice), "-filter_complex", "[1:a]apad=pad_dur=0.6[a]", "-map", "0:v", "-map", "[a]",
                        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", str(v)], check=True)
        parts.append(v)
        sents = re.split(r"(?<=[.!?])\s+", sc["narration"]); tot = sum(len(s) for s in sents); tt = t
        for s in sents:
            dd = (d - 0.6) * len(s) / tot
            srt.append(f"{len(srt)+1}\n{ts(tt)} --> {ts(tt+dd)}\n{s}\n"); tt += dd
        t += d
    (work / "all.txt").write_text("".join(f"file '{p}'\n" for p in parts))
    out = ROOT.parent / "video-001_final.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(work / "all.txt"), "-c", "copy", str(out)], check=True)
    (ROOT.parent / "video-001_final.srt").write_text("\n".join(srt))
    print("wrote", out, f"{t/60:.1f} min")

if __name__ == "__main__":
    {"plan": cmd_plan, "voice": cmd_voice, "images": cmd_images, "render": cmd_render}.get(sys.argv[1] if len(sys.argv) > 1 else "", lambda: sys.exit(__doc__))()
