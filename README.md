# jawohlkapitan.com

The one-page site for Jawohl Kapitän. Plain HTML and CSS: no framework, no build step, no script, no web fonts, nothing from other hosts except one `youtube-nocookie.com` iframe (section 3).

This repository is public, history included. Put nothing private in it, and never use Git LFS: GitHub Pages does not serve LFS files (the check fails if `.gitattributes` turns LFS on). The published site holds only the files the workflow stages (`.github/workflows/check.yml`): the pages, `assets/`, `press/` and the site files. `tools/`, `README.md`, `PLACEHOLDERS.md` and `.github/` stay in the repository and are never served, but the repository itself is public, so they can still be read there.

Nothing is public until it is announced. German stays off until a native speaker has checked it.

## Layout

```
index.html                 English page (nine sections)
de/index.html              German page (built, unlinked, noindex)
privacy/  de/datenschutz/  privacy notice (EN / DE)
legal-notice/  de/rechtliches/   legal notice (EN / DE)
404.html  robots.txt  sitemap.xml  CNAME  .nojekyll
assets/site.css            the only stylesheet (no inline styles anywhere: the CSP forbids them)
assets/img  assets/video   pictures (WebP in 1x/2x, srcset) and clips
press/kit-src/             what goes into the press kit zip
press/jawohl-kapitan-press-kit.zip
tools/check_site.py        the check
tools/build_press_kit.py   builds the zip
tools/placeholders.json    hashes of the generated placeholder files (the release check uses it)
tools/kit-de/              German press kit texts, parked while German is off (not zipped, not checked)
```

Section ids, both pages, in order: `top`, `orders`, `video`, `screenshots`, `status`, `support`, `follow`, `press`, then `footer#footer`.

## Checks

```
python3 tools/check_site.py             # runs on every push (.github/workflows/check.yml)
python3 tools/check_site.py --release   # before going public: also fails on any TODO- marker and on placeholder files
```

It fails on: any `<script>`, `<object>`, `<embed>`, `<base>`, inline `style=` or `<style>`, inline `on...=` handlers, an `<iframe srcdoc>`, any host other than `www.youtube-nocookie.com` (iframe only) and the allowed outbound link hosts (any URL with a host counts, including `//host/...`; this covers `href`, `src`, `srcset`, `poster`, `action`, `<object data>` and `<meta http-equiv="refresh">`), a CSS `url()` or `@import` to another host, an image over 200 KB or a clip over 2 MB, a broken internal link, anchor or asset, a missing `alt`, a `<video>` without `controls`, EN and DE pages with different section ids, missing Open Graph or Twitter tags, an `og:image` that is not a 1200x630 JPEG, low text contrast in `site.css`, a press kit zip that is not exactly what `press/kit-src/` builds, kit texts that differ from section 8 of the page, and German state that does not match the `noindex` switch. It looks at every `.html` and `.svg` file outside `tools/`.

`--release` additionally fails on every `TODO-` marker (in pages, comments, CSS, sitemap and kit texts) and on the word `PLACEHOLDER`, on any file or zip member that is still a generated placeholder (hashes in `tools/placeholders.json`), and on placeholder names in `press/kit-src/`.

## Hosting: GitHub Pages and Cloudflare

As set up on 2026-11-21:

1. GitHub: this repository, Pages source **GitHub Actions**, custom domain `jawohlkapitan.com`, "Enforce HTTPS" on. The workflow runs the check and publishes only when it passes; a failing push leaves the live site as it was.
2. Cloudflare DNS: two records, both proxied (orange cloud): `CNAME jawohlkapitan.com → salsquared.github.io` (Cloudflare flattens a CNAME at the apex, so no A/AAAA records are needed) and `CNAME www → salsquared.github.io`. GitHub redirects `www` and plain `http` to `https://jawohlkapitan.com` itself, so no redirect rule is needed. The mail records (MX, SPF, DKIM) are separate and untouched.
3. Order that worked: add the records as **DNS only** first; GitHub issues its certificate only while it can see its own addresses. If the certificate stays empty for minutes, remove the custom domain in the Pages settings and add it again. Once HTTPS works, enforce it, then switch the proxy on. SSL/TLS mode: **Full**. Leave "Always Use HTTPS" off: GitHub already redirects, and its certificate renewal (due before February 2027) needs plain-HTTP requests to reach it. If a renewal fails, switch the records to DNS only until it is issued.
4. Off, because each one injects a script or rewrites the page: Email Address Obfuscation, Rocket Loader, Web Analytics automatic setup, Bot Fight Mode JavaScript detections. Visitor counts come only from Cloudflare's server-side zone analytics.
5. A Response Header Transform Rule (hostname `jawohlkapitan.com`) sets:
   - `Content-Security-Policy: default-src 'self'; script-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'; frame-src https://www.youtube-nocookie.com; img-src 'self' data:; media-src 'self'; style-src 'self'`
   - `Referrer-Policy: strict-origin-when-cross-origin`
   - `X-Content-Type-Options: nosniff`

   GitHub Pages cannot set headers itself. The CSP has no `'unsafe-inline'`, which is why no page has a `style=` attribute, `<style>` block or script.
6. After any Cloudflare change, view the live page source: no `<script>`, no `/cdn-cgi/`, and `press@jawohlkapitan.com` and `support@jawohlkapitan.com` written out as they are.

The iframe uses `loading="lazy"`, so on a phone it connects to Google only when it scrolls near it. Click-to-load would need a few lines of inline script and therefore a CSP change; do not add it without deciding that first.

## Stage switches

Stage 1 (from 1 Dec 2026) is what is in the files. Both languages, both pages (`index.html`, `de/index.html`):

| Stage | Section 1 main button | Second button | Section 6 | Section 7 |
| --- | --- | --- | --- | --- |
| 1: GoFundMe | "Support on GoFundMe" / "Auf GoFundMe unterstützen", `https://TODO-GOFUNDME` | "Play the free demo" / "Gratis-Demo spielen", `https://TODO-ITCH` | shown | TikTok, YouTube, Reddit |
| 2: Coming Soon page | change label to "Wishlist on Steam" / "Auf die Steam-Wunschliste" and href to the Steam store page. Valve rules: plain text link or Valve's own badge with its trademark line, never a home-made Steam-logo button | href becomes the Steam page once the demo is there | stays, GoFundMe link moves here only | uncomment `STEAM_BLOCK` and set the URL |
| 3: Early Access | label "Buy on Steam" / "Auf Steam kaufen" | Steam | delete the block between `CAMPAIGN_BLOCK_START` and `CAMPAIGN_BLOCK_END` once the campaign ends, and the GoFundMe update link in section 5 | add Bluesky or X (`BLUESKY_BLOCK`, `X_BLOCK`) when claimed and posting |

Also at each milestone: rewrite the one dated line in section 5 (both languages), point the update link there at the latest GoFundMe update, and swap the picture. Never imply Early Access is crowdfunding, and never mention a reward for a GoFundMe gift.

## Other TODOs

Everything marked `TODO-` is caught by `--release`. Where they are:

- `TODO-VIDEO-ID` (section 3, both pages): delete the placeholder div, uncomment the iframe, put the real ID in.
- `TODO-GOFUNDME`, `TODO-GOFUNDME-UPDATE`, `TODO-ITCH` (both pages), and `TODO-STEAM-URL`, `TODO-X-HANDLE` inside the commented blocks in section 7.
- `TODO-VIDEO-URL` in `press/kit-src/README.txt`: the video link for the press kit.
- `TODO-LEGAL` boxes: notice text pending on the four notice pages (`/privacy/`, `/legal-notice/`, `/de/datenschutz/`, `/de/rechtliches/`), plus the draft YouTube paragraph on `/privacy/`.
- `TODO-LEGAL` in `de/index.html`, section 8: the German use line is pending (the English line stays until then).
- `TODO-COPY`: none open. Wording that is not settled gets a `TODO-COPY` comment line in a page, or a `TODO-COPY` line in a kit `.txt` file (left out of the zip); `--release` fails on every one.

## Switching German on

German is built but off. What is off now: `/de/` has `<meta name="robots" content="noindex">`, nothing links to it, the hreflang links and the language switch are inside `DE_LIVE` comments, the sitemap lists no German page, each German page shows a "Translation draft" note, and the German press kit texts are parked in `tools/kit-de/` instead of `press/kit-src/`.

What switching it on takes:

1. A native-speaker check of every German text: the pages under `de/` and the two files in `tools/kit-de/`. The German notice pages are still `TODO-LEGAL` boxes, and the German use line in section 8 is still the English line (`TODO-LEGAL` in `de/index.html`); both need real text first.
2. Remove the `noindex` meta tag from `de/index.html` (marked `DE_NOINDEX`) and from `de/datenschutz/index.html`. **`de/rechtliches/index.html` stays `noindex`.** Remove the `DE_DRAFT_NOTE` block on `de/index.html` and the "Translation draft" notes on the other two German pages.
3. Uncomment every `DE_LIVE` block: the hreflang `<link>` tags in `<head>` of `index.html` and `de/index.html`, the EN | DE switch in both `<header>` elements, and on the English page the `Datenschutz` footer link.
4. `sitemap.xml`: add `https://jawohlkapitan.com/de/` and `https://jawohlkapitan.com/de/datenschutz/`. Do not add `/de/rechtliches/`.
5. Move `tools/kit-de/descriptions-de.txt` and `tools/kit-de/fact-sheet-de.txt` into `press/kit-src/`, delete their first line ("Translation draft, pending native check."), change "(English)" to "(English, German)" in `press/kit-src/README.txt`, and run `python3 tools/build_press_kit.py`.
6. Run `python3 tools/check_site.py`. It knows German is live once the `noindex` is gone, and then requires the exact hreflang links and their targets, both switches, the footer link, the two sitemap entries, no draft notes, `noindex` still on `de/rechtliches/`, and German kit texts that match section 8 of `de/index.html`.

Until then the check does the opposite: it fails if a German kit text is in `press/kit-src/`, if any non-German page links to a German page, or if the sitemap lists one.

## Press kit rebuild

`press/jawohl-kapitan-press-kit.zip` is built from `press/kit-src/`, which for now holds **placeholder** pictures and the real logo as a transparent PNG (`logo.png`, no SVG yet). To rebuild: replace the files in `press/kit-src/` (drop `-PLACEHOLDER` from the names), update the text files if the page text changed, then run `python3 tools/build_press_kit.py` and commit the zip. The zip is deterministic, so an unchanged source gives an identical zip, and the check compares the zip on disk with a fresh build. Lines starting with `TODO-COPY` in the kit `.txt` files are notes and are left out of the zip. The check also compares `descriptions-en.txt`, `fact-sheet-en.txt` and `use-line.txt` with section 8 of `index.html`, so change them together.

## Legal text

All four notice pages are `TODO-LEGAL` boxes (notice text pending), except the English YouTube paragraph on `/privacy/`, which is draft text. The footer links and the pages exist; `/legal-notice/` and `/de/rechtliches/` are `noindex` and not in the sitemap.
