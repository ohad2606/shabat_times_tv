#!/usr/bin/env python3
"""Turn the Claude Design .dc.html into a standalone page for the TV.

Two jobs:
  1. Re-point every external dependency (React, fonts, background image) at
     files we serve ourselves, so the display never depends on a third party.
  2. Give every oklch() colour an sRGB fallback. Smart-TV browsers run old
     Chromium builds that treat oklch() as invalid and drop the declaration,
     which would render the design as flat black. Modern browsers take the
     oklch; old ones fall back to the hex/rgba we emit just before it.
"""
import math, re, pathlib, shutil, sys

SRC = pathlib.Path(__file__).parent

# How strongly the background photo reads behind the text. 1.0 is the photo at
# full strength; lower values fade it toward the near-black base underneath,
# which lifts the contrast of the cream/gold type sitting on top.
# "light": dark charcoal/bronze type on a bright photo (the white Yom Kippur image).
# "dark":  the original cream/gold type on dark scrims, for dark photos.
THEME = "light"

# A bright photo over the (now white) base needs no fading, so light defaults to 1.0.
BG_OPACITY = float(sys.argv[1]) if len(sys.argv) > 1 else (1.0 if THEME == "light" else 0.85)
DISTANCE_MODE = True
DC  = SRC / "שבת וראש השנה.dc.html"


# --- distance mode -----------------------------------------------------------
# The panel is a 160" outdoor screen read from ~20 m. At that angular size the
# design's original type tops out at roughly 1/200 of viewing distance, which is
# the threshold of "barely legible". These overrides push the information that
# matters -- the two times -- to about 1/78, and lift everything else as far as
# the fixed 1920x1080 canvas allows. Each entry is (what to find, what to use).
TYPE_SCALE = [
    # the two times: the whole reason the screen exists
    ("font-size: 78px; line-height: 1;", "font-size: 130px; line-height: 0.95;"),
    # their labels
    ("font-size: 30px; font-weight: 600;", "font-size: 52px; font-weight: 700;"),
    # dates under the times
    ("font-size: 25px;", "font-size: 28px;"),
    # day / hebrew date / clock row
    ("font-size: 46px;", "font-size: 54px;"),
    # gregorian date + city, sitting in that same row
    ("font-size: 26px; color:", "font-size: 38px; color:"),
    # greeting headline
    ("font-weight: 500; font-size: 98px;", "font-weight: 700; font-size: 80px;"),
    # family name
    ("font-weight: 700; font-size: 72px;", "font-weight: 700; font-size: 94px;"),
    # eyebrow above the greeting
    ("font-size: 26px; letter-spacing: 0.24em;", "font-size: 34px; letter-spacing: 0.2em;"),
    # blessing paragraph
    ("font-size: 30px; line-height: 1.5; font-weight: 300;",
     "font-size: 42px; line-height: 1.45; font-weight: 400;"),
    # bs"d
    ("font-size: 34px; letter-spacing: 0.04em;", "font-size: 44px; letter-spacing: 0.04em;"),
]

# Darker scrims directly under the text. Outdoors at night the photo behind the
# type is what eats the contrast, so these go deeper than the original design.
SCRIM_SCALE = [
    ("oklch(0.07 0.02 26 / 0.62) 0%, oklch(0.07 0.02 26 / 0.3) 54%",
     "oklch(0.05 0.02 26 / 0.88) 0%, oklch(0.05 0.02 26 / 0.6) 54%"),
    ("oklch(0.06 0.02 26 / 0.9) 0%, oklch(0.06 0.02 26 / 0.72) 42%, oklch(0.06 0.02 26 / 0.32) 70%",
     "oklch(0.04 0.02 26 / 0.97) 0%, oklch(0.04 0.02 26 / 0.9) 42%, oklch(0.04 0.02 26 / 0.55) 70%"),
]


# Growing the type this much breaks the design's absolute positioning: the
# bottom block climbs into the greeting. So distance mode also reclaims space.
LAYOUT = [
    # the blessing paragraph is 1/368 at 20 m -- never readable from the yard,
    # and it is what collides with the times. Drop it and the greeting fits.
    ("PARAGRAPH", None),
    # pull the greeting block up into the space that frees
    ("top: 96px; right: -20px;", "top: 34px; right: -20px;"),
    # tighten the bottom block so the times own the lower third
    ("gap: 24px; padding: 46px 60px 34px;", "gap: 10px; padding: 14px 60px 12px;"),
    # and its two columns
    ("justify-content: center; gap: 74px;", "justify-content: center; gap: 96px;"),
    # Tightened for the extra Yom Kippur row -- measured, not guessed.
    ("padding: 44px 30px 50px 110px;", "padding: 10px 30px 8px 110px;"),
    ("margin: 20px 0 0; font-family: 'Frank Ruhl Libre', serif;",
     "margin: 10px 0 0; font-family: 'Frank Ruhl Libre', serif;"),

]


# The design shipped with a hardcoded time override. Its delta is computed
# against the same value it is then applied to, so the two cancel and the page
# shows the override verbatim every week, for ever -- the city and the sunset
# maths underneath it have no effect at all. Clearing the override is what makes
# the city setting real, so these two changes only work as a pair.
TIMES = [
    # empty string -> toMin() returns null -> delta 0 -> the computed time wins
    ("&quot;default&quot;:&quot;18:21&quot;", "&quot;default&quot;:&quot;&quot;"),
    ("&quot;default&quot;:&quot;19:27&quot;", "&quot;default&quot;:&quot;&quot;"),
    ("?? '18:21'", "?? ''"),
    ("?? '19:27'", "?? ''"),
    # Tel Aviv: candle 20 min before sunset, tzeit 40 min after (already in CITIES)
    ("&quot;default&quot;:&quot;\u05d9\u05e8\u05d5\u05e9\u05dc\u05d9\u05dd&quot;",
     "&quot;default&quot;:&quot;\u05ea\u05dc \u05d0\u05d1\u05d9\u05d1&quot;"),
    # and the fallback used when the prop is missing entirely
    ("? this.props.city : '\u05d9\u05e8\u05d5\u05e9\u05dc\u05d9\u05dd'",
     "? this.props.city : '\u05ea\u05dc \u05d0\u05d1\u05d9\u05d1'"),
]


# --- content: parasha + Yom Kippur -------------------------------------------
GOLD   = "oklch(0.89 0.13 84)"
CREAM  = "oklch(0.98 0.03 85)"
MUTED  = "oklch(0.88 0.02 80)"
SHADOW = "text-shadow: 0 3px 22px oklch(0.06 0.02 25 / 0.95);"

# Manually fixed by the family -- these are not computed from sunset.
# `from`/`until` bound the stretch where Yom Kippur is the ONLY thing worth
# showing: once Shabbat is out, the Shabbat panel would otherwise advertise
# times a week away while the fast is starting that evening.
YOM_KIPPUR = {
    "from":  "2026-09-19T19:22:00+03:00",   # motzaei Shabbat
    "until": "2026-09-21T19:12:00+03:00",   # end of the fast
    "title": "\u05d9\u05d5\u05dd \u05db\u05d9\u05e4\u05d5\u05e8",
    "sub": "\u05d9\u05f3 \u05d1\u05ea\u05e9\u05e8\u05d9 \u05ea\u05e9\u05e4\u05f4\u05d6",
    "times": [
        ("\u05db\u05dc \u05e0\u05d3\u05e8\u05d9", "18:30", "\u05d9\u05d5\u05dd \u05d0\u05f3 \u05d1\u05e2\u05e8\u05d1 \u00b7 20.9", True),
        ("\u05e9\u05d7\u05e8\u05d9\u05ea", "05:45", "\u05d9\u05d5\u05dd \u05d1\u05f3 \u00b7 21.9", False),
        ("\u05de\u05e0\u05d7\u05d4", "16:30", "\u05d9\u05d5\u05dd \u05d1\u05f3 \u00b7 21.9", False),
        ("\u05e6\u05d0\u05ea \u05d4\u05e6\u05d5\u05dd", "19:12", "\u05d9\u05d5\u05dd \u05d1\u05f3 \u00b7 21.9", True),
    ],
}


# Yom Kippur is past. Leave the block out of the markup altogether rather than
# shipping it hidden -- flip back to True and refresh the dates if it returns.
SHOW_YOM_KIPPUR = False

# A verse under the times, set in the same diamond-and-rule motif as the header
# so it reads as part of the design rather than a caption bolted on.
VERSE = "בסוכות תשבו שבעת ימים"
SHOW_VERSE = True


def verse_block():
    rule = ('<span style="width: 120px; height: 1px;'
            ' background: oklch(0.86 0.1 85 / 0.5);"></span>')
    diamond = (f'<span style="width: 9px; height: 9px; background: {GOLD};'
               f' transform: rotate(45deg);"></span>')
    return (
        f'\n    <div style="display: flex; align-items: center; justify-content: center;'
        f' gap: 22px; padding-top: 18px; margin-top: 2px; {SHADOW}">'
        f'{diamond}{rule}'
        f'<span style="font-family: \'Frank Ruhl Libre\', serif; font-size: 56px;'
        f' letter-spacing: 0.05em; white-space: nowrap; color: {GOLD};">{VERSE}</span>'
        f'{rule}{diamond}'
        f'</div>\n  ')


def yom_kippur_block():
    cols = []
    for label, time, day, accent in YOM_KIPPUR["times"]:
        cols.append(
            f'<div style="display: flex; flex-direction: column; align-items: center; gap: 1px;">'
            f'<span style="font-size: {{{{ ykLabel }}}}px; font-weight: 600; color: {MUTED};">{label}</span>'
            f'<span style="font-family: \'Frank Ruhl Libre\', serif; font-size: {{{{ ykTime }}}}px;'
            f' line-height: 1; font-variant-numeric: tabular-nums;'
            f' color: {GOLD if accent else CREAM};">{time}</span>'
            f'<span style="font-size: {{{{ ykDay }}}}px; color: {MUTED};">{day}</span>'
            f'</div>')
    divider = ('<div style="width: 1px; background: linear-gradient(180deg, transparent,'
               ' oklch(0.86 0.1 85 / 0.4), transparent);"></div>')
    return (
        f'\n    <div style="display: {{{{ ykDisplay }}}}; flex-direction: column; align-items: center;'
        f' gap: 6px; padding-top: {{{{ ykPadTop }}}}px; margin-top: 2px;'
        f' border-top: {{{{ ykBorderW }}}}px solid oklch(0.86 0.1 85 / 0.28);'
        f' {SHADOW}">'
        f'<div style="display: flex; align-items: baseline; gap: 22px;">'
        f'<span style="font-size: {{{{ ykTitle }}}}px; letter-spacing: 0.16em; font-weight: 700;'
        f' color: {GOLD};">{YOM_KIPPUR["title"]}</span>'
        f'<span style="font-size: {{{{ ykSub }}}}px; color: {MUTED};">{YOM_KIPPUR["sub"]}</span>'
        f'</div>'
        f'<div style="display: flex; align-items: stretch; justify-content: center;'
        f' gap: {{{{ ykGap }}}}px;">'
        f'{divider.join(cols)}</div></div>\n  ')


def apply_content(html):
    """Parasha of the week in place of the Rosh Hashana caption, plus the
    manually-set Yom Kippur schedule. Runs before the oklch fallback pass so the
    colours above get their sRGB twins like everything else."""
    # 1. the parasha table, generated at build time by gen_parasha.mjs
    table = (SRC / "parasha.json").read_text().strip()
    html = html.replace("const TZ = 'Asia/Jerusalem';",
                        "const PARASHA = " + table + ";\nconst TZ = 'Asia/Jerusalem';")

    # 2. the parasha, and the switch that decides what the screen is FOR right now.
    #    Written in plain ES5 on purpose -- no spread, no arrow functions -- so it
    #    stays inside whatever the TV's browser can parse.
    lookup = """    var _t = now.getTime();
    var _ykFrom = new Date('%s').getTime();
    var _ykUntil = new Date('%s').getTime();
    var _ykOnly = _t >= _ykFrom && _t <= _ykUntil;   // Shabbat out, fast not yet over
    var _ykOver = _t > _ykUntil;
    var _parasha = (function () {
      var a = todayAbs;
      while (a %% 7 !== 6) a++;              // the Shabbat this week runs up to
      var g = gregFromAbs(a);
      var k = g.y + '-' + ('0' + g.m).slice(-2) + '-' + ('0' + g.d).slice(-2);
      return PARASHA[k] ? '\u05e4\u05e8\u05e9\u05ea ' + PARASHA[k] : '';
    })();

    return {
      parasha: _parasha,
      parashaDisplay: _parasha ? 'flex' : 'none',
      shabbatDisplay: _ykOnly ? 'none' : 'flex',
      ykDisplay: _ykOver ? 'none' : 'flex',
      ykTime:    _ykOnly ? 150 : 86,
      ykLabel:   _ykOnly ? 54 : 32,
      ykDay:     _ykOnly ? 32 : 24,
      ykTitle:   _ykOnly ? 56 : 34,
      ykSub:     _ykOnly ? 38 : 28,
      ykGap:     _ykOnly ? 64 : 48,
      ykPadTop:  _ykOnly ? 0 : 14,
      ykBorderW: _ykOnly ? 0 : 1,
""" % (YOM_KIPPUR["from"], YOM_KIPPUR["until"])
    anchor = "    return {\n      dayName: DOW[hebAbs % 7],"
    if anchor not in html:
        raise SystemExit("! could not find the vals object to extend")
    html = html.replace(anchor, lookup + "      dayName: DOW[hebAbs % 7],")

    # 2b. the two blocks that switch on and off
    shab = "display: flex; align-items: stretch; justify-content: center; gap: 74px;"
    if shab not in html:
        raise SystemExit("! Shabbat times row not found - template changed?")
    html = html.replace(shab, "display: {{ shabbatDisplay }};" + shab[len("display: flex;"):])

    eyebrow = "display: flex; align-items: center; gap: 16px; color: oklch(0.88 0.11 85);"
    if eyebrow not in html:
        raise SystemExit("! parasha eyebrow row not found - template changed?")
    html = html.replace(eyebrow, "display: {{ parashaDisplay }};" + eyebrow[len("display: flex;"):])

    # 3. the Rosh Hashana caption gives up its slot to the parasha
    rh = "\u05e8\u05d0\u05e9 \u05d4\u05e9\u05e0\u05d4 \u05d5\u05e9\u05d1\u05ea \u05e7\u05d5\u05d3\u05e9"
    if rh not in html:
        raise SystemExit("! Rosh Hashana caption not found - template changed?")
    html = html.replace(">" + rh + "<", ">{{ parasha }}<")

    # 4. whatever belongs under the times, appended inside the bottom block
    tail = ""
    if SHOW_YOM_KIPPUR:
        tail += yom_kippur_block()
    if SHOW_VERSE:
        tail += verse_block()
    if "\n  </main>" not in html:
        raise SystemExit("! could not find </main> to append the bottom blocks")
    html = html.replace("\n  </main>", tail + "</main>")
    return html


def apply_distance_mode(html):
    """Runs on the raw design source, before the oklch fallback pass."""
    missed = []
    for find, repl in TYPE_SCALE + SCRIM_SCALE + LAYOUT + TIMES:
        if find == "PARAGRAPH":
            html, n = re.subn(r"\s*<p style=\"margin: 24px 0 0;.*?</p>", "", html, flags=re.S)
            if n == 0:
                missed.append("blessing paragraph")
            continue
        if find not in html:
            missed.append(find)
            continue
        html = html.replace(find, repl)
    if missed:
        # Loud, because a silently-skipped rule means the TV shows small text.
        for m in missed:
            print(f"  ! distance-mode rule did not match: {m[:60]}")
    return html


def oklch_to_css(L, C, H, alpha):
    a = C * math.cos(math.radians(H))
    b = C * math.sin(math.radians(H))
    l_ = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m_ = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s_ = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
    lin = (
        +4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_,
        -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_,
        -0.0041960863 * l_ - 0.7034186147 * m_ + 1.7076147010 * s_,
    )
    def gamma(c):
        c = max(0.0, min(1.0, c))
        c = 12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055
        return max(0, min(255, round(c * 255)))
    r, g, bl = (gamma(c) for c in lin)
    if alpha < 1:
        return f"rgba({r}, {g}, {bl}, {alpha:g})"
    return f"#{r:02x}{g:02x}{bl:02x}"


OKLCH = re.compile(r"oklch\(\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*(?:/\s*([\d.]+)\s*)?\)")

def convert_colors(value):
    """Replace every oklch() in a CSS value with its sRGB equivalent."""
    def sub(m):
        L, C, H = float(m[1]), float(m[2]), float(m[3])
        alpha = float(m[4]) if m[4] else 1.0
        return oklch_to_css(L, C, H, alpha)
    return OKLCH.sub(sub, value)


def add_fallbacks(decls):
    """decls: 'a: x; b: y'. Duplicate any oklch declaration with an sRGB one first."""
    out = []
    for decl in decls.split(";"):
        if not decl.strip():
            continue
        if "oklch(" in decl and ":" in decl:
            prop, _, value = decl.partition(":")
            out.append(f"{prop}:{convert_colors(value)}")
        out.append(decl)
    return "; ".join(s.strip() for s in out)


def apply_light_theme(html):
    """Invert the palette by ROLE, not by blind lightness flip.

    The design paints light type over dark veils: every text colour is bright
    (L >= 0.7) and every scrim, glow and text-shadow is near-black (L < 0.7).
    Swapping only the text colour would leave charcoal type sitting on dark
    scrims -- unreadable. So both halves move together:
      * bright + chromatic (the gold family) -> dark bronze. Plain gold on white
        fails contrast; bronze keeps the accent and clears ~7:1.
      * bright + neutral (cream, greys)      -> charcoal, preserving hierarchy:
        the brightest cream becomes the darkest charcoal, muted greys stay lighter.
      * everything dark (scrims, halos, base) -> warm near-white, same alpha,
        so the veils that used to darken the photo now lift the type off it.
    """
    def remap(m):
        L, C, H = float(m[1]), float(m[2]), float(m[3])
        a = m[4]
        alpha = f" / {a}" if a else ""
        if L >= 0.7:
            if C >= 0.08:
                nl = min(0.5, 0.44 + (0.89 - L) * 0.6)
                return f"oklch({nl:.3f} 0.1 70{alpha})"
            nl = max(0.25, min(0.6, 0.25 + (0.98 - L) * 1.5))
            return f"oklch({nl:.3f} 0.006 {H:g}{alpha})"
        return f"oklch(0.985 0.008 85{alpha})"

    html = OKLCH.sub(remap, html)
    # the one hard-coded hex: page background behind the canvas
    html = html.replace("html, body { margin: 0; padding: 0; background: #1a0a10; }",
                        "html, body { margin: 0; padding: 0; background: #fbfaf7; }")
    return html


def main():
    html = DC.read_text()
    html = apply_content(html)
    if DISTANCE_MODE:
        html = apply_distance_mode(html)
    if THEME == "light":
        html = apply_light_theme(html)
    n_oklch = len(OKLCH.findall(html))

    # --- inline style="..." attributes ---
    html = re.sub(r'style="([^"]*)"',
                  lambda m: 'style="%s"' % add_fallbacks(m[1]),
                  html)

    # --- declarations inside <style> blocks ---
    def style_block(m):
        body = re.sub(r"\{([^{}]*)\}",
                      lambda d: "{ %s }" % add_fallbacks(d[1]),
                      m[1])
        return f"<style>{body}</style>"
    html = re.sub(r"<style>(.*?)</style>", style_block, html, flags=re.S)

    # --- serve fonts ourselves instead of from Google ---
    html = re.sub(
        r'\s*<link rel="preconnect"[^>]*>\s*|\s*<link href="https://fonts\.googleapis\.com[^>]*>\s*',
        "", html)
    html = html.replace("<helmet>",
        '<helmet>\n<link rel="stylesheet" href="fonts.css" />'
        '\n<link rel="icon" href="data:," />')

    # --- React must be defined before support.js boots, or it fetches unpkg ---
    html = html.replace(
        '<script src="./support.js"></script>',
        '<script src="./vendor/react.production.min.js"></script>\n'
        '<script src="./vendor/react-dom.production.min.js"></script>\n'
        '<script src="./support.js"></script>')

    # --- background image: local file, plain ASCII name ---
    html = html.replace("uploads/Codex Image Sep 11, 2026, 05_01_51 PM.png", "bg.png")

    # --- background image: accept any common format, ship only a complete file ---
    # Whatever gets dropped into tv-src as bg.<ext> is picked up here, so the
    # source format never has to match what the design originally referenced.
    def sniff(path):
        """Identify by magic bytes, not by filename — a .jpg that is really a
        PNG is common when a file gets renamed on its way over. Returns the
        true extension, or None if the file is truncated or unrecognised."""
        b = path.read_bytes()
        if b[:8] == b"\x89PNG\r\n\x1a\n":
            return ".png" if b[-8:] == b"IEND\xaeB`\x82" else None
        if b[:2] == b"\xff\xd8":
            return ".jpg" if b[-2:] == b"\xff\xd9" else None
        if b[:4] == b"RIFF" and b[8:12] == b"WEBP":
            return ".webp"
        return None

    bg, bg_name = None, None
    for cand in sorted(SRC.glob("bg.*")):
        if cand.name.startswith("bg.partial"):
            continue
        ext = sniff(cand)
        if ext is None:
            print(f"  ! {cand.name} is truncated or not an image - skipping")
            continue
        bg, bg_name = cand, "bg" + ext        # serve under its true extension
        if cand.suffix.lower() != ext:
            print(f"  note: {cand.name} is actually {ext[1:].upper()}; serving as {bg_name}")
        break

    if bg is None:
        # Drop the slot entirely rather than leave its "drag an image here"
        # placeholder on screen. The design's own gradient shows through.
        html = re.sub(r"\s*<image-slot\b[^>]*></image-slot>", "", html)
    else:
        html = html.replace('src="bg.png"', f'src="{bg_name}"')
        if BG_OPACITY < 1.0:
            # Wrap rather than style the element itself: image-slot owns its
            # own :host styles and we don't want to fight them.
            html = re.sub(
                r"(<image-slot\b[^>]*></image-slot>)",
                r'<div style="position: absolute; inset: 0; opacity: %g;">\1</div>' % BG_OPACITY,
                html)

    # --- assemble dist/ ---
    dist = SRC / "dist"
    if dist.exists():
        shutil.rmtree(dist)
    (dist / "fonts").mkdir(parents=True)
    (dist / "vendor").mkdir()

    (dist / "index.html").write_text(html)
    for name in ("support.js", "image-slot.js"):
        shutil.copy2(SRC / name, dist / name)
    for f in (SRC / "vendor").glob("*.js"):
        shutil.copy2(f, dist / "vendor" / f.name)
    for f in (SRC / "fonts" / "files").glob("*.woff2"):
        shutil.copy2(f, dist / "fonts" / f.name)
    # font CSS sits at the root, so its url()s point into fonts/
    css = (SRC / "fonts" / "fonts.css").read_text().replace("url(files/", "url(fonts/")
    (dist / "fonts.css").write_text(css)
    if bg is not None:
        shutil.copy2(bg, dist / bg_name)

    print(f"oklch colours given sRGB fallbacks: {n_oklch}")
    print(f"background image: {bg_name if bg else 'MISSING - using gradient only'}"
          + (f" @ {BG_OPACITY:g} opacity" if bg else ""))
    print(f"dist/ built ({sum(f.stat().st_size for f in dist.rglob('*') if f.is_file()):,} bytes)")


main()
