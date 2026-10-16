#!/usr/bin/env python3
"""Build tokens.css and the Savas brand standards page/PDFs from tokens.json.

    python3 build.py          # tokens.css + Savas-Brand-Standards.html
    python3 build.py --pdf    # also the paged PDF and the single long PDF
"""
import io, json, sys
from pathlib import Path

HERE = Path(__file__).parent
T = json.loads((HERE / "tokens.json").read_text())


# ── helpers ────────────────────────────────────────────────────────────────
def rgb(hexv):
    h = hexv.lstrip("#")[:6]
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def lum(hexv):
    def f(c): return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (f(c) for c in rgb(hexv))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def grade(r):
    return "AAA" if r >= 7 else "AA" if r >= 4.5 else "AA Large" if r >= 3 else "Fail"


def css_color(v):
    v = v.lstrip("#")
    if len(v) == 8:
        a = round(int(v[6:], 16) / 255, 2)
        return f"rgba({int(v[0:2],16)},{int(v[2:4],16)},{int(v[4:6],16)},{a})"
    return "#" + v


def flat(group, prefix=""):
    for k, v in group.items():
        if k.startswith("$"): continue
        if "$value" in v: yield f"{prefix}{k}", v
        else: yield from flat(v, f"{prefix}{k}-")


# ── tokens.css ─────────────────────────────────────────────────────────────
lines = [":root {"]
for name, t in flat(T["color"]):
    if t["$value"].startswith("{"): continue
    lines.append(f"  --sv-color-{name}: {css_color(t['$value'])};")
for name, t in flat(T["font"]["family"]):
    stack = {"sans": "'Manrope', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
             "serif": "'PT Serif', Georgia, 'Times New Roman', serif",
             "mono": "'SF Mono', SFMono-Regular, Consolas, Menlo, monospace"}[name]
    lines.append(f"  --sv-font-{name}: {stack};")
for group in ("radius", "space", "shadow"):
    for name, t in flat(T[group]):
        lines.append(f"  --sv-{group}-{name}: {t['$value']};")
lines.append("}")
(HERE / "tokens.css").write_text("\n".join(lines) + "\n")

# ── page ───────────────────────────────────────────────────────────────────
C = {n: t["$value"] for n, t in flat(T["color"]) if not t["$value"].startswith("{")}
WHITE, INK = C["paper-white"], C["neutral-ink"]


def chip(name, hexv, desc=""):
    hx = hexv[:7]
    dark = lum(hx) < 0.35
    border = "border:1.5px solid var(--sv-color-line-default);" if lum(hx) > 0.8 else ""
    return (f'<div class="chip"><div class="sw" style="background:{css_color(hexv)};{border}"></div>'
            f'<div class="hex">{hexv.upper() if len(hexv)==7 else hx.upper()+" · "+desc}</div>'
            f'<div class="nm">{name}</div></div>')


def group(label, keys, descs=True):
    out = f'<p class="label">{label}</p><div class="chips">'
    for k in keys:
        raw = C[k]
        out += chip(k.split("-", 1)[1].replace("-", " ").title(), raw[:7], "")
        if descs:
            d = next(t.get("$description", "") for n, t in flat(T["color"]) if n == k)
            out = out[:-len("</div>")] + f'<div class="ds">{d}</div></div>'
    return out + "</div>"


pairs = [
    ("Ink on White", INK, WHITE), ("Graphite on White", C["neutral-graphite"], WHITE),
    ("Mute on White", C["neutral-mute"], WHITE), ("Mint-text on White", C["accent-mint-text"], WHITE),
    ("Coral-text on White", C["accent-coral-text"], WHITE), ("Mint-ink on White", C["accent-mint-ink"], WHITE),
    ("Ink on Mint", INK, C["accent-mint"]), ("Ink on Coral", INK, C["accent-coral"]),
    ("Ink on Marigold", INK, C["accent-marigold"]), ("Ink on Lavender", INK, C["accent-lavender"]),
    ("Mint on Ink", C["accent-mint"], INK), ("White on Ink", WHITE, INK),
]
rows = ""
for n, fg, bg in pairs:
    r = contrast(fg[:7], bg[:7]); g = grade(r)
    cls = "ok" if g.startswith("AA") and g != "AA Large" else "warn" if g == "AA Large" else "bad"
    rows += (f'<tr><td><span class="demo" style="background:{bg};color:{fg}">Aa</span> {n}</td>'
             f'<td>{fg.upper()} / {bg.upper()}</td><td>{r:.2f}:1</td><td><span class="pill {cls}">{g}</span></td></tr>')

type_rows = ""
for name, s in T["type"].items():
    if name.startswith("$"): continue
    fam = f"var(--sv-font-{s['family']})"
    st = (f"font-family:{fam};font-size:{s['size']}px;font-weight:{s['weight']};line-height:{s['lineHeight']};"
          f"letter-spacing:{s['tracking']}em;" + (f"text-transform:{s['transform']};" if s.get('transform') else "")
          + ("font-style:italic;" if s.get("italic") else ""))
    color = C["accent-coral-text"] if name == "flourish" else C["neutral-graphite"] if name.startswith("body") else INK
    meta = f"{T['font']['family'][s['family']]['$value']} · {s['size']}px · {s['weight']} · LH {s['lineHeight']} · {s['tracking']}em"
    type_rows += (f'<div class="trow"><div class="tmeta"><b>{name}</b><span>{meta}</span></div>'
                  f'<div style="{st}color:{color}">{s["sample"]}</div></div>')

radius = "".join(
    f'<div class="rad"><div class="rbox" style="border-radius:{t["$value"]}"></div><b>{n}</b><span>{t["$value"]}</span></div>'
    for n, t in flat(T["radius"]))
space = "".join(
    f'<div class="srow"><span>space-{n}</span><div class="sbar" style="width:{t["$value"]}"></div><span>{t["$value"]}</span></div>'
    for n, t in flat(T["space"]))

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=PT+Serif:ital,wght@0,400;0,700;1,400&display=swap');
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html,body{background:var(--sv-color-paper-white);color:var(--sv-color-neutral-graphite);font-family:var(--sv-font-sans);-webkit-font-smoothing:antialiased;line-height:1.6}
::selection{background:var(--sv-color-accent-mint);color:var(--sv-color-neutral-ink)}
header{background:var(--sv-color-neutral-ink);padding:4rem 2rem 3.5rem}
.hi{max-width:1100px;margin:0 auto}
.logo{display:inline-flex;align-items:center;gap:.5rem;margin-bottom:1.5rem}
.dot{width:10px;height:10px;border-radius:50%;background:var(--sv-color-accent-mint)}
.logo span{font-size:.75rem;font-weight:700;letter-spacing:.15em;text-transform:uppercase;color:var(--sv-color-accent-mint)}
h1{font-size:clamp(2rem,5vw,3.4rem);font-weight:800;color:#fff;letter-spacing:-.02em;line-height:1.1}
h1 em{font-family:var(--sv-font-serif);font-weight:400;color:var(--sv-color-accent-coral);letter-spacing:-.02em}
header p{color:rgba(255,255,255,.55);margin-top:.9rem;font-weight:500;font-size:1.05rem}
nav{display:flex;gap:.5rem;flex-wrap:wrap;padding:1rem 2rem;border-bottom:1px solid var(--sv-color-line-subtle);background:var(--sv-color-paper-warm);position:sticky;top:0;z-index:5}
nav a{color:var(--sv-color-neutral-ink);text-decoration:none;font-size:.8rem;font-weight:600;padding:.35rem .9rem;border-radius:9999px;border:1.5px solid var(--sv-color-line-subtle)}
nav a:hover{background:var(--sv-color-accent-mint);border-color:var(--sv-color-accent-mint)}
main{max-width:1100px;margin:0 auto;padding:3rem 2rem 5rem}
section{margin-bottom:4.5rem;scroll-margin-top:5rem}
.eyebrow{font-size:.78rem;font-weight:700;letter-spacing:.18em;text-transform:uppercase;color:var(--sv-color-neutral-mute);margin-bottom:.4rem}
h2{font-size:2.4rem;font-weight:700;letter-spacing:-.025em;line-height:1.1;color:var(--sv-color-neutral-ink);margin-bottom:.6rem;padding-bottom:1rem;border-bottom:3px solid var(--sv-color-accent-mint)}
.lead{max-width:680px;margin:1.2rem 0 2rem;font-size:1.05rem}
.label{font-size:.65rem;font-weight:800;letter-spacing:.12em;text-transform:uppercase;color:var(--sv-color-accent-mint-text);margin:1.8rem 0 .7rem}
.chips{display:flex;flex-wrap:wrap;gap:1.1rem}
.chip{width:150px}
.sw{height:84px;border-radius:12px;margin-bottom:.5rem}
.hex{font-family:var(--sv-font-mono);font-size:.75rem;color:var(--sv-color-neutral-ink)}
.nm{font-weight:700;font-size:.85rem;color:var(--sv-color-neutral-ink)}
.ds{font-size:.72rem;color:var(--sv-color-neutral-mute);line-height:1.35;margin-top:.15rem}
table{width:100%;border-collapse:collapse;font-size:.88rem;margin-top:1rem}
th{text-align:left;padding:.55rem .75rem;background:var(--sv-color-line-wash);color:var(--sv-color-accent-mint-text);font-size:.65rem;font-weight:800;text-transform:uppercase;letter-spacing:.1em}
td{padding:.55rem .75rem;border-bottom:1px solid var(--sv-color-line-wash);vertical-align:middle}
.demo{display:inline-flex;width:30px;height:24px;border-radius:5px;align-items:center;justify-content:center;font-weight:800;font-size:.8rem;margin-right:.5rem;border:1px solid var(--sv-color-line-subtle)}
.pill{font-size:.7rem;font-weight:800;padding:.15rem .6rem;border-radius:9999px}
.ok{background:var(--sv-color-accent-mint);color:var(--sv-color-neutral-ink)}
.warn{background:var(--sv-color-accent-marigold);color:var(--sv-color-neutral-ink)}
.bad{background:var(--sv-color-accent-coral);color:var(--sv-color-neutral-ink)}
.trow{display:grid;grid-template-columns:260px 1fr;gap:1.5rem;align-items:center;padding:1.1rem 0;border-bottom:1px solid var(--sv-color-line-wash)}
.tmeta b{display:block;font-size:.85rem;color:var(--sv-color-neutral-ink)}
.tmeta span{font-family:var(--sv-font-mono);font-size:.68rem;color:var(--sv-color-neutral-mute)}
.rads{display:flex;gap:2rem;flex-wrap:wrap}
.rad{display:flex;flex-direction:column;gap:.2rem;font-size:.8rem}
.rad span{font-family:var(--sv-font-mono);font-size:.7rem;color:var(--sv-color-neutral-mute)}
.rbox{width:84px;height:84px;background:var(--sv-color-line-wash);border:2px solid var(--sv-color-neutral-ink);margin-bottom:.4rem}
.srow{display:flex;align-items:center;gap:1rem;font-family:var(--sv-font-mono);font-size:.72rem;padding:.25rem 0}
.srow span:first-child{width:80px}
.sbar{height:14px;background:var(--sv-color-accent-mint);border-radius:3px}
.demos{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:1.5rem}
.card{background:#fff;border:1.5px solid var(--sv-color-line-subtle);border-radius:16px;overflow:hidden}
.card-h{display:flex;align-items:center;gap:.75rem;padding:1rem 1.25rem;border-bottom:1.5px solid var(--sv-color-line-subtle);background:var(--sv-color-line-wash)}
.card-i{width:32px;height:32px;border-radius:8px;background:var(--sv-color-accent-mint)}
.card-h b{font-size:1rem;color:var(--sv-color-neutral-ink)}
.card-b{padding:1.25rem;display:flex;flex-direction:column;gap:.9rem;font-size:.9rem}
code{font-family:var(--sv-font-mono);font-size:.82rem;background:var(--sv-color-line-wash);padding:.2rem .55rem;border-radius:4px;border:1px solid var(--sv-color-line-subtle);color:var(--sv-color-neutral-ink)}
.btn{display:inline-block;font-weight:700;font-size:.85rem;padding:.6rem 1.3rem;border-radius:9999px;text-decoration:none;border:1.5px solid var(--sv-color-neutral-ink);margin-right:.5rem}
.btn.p{background:var(--sv-color-accent-mint);border-color:var(--sv-color-accent-mint);color:var(--sv-color-neutral-ink)}
.btn.d{background:var(--sv-color-neutral-ink);color:var(--sv-color-accent-mint)}
.btn.o{color:var(--sv-color-neutral-ink)}
.num{display:inline-flex;width:22px;height:22px;border-radius:50%;background:var(--sv-color-accent-mint);color:var(--sv-color-neutral-ink);font-size:.65rem;font-weight:800;align-items:center;justify-content:center;margin-right:.5rem}
.flourish{font-family:var(--sv-font-serif);font-style:italic;color:var(--sv-color-accent-coral-text);font-size:1.12em}
.rules{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:1.5rem}
.rule{border-left:4px solid var(--sv-color-accent-mint);padding:.2rem 0 .2rem 1rem}
.rule.no{border-color:var(--sv-color-accent-coral)}
.rule b{display:block;color:var(--sv-color-neutral-ink);margin-bottom:.2rem}
.flow{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:1rem;margin-top:1rem}
.flow div{background:var(--sv-color-paper-warm);border:1.5px solid var(--sv-color-line-subtle);border-radius:16px;padding:1.2rem}
.flow b{display:block;color:var(--sv-color-neutral-ink);margin:.4rem 0 .2rem}
footer{background:var(--sv-color-neutral-ink);color:rgba(255,255,255,.4);text-align:center;padding:2rem;font-size:.78rem}
footer span{color:var(--sv-color-accent-mint)}
@media(max-width:700px){.trow{grid-template-columns:1fr}}
@media print{nav{position:static}section{break-inside:avoid-page}}
"""

HTML = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Savas Labs — Brand Standards</title>
<style>{(HERE/'tokens.css').read_text()}{CSS}</style></head><body>
<header><div class="hi"><div class="logo"><div class="dot"></div><span>Savas Labs</span></div>
<h1>Brand Standards for the web, <em>in one place</em></h1>
<p>Color, type, shape and components. Generated from tokens.json, the same file Figma Variables sync with.</p></div></header>
<nav><a href="#colors">Color</a><a href="#contrast">Contrast</a><a href="#type">Typography</a><a href="#shape">Shape &amp; space</a><a href="#components">Components</a><a href="#rules">Usage rules</a><a href="#workflow">Figma workflow</a></nav>
<main>

<section id="colors"><p class="eyebrow">01</p><h2>Color palette</h2>
<p class="lead">Ink and white carry the page. Mint is the signature accent; coral is a spice used for emphasis. Each accent has a darker <code>-text</code> sibling for small text.</p>
{group("Paper", ["paper-white","paper-warm","paper-cream"])}
{group("Ink &amp; neutrals", ["neutral-ink","neutral-graphite","neutral-mute"])}
{group("Accents", ["accent-mint","accent-mint-ink","accent-mint-text","accent-coral","accent-coral-text","accent-marigold","accent-lavender","accent-ojo-blue"])}
{group("Lines (ink at opacity)", ["line-wash","line-subtle","line-default","line-strong"], descs=True)}
</section>

<section id="contrast"><p class="eyebrow">02</p><h2>Contrast</h2>
<p class="lead">Computed from the token values (WCAG 2.x). Anything marked AA Large is for headings 24px+ or rules only.</p>
<table><tr><th>Pair</th><th>Foreground / Background</th><th>Ratio</th><th>Grade</th></tr>{rows}</table></section>

<section id="type"><p class="eyebrow">03</p><h2>Typography</h2>
<p class="lead">Manrope is the workhorse. PT Serif Italic is a deliberate flourish in coral, used for one word or phrase at a time. SF Mono is for code only.</p>
{type_rows}</section>

<section id="shape"><p class="eyebrow">04</p><h2>Radius, spacing &amp; shadow</h2>
<p class="label">Corner radius</p><div class="rads">{radius}</div>
<p class="label">Spacing scale</p>{space}
<p class="label">Elevation</p><div class="chips">
<div class="chip"><div class="sw" style="box-shadow:var(--sv-shadow-1);border:1px solid var(--sv-color-line-wash)"></div><div class="nm">shadow-1</div><div class="ds">Resting cards</div></div>
<div class="chip"><div class="sw" style="box-shadow:var(--sv-shadow-2);border:1px solid var(--sv-color-line-wash)"></div><div class="nm">shadow-2</div><div class="ds">Raised, hover</div></div></div></section>

<section id="components"><p class="eyebrow">05</p><h2>Components</h2>
<p class="lead">The building blocks used in the cheatsheet, decks and reports. Each should exist as a Figma component with the same name.</p>
<div class="demos">
<div class="card"><div class="card-h"><div class="card-i"></div><b>Section card</b></div><div class="card-b"><span class="label" style="margin:0">Group label</span><p>16px radius, 1.5px subtle border, wash header with a mint icon tile.</p><div><code>git status</code> <code>claude</code></div></div></div>
<div class="card"><div class="card-h"><div class="card-i" style="background:var(--sv-color-accent-coral)"></div><b>Buttons</b></div><div class="card-b"><div><a class="btn p">Primary</a><a class="btn d">Dark</a><a class="btn o">Outline</a></div><p>Pill shaped, Manrope 700. One primary per view.</p></div></div>
<div class="card"><div class="card-h"><div class="card-i" style="background:var(--sv-color-accent-lavender)"></div><b>Steps &amp; flourish</b></div><div class="card-b"><p><span class="num">1</span>Numbered step marker</p><p><span class="num">2</span>Ship it <span class="flourish">with confidence</span></p></div></div>
</div></section>

<section id="rules"><p class="eyebrow">06</p><h2>Usage rules</h2>
<div class="rules">
<div class="rule"><b>Do</b>Use ink text on mint, coral, marigold and lavender fills. Never white.</div>
<div class="rule"><b>Do</b>Use <code>mint-text</code> / <code>coral-text</code> when an accent colors body-size text.</div>
<div class="rule"><b>Do</b>Keep one serif-italic flourish per heading, in coral.</div>
<div class="rule no"><b>Don't</b>Set small text in <code>mint</code>, <code>mint-ink</code> or <code>mute</code> on white. They fail AA below large size.</div>
<div class="rule no"><b>Don't</b>Introduce new hexes. Add a token to tokens.json first.</div>
<div class="rule no"><b>Don't</b>Stack more than two accents in one component.</div>
</div></section>

<section id="workflow"><p class="eyebrow">07</p><h2>Figma ⇄ code workflow</h2>
<p class="lead">Tokens and components sync both ways. Page layouts go design → code only.</p>
<div class="flow">
<div><span class="num">1</span><b>Edit in Figma</b>Designers change Variables and components in the Savas Design System file.</div>
<div><span class="num">2</span><b>Export tokens</b>Variables export to tokens.json (Tokens Studio or the Variables API) and land in a PR.</div>
<div><span class="num">3</span><b>Build</b><code>python3 build.py</code> regenerates tokens.css and this page. The site consumes tokens.css.</div>
<div><span class="num">4</span><b>Review &amp; ship</b>Preview deploy, designer sign-off, merge to production.</div>
</div></section>

</main><footer><span>Savas Labs</span> · Brand Standards · generated from tokens.json</footer></body></html>"""

out = HERE / "Savas-Brand-Standards.html"
out.write_text(HTML)
print(f"wrote {out.name}, tokens.css")

# ── PDFs ───────────────────────────────────────────────────────────────────
if "--pdf" in sys.argv:
    from playwright.sync_api import sync_playwright
    from PIL import Image
    with sync_playwright() as p:
        try: b = p.chromium.launch()
        except Exception: b = p.chromium.launch(channel="chrome")
        pg = b.new_page(viewport={"width": 1400, "height": 900})
        pg.goto(out.as_uri()); pg.wait_for_load_state("networkidle")
        pg.pdf(path=str(HERE / "Savas-Brand-Standards.pdf"), format="Letter", print_background=True,
               margin={"top": "0.4in", "bottom": "0.4in", "left": "0.3in", "right": "0.3in"})
        png = pg.screenshot(full_page=True, type="png"); b.close()
    Image.open(io.BytesIO(png)).convert("RGB").save(str(HERE / "Savas-Brand-Standards-Full.pdf"), resolution=150)
    print("wrote PDFs")
