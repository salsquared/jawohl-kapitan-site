#!/usr/bin/env python3
"""Checks the Jawohl Kapitaen site (stdlib only).

    python3 tools/check_site.py             # structure, security, size and press kit rules
    python3 tools/check_site.py --release   # also fails on any TODO- marker and on placeholder files

Exit 0 means every check passed; each failure is printed as one line.
"""
import hashlib
import json
import re
import struct
import sys
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_press_kit as kit  # noqa: E402  (the same routine that builds the zip)

ROOT = Path(__file__).resolve().parent.parent
RELEASE = "--release" in sys.argv[1:]

SITE = "jawohlkapitan.com"
SITE_HOSTS = (SITE, "www." + SITE)
IMG_MAX = 200 * 1024
VIDEO_MAX = 2 * 1024 * 1024
LINK_HOSTS = {  # plain outbound <a> links
    "www.tiktok.com", "www.youtube.com", "www.reddit.com", "www.gofundme.com", "store.steampowered.com",
    "bsky.app", "x.com", "policies.google.com", *SITE_HOSTS,
}
LINK_HOST_SUFFIX = (".itch.io",)
EMBED_HOST = "www.youtube-nocookie.com"
REQUIRED_PAGES = ["index.html", "de/index.html", "privacy/index.html", "de/datenschutz/index.html",
                  "legal-notice/index.html", "de/rechtliches/index.html", "404.html"]
H1_PAGES = ("index.html", "de/index.html", "privacy/index.html", "de/datenschutz/index.html")
SECTION_IDS = ["top", "orders", "video", "screenshots", "status", "support", "follow", "press"]
URL_ATTRS = ("href", "src", "poster", "action", "formaction", "ping", "manifest", "background", "cite",
             "longdesc", "xlink:href")
SKIP_DIRS = {".git", "tools"}
MARKER = re.compile(r"TODO-[A-Z0-9][A-Z0-9-]*|PLACEHOLDER")

errors = []


def fail(where, msg):
    errors.append(f"{where}: {msg}")


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tags = []      # (tag, attrs dict, line)
        self.comments = []
        self.text = []

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, {k: (v or "") for k, v in attrs}, self.getpos()[0]))

    handle_startendtag = handle_starttag

    def handle_comment(self, data):
        self.comments.append(data)

    def handle_data(self, data):
        self.text.append(data)


class Press(HTMLParser):
    """Pulls the press kit texts (section 8) out of a home page."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.inside = self.in_long = False
        self.cell = self.buf = self.row = None
        self.facts, self.short, self.long, self.use = [], None, [], None

    def handle_starttag(self, tag, attrs):
        a = {k: (v or "") for k, v in attrs}
        classes = a.get("class", "").split()
        if tag == "section":
            self.inside = a.get("id") == "press"
        if not self.inside:
            return
        if tag == "tr":
            self.row = []
        elif tag in ("th", "td"):
            self.cell, self.buf = tag, []
        elif tag == "div" and "desc" in classes:
            self.in_long = True
        elif tag == "p":
            if "desc" in classes:
                self.cell, self.buf = "short", []
            elif "use-line" in classes:
                self.cell, self.buf = "use", []
            elif self.in_long:
                self.cell, self.buf = "long", []

    def handle_data(self, data):
        if self.buf is not None:
            self.buf.append(data)

    def handle_endtag(self, tag):
        if tag == "section":
            self.inside = False
        if not self.inside:
            return
        text = " ".join("".join(self.buf or []).split())
        if tag in ("th", "td") and self.cell == tag:
            self.row.append(text)
            self.cell = self.buf = None
        elif tag == "tr" and self.row is not None:
            self.facts.append(self.row)
            self.row = None
        elif tag == "div":
            self.in_long = False
        elif tag == "p" and self.cell in ("short", "use", "long"):
            if self.cell == "long":
                self.long.append(text)
            elif self.cell == "short":
                self.short = text
            else:
                self.use = text
            self.cell = self.buf = None


def parse(rel):
    p = Page()
    raw = (ROOT / rel).read_text(encoding="utf-8")
    p.feed(raw)
    p.raw = raw
    return p


def site_files(*suffixes):
    """Every file with one of these suffixes outside .git and tools/."""
    return sorted(f.relative_to(ROOT).as_posix() for f in ROOT.rglob("*")
                  if f.is_file() and f.suffix.lower() in suffixes
                  and not SKIP_DIRS & set(f.relative_to(ROOT).parts))


def is_todo_host(host):
    return host.lower().startswith("todo-")


def local_target(page_rel, url):
    """Map a URL to a repo file path, or None when it is not local."""
    parts = urlsplit(url)
    if parts.netloc or parts.scheme:
        if parts.scheme not in ("", "http", "https") or parts.netloc not in SITE_HOSTS:
            return None
        path = parts.path or "/"
    else:
        path = parts.path
        if not path:
            return Path(page_rel)
        if not path.startswith("/"):
            path = "/" + (Path(page_rel).parent / path).as_posix()
    rel = path.lstrip("/")
    cand = ROOT / rel
    if path.endswith("/") or cand.is_dir():
        rel = (rel.rstrip("/") + "/index.html").lstrip("/")
    return Path(rel)


def jpeg_size(path):
    d = path.read_bytes()
    i = 2
    while i < len(d):
        if d[i] != 0xFF:
            i += 1
            continue
        m = d[i + 1]
        if 0xC0 <= m <= 0xCF and m not in (0xC4, 0xC8, 0xCC):
            h, w = struct.unpack(">HH", d[i + 5:i + 9])
            return w, h
        i += 2 + struct.unpack(">H", d[i + 2:i + 4])[0]
    return None


def luminance(hexcol):
    h = hexcol.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    ch = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    ch = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in ch]
    return 0.2126 * ch[0] + 0.7152 * ch[1] + 0.0722 * ch[2]


def contrast(a, b):
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def noindex(p):
    return any(t == "meta" and a.get("name") == "robots" and "noindex" in a.get("content", "").lower()
               for t, a, _ in p.tags)


def page_urls(tag, attrs):
    """Every (attribute, url) a tag can make the browser fetch or follow."""
    urls = [(k, attrs[k]) for k in URL_ATTRS if k in attrs]
    if tag == "object" and "data" in attrs:
        urls.append(("data", attrs["data"]))
    if "srcset" in attrs:
        urls += [("srcset", part.strip().split()[0]) for part in attrs["srcset"].split(",") if part.strip()]
    if tag == "meta":
        content = attrs.get("content", "")
        if attrs.get("http-equiv", "").lower() == "refresh":
            target = re.split(r"[;,]", content, maxsplit=1)[1:]
            if target:
                urls.append(("refresh", re.sub(r"^\s*url\s*=\s*['\"]?", "", target[0], flags=re.I).strip("'\" ")))
        elif content.startswith(("http", "//")):
            urls.append(("content", content))
    return urls


def check_url(rel, loc, tag, k, url, pages):
    url = url.strip()
    if re.search(r"[\x00-\x20\\]", url):
        fail(loc, f"{tag} {k} has whitespace, control characters or a backslash: {url!r}")
        return
    parts = urlsplit(url)
    if parts.scheme == "mailto":
        return
    if parts.scheme not in ("", "http", "https"):
        fail(loc, f"unexpected URL scheme in {url!r}")
        return
    host = parts.netloc  # exact: user@host tricks and ports do not match
    if tag == "iframe" and host != EMBED_HOST:
        fail(loc, f"iframe from {host or 'a local path'}; only {EMBED_HOST} is allowed")
        return
    if host:
        if tag == "iframe":
            return
        if tag == "a":
            if not (host in LINK_HOSTS or host.endswith(LINK_HOST_SUFFIX) or is_todo_host(host)):
                fail(loc, f"outbound link to {host} is not on the allowed list")
                return
        elif host not in SITE_HOSTS:
            fail(loc, f"{tag} {k} loads from {host}; only the site itself is allowed")
            return
    target = local_target(rel, url)
    if target is None:
        return
    if not (ROOT / target).is_file():
        fail(loc, f"broken internal {k} {url!r} (no file {target})")
    elif parts.fragment and str(target).endswith(".html"):
        tp = pages.get(target.as_posix()) or parse(target.as_posix())
        if parts.fragment not in {a["id"] for _, a, _ in tp.tags if "id" in a}:
            fail(loc, f"broken anchor {url!r}")


# ---------- parse every page
html_files = site_files(".html")
svg_files = site_files(".svg")
pages = {}
for rel in REQUIRED_PAGES:
    if not (ROOT / rel).exists():
        fail(rel, "page is missing")
for rel in html_files:
    pages[rel] = parse(rel)
svgs = {rel: parse(rel) for rel in svg_files}

# ---------- per page rules
for rel, p in list(pages.items()) + list(svgs.items()):
    is_svg = rel in svgs
    ids = [a["id"] for _, a, _ in p.tags if "id" in a]
    for i in set(ids):
        if ids.count(i) > 1:
            fail(rel, f"duplicate id {i!r}")

    if re.search(r"<script", p.raw, re.I):
        fail(rel, "contains a <script> tag (also not allowed inside comments)")
    for tag, attrs, line in p.tags:
        loc = f"{rel}:{line}"
        if tag == "style":
            fail(loc, "<style> block")
        if "style" in attrs:
            fail(loc, "inline style= attribute")
        for k in attrs:
            if k.startswith("on"):
                fail(loc, f"inline event handler {k}=")
        if tag in ("object", "embed", "applet", "base"):
            fail(loc, f"<{tag}> is not allowed")
        if tag == "iframe" and "srcdoc" in attrs:
            fail(loc, "<iframe srcdoc> is not allowed")
        if is_svg:
            continue
        if tag == "img" and not attrs.get("alt", "").strip():
            fail(loc, "<img> without alt text")
        if tag == "iframe" and not attrs.get("title"):
            fail(loc, "<iframe> without title")
        if tag == "video":
            for need in ("muted", "loop", "playsinline", "autoplay", "controls", "poster"):
                if need not in attrs:
                    fail(loc, f"<video> without {need}")
        if tag == "a" and attrs.get("href", "").startswith("http") and "target" in attrs:
            fail(loc, "target= on a link (use none)")

    # URLs: collected from the tags (comments are not tags, so they are skipped)
    for tag, attrs, line in p.tags:
        for k, url in page_urls(tag, attrs):
            check_url(rel, f"{rel}:{line}", tag, k, url, pages)

    if is_svg:
        continue
    tags = {t for t, _, _ in p.tags}
    html_tag = next((a for t, a, _ in p.tags if t == "html"), {})
    if not html_tag.get("lang"):
        fail(rel, "<html> has no lang")
    if not any(t == "meta" and a.get("name") == "viewport" for t, a, _ in p.tags):
        fail(rel, "no viewport meta")
    if "title" not in tags:
        fail(rel, "no <title>")
    if "main" not in tags:
        fail(rel, "no <main> landmark")
    if "footer" not in tags and rel != "404.html":
        fail(rel, "no <footer> landmark")
    if sum(1 for t, _, _ in p.tags if t == "h1") != 1 and rel in H1_PAGES:
        fail(rel, "needs exactly one <h1>")

# ---------- the two home pages
en, de = pages.get("index.html"), pages.get("de/index.html")
sitemap = (ROOT / "sitemap.xml").read_text(encoding="utf-8") if (ROOT / "sitemap.xml").exists() else ""
locs = set(re.findall(r"<loc>([^<]*)</loc>", sitemap))
de_pages = {r: p for r, p in pages.items() if r.startswith("de/")}
kit_src = ROOT / "press" / "kit-src"

if en and de:
    sec_en = [a["id"] for t, a, _ in en.tags if t == "section" and "id" in a]
    sec_de = [a["id"] for t, a, _ in de.tags if t == "section" and "id" in a]
    if sec_en != sec_de:
        fail("index.html vs de/index.html", f"section ids differ: {sec_en} / {sec_de}")
    if sec_en != SECTION_IDS:
        fail("index.html", f"section ids {sec_en} are not the nine-section order {SECTION_IDS} (+footer)")
    for rel, p in (("index.html", en), ("de/index.html", de)):
        if not any(t == "footer" and a.get("id") == "footer" for t, a, _ in p.tags):
            fail(rel, "no footer#footer (section 9)")
        for need in ("og:title", "og:description", "og:image", "og:url", "og:type"):
            if not any(t == "meta" and a.get("property") == need and a.get("content") for t, a, _ in p.tags):
                fail(rel, f"missing {need}")
        for need in ("twitter:card", "twitter:title", "twitter:description", "twitter:image"):
            if not any(t == "meta" and a.get("name") == need and a.get("content") for t, a, _ in p.tags):
                fail(rel, f"missing {need}")
        for t, a, _ in p.tags:
            if t == "meta" and a.get("property") in ("og:image", "og:url") or t == "meta" and a.get("name") == "twitter:image":
                if not a["content"].startswith("https://" + SITE + "/"):
                    fail(rel, f"{a.get('property') or a.get('name')} must be an absolute https://{SITE}/ URL")
        if not any(t == "link" and a.get("rel") == "canonical" for t, a, _ in p.tags):
            fail(rel, "no canonical link")
        if not any(t == "meta" and a.get("name") == "description" and a.get("content") for t, a, _ in p.tags):
            fail(rel, "no meta description")
        if "TODO-VIDEO-ID" not in p.raw and not any(t == "iframe" for t, _, _ in p.tags):
            fail(rel, "section 3 has neither an iframe nor the TODO-VIDEO-ID block")

    ogs = [a["content"] for t, a, _ in en.tags if t == "meta" and a.get("property") == "og:image"]
    if ogs:
        f = ROOT / urlsplit(ogs[0]).path.lstrip("/")
        if not f.is_file():
            fail("index.html", "og:image file is missing")
        elif f.suffix.lower() not in (".jpg", ".jpeg"):
            fail("index.html", "og:image must be a JPEG, crawlers do not read WebP")
        else:
            size = jpeg_size(f)
            if size != (1200, 630):
                fail("index.html", f"og:image is {size}, expected (1200, 630)")

    # German switch state
    def alternates(p):
        return {a["hreflang"]: a.get("href") for t, a, _ in p.tags
                if t == "link" and a.get("rel") == "alternate" and a.get("hreflang")}

    de_live = not noindex(de)
    german_kit = [kit_src / "descriptions-de.txt", kit_src / "fact-sheet-de.txt"]
    if "de/rechtliches/index.html" in de_pages and not noindex(de_pages["de/rechtliches/index.html"]):
        fail("de/rechtliches/index.html", "this page must stay noindex")
    if de_live:
        want = {"en": f"https://{SITE}/", "de": f"https://{SITE}/de/", "x-default": f"https://{SITE}/"}
        for rel, p in (("index.html", en), ("de/index.html", de)):
            if alternates(p) != want:
                fail(rel, f"DE is live but the hreflang links are {alternates(p)}; need exactly {want}")
        if not any(t == "a" and a.get("href") == "/de/" and a.get("hreflang") == "de" for t, a, _ in en.tags):
            fail("index.html", "DE is live but there is no EN|DE switch linking /de/")
        if not any(t == "a" and a.get("href") == "/" and a.get("hreflang") == "en" for t, a, _ in de.tags):
            fail("de/index.html", "DE is live but there is no switch back to English")
        if not any(t == "a" and a.get("href") == "/de/datenschutz/" for t, a, _ in en.tags):
            fail("index.html", "DE is live but the Datenschutz footer link is missing")
        for url in (f"https://{SITE}/de/", f"https://{SITE}/de/datenschutz/"):
            if url not in locs:
                fail("sitemap.xml", f"DE is live but <loc>{url}</loc> is not listed")
        for rel, p in de_pages.items():
            if rel != "de/rechtliches/index.html" and noindex(p):
                fail(rel, "DE is live but this page is still noindex")
            if "Translation draft" in " ".join(p.text):
                fail(rel, "DE is live but the 'Translation draft' note is still shown")
        for f in german_kit:
            if not f.is_file():
                fail(f.relative_to(ROOT).as_posix(), "DE is live but the German press kit text is missing")
    else:
        for rel, p in de_pages.items():
            if not noindex(p):
                fail(rel, "DE is not live, so this page needs noindex")
            if "Translation draft" not in " ".join(p.text):
                fail(rel, "German is not live and the 'Translation draft, pending native check' note is missing")
        if not any("DE_LIVE" in c for c in en.comments):
            fail("index.html", "DE is not live but the DE_LIVE comment block is missing")
        for rel, p in pages.items():
            if rel.startswith("de/"):
                continue
            for t, a, line in p.tags:
                if t == "link" and a.get("rel") == "alternate" and a.get("hreflang"):
                    fail(f"{rel}:{line}", "hreflang link while German is not live (put it in the DE_LIVE comment)")
                if t in ("a", "link") and "href" in a:
                    target = local_target(rel, a["href"].strip())
                    if target is not None and target.as_posix().startswith("de/"):
                        fail(f"{rel}:{line}", f"links to {a['href']!r} (a German page) while German is not live "
                                              "(put it in the DE_LIVE comment)")
        if any(u.startswith(f"https://{SITE}/de/") for u in locs):
            fail("sitemap.xml", "lists a German page while German is not live")
        for f in german_kit:
            if f.exists():
                fail(f.relative_to(ROOT).as_posix(), "German press kit text in the kit sources while German is not live")

    # the sitemap lists only real, indexable pages
    for url in sorted(locs):
        parts = urlsplit(url)
        target = local_target("index.html", url)
        if parts.scheme != "https" or parts.netloc != SITE or target is None or target.as_posix() not in pages:
            fail("sitemap.xml", f"<loc>{url}</loc> is not a page of this site")
        elif noindex(pages[target.as_posix()]):
            fail("sitemap.xml", f"lists noindex page {url}")

    # ---------- press kit texts against section 8
    def press_checks(rel, p, fact_file, desc_file, use_file=None):
        press = Press()
        press.feed(p.raw)
        files = [fact_file, desc_file] + ([use_file] if use_file else [])
        for f in files:
            if not f.is_file():
                fail(f.relative_to(ROOT).as_posix(), "press kit text is missing")
                return
        facts = "".join(f"{r[0]}: {r[1]}\n" for r in press.facts if len(r) == 2)
        desc = "SHORT\n" + (press.short or "") + "\n\nLONG\n" + "\n\n".join(press.long) + "\n"
        pairs = [(fact_file, facts, "fact sheet"), (desc_file, desc, "descriptions")]
        if use_file:
            pairs.append((use_file, (press.use or "") + "\n", "use line"))
        for f, expected, what in pairs:
            if kit.strip_notes(f.read_text(encoding="utf-8")) != expected:
                fail(f.relative_to(ROOT).as_posix(), f"differs from the {what} in section 8 of {rel}")

    press_checks("index.html", en, kit_src / "fact-sheet-en.txt", kit_src / "descriptions-en.txt",
                 kit_src / "use-line.txt")
    if de_live:
        press_checks("de/index.html", de, kit_src / "fact-sheet-de.txt", kit_src / "descriptions-de.txt")

# ---------- the zip against its sources
zip_path = kit.OUT
if not zip_path.is_file():
    fail("press/jawohl-kapitan-press-kit.zip", "file is missing")
elif zip_path.read_bytes() != kit.zip_bytes():
    fail("press/jawohl-kapitan-press-kit.zip", "is not what press/kit-src/ builds; run tools/build_press_kit.py")

# ---------- files
for name in ("CNAME", ".nojekyll", "robots.txt", "sitemap.xml", "404.html", "README.md", "PLACEHOLDERS.md",
             "assets/site.css", ".github/workflows/check.yml"):
    if not (ROOT / name).exists():
        fail(name, "file is missing")
if (ROOT / "CNAME").exists() and (ROOT / "CNAME").read_text().strip() != SITE:
    fail("CNAME", f"must contain {SITE}")
ga = ROOT / ".gitattributes"
if ga.exists() and "lfs" in ga.read_text().lower():
    fail(".gitattributes", "Git LFS is on; GitHub Pages does not serve LFS files")

for f in sorted(ROOT.rglob("*")):
    if not f.is_file() or SKIP_DIRS & set(f.relative_to(ROOT).parts):
        continue
    rel = f.relative_to(ROOT).as_posix()
    ext = f.suffix.lower()
    if ext in (".webp", ".jpg", ".jpeg", ".png", ".gif") and f.stat().st_size > IMG_MAX:
        fail(rel, f"image is {f.stat().st_size // 1024} KB, limit {IMG_MAX // 1024} KB")
    if ext in (".mp4", ".webm") and f.stat().st_size > VIDEO_MAX:
        fail(rel, f"clip is {f.stat().st_size // 1024} KB, limit {VIDEO_MAX // 1024} KB")
    if ext in (".js", ".mjs"):
        fail(rel, "script file in the site")

css = ROOT / "assets" / "site.css"
if css.exists():
    ctext = css.read_text(encoding="utf-8")
    if re.search(r"@import|url\(\s*['\"]?(https?:)?//", ctext):
        fail("assets/site.css", "loads something from another host")
    var = dict(re.findall(r"--([\w-]+):\s*(#[0-9a-fA-F]{3,6})", ctext))
    pairs = [("text", "bg"), ("muted", "bg"), ("muted", "surface"), ("accent", "bg"), ("accent-text", "accent"),
             ("text", "surface-2"), ("accent", "surface")]
    for a, b in pairs:
        if a in var and b in var and contrast(var[a], var[b]) < 4.5:
            fail("assets/site.css", f"contrast {a} on {b} is {contrast(var[a], var[b]):.1f}, need 4.5")

# ---------- release gate
if RELEASE:
    scan = html_files + svg_files + ["assets/site.css", "robots.txt", "sitemap.xml"]
    scan += sorted(f.relative_to(ROOT).as_posix() for f in kit_src.glob("*.txt"))
    for rel in scan:
        if not (ROOT / rel).is_file():
            continue
        text = (ROOT / rel).read_text(encoding="utf-8")
        for m in MARKER.finditer(text):
            fail(rel, f"release: {m.group(0)} is still there (line {text[:m.start()].count(chr(10)) + 1})")
    manifest = ROOT / "tools" / "placeholders.json"
    if manifest.exists():
        placeholders = json.loads(manifest.read_text())
        for rel, digest in placeholders.items():
            f = ROOT / rel
            if f.exists() and hashlib.sha256(f.read_bytes()).hexdigest() == digest:
                fail(rel, "release: still the generated placeholder file")
        digests = set(placeholders.values())
        if zip_path.is_file():
            with zipfile.ZipFile(zip_path) as z:
                for name in z.namelist():
                    if "PLACEHOLDER" in name or hashlib.sha256(z.read(name)).hexdigest() in digests:
                        fail("press/jawohl-kapitan-press-kit.zip", f"release: member {name} is still a placeholder")
    else:
        fail("tools/placeholders.json", "release: manifest missing")
    for f in kit_src.glob("*PLACEHOLDER*"):
        fail(f.relative_to(ROOT).as_posix(), "release: placeholder in the press kit sources")

if errors:
    print(f"FAILED: {len(errors)} problem(s)")
    for e in errors:
        print("  " + e)
    sys.exit(1)
print("OK: all checks passed" + (" (release mode)" if RELEASE else ""))
