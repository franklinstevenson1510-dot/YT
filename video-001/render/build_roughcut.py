#!/usr/bin/env python3
"""Builds a rough-cut MP4 (animatic) of video 001 from 02-script.md.
Scratch narration = espeak-ng (replace with a real voice before publishing).
Usage: python3 build_roughcut.py   -> writes ../video-001_roughcut.mp4 and .srt
"""
import re, subprocess, math, random, shutil
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = Path(__file__).parent
SCRIPT = HERE.parent / "02-script.md"
WORK = Path("/tmp/claude-0/-home-user-YT/7391ebe5-f828-5a83-a33e-b159a9f0f04e/scratchpad/build")
shutil.rmtree(WORK, ignore_errors=True); WORK.mkdir(parents=True)
W, H, FPS = 1280, 720, 25
BG, PAPER, RED = (11, 11, 15), (237, 231, 218), (215, 38, 61)
FB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FS = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
FM = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
font = lambda p, s: ImageFont.truetype(p, s)

# ---------- parse script ----------
scenes, cur, vis = [], None, ""
for raw in SCRIPT.read_text().splitlines():
    line = raw.strip()
    if line.startswith("## "):
        title = re.sub(r"\s*\(.*?\)\s*$", "", line[3:]).strip()
        cur = {"title": title, "lines": []}; scenes.append(cur); vis = ""; continue
    if cur is None or not line or line == "---" or line.startswith(("#", "(Facts", "Target")): continue
    m = re.match(r"\[VISUAL:\s*(.*?)\]?$", line)
    if m: vis = m.group(1).rstrip("]"); continue
    if line.startswith("[SFX"): continue
    text = re.sub(r"\*\*|⚠.*$|\[.*?\]", "", line).strip()
    if text: cur["lines"].append((text, vis))
MOTIF = {"COLD OPEN": "tower", "WHO IS THIS GUY": "map", "THE SETUP": "tower",
         "ESCALATION 1: THE CHOSEN MARK": "mark", "THE TWIST": "paper",
         "ESCALATION 2: THE BOX": "box", "ESCALATION 3: CAPONE": "cash",
         "THE FALL": "bars", "THE TELL": "tell"}

# ---------- drawing ----------
def vignette(img):
    v = Image.new("L", (W, H), 0); d = ImageDraw.Draw(v)
    d.ellipse((-W*0.2, -H*0.3, W*1.2, H*1.3), fill=255)
    v = v.filter(ImageFilter.GaussianBlur(160))
    return Image.composite(img, Image.new("RGB", (W, H), (0, 0, 0)), v)

def tower(d, cx, base, h, col):
    w = h * 0.42
    pts_l = [(cx - w/2, base), (cx - w*0.09, base - h*0.92), (cx, base - h)]
    d.polygon([(cx - w/2, base), (cx - w*0.3, base), (cx - w*0.07, base - h*0.55),
               (cx - w*0.035, base - h*0.92), (cx, base - h), (cx + w*0.035, base - h*0.92),
               (cx + w*0.07, base - h*0.55), (cx + w*0.3, base), (cx + w/2, base),
               (cx + w*0.2, base - h*0.2), (cx - w*0.2, base - h*0.2)], fill=col)
    d.polygon([(cx - w*0.16, base), (cx + w*0.16, base), (cx + w*0.12, base - h*0.2), (cx - w*0.12, base - h*0.2)], fill=BG)
    for y in (0.2, 0.55): d.rectangle((cx - w*(0.3 - y*0.4), base - h*y - 5, cx + w*(0.3 - y*0.4), base - h*y + 5), fill=col)

def background(motif, seed):
    img = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(img)
    random.seed(seed)
    for _ in range(90):  # dust
        x, y = random.randint(0, W), random.randint(0, H)
        d.point((x, y), fill=(60, 60, 66))
    if motif in ("tower", "tell"): tower(d, W*0.74, H*0.95, H*0.8, (28, 28, 36)); tower(d, W*0.74, H*0.95, H*0.8, (28, 28, 36))
    if motif == "map":
        for i in range(0, W, 80): d.line((i, 0, i, H), fill=(22, 22, 28))
        for i in range(0, H, 80): d.line((0, i, W, i), fill=(22, 22, 28))
        d.ellipse((W*0.62, H*0.32, W*0.62+26, H*0.32+26), fill=RED)
        d.text((W*0.62+40, H*0.32), "HOSTINNE, 1890", font=font(FM, 22), fill=PAPER)
    if motif == "mark":
        d.ellipse((W*0.66, H*0.14, W*0.66+220, H*0.14+220), fill=(26, 26, 32)); d.rectangle((W*0.6, H*0.5, W*0.6+330, H*0.95), fill=(26, 26, 32))
        d.rectangle((W*0.66+10, H*0.14+95, W*0.66+210, H*0.14+120), fill=RED)
        d.text((W*0.66+50, H*0.14+240), "POISSON", font=font(FB, 30), fill=PAPER)
    if motif == "paper":
        for i in range(5): d.rectangle((W*0.58+i*16, H*0.12+i*30, W*0.58+i*16+300, H*0.12+i*30+380), fill=(34+i*4, 34+i*4, 34+i*4), outline=(70, 70, 76))
    if motif == "box":
        d.rectangle((W*0.58, H*0.35, W*0.58+360, H*0.35+210), fill=(70, 38, 22), outline=PAPER, width=3)
        for k in range(3): d.ellipse((W*0.58+50+k*100, H*0.35+60, W*0.58+110+k*100, H*0.35+120), outline=PAPER, width=4)
        d.text((W*0.58+30, H*0.35+150), "$100  ->  $100  ->  ???", font=font(FM, 26), fill=PAPER)
    if motif == "cash":
        for k in range(6): d.rectangle((W*0.58, H*0.55-k*30, W*0.58+330, H*0.55-k*30+24), fill=(40, 70, 48), outline=(90, 130, 98))
        d.text((W*0.58, H*0.12), "$50,000", font=font(FB, 90), fill=RED)
    if motif == "bars":
        for k in range(9): d.rectangle((W*0.58+k*44, 0, W*0.58+k*44+16, H), fill=(34, 34, 40))
        d.text((W*0.58, H*0.1), "1935 - 1947", font=font(FM, 34), fill=PAPER)
    return img

def draw_wrapped(d, text, f, x, y, maxw, fill, spacing=10):
    words, lines, ln = text.split(), [], ""
    for w in words:
        t = (ln + " " + w).strip()
        if d.textlength(t, font=f) <= maxw: ln = t
        else: lines.append(ln); ln = w
    lines.append(ln)
    for i, l in enumerate(lines):
        d.text((x, y + i*(f.size + spacing)), l, font=f, fill=fill)
    return len(lines)

def frame(scene_title, motif, caption, visual, seed, idx):
    img = background(motif, seed); d = ImageDraw.Draw(img)
    d.rectangle((0, 0, 14, H), fill=RED)
    d.text((50, 36), "CON FILES", font=font(FB, 26), fill=RED)
    d.text((50, 74), scene_title, font=font(FM, 20), fill=(150, 150, 156))
    if visual:
        d.rectangle((50, 118, 50 + min(700, 14 + len(visual)*10.5), 150), fill=(24, 24, 30))
        d.text((60, 123), ("EDIT NOTE: " + visual)[:68], font=font(FM, 16), fill=(180, 160, 90))
    img = vignette(img); d = ImageDraw.Draw(img)
    cap_f = font(FS, 44)
    tmp = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    n = len(tmp.textbbox((0, 0), caption, font=cap_f)) and math.ceil(tmp.textlength(caption, font=cap_f) / (W*0.76))
    y = H - 90 - n * 56
    draw_wrapped(d, caption, cap_f, 70, y, int(W*0.76), PAPER)
    p = WORK / f"f{idx:04d}.png"; img.save(p); return p

# ---------- narration + clips ----------
def sentences(t): return [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-Z\"'\[])", t) if s.strip()]
def dur(p): return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)]))

clips, srt, t_now, idx = [], [], 0.0, 0
def ts(t): return f"{int(t//3600):02}:{int(t%3600//60):02}:{int(t%60):02},{int(t%1*1000):03}"
for sc in scenes:
    motif = MOTIF.get(sc["title"], "tower")
    for text, vis in sc["lines"]:
        for s in sentences(text):
            idx += 1
            wav = WORK / f"a{idx:04d}.wav"
            spoken = s.replace("—", ", ").replace("*", "")
            subprocess.run(["espeak-ng", "-v", "en-gb-x-rp", "-s", "148", "-p", "28", "-w", str(wav), spoken], check=True)
            d_s = dur(wav) + 0.35
            png = frame(sc["title"], motif, s, vis, idx, idx)
            clip = WORK / f"c{idx:04d}.mp4"
            frames = int(d_s * FPS)
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", str(png), "-i", str(wav),
                "-vf", f"scale=2560:-1,zoompan=z='1+0.0004*on':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{H}:fps={FPS}",
                "-af", "apad=pad_dur=0.35", "-t", f"{d_s:.3f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "44100", "-ac", "2", str(clip)], check=True)
            clips.append(clip)
            srt.append(f"{len(srt)+1}\n{ts(t_now)} --> {ts(t_now+d_s-0.1)}\n{s}\n")
            t_now += d_s
print(f"{idx} clips, {t_now/60:.1f} min narration")
lst = WORK / "list.txt"; lst.write_text("".join(f"file '{c}'\n" for c in clips))
voice = WORK / "voice.mp4"
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(voice)], check=True)
out = HERE.parent / "video-001_roughcut.mp4"
# dark drone bed under the voice
drone = ("aevalsrc='0.5*sin(2*PI*55*t)+0.3*sin(2*PI*82.4*t+0.5*sin(2*PI*0.1*t))+0.2*sin(2*PI*110.5*t)':s=44100:d=%f,"
         "lowpass=f=300,volume=0.10" % (t_now + 2))
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(voice), "-f", "lavfi", "-i", drone,
    "-filter_complex", "[0:a]volume=1.0[v];[1:a]afade=t=in:d=3,afade=t=out:st=%f:d=3[m];[v][m]amix=inputs=2:duration=first:normalize=0[a]" % max(0, t_now-3),
    "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", str(out)], check=True)
(HERE.parent / "video-001_roughcut.srt").write_text("\n".join(srt))
print("wrote", out, f"{out.stat().st_size/1e6:.1f} MB")
