#!/usr/bin/env python3
"""Silent images + text version of video 001 (no voiceover).
Reads 02-script.md (on-screen text) + shotlist.json (image prompts).
Images: put Higgsfield images in assets/images/ named <scene#>_<shot#>.png|jpg  (e.g. 03_2.png).
Missing images show a dark placeholder card containing the prompt, so you can see what goes where.
Usage: python3 render_silent.py [--hd]      (default 1280x720 preview, --hd = 1920x1080)
Output: ../video-001_silent.mp4
"""
import json, re, shutil, subprocess, sys, math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).parent
W, H = (1920, 1080) if "--hd" in sys.argv else (1280, 720)
S = W / 1280
FPS = 25
BG, PAPER, RED = (11, 11, 15), (237, 231, 218), (215, 38, 61)
WORK = ROOT / ".work"; shutil.rmtree(WORK, ignore_errors=True); WORK.mkdir()
SHOTS = json.loads((ROOT / "shotlist.json").read_text())["scenes"]
F = lambda p, s: ImageFont.truetype(p, int(s * S))
SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"

def parse():
    scenes, cur = [], None
    for raw in (ROOT.parent / "02-script.md").read_text().splitlines():
        s = raw.strip()
        if s.startswith("## "):
            cur = {"title": re.sub(r"\s*\(.*?\)\s*$", "", s[3:]).strip(), "sents": []}; scenes.append(cur); continue
        if cur is None or not s or s == "---" or s.startswith(("#", "(Facts", "Target", "[VISUAL", "[SFX")): continue
        t = re.sub(r"\*\*|⚠.*$|\[.*?\]", "", s).strip()
        cur["sents"] += [x for x in re.split(r"(?<=[.!?])\s+(?=[A-Z\"'])", t) if x]
    return scenes

def wrap(d, text, f, maxw):
    out, ln = [], ""
    for w in text.split():
        t = (ln + " " + w).strip()
        if d.textlength(t, font=f) <= maxw: ln = t
        else: out.append(ln); ln = w
    return out + [ln]

def background(sc_n, k, prompt):
    for ext in ("png", "jpg", "jpeg", "webp"):
        p = ROOT / "assets" / "images" / f"{sc_n:02d}_{k}.{ext}"
        if p.exists():
            im = Image.open(p).convert("RGB"); r = max(W / im.width, H / im.height)
            im = im.resize((int(im.width * r), int(im.height * r))); l, t = (im.width - W) // 2, (im.height - H) // 2
            return im.crop((l, t, l + W, t + H)), True
    im = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(im)
    for x in range(0, W, int(80 * S)): d.line((x, 0, x, H), fill=(20, 20, 26))
    for y in range(0, H, int(80 * S)): d.line((0, y, W, y), fill=(20, 20, 26))
    d.text((int(60 * S), int(130 * S)), f"IMAGE {sc_n:02d}_{k}", font=F(SANS, 30), fill=RED)
    y = int(180 * S)
    for ln in wrap(d, prompt, F(MONO, 20), W * 0.6)[:7]:
        d.text((int(60 * S), y), ln, font=F(MONO, 20), fill=(110, 110, 118)); y += int(28 * S)
    return im, False

def overlay(text, title, idx, total):
    """transparent RGBA: bottom gradient + caption + header"""
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for i in range(int(H * 0.5)):
        a = int(210 * (i / (H * 0.5)) ** 1.6); d.line((0, H - int(H * 0.5) + i, W, H - int(H * 0.5) + i), fill=(0, 0, 0, a))
    d.rectangle((0, 0, int(10 * S), H), fill=RED + (255,))
    d.text((int(44 * S), int(30 * S)), "CON FILES", font=F(SANS, 24), fill=RED + (255,))
    d.text((int(44 * S), int(62 * S)), title, font=F(MONO, 18), fill=(200, 200, 206, 200))
    f = F(SERIF, 44); lines = wrap(d, text, f, W * 0.8); y = H - int(70 * S) - len(lines) * int(58 * S)
    for ln in lines:
        d.text((int(60 * S) + 2, y + 2), ln, font=f, fill=(0, 0, 0, 255)); d.text((int(60 * S), y), ln, font=f, fill=PAPER + (255,)); y += int(58 * S)
    d.rectangle((0, H - int(6 * S), int(W * idx / total), H), fill=RED + (255,))
    return im

def clip(bg_img, ov_img, secs, n, k_alt):
    bg, ov = WORK / f"b{n}.png", WORK / f"o{n}.png"; bg_img.save(bg); ov_img.save(ov); out = WORK / f"c{n:04d}.mp4"
    fr = int(secs * FPS); z = "min(zoom+0.0005,1.12)" if k_alt else "max(1.12-0.0005*on,1.0)"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", str(bg), "-loop", "1", "-i", str(ov), "-t", f"{secs:.2f}",
        "-filter_complex", f"[0]scale={int(W*1.25)}:-1,zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={fr}:s={W}x{H}:fps={FPS},"
        f"eq=contrast=1.06:saturation=0.9[v];[v][1]overlay,fade=t=in:d=0.25,fade=t=out:st={secs-0.25:.2f}:d=0.25",
        "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "26", "-pix_fmt", "yuv420p", str(out)], check=True)
    return out

scenes = parse(); total = sum(len(s["sents"]) for s in scenes); clips, n, t = [], 0, 0.0
# title card
tc = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(tc)
d.text((int(120 * S), int(250 * S)), "CON FILES", font=F(SANS, 40), fill=RED)
for i, ln in enumerate(["HE SOLD THE", "EIFFEL TOWER.", "TWICE."]): d.text((int(120 * S), int((320 + i * 100) * S)), ln, font=F(SANS, 90), fill=PAPER)
tc.save(WORK / "title.png")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", str(WORK / "title.png"), "-t", "3", "-vf", f"fade=t=in:d=0.5,fade=t=out:st=2.5:d=0.5",
                "-r", str(FPS), "-c:v", "libx264", "-pix_fmt", "yuv420p", str(WORK / "c0000.mp4")], check=True); clips.append(WORK / "c0000.mp4"); t += 3
for sc_n, sc in enumerate(scenes, 1):
    prompts = SHOTS.get(sc["title"], ["(no prompt)"]); per = max(1, math.ceil(len(sc["sents"]) / len(prompts)))
    for i, s in enumerate(sc["sents"]):
        n += 1; k = min(i // per + 1, len(prompts))
        bg, _ = background(sc_n, k, prompts[k - 1])
        secs = max(3.0, len(s.split()) / 3.0 + 1.0)   # ~180 wpm reading + 1s hold
        clips.append(clip(bg, overlay(s, sc["title"], n, total), secs, n, n % 2)); t += secs
(WORK / "list.txt").write_text("".join(f"file '{c}'\n" for c in clips))
silent = WORK / "silent.mp4"
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(WORK / "list.txt"), "-c", "copy", str(silent)], check=True)
out = ROOT.parent / "video-001_silent.mp4"
drone = ("aevalsrc='0.5*sin(2*PI*55*t)+0.3*sin(2*PI*82.4*t+0.5*sin(2*PI*0.1*t))+0.2*sin(2*PI*110.5*t)':s=44100:d=%f,lowpass=f=300,volume=0.12,"
         "afade=t=in:d=3,afade=t=out:st=%f:d=3" % (t, t - 3))
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(silent), "-f", "lavfi", "-i", drone, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-shortest", str(out)], check=True)
print(f"wrote {out} ({t/60:.1f} min, {W}x{H}, {sum(1 for c in clips)} clips)")
