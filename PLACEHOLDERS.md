# Placeholders to replace

Every file below is generated flat art that says PLACEHOLDER on it. Drop the real file in at the same path (same name).
`python3 tools/check_site.py --release` fails while any of these is still the generated file (also inside the press kit zip), and on every `TODO-` marker.
Real pictures and clips must come from the build approved for public material.

| File | What goes there |
| --- | --- |
| `assets/img/hero-1x.webp`, `hero-2x.webp` | Key art, periscope view of a convoy, no title: 800 px and 1600 px wide, 16:9, each under 200 KB |
| `assets/video/clip-1.mp4`, `clip-2.mp4`, `clip-3.mp4` | Three silent 5 to 8 s loops (order and answer with captions burned in; position cuts; torpedo run), landscape, under about 2 MB each, H.264, written with `-movflags +faststart` so playback starts before the download ends |
| `assets/img/clip-1-poster.webp` ... `clip-3-poster.webp` | One still per clip, 640x360, shown until the clip loads (and under reduced motion) |
| `assets/img/shot-1-1x.webp` ... `shot-4-1x.webp` | Screenshots, 800 px wide (control room, boat from outside, a gauge, corvette on the horizon) |
| `assets/img/shot-1-2x.webp` ... `shot-4-2x.webp` | The same, 1600 px wide. This is also the "full size" link target, so keep it under 200 KB |
| `assets/img/status-1x.webp`, `status-2x.webp` | Newest picture for "Where it stands" (800 / 1600 px) |
| `assets/img/og.jpg` | Social card, 1200x630 JPEG (not WebP: crawlers), under 200 KB. It carries the final logo on a placeholder card |
| `press/kit-src/key-art-PLACEHOLDER.webp`, `screenshot-1..4-PLACEHOLDER.webp` | Full-size key art and stills for the zip (rename without PLACEHOLDER; the zip may use larger files, the 200 KB limit applies to them too) |

Not placeholders but still to settle:

- **Logo (final).** The orange ship's wheel, cut out with a transparent background from the 2000x2000 logo image (no letters; the title "Jawohl Kapitän" is real text beside it). `assets/img/logo-1x.webp` / `logo-2x.webp` (256 / 512 px), `favicon.png` (64 px, transparent), `apple-touch-icon.png` (180 px, on the site's dark background) and `press/kit-src/logo.png` (1024 px, transparent) are all made from it. **Still missing: an SVG logo for the press kit** (the kit has the PNG only).
- Colours in the `:root` block of `assets/site.css` are placeholders.
- `https://TODO-GOFUNDME`, `https://TODO-GOFUNDME-UPDATE`, `https://TODO-ITCH`, `TODO-VIDEO-ID` (both pages), `TODO-VIDEO-URL` (press kit README), and all `TODO-LEGAL` boxes (see README, "Other TODOs").
- The YouTube channel URL `youtube.com/@jawohlkapitan` is unconfirmed; the TikTok and Reddit URLs are built from the handle.

The zip `press/jawohl-kapitan-press-kit.zip` is built from `press/kit-src/`, which holds placeholders, so it is a placeholder too.
