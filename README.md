# ROSE BOUQUET IN ASCII

*An ASCII animation by [@dwcminh.ascii](https://instagram.com/dwcminh.ascii) (2026)*

![ROSE BOUQUET IN ASCII](preview.gif)

## The idea

A bouquet that grows like a living plant, sparkling wherever it grows. Stems shoot up and
branch out to where the flowers will sit, leaves sprout and a bed of greenery fills in. Then
nineteen rosebuds appear one after another, silver paper wraps around from behind, a gold ribbon
and bow click into place, and the baby's breath lights up sprig by sprig. One at a time the
roses open, each with a flash and a shower of sparks, and "FOR YOU <3" types itself out below
with a beating red heart. A shine slides along the ribbon, petals drift down, and the bouquet
sways gently from side to side under twinkling stars, dew glinting on the petals.

## How it's made

- **Growth:** stems, leaves and greenery each have their own moment to appear, so the bouquet builds itself in order instead of fading in.
- **Roses:** every rose starts as a closed bud and opens on its own cue, popping white-hot before settling into its colour.
- **Wrapping:** the paper, the ribbon and the bow are separate layers that snap on in turn.
- **Picking characters:** edges get an outline that follows their direction, solid areas are filled with letters chosen by brightness.
- **Extras:** sparks, falling petals, dew glints, a gleam on the ribbon, a typed message with a beating heart.
- **Rendering:** a character grid drawn with a soft double glow and fading trails.

The desktop version is built with Python, NumPy and pygame-ce. The browser version
uses HTML, JavaScript and Canvas, so it starts without downloading a Python runtime.

## Run it

```
pip install -r requirements.txt
python rose_bouquet.py
```

Both versions play and loop the soundtrack extracted from `rose.mp4`.

Keys: `Space` pause · `R` restart · `S` save a screenshot · `Esc` exit

## Run in a browser

Serve the static web app from the project folder:

```
python -m http.server 8000
```

Then open `http://localhost:8000`. The animation and soundtrack attempt to start immediately.
Use **Bật nhạc / Tắt nhạc** to control playback. If the browser blocks autoplay, tap the button
or anywhere on the animation once; browser autoplay restrictions cannot be bypassed.

## Deploy to GitHub Pages

Push this project to a GitHub repository on the `main` branch. The workflow at
`.github/workflows/deploy-pages.yml` stages the root-level web files and deploys them automatically.
In the repository, open **Settings → Pages** and set the source to **GitHub Actions**.
After the workflow completes, the public URL is shown in its deployment job.

## Using this code

The source is free for personal use. If you post something you made with it, a mention of
@dwcminh.ascii would be appreciated. The full terms are in LICENSE.txt.

---

Made by [@dwcminh.ascii](https://instagram.com/dwcminh.ascii) on Instagram.
The images and video in this folder belong to @dwcminh.ascii. Please ask before reusing them.
