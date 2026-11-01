"""Builds the two sites from the content folder.

    python3 build.py   ->   dist/en  (www.yairaschresnick.com)
                            dist/he  (he.yairaschresnick.com)

You normally never run this yourself: the host runs it after every change
you save in the dashboard. Text lives in content/, images in media/,
design in styles/en.css and styles/he.css.
"""
import json, os, re, shutil, html
from pathlib import Path

ROOT = Path(__file__).parent
DIST = ROOT / "dist"
HOSTS = {"en": "https://www.yairaschresnick.com", "he": "https://he.yairaschresnick.com"}

UI = {
    "en": dict(dir="ltr", nav=[("index.html", "Projects"), ("about.html", "About"), ("contact.html", "Contact")],
               switch="עברית", prev="Previous", next="Next", back="All projects", about="About",
               cv="Full CV (PDF)", contact="Contact", email="Email", phone="Phone",
               fonts="family=Familjen+Grotesk:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans+Hebrew:wght@500",
               rights="© {y} {n}"),
    "he": dict(dir="rtl", nav=[("index.html", "פרויקטים"), ("about.html", "אודות"), ("contact.html", "צור קשר")],
               switch="English", prev="הקודם", next="הבא", back="כל הפרויקטים", about="אודות",
               cv="קורות חיים מלאים (PDF)", contact="צור קשר", email="דוא״ל", phone="טלפון",
               fonts="family=Frank+Ruhl+Libre:ital,wght@0,400;0,500;0,700&family=IBM+Plex+Sans+Hebrew:wght@400;500&family=IBM+Plex+Mono:wght@500",
               rights="© {y} {n}"),
}

e = lambda s: html.escape(s or "")


def slugify(name):
    s = re.sub(r"[^\w֐-׿-]+", "-", name.lower()).strip("-")
    return s or "project"


def src(path, up):
    """Uploaded images are stored as /media/...; make them relative so they work everywhere."""
    if not path:
        return ""
    return up + path.lstrip("/") if path.startswith("/") else path


def paras(text):
    blocks = [b.strip() for b in re.split(r"\n\s*\n", text or "") if b.strip()]
    return "".join("<p>" + e(b).replace("\n", "<br>") + "</p>" for b in blocks)


# ---------- images ----------
# Each image is served in several widths; the browser downloads only the size it needs.
WIDTHS = [480, 900, 1400, 2000]
CARD = "(max-width:700px) 100vw, 50vw"
FULL = "(max-width:1100px) 100vw, 1100px"
TILE = "(max-width:700px) 100vw, 540px"
SIZES = {}   # /media/x.png -> (width, height) of the original
WIX = re.compile(r"https://static\.wixstatic\.com/media/([^/]+)")


def optimize_media(out):
    """Copy media/ and add compressed WebP copies in several widths (x-900.webp ...)."""
    srcdir = ROOT / "media"
    if not srcdir.exists():
        return
    try:
        from PIL import Image, ImageOps
    except ImportError:
        Image = None
    for f in srcdir.rglob("*"):
        if not f.is_file():
            continue
        rel = f.relative_to(srcdir)
        dest = out / "media" / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(f, dest)
        if Image is None or f.suffix.lower() not in (".jpg", ".jpeg", ".png", ".webp"):
            continue
        with Image.open(f) as im:
            im = ImageOps.exif_transpose(im)
            SIZES["/media/" + rel.as_posix()] = im.size
            if im.mode not in ("RGB", "RGBA"):
                im = im.convert("RGBA" if "A" in im.getbands() else "RGB")
            for w in WIDTHS:
                if w >= im.width and w != WIDTHS[0]:
                    continue
                small = im if w >= im.width else im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)
                small.save(dest.with_name(f"{dest.stem}-{w}.webp"), "WEBP", quality=82, method=6)


def variants(path, up):
    """Return (fallback src, srcset) for an image path or Wix URL."""
    m = WIX.match(path or "")
    if m:
        f = m.group(1)
        mk = lambda w: f"https://static.wixstatic.com/media/{f}/v1/fit/w_{w},h_{w * 2},q_80,enc_avif,quality_auto/{f}"
        return mk(1400), ", ".join(f"{mk(w)} {w}w" for w in WIDTHS)
    if path and path.startswith("/media/") and path in SIZES:
        ow = SIZES[path][0]
        stem, base = path.rsplit(".", 1)[0], up + path.lstrip("/").rsplit(".", 1)[0]
        ws = [w for w in WIDTHS if w < ow] or [WIDTHS[0]]
        return f"{base}-{ws[-1]}.webp", ", ".join(f"{base}-{w}.webp {min(w, ow)}w" for w in ws)
    return src(path, up), ""


def pic(path, up, alt, sizes, cls="", eager=False):
    s, srcset = variants(path, up)
    attrs = [f'src="{e(s)}"', f'alt="{e(alt)}"', 'decoding="async"']
    if srcset:
        attrs += [f'srcset="{e(srcset)}"', f'sizes="{sizes}"']
    if path in SIZES:
        attrs += ['width="%d" height="%d"' % SIZES[path]]
    attrs.append('fetchpriority="high"' if eager else 'loading="lazy"')
    if cls:
        attrs.insert(0, f'class="{cls}"')
    return "<img " + " ".join(attrs) + ">"


def insta(site, up):
    url = site.get("instagram")
    if not url:
        return ""
    icon = ROOT / "media/icons/instagram.svg"
    inner = f'<img src="{up}media/icons/instagram.svg" alt="">' if icon.exists() else "IG"
    return f'<a class="insta" href="{e(url)}" aria-label="Instagram" target="_blank" rel="noopener">{inner}</a>'


def load():
    site = json.loads((ROOT / "content/site.json").read_text(encoding="utf-8"))
    projects = []
    for f in sorted((ROOT / "content/projects").glob("*.json")):
        p = json.loads(f.read_text(encoding="utf-8"))
        if p.get("draft"):
            continue
        p["slug"] = slugify(f.stem)
        projects.append(p)
    projects.sort(key=lambda p: (p.get("order") or 999, p["slug"]))
    return site, projects


def page(lng, site, path, title, body, active="", depth=0):
    u, up = UI[lng], "../" * depth
    other = "he" if lng == "en" else "en"
    nav = "".join(f'<a href="{up}{h}"{" aria-current=\"page\"" if h == active else ""}>{e(t)}</a>' for h, t in u["nav"])
    name = site[f"name_{lng}"]
    return f"""<!doctype html>
<html lang="{lng}" dir="{u['dir']}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?{u['fonts']}&display=swap">
{f'<link rel="preload" href="{up}fonts/telaviv-brutalist-regular.woff2" as="font" type="font/woff2" crossorigin>'}
<link rel="stylesheet" href="{up}base.css">
<link rel="stylesheet" href="{up}style.css">
<link rel="alternate" hreflang="{other}" href="{HOSTS[other]}/{path}">
</head>
<body>
<header class="site-head">
  <a class="brand" href="{up}index.html">{e(name)}</a>
  <nav class="nav">{nav}</nav>
  <div class="tools">{insta(site, up)}<a class="lang" href="{HOSTS[other]}/{path}" data-local="{up}../{other}/{path}" lang="{other}">{e(u['switch'])}</a></div>
</header>
<main>
{body}
</main>
<footer class="site-foot"><span>{e(u['rights'].format(y=2026, n=name))}</span></footer>
<script>
(function(){{var a=document.querySelector('.lang');if(location.protocol==='file:'){{a.href=a.getAttribute('data-local');}}}})();
/* Project images: click a tile to see it large; arrows move, Esc closes. */
(function(){{
  var tiles=[].slice.call(document.querySelectorAll('.gallery img'));if(!tiles.length)return;
  var box=document.createElement('div');box.className='lightbox';box.hidden=true;
  box.innerHTML='<img alt=""><button class="lb-close" aria-label="Close">×</button>';
  document.body.appendChild(box);var big=box.querySelector('img'),i=0;
  function show(n){{i=(n+tiles.length)%tiles.length;var t=tiles[i];
    big.removeAttribute('srcset');big.src=t.currentSrc||t.src;
    if(t.getAttribute('srcset')){{big.srcset=t.getAttribute('srcset');big.sizes='100vw';}}
    box.hidden=false;document.documentElement.style.overflow='hidden';}}
  function hide(){{box.hidden=true;document.documentElement.style.overflow='';}}
  tiles.forEach(function(t,n){{t.tabIndex=0;t.addEventListener('click',function(){{show(n);}});
    t.addEventListener('keydown',function(ev){{if(ev.key==='Enter')show(n);}});}});
  box.addEventListener('click',function(ev){{if(ev.target!==big)hide();}});
  document.addEventListener('keydown',function(ev){{if(box.hidden)return;
    if(ev.key==='Escape')hide();
    else if(ev.key==='ArrowRight')show(document.dir==='rtl'?i-1:i+1);
    else if(ev.key==='ArrowLeft')show(document.dir==='rtl'?i+1:i-1);}});
}})();
</script>
</body>
</html>
"""


def build(lng, site, projects):
    u, out = UI[lng], DIST / lng
    (out / "projects").mkdir(parents=True, exist_ok=True)
    shutil.copy(ROOT / f"styles/{lng}.css", out / "style.css")
    shutil.copy(ROOT / "styles/base.css", out / "base.css")
    if (ROOT / "fonts").exists():
        shutil.copytree(ROOT / "fonts", out / "fonts", dirs_exist_ok=True)
    optimize_media(out)

    t = lambda p, k: p.get(f"{k}_{lng}") or p.get(f"{k}_en") or ""

    cards = []
    for p in projects:
        cover = src(p.get("cover") or (p.get("images") or [""])[0], "")
        fig = pic(cover, "", t(p, "title"), CARD) if cover else ""
        cards.append(f'<a class="card" href="projects/{p["slug"]}.html"><div class="frame">{fig}'
                     f'<div class="reveal"><h2>{e(t(p, "title"))}</h2></div></div></a>')
    intro = site.get(f"intro_{lng}")
    body = (f'<section class="intro"><p>{e(intro)}</p></section>\n' if intro else "") + \
           '<section class="grid">\n' + "\n".join(cards) + "\n</section>"
    (out / "index.html").write_text(page(lng, site, "index.html", site[f"name_{lng}"], body, "index.html"), encoding="utf-8")

    for i, p in enumerate(projects):
        prv, nxt = projects[i - 1], projects[(i + 1) % len(projects)]
        hero = pic(p.get("cover"), "../", t(p, "title"), FULL, cls="hero", eager=True) if p.get("cover") else ""
        imgs = "".join(pic(x, "../", "", TILE) for x in p.get("images") or [] if x)
        meta = f'<p class="meta">{e(t(p, "meta"))}</p>' if t(p, "meta") else ""
        body = f"""<article class="project">
  {hero}
  <div class="project-text"><h1>{e(t(p, "title"))}</h1>{meta}{paras(t(p, "text"))}</div>
  <div class="gallery">{imgs}</div>
  <nav class="pager"><a href="{prv['slug']}.html">{e(u['prev'])}: {e(t(prv, 'title'))}</a><a href="../index.html">{e(u['back'])}</a><a href="{nxt['slug']}.html">{e(u['next'])}: {e(t(nxt, 'title'))}</a></nav>
</article>"""
        path = f"projects/{p['slug']}.html"
        (out / path).write_text(page(lng, site, path, f"{t(p, 'title')} · {site[f'name_{lng}']}", body, "", 1), encoding="utf-8")

    rows = "".join(f'<li><span class="yr">{e(c.get("years"))}</span><span>{e(c.get(f"text_{lng}"))}</span></li>' for c in site.get("cv") or [])
    portrait = site.get("portrait")
    cvpdf = src(site.get("cv_pdf"), "")
    body = f"""<section class="about">{pic(portrait, "", site[f"name_{lng}"], "(max-width:700px) 220px, 260px", cls="portrait", eager=True) if portrait else '<div></div>'}
<div><h1>{e(u['about'])}</h1><ol class="cv">{rows}</ol>{f'<a class="cvlink" href="{e(cvpdf)}">{e(u["cv"])}</a>' if cvpdf else ''}</div></section>"""
    (out / "about.html").write_text(page(lng, site, "about.html", f"{u['about']} · {site[f'name_{lng}']}", body, "about.html"), encoding="utf-8")

    phone = site.get(f"phone_{lng}") or ""
    body = f"""<section class="contact"><h1>{e(u['contact'])}</h1><p>{e(site.get(f'contact_{lng}'))}</p>
<dl><dt>{e(u['email'])}</dt><dd><a href="mailto:{e(site.get('email'))}">{e(site.get('email'))}</a></dd>
<dt>{e(u['phone'])}</dt><dd><a href="tel:{re.sub(r'[^0-9+]', '', phone)}" dir="ltr">{e(phone)}</a></dd></dl></section>"""
    (out / "contact.html").write_text(page(lng, site, "contact.html", f"{u['contact']} · {site[f'name_{lng}']}", body, "contact.html"), encoding="utf-8")


if __name__ == "__main__":
    site, projects = load()
    shutil.rmtree(DIST, ignore_errors=True)
    for lng in ("en", "he"):
        build(lng, site, projects)
    print(f"Built {len(projects)} projects -> dist/en, dist/he")
