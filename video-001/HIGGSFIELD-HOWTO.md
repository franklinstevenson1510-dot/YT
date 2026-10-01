# Adding Higgsfield images (simple way — no API needed)

1. Go to higgsfield.ai and sign in.
2. Open the image generator. Paste the first line of `production/shotlist.json` "style" + the scene prompt, e.g.
   `wide shot of the Eiffel Tower at dusk in 1925, fog over Paris rooftops... Style: cinematic 1920s noir illustration, grainy black-and-white with selective signal-red accents...`
3. Set aspect ratio **16:9**. Generate, pick the best result, download it.
4. Rename it to `<scene#>_<shot#>.png` — the exact names are shown on each placeholder card in the video
   (e.g. `01_1.png`, `01_2.png`, `01_3.png`, `02_1.png` ... `09_3.png`; 27 images total).
5. Put the files in `video-001/production/assets/images/` (GitHub: open that folder → Add file → Upload files → commit to branch `claude/youtube-faceless-channel-0htg3o`).
6. Tell Claude "images are in" — it re-runs `python3 production/render_silent.py --hd` and you get the finished 1080p video.

Tips: keep the same style line on every prompt so the look is consistent; generate 2–4 variations and keep the best; no readable text in images (captions are added by the video).

## Optional: automatic generation through Higgsfield's API (later)
Needs, in the environment settings (cloud environment menu → Edit): allow the Higgsfield API host in Network access, and add `HIGGSFIELD_API_KEY` (and secret if your plan has one) as environment variables. Then a new session; I'd wire `production/produce.py` to it. Never paste keys in chat.
