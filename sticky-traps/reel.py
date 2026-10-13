"""Planet Gamla — BuildingShop sticky traps reel (Director #3: The Nature Documentary).

9:16 1080x1920, 30fps, skia + numpy + ffmpeg. Semi-realistic filmic plates (DOF blur,
god-rays, bokeh, grain) + cel-shaded characters. Word-highlight captions with speaker tags.

Timeline lives in LINES. When ElevenLabs VO arrives, replace the estimated (start, end)
pairs with whisper word timings and drop the mp3s into vo/ — the scene clock follows LINES.

usage: python3 reel.py [--stills] [--draft]
"""
import math, os, random, subprocess, sys
import numpy as np
import skia

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
W, H, FPS = 1080, 1920, 30
W_ = W

# ------------------------------------------------------------------ script / timeline
# (start, end, speaker, text)  — estimated until real VO is in
import json
SR = 48000
# ---- real VO timeline (ElevenLabs files, segmented by vo_split.py) --------------------------
VO_FILES = {"NARRATOR": "vo/file_bunty_voice.mp3", "MEERA": "vo/file_zara_voice.mp3",
            "RAJU KAKA": "vo/file_raju_voice.mp3"}
SEG = json.load(open(os.path.join(HERE, "vo", "segments.json")))
# reading order: (speaker, line index in that file, caption text in Roman Hinglish, gap before)
ORDER = [
    ("NARRATOR", 0, "Shhh… dekhiye. Yeh hai whitefly.", 0.15),
    ("NARRATOR", 1, "Chhota sa… par poore plant ka ras choos leta hai.", 0.2),
    ("MEERA", 0, "Arre! Mere tamatar ke patte phir se peele!", 0.25),
    ("MEERA", 1, "Itne saare keede… kahan se aa gaye?!", 0.2),
    ("NARRATOR", 2, "Par jungle ka ek niyam hai… kuch rang, inse bardasht nahi hote.", 0.25),
    ("NARRATOR", 3, "Peela. Aur neela.", 0.2),
    ("MEERA", 2, "Bas film utaaro, aur plant ke thoda upar latka do.", 0.3),
    ("NARRATOR", 4, "Aur phir… shikari khud shikaar ban jaata hai.", 0.2),
    ("RAJU KAKA", 0, "Humare khet mein bhi lagaye… thrips, aphids, sab chipak gaye!", 0.2),
    ("RAJU KAKA", 1, "15 by 20 ka size, peela bhi, neela bhi…", 0.15),
    ("RAJU KAKA", 2, "buildingshop.in se mangaya tha!", 0.15),
    ("NARRATOR", 5, "Dono taraf sticky. Waterproof. Non-toxic. Indoor ho ya outdoor.", 0.2),
    ("NARRATOR", 6, "Terrace ho, greenhouse ya khet… yeh hai jungle ka naya kanoon.", 0.2),
]
TAIL = 2.0  # STUCK stamp + cut to black after the last line
if os.environ.get("AMAZON") == "1":
    TAIL = 2.6  # hold the product end card instead of cutting to black

LINES, CLIPS, WORDS = [], [], []  # LINES: (start,end,speaker,text); CLIPS: (global_start, speaker, src_a, src_b)
_t = 0.0
AMAZON = os.environ.get("AMAZON") == "1"  # Amazon cut: no URLs / off-Amazon mentions, no black frames
for sp, idx, txt, gap in ORDER:
    seg = SEG[sp][idx]
    if AMAZON and sp == "RAJU KAKA" and idx == 2:  # "buildingshop.in se mangaya tha" -> dropped for Amazon
        LINES.append((_t, _t, sp, ""))
        WORDS.append([])
        continue
    _t += gap
    a0, b0 = seg["start"], seg["end"]
    g0 = _t
    LINES.append((g0, g0 + (b0 - a0), sp, txt))
    CLIPS.append((g0, sp, a0 - 0.03, b0 + 0.06))
    # word timings: spread caption words over the voiced runs by character share
    rr = [(ra - a0 + g0, rb - a0 + g0) for ra, rb in seg["runs"]]
    tot = sum(rb - ra for ra, rb in rr)
    words = txt.split()
    lens = [max(1, len(w.strip(".,!?…"))) for w in words]
    acc, wl = 0.0, []

    def at(frac):
        s = frac * tot
        for ra, rb in rr:
            if s <= rb - ra:
                return ra + s
            s -= rb - ra
        return rr[-1][1]
    for w, L in zip(words, lens):
        f0 = acc / sum(lens)
        acc += L
        wl.append((at(f0), at(acc / sum(lens)), w))
    WORDS.append(wl)
    _t = g0 + (b0 - a0)
DUR = round(_t + TAIL, 2)


def L(i):  # start of line i
    return LINES[i][0]


def LE(i):
    return LINES[i][1]


def WT(i, j):  # start of word j in line i
    return WORDS[i][j][0]


STUCK_T = LE(12) + 0.25
SCENES = [
    (0.0, L(1), "macro_fly"), (L(1), L(2) - 0.05, "leaf_reveal"), (L(2) - 0.05, L(4) - 0.05, "meera_worried"),
    (L(4) - 0.05, L(6) - 0.05, "species_entrance"), (L(6) - 0.05, L(7) - 0.05, "meera_hangs"),
    (L(7) - 0.05, L(8) - 0.05, "the_hunt"), (L(8) - 0.05, L(11) - 0.05, "farm"),
    (L(11) - 0.05, L(12) - 0.05, "field_notes"), (L(12) - 0.05, STUCK_T, "finale"), (STUCK_T, DUR, "stuck_stamp"),
]


def RUN(i, k):  # global start of voiced run k in reading-order line i
    sp, idx = ORDER[i][0], ORDER[i][1]
    seg = SEG[sp][idx]
    return L(i) + seg["runs"][k][0] - seg["start"]


CUE = dict(peela=RUN(5, 0), neela=RUN(5, 1), hunt=L(7), r2=L(9), r3=L(10),
           notes=[RUN(11, 0) + 0.45, RUN(11, 2), RUN(11, 3), RUN(11, 4)], black=STUCK_T + 1.35)
if AMAZON:
    CUE["black"] = DUR + 10
    CUE["r3"] = DUR + 10

# ------------------------------------------------------------------ colour / paint helpers
YEL = (255, 214, 0)
BLU = (28, 110, 218)


def C(rgb, a=255):
    return skia.ColorSetARGB(int(max(0, min(255, a))), int(rgb[0]), int(rgb[1]), int(rgb[2]))


def hexc(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def shade(rgb, f):
    return tuple(max(0, min(255, c * f)) for c in rgb)


def mix(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def fill(rgb, a=255, blur=0.0):
    p = skia.Paint(AntiAlias=True, Color=C(rgb, a))
    if blur > 0:
        p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    return p


def stroke(rgb, w, a=255, cap=skia.Paint.kRound_Cap):
    return skia.Paint(AntiAlias=True, Color=C(rgb, a), Style=skia.Paint.kStroke_Style,
                      StrokeWidth=w, StrokeCap=cap, StrokeJoin=skia.Paint.kRound_Join)


def lin(p0, p1, cols, pos=None):
    p = skia.Paint(AntiAlias=True)
    p.setShader(skia.GradientShader.MakeLinear([skia.Point(*p0), skia.Point(*p1)],
                                               [C(c[0], c[1]) if isinstance(c[0], tuple) else C(c) for c in cols], pos))
    return p


def rad(c, r, cols, pos=None):
    p = skia.Paint(AntiAlias=True)
    p.setShader(skia.GradientShader.MakeRadial(skia.Point(*c), r,
                                               [C(x[0], x[1]) if isinstance(x[0], tuple) else C(x) for x in cols], pos))
    return p


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def eout(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def bout(x):
    x = clamp(x)
    c = 1.5
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


def lerp(a, b, t):
    return a + (b - a) * t


def rrect(x, y, w, h, r):
    return skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, w, h), r, r)


TF = {
    "sans": skia.Typeface("DejaVu Sans", skia.FontStyle.Bold()),
    "serif": skia.Typeface("DejaVu Serif", skia.FontStyle.Bold()),
    "serif_i": skia.Typeface("DejaVu Serif", skia.FontStyle.Italic()),
    "serif_r": skia.Typeface("DejaVu Serif", skia.FontStyle.Normal()),
    "mono": skia.Typeface("DejaVu Sans Mono", skia.FontStyle.Bold()),
}


def font(kind, size):
    f = skia.Font(TF[kind], size)
    f.setEdging(skia.Font.Edging.kAntiAlias)
    return f


def text(cv, s, x, y, kind, size, rgb=(255, 255, 255), a=255, anchor="l", shadow=0):
    f = font(kind, size)
    w = f.measureText(s)
    if anchor == "c":
        x -= w / 2
    elif anchor == "r":
        x -= w
    if shadow:
        cv.drawString(s, x + 2, y + 3, f, fill((0, 0, 0), a * 0.5, blur=shadow))
    cv.drawString(s, x, y, f, fill(rgb, a))
    return w


# ------------------------------------------------------------------ film look
_rng = np.random.default_rng(3)
GRAIN = []
for _ in range(6):
    n = (_rng.normal(128, 38, (H // 2, W // 2))).clip(0, 255).astype(np.uint8)
    a = np.dstack([n, n, n, np.full_like(n, 255)])
    GRAIN.append(skia.Image.fromarray(np.ascontiguousarray(a), colorType=skia.kRGBA_8888_ColorType))


def film_finish(cv, t, vign=0.55, grain=14):
    cv.drawRect(skia.Rect(0, 0, W, H), rad((W / 2, H * 0.48), H * 0.75,
                                         [((0, 0, 0), 0), ((0, 0, 0), 0), ((0, 0, 0), int(255 * vign))], [0, 0.55, 1]))
    p = skia.Paint(Alphaf=grain / 255.0, BlendMode=skia.BlendMode.kOverlay)
    cv.drawImageRect(GRAIN[int(t * FPS) % len(GRAIN)], skia.Rect(0, 0, W, H),
                     skia.SamplingOptions(skia.FilterMode.kLinear), p)


def blur_layer(cv, sigma):
    p = skia.Paint()
    p.setImageFilter(skia.ImageFilters.Blur(sigma, sigma))
    cv.saveLayer(None, p)


def bokeh(cv, t, seed, n, cols, rmin=20, rmax=70, a=60, drift=12):
    rnd = random.Random(seed)
    for i in range(n):
        x = rnd.uniform(-50, W + 50) + math.sin(t * 0.4 + i) * drift
        y = rnd.uniform(-50, H + 50) + math.cos(t * 0.3 + i) * drift
        r = rnd.uniform(rmin, rmax)
        c = rnd.choice(cols)
        cv.drawCircle(x, y, r, fill(c, a * rnd.uniform(0.5, 1.0), blur=r * 0.15))


def god_rays(cv, t, origin, cols=(255, 240, 190), a=40, n=7, spread=0.9, length=2600):
    ox, oy = origin
    for i in range(n):
        ang = math.pi / 2 + (i - n / 2) * spread / n + math.sin(t * 0.3 + i) * 0.03
        w = 0.05 + 0.04 * ((i * 37) % 5) / 5
        path = skia.Path()
        path.moveTo(ox, oy)
        path.lineTo(ox + math.cos(ang - w) * length, oy + math.sin(ang - w) * length)
        path.lineTo(ox + math.cos(ang + w) * length, oy + math.sin(ang + w) * length)
        path.close()
        p = rad((ox, oy), length, [(cols, a), (cols, 0)])
        p.setBlendMode(skia.BlendMode.kScreen)
        cv.drawPath(path, p)


# ------------------------------------------------------------------ nature props
def leaf_path(L, wfac=0.42):
    p = skia.Path()
    p.moveTo(0, 0)
    p.cubicTo(L * 0.25, -L * wfac, L * 0.75, -L * wfac * 0.85, L, 0)
    p.cubicTo(L * 0.75, L * wfac * 0.85, L * 0.25, L * wfac, 0, 0)
    p.close()
    return p


def draw_leaf(cv, x, y, L, ang, base=(54, 128, 52), sick=0.0, veins=True, seed=1, light=1.0):
    cv.save()
    cv.translate(x, y)
    cv.rotate(math.degrees(ang))
    path = leaf_path(L)
    top = mix(shade(base, 1.25 * light), (180, 170, 60), sick * 0.6)
    bot = mix(shade(base, 0.7 * light), (150, 130, 40), sick * 0.5)
    cv.drawPath(path, lin((0, -L * 0.4), (0, L * 0.4), [top, bot]))
    cv.save()
    cv.clipPath(path, doAntiAlias=True)
    # chlorosis blotches
    if sick > 0:
        rnd = random.Random(seed)
        for i in range(int(6 + 10 * sick)):
            bx, by = rnd.uniform(L * 0.15, L * 0.9), rnd.uniform(-L * 0.25, L * 0.25)
            cv.drawCircle(bx, by, rnd.uniform(L * 0.03, L * 0.09), fill((214, 196, 70), 150 * sick, blur=L * 0.02))
    # sheen
    cv.drawOval(skia.Rect(L * 0.1, -L * 0.33, L * 0.8, -L * 0.05), fill((255, 255, 230), 40, blur=L * 0.05))
    if veins:
        sp = stroke(shade(top, 1.18), max(1.0, L * 0.018), 150)
        mid = skia.Path()
        mid.moveTo(0, 0)
        mid.quadTo(L * 0.5, -L * 0.02, L * 0.97, 0)
        cv.drawPath(mid, sp)
        sp2 = stroke(shade(top, 1.12), max(0.8, L * 0.008), 110)
        for k in range(1, 7):
            fx = L * k / 7.5
            for sg in (-1, 1):
                v = skia.Path()
                v.moveTo(fx, 0)
                v.quadTo(fx + L * 0.08, sg * L * 0.12, fx + L * 0.16, sg * L * 0.25 * (1 - k / 9))
                cv.drawPath(v, sp2)
    cv.restore()
    cv.restore()


def draw_insect(cv, x, y, s, kind, t, ang=0.0, stuck=False, a=255, blur=0.0):
    """kind: whitefly | gnat | thrips | aphid. s ~ body length px."""
    cv.save()
    cv.translate(x, y)
    cv.rotate(math.degrees(ang))
    flap = 0.25 if stuck else 0.5 + 0.5 * math.sin(t * 70 + x * 0.1)
    bl = blur
    if kind == "whitefly":
        for sg in (-1, 1):
            cv.save()
            cv.rotate(sg * (18 + 30 * flap))
            wp = skia.Path()
            wp.addOval(skia.Rect(-s * 0.12, sg * s * 0.02, s * 0.62, sg * s * 0.55) if sg > 0
                       else skia.Rect(-s * 0.12, -s * 0.55, s * 0.62, -s * 0.02))
            cv.drawPath(wp, fill((250, 250, 245), a * 0.95, blur=bl + s * 0.02))
            cv.drawPath(wp, stroke((210, 210, 200), max(0.6, s * 0.015), a * 0.6))
            cv.restore()
        if s > 60:  # macro detail: wing veins + waxy powder
            for sg in (-1, 1):
                cv.save()
                cv.rotate(sg * (18 + 30 * flap))
                vp = stroke((205, 205, 195), s * 0.008, 160)
                for k in range(3):
                    v = skia.Path()
                    v.moveTo(0, sg * s * 0.05)
                    v.quadTo(s * 0.25, sg * s * (0.12 + k * 0.1), s * 0.5, sg * s * (0.15 + k * 0.12))
                    cv.drawPath(v, vp)
                rnd = random.Random(int(s))
                for k in range(40):
                    cv.drawCircle(rnd.uniform(0, s * 0.5), sg * rnd.uniform(s * 0.05, s * 0.5), s * 0.006,
                                  fill((255, 255, 255), 200))
                cv.restore()
        cv.drawOval(skia.Rect(-s * 0.32, -s * 0.11, s * 0.36, s * 0.11),
                    rad((0, -s * 0.04), s * 0.35, [(250, 232, 140), (205, 175, 70)]) if s > 60 else fill((236, 214, 110), a, blur=bl))
        cv.drawCircle(s * 0.38, 0, s * 0.1, fill((225, 200, 110), a, blur=bl))
        cv.drawCircle(s * 0.44, -s * 0.06, s * 0.05, fill((180, 30, 30), a))
        cv.drawCircle(s * 0.44, s * 0.06, s * 0.05, fill((180, 30, 30), a))
        if s > 60:
            ap = stroke((190, 170, 100), s * 0.012, a)
            for sg in (-1, 1):
                an = skia.Path()
                an.moveTo(s * 0.46, sg * s * 0.03)
                an.quadTo(s * 0.6, sg * s * 0.08, s * 0.7, sg * s * 0.18)
                cv.drawPath(an, ap)
    elif kind == "aphid":
        cv.drawOval(skia.Rect(-s * 0.4, -s * 0.28, s * 0.4, s * 0.28), fill((120, 170, 60), a, blur=bl))
        cv.drawOval(skia.Rect(-s * 0.2, -s * 0.18, s * 0.2, -s * 0.02), fill((200, 230, 140), a * 0.6, blur=bl))
        sp = stroke((60, 90, 30), max(0.8, s * 0.04), a)
        for k in (-1, 0, 1):
            cv.drawLine(k * s * 0.15, s * 0.2, k * s * 0.22, s * 0.45, sp)
            cv.drawLine(k * s * 0.15, -s * 0.2, k * s * 0.22, -s * 0.45, sp)
    else:
        wingc = (200, 205, 210) if kind == "gnat" else (225, 215, 190)
        bodyc = (35, 32, 30) if kind == "gnat" else (95, 65, 35)
        for sg in (-1, 1):
            cv.save()
            cv.rotate(sg * (10 + 26 * flap))
            r = skia.Rect(-s * 0.05, -s * 0.09, s * 0.75, s * 0.09)
            cv.translate(0, sg * s * 0.12)
            cv.drawOval(r, fill(wingc, a * 0.55, blur=bl + s * 0.01))
            cv.restore()
        bw = 0.09 if kind == "thrips" else 0.12
        cv.drawOval(skia.Rect(-s * 0.45, -s * bw, s * 0.4, s * bw), fill(bodyc, a, blur=bl))
        cv.drawCircle(s * 0.42, 0, s * 0.08, fill(bodyc, a, blur=bl))
    cv.restore()


TRAP_ASPECT = 20 / 15


def draw_trap(cv, cx, cy, w, col, bugs=0, seed=1, glow=0.0, rot=0.0, peel=1.0, a=255, hang=False,
              hang_len=120, skew=1.0):
    """Sticky card, portrait 15x20, glossy. peel <1 shows clear film still on (peels from bottom-right)."""
    h = w * TRAP_ASPECT
    cv.save()
    cv.translate(cx, cy)
    cv.rotate(math.degrees(rot))
    cv.scale(skew, 1)
    if hang:
        cv.drawLine(0, -h / 2 + w * 0.05, 0, -h / 2 - hang_len, stroke((140, 110, 70), max(2, w * 0.012), a))
    if glow > 0:
        cv.drawRRect(rrect(-w * 0.75, -h * 0.75, w * 1.5, h * 1.5, w * 0.3), fill(col, 120 * glow, blur=w * 0.35))
    cv.drawRRect(rrect(-w / 2 + w * 0.04, -h / 2 + w * 0.06, w, h, w * 0.04), fill((0, 0, 0), 70 * a / 255, blur=w * 0.05))
    body = rrect(-w / 2, -h / 2, w, h, w * 0.04)
    cv.drawRRect(body, lin((-w / 2, -h / 2), (w / 2, h / 2), [(shade(col, 1.08), a), (shade(col, 0.86), a)]))
    cv.save()
    cv.clipRRect(body, doAntiAlias=True)
    gp = stroke(shade(col, 0.72), max(1, w * 0.005), 120 * a / 255)
    for i in range(1, 6):
        cv.drawLine(-w / 2 + w * i / 6, -h / 2 + h * 0.1, -w / 2 + w * i / 6, h / 2, gp)
    for j in range(1, 8):
        yy = -h / 2 + h * 0.1 + h * 0.9 * j / 8
        cv.drawLine(-w / 2, yy, w / 2, yy, gp)
    rnd = random.Random(seed)
    for i in range(bugs):
        draw_insect(cv, rnd.uniform(-w * 0.44, w * 0.44), rnd.uniform(-h * 0.36, h * 0.47),
                    w * rnd.uniform(0.03, 0.05), rnd.choice(["whitefly", "whitefly", "gnat", "thrips", "aphid"]),
                    0, rnd.uniform(0, 6.28), stuck=True, a=a)
    # glue sheen
    sh = skia.Path()
    sh.moveTo(-w / 2, -h * 0.1)
    sh.lineTo(-w * 0.1, -h / 2)
    sh.lineTo(w * 0.15, -h / 2)
    sh.lineTo(-w / 2, h * 0.15)
    sh.close()
    cv.drawPath(sh, fill((255, 255, 255), 60 * a / 255, blur=w * 0.03))
    if peel < 1.0:
        p = ease(peel)
        d = (w + h) * p
        c1 = (w / 2, h / 2 - d) if d <= h else (w / 2 - (d - h), -h / 2)
        c2 = (w / 2 - d, h / 2) if d <= w else (-w / 2, h / 2 - (d - w))
        film = skia.Path()
        film.moveTo(-w / 2, -h / 2)
        film.lineTo(w / 2, -h / 2)
        film.lineTo(*c1)
        film.lineTo(*c2)
        film.lineTo(-w / 2, h / 2)
        film.close()
        cv.drawPath(film, fill((255, 255, 255), 85 * a / 255))
        cv.restore()
        if p > 0.01:
            mx, my = (c1[0] + c2[0]) / 2, (c1[1] + c2[1]) / 2
            tip = (mx - d * 0.3, my - d * 0.3)
            fl = skia.Path()
            fl.moveTo(*c1)
            fl.quadTo(tip[0], tip[1], *c2)
            fl.close()
            cv.drawPath(fl, fill((240, 246, 252), 235 * a / 255))
            cv.drawPath(fl, stroke((150, 160, 170), 2, 180 * a / 255))
    else:
        cv.restore()
    cv.drawCircle(0, -h / 2 + w * 0.05, w * 0.03, fill((250, 250, 250), a))
    cv.restore()


# ------------------------------------------------------------------ characters (cel-shaded, ~1:5.5)
MEERA = dict(skin=hexc("#C98B5E"), skin_sh=hexc("#A86C45"), hair=hexc("#1E1410"), hair_hi=hexc("#5A3A2A"),
             top=hexc("#C2185B"), top_sh=hexc("#8E1044"), trim=hexc("#F2C14E"), dupatta=hexc("#2E8B57"),
             bottom=hexc("#F5E6C8"), lips=hexc("#A2403E"), kind="f")
RAJU = dict(skin=hexc("#9C6440"), skin_sh=hexc("#7A4A2E"), hair=hexc("#2A221E"), hair_hi=hexc("#6D6058"),
            top=hexc("#F4F1E8"), top_sh=hexc("#CFC8B6"), trim=hexc("#B03A2E"), dupatta=hexc("#C0392B"),
            bottom=hexc("#EDE8DA"), lips=hexc("#6E3B2C"), turban=hexc("#F28C1B"), turban_sh=hexc("#C86A0A"),
            kind="m")


def cel(cv, path, base, sh, light_dx=0.35, rim=None, a=255):
    """Two-tone cel fill: base + shadow on the right-hand portion + optional rim light on the left edge."""
    cv.drawPath(path, fill(base, a))
    b = path.computeTightBounds()
    cv.save()
    cv.clipPath(path, doAntiAlias=True)
    sp = skia.Path()
    x0 = b.left() + b.width() * (0.5 + light_dx * 0.5)
    sp.moveTo(x0, b.top() - 10)
    sp.cubicTo(x0 - b.width() * 0.12, b.centerY(), x0 + b.width() * 0.05, b.centerY(), x0 - b.width() * 0.08, b.bottom() + 10)
    sp.lineTo(b.right() + 10, b.bottom() + 10)
    sp.lineTo(b.right() + 10, b.top() - 10)
    sp.close()
    cv.drawPath(sp, fill(sh, a))
    if rim:
        cv.drawPath(path, stroke(rim, max(2.0, b.width() * 0.06), 90 * a / 255))
    cv.restore()


def limb(x0, y0, x1, y1, w0, w1):
    ang = math.atan2(y1 - y0, x1 - x0)
    nx, ny = -math.sin(ang), math.cos(ang)
    p = skia.Path()
    p.moveTo(x0 + nx * w0 / 2, y0 + ny * w0 / 2)
    p.lineTo(x1 + nx * w1 / 2, y1 + ny * w1 / 2)
    p.arcTo(skia.Rect(x1 - w1 / 2, y1 - w1 / 2, x1 + w1 / 2, y1 + w1 / 2), math.degrees(ang) + 90, -180, False)
    p.lineTo(x0 - nx * w0 / 2, y0 - ny * w0 / 2)
    p.arcTo(skia.Rect(x0 - w0 / 2, y0 - w0 / 2, x0 + w0 / 2, y0 + w0 / 2), math.degrees(ang) - 90, -180, False)
    p.close()
    return p


def draw_hand(cv, x, y, u, ang, P, curl=0.0, a=255):
    """Hand with palm, 4 fingers and thumb. u = unit size (head height)."""
    cv.save()
    cv.translate(x, y)
    cv.rotate(math.degrees(ang))
    palm = skia.Path()
    palm.addRRect(rrect(-u * 0.11, 0, u * 0.22, u * 0.2, u * 0.07))
    cel(cv, palm, P["skin"], P["skin_sh"], a=a)
    for i in range(4):
        fx = -u * 0.085 + i * u * 0.057
        L = u * (0.15 + (0.03 if i in (1, 2) else 0)) * (1 - curl * 0.5)
        f = limb(fx, u * 0.18, fx + curl * u * 0.04, u * 0.18 + L, u * 0.05, u * 0.042)
        cel(cv, f, P["skin"], P["skin_sh"], a=a)
    th = limb(u * 0.1, u * 0.06, u * 0.19, u * 0.16 - curl * u * 0.04, u * 0.06, u * 0.05)
    cel(cv, th, P["skin"], P["skin_sh"], a=a)
    cv.restore()


def draw_person(cv, x, y, u, t, P, arm_r=(0.25, 0.2), arm_l=(-0.25, -0.2), talk=0.0, brow=0.0, tilt=0.0,
                look=0.0, curl_r=0.0, curl_l=0.0, sway=0.0):
    """Feet at (x,y), u = head height px. arm = (shoulder angle, elbow angle) radians from hanging down,
    positive swings toward camera-left... returns dict of hand positions."""
    blink = 0.12 if (t % 3.3) < 0.11 else 1.0
    br = math.sin(t * 2.0) * u * 0.012
    cv.save()
    cv.translate(x, y)
    # contact shadow
    cv.drawOval(skia.Rect(-u * 0.9, -u * 0.08, u * 0.9, u * 0.08), fill((0, 0, 0), 70, blur=u * 0.06))
    hipY, shY = -u * 2.9, -u * 4.55 + br
    # legs / bottom wear
    for sg in (-1, 1):
        lg = limb(sg * u * 0.2, hipY, sg * u * 0.22, -u * 0.12, u * 0.36, u * 0.26)
        cel(cv, lg, P["bottom"], shade(P["bottom"], 0.82))
        cv.drawOval(skia.Rect(sg * u * 0.22 - u * 0.2, -u * 0.16, sg * u * 0.22 + u * 0.24, u * 0.02),
                    fill((70, 45, 30)))
    hands = {}

    def arm(side, angs, curl, front):
        sx = side * u * 0.62
        a1, a2 = angs
        ex, ey = sx + math.sin(a1) * u * 1.15 * side * -1, shY + u * 0.1 + math.cos(a1) * u * 1.15
        hx, hy = ex + math.sin(a1 + a2) * u * 1.05 * side * -1, ey + math.cos(a1 + a2) * u * 1.05
        up = limb(sx, shY + u * 0.1, ex, ey, u * 0.34, u * 0.27)
        cel(cv, up, P["top"], P["top_sh"])
        fo = limb(ex, ey, hx, hy, u * 0.25, u * 0.19)
        if P["kind"] == "f":
            cel(cv, fo, P["skin"], P["skin_sh"])
            cv.drawLine(ex + (hx - ex) * 0.75, ey + (hy - ey) * 0.75, ex + (hx - ex) * 0.78, ey + (hy - ey) * 0.78,
                        stroke(P["trim"], u * 0.22, 230))  # bangle
        else:
            cel(cv, fo, P["top"], P["top_sh"])
        ang = math.atan2(hy - ey, hx - ex) - math.pi / 2
        draw_hand(cv, hx, hy, u, ang, P, curl)
        hands[side] = (x + hx, y + hy)

    arm(1, arm_r, curl_r, False)  # far arm (camera-right side)
    # torso / kurta with flare and folds
    tor = skia.Path()
    tor.moveTo(-u * 0.62, shY)
    tor.cubicTo(-u * 0.75, shY + u * 0.4, -u * 0.55, hipY - u * 0.3, -u * 0.55, hipY)
    tor.lineTo(-u * (0.85 + 0.03 * math.sin(t * 1.5 + sway)), -u * 1.35)
    tor.quadTo(0, -u * 1.25, u * (0.85 + 0.03 * math.sin(t * 1.5 + 1 + sway)), -u * 1.35)
    tor.lineTo(u * 0.55, hipY)
    tor.cubicTo(u * 0.55, hipY - u * 0.3, u * 0.75, shY + u * 0.4, u * 0.62, shY)
    tor.quadTo(0, shY - u * 0.12, -u * 0.62, shY)
    tor.close()
    cel(cv, tor, P["top"], P["top_sh"], rim=(255, 230, 200))
    cv.save()
    cv.clipPath(tor, doAntiAlias=True)
    fp = stroke(P["top_sh"], u * 0.025, 160)
    for k in (-0.35, 0.05, 0.4):
        f = skia.Path()
        f.moveTo(k * u, hipY + u * 0.2)
        f.quadTo(k * u * 1.2 + u * 0.05, -u * 2.0, k * u * 1.5, -u * 1.4)
        cv.drawPath(f, fp)
    # border trim + booti pattern
    cv.drawRect(skia.Rect(-u, -u * 1.5, u, -u * 1.33), fill(P["trim"], 230))
    if P["kind"] == "f":
        for i in range(-4, 5):
            for j in range(4):
                cv.drawCircle(i * u * 0.2 + (j % 2) * u * 0.1, hipY + u * 0.2 + j * u * 0.3, u * 0.025, fill(P["trim"], 170))
    cv.restore()
    # dupatta / gamchha with secondary motion
    sw = math.sin(t * 2.2 + sway) * u * 0.06
    d = skia.Path()
    if P["kind"] == "f":
        d.moveTo(-u * 0.55, shY - u * 0.02)
        d.cubicTo(-u * 0.1, shY + u * 0.6, u * 0.3, hipY, u * 0.55 + sw, hipY + u * 0.4)
        d.lineTo(u * 0.75 + sw, hipY + u * 0.2)
        d.cubicTo(u * 0.5, hipY - u * 0.4, u * 0.1, shY + u * 0.3, -u * 0.2, shY - u * 0.06)
        d.close()
    else:
        d.moveTo(-u * 0.62, shY)
        d.lineTo(-u * 0.3, shY - u * 0.05)
        d.lineTo(-u * 0.38 + sw, shY + u * 1.1)
        d.lineTo(-u * 0.62 + sw, shY + u * 1.05)
        d.close()
    cel(cv, d, P["dupatta"], shade(P["dupatta"], 0.75))
    if P["kind"] == "m":  # check pattern on gamchha
        cv.save()
        cv.clipPath(d, doAntiAlias=True)
        for k in range(8):
            cv.drawLine(-u, shY + k * u * 0.15, u, shY + k * u * 0.15, stroke((240, 220, 200), u * 0.02, 120))
        cv.restore()
    # neck
    nk = limb(0, shY - u * 0.05, 0, shY - u * 0.35, u * 0.26, u * 0.24)
    cel(cv, nk, P["skin"], P["skin_sh"])
    # head
    cv.save()
    cv.translate(0, shY - u * 0.85)
    cv.rotate(math.degrees(tilt))
    hw, hh = u * 0.4, u * 0.5
    if P["kind"] == "f":  # hair mass behind (braid over shoulder)
        hb = skia.Path()
        hb.addOval(skia.Rect(-hw * 1.15, -hh * 1.05, hw * 1.15, hh * 0.75))
        cv.drawPath(hb, fill(P["hair"]))
        br_ = skia.Path()
        br_.moveTo(-hw * 0.9, hh * 0.3)
        br_.cubicTo(-hw * 1.4 + sw * 0.5, hh * 1.2, -hw * 1.1 + sw, hh * 2.2, -hw * 1.3 + sw, hh * 2.9)
        cv.drawPath(br_, stroke(P["hair"], u * 0.16))
    ears = (P["skin_sh"])
    for sg in (-1, 1):
        cv.drawOval(skia.Rect(sg * hw * 0.98 - u * 0.06, -u * 0.05, sg * hw * 0.98 + u * 0.06, u * 0.12), fill(ears))
        if P["kind"] == "f":
            cv.drawCircle(sg * hw * 0.98, u * 0.16, u * 0.035, fill(P["trim"]))
    face = skia.Path()
    face.moveTo(-hw, -hh * 0.2)
    face.cubicTo(-hw, -hh * 1.05, hw, -hh * 1.05, hw, -hh * 0.2)
    face.cubicTo(hw, hh * 0.45, hw * 0.45, hh * 0.95, 0, hh)
    face.cubicTo(-hw * 0.45, hh * 0.95, -hw, hh * 0.45, -hw, -hh * 0.2)
    face.close()
    cel(cv, face, P["skin"], P["skin_sh"], light_dx=0.55, rim=(255, 225, 190))
    lx = look * u * 0.05
    # eyes
    for sg in (-1, 1):
        ex, ey = sg * hw * 0.42 + lx, -hh * 0.05
        cv.save()
        cv.translate(ex, ey)
        cv.scale(1, blink)
        eye = skia.Path()
        eye.moveTo(-u * 0.09, 0)
        eye.quadTo(0, -u * 0.075, u * 0.09, 0)
        eye.quadTo(0, u * 0.06, -u * 0.09, 0)
        cv.drawPath(eye, fill((250, 248, 244)))
        cv.save()
        cv.clipPath(eye, doAntiAlias=True)
        cv.drawCircle(lx * 0.6, 0, u * 0.055, fill((70, 42, 25)))
        cv.drawCircle(lx * 0.6, 0, u * 0.028, fill((15, 10, 8)))
        cv.drawCircle(lx * 0.6 + u * 0.018, -u * 0.02, u * 0.014, fill((255, 255, 255)))
        cv.restore()
        cv.drawPath(eye, stroke((30, 20, 15), u * 0.016))
        cv.restore()
        # brows (acting)
        bp = skia.Path()
        by = ey - u * 0.11 - brow * u * 0.04
        bp.moveTo(ex - u * 0.1, by + sg * brow * u * 0.02 * -1 + u * 0.01)
        bp.quadTo(ex, by - u * 0.03, ex + u * 0.1, by + sg * brow * u * 0.02)
        cv.drawPath(bp, stroke(P["hair"], u * 0.03))
    # nose
    nose = skia.Path()
    nose.moveTo(lx, hh * 0.05)
    nose.quadTo(lx + u * 0.05, hh * 0.3, lx - u * 0.02, hh * 0.35)
    cv.drawPath(nose, stroke(P["skin_sh"], u * 0.022))
    # mouth (lip-sync)
    my = hh * 0.58
    if P["kind"] == "m":  # moustache
        mo = skia.Path()
        mo.moveTo(lx - u * 0.16, my - u * 0.01)
        mo.quadTo(lx, my - u * 0.1, lx + u * 0.16, my - u * 0.01)
        mo.quadTo(lx, my - u * 0.04, lx - u * 0.16, my - u * 0.01)
        cv.drawPath(mo, fill(P["hair_hi"]))
    op = clamp(talk)
    if op > 0.08:
        m = skia.Path()
        m.addOval(skia.Rect(lx - u * 0.08, my - u * 0.02, lx + u * 0.08, my + u * (0.03 + 0.09 * op)))
        cv.drawPath(m, fill((90, 25, 25)))
        cv.save()
        cv.clipPath(m, doAntiAlias=True)
        cv.drawRect(skia.Rect(lx - u * 0.08, my - u * 0.02, lx + u * 0.08, my + u * 0.015), fill((250, 250, 245)))
        cv.restore()
        cv.drawPath(m, stroke(P["lips"], u * 0.018))
    else:
        sm = skia.Path()
        sm.moveTo(lx - u * 0.08, my)
        sm.quadTo(lx, my + u * 0.05 * (1 - brow), lx + u * 0.08, my)
        cv.drawPath(sm, stroke(P["lips"], u * 0.025))
    if P["kind"] == "f":
        cv.drawCircle(lx, -hh * 0.42, u * 0.022, fill((200, 20, 40)))  # bindi
        for sg in (-1, 1):
            cv.drawCircle(sg * hw * 0.55 + lx, hh * 0.3, u * 0.06, fill((230, 110, 110), 50, blur=u * 0.03))
        # front hair mass with parting + highlight
        fh = skia.Path()
        fh.moveTo(-hw * 1.08, hh * 0.15)
        fh.cubicTo(-hw * 1.15, -hh * 1.25, hw * 1.15, -hh * 1.25, hw * 1.08, hh * 0.15)
        fh.cubicTo(hw * 0.95, -hh * 0.45, hw * 0.3, -hh * 0.62, u * 0.0, -hh * 0.75)
        fh.cubicTo(-hw * 0.3, -hh * 0.62, -hw * 0.95, -hh * 0.45, -hw * 1.08, hh * 0.15)
        fh.close()
        cv.drawPath(fh, fill(P["hair"]))
        hl = skia.Path()
        hl.moveTo(-hw * 0.7, -hh * 0.7)
        hl.quadTo(-hw * 0.3, -hh * 0.95, hw * 0.1, -hh * 0.9)
        cv.drawPath(hl, stroke(P["hair_hi"], u * 0.045, 200))
    else:  # turban with wrapped folds
        tb = skia.Path()
        tb.moveTo(-hw * 1.12, -hh * 0.25)
        tb.cubicTo(-hw * 1.3, -hh * 1.6, hw * 1.3, -hh * 1.6, hw * 1.12, -hh * 0.25)
        tb.quadTo(0, -hh * 0.45, -hw * 1.12, -hh * 0.25)
        tb.close()
        cel(cv, tb, P["turban"], P["turban_sh"], rim=(255, 220, 160))
        for k in range(3):
            fo = skia.Path()
            fo.moveTo(-hw * 1.05, -hh * (0.45 + k * 0.25))
            fo.quadTo(0, -hh * (0.75 + k * 0.32), hw * 1.05, -hh * (0.35 + k * 0.28))
            cv.drawPath(fo, stroke(P["turban_sh"], u * 0.025, 200))
    cv.restore()  # head
    arm(-1, arm_l, curl_l, True)  # near arm
    cv.restore()
    return hands


_ENV = {}


def talk_curve(t, speaker):
    """Mouth-open 0..1 from the speaker's own VO amplitude (computed in build_vo)."""
    e = _ENV.get(speaker)
    if e is None:
        return 0.0
    i = int(t * 100)
    return float(e[i]) if 0 <= i < len(e) else 0.0


# ------------------------------------------------------------------ backgrounds (semi-real plates)
def sky(cv, top, bot):
    cv.drawRect(skia.Rect(0, 0, W, H), lin((0, 0), (0, H), [top, bot]))


def city_blur(cv, t, base_y, warm=0.0):
    blur_layer(cv, 9)
    rnd = random.Random(5)
    x = -60
    while x < W + 60:
        w = rnd.uniform(110, 220)
        h = rnd.uniform(250, 620)
        c = mix((150, 165, 185), (210, 175, 150), warm)
        cv.drawRect(skia.Rect(x, base_y - h, x + w, base_y), fill(c))
        for wy in range(int(base_y - h + 30), int(base_y - 20), 52):
            for wx in range(int(x + 16), int(x + w - 24), 40):
                if rnd.random() < 0.7:
                    cv.drawRect(skia.Rect(wx, wy, wx + 18, wy + 24), fill(mix(c, (255, 250, 230), 0.35)))
        x += w + rnd.uniform(6, 30)
    cv.restore()


def terrace_plate(cv, t, cam=1.0, warm=0.0, plants=True, sick=0.6):
    sky(cv, mix((150, 195, 235), (250, 180, 120), warm), mix((235, 230, 215), (255, 215, 170), warm))
    cv.drawCircle(W * 0.78, H * 0.17, 260, rad((W * 0.78, H * 0.17), 260, [((255, 245, 210), 220), ((255, 245, 210), 0)]))
    city_blur(cv, t, H * 0.52, warm)
    # parapet (slightly soft)
    blur_layer(cv, 3)
    cv.drawRect(skia.Rect(0, H * 0.5, W, H * 0.6), lin((0, H * 0.5), (0, H * 0.6), [(236, 226, 205), (210, 196, 172)]))
    cv.drawRect(skia.Rect(0, H * 0.49, W, H * 0.51), fill((190, 172, 145)))
    cv.restore()
    cv.drawRect(skia.Rect(0, H * 0.6, W, H), lin((0, H * 0.6), (0, H), [(205, 170, 135), (150, 112, 82)]))
    gp = stroke((120, 85, 60), 3, 70)
    for i in range(-10, 11):
        cv.drawLine(W / 2 + i * 70, H * 0.6, W / 2 + i * 300, H, gp)
    for yy in (0.63, 0.68, 0.75, 0.85, 0.98):
        cv.drawLine(0, H * yy, W, H * yy, gp)
    if plants:
        for i, (px, py, s) in enumerate([(160, 1150, 1.0), (520, 1100, 0.85), (880, 1170, 1.05)]):
            pot_plant(cv, px, py, 300 * s, t, seed=10 + i, sick=sick)


def pot_plant(cv, x, y, s, t, seed=1, sick=0.0, fruits=True):
    rnd = random.Random(seed)
    sw = math.sin(t * 1.1 + seed) * 0.03
    for i in range(9):
        ang = -math.pi / 2 + (i - 4) * 0.28 + sw + rnd.uniform(-0.1, 0.1)
        L = s * rnd.uniform(0.55, 0.95)
        ex, ey = x + math.cos(ang) * L, y - s * 0.3 + math.sin(ang) * L
        st = skia.Path()
        st.moveTo(x, y - s * 0.3)
        st.quadTo(x + (ex - x) * 0.3, y - s * 0.6, ex, ey)
        cv.drawPath(st, stroke((70, 110, 50), s * 0.022))
        for k in range(3):
            f = 0.45 + k * 0.25
            lx, ly = lerp(x, ex, f), lerp(y - s * 0.4, ey, f)
            for sg in (-1, 1):
                draw_leaf(cv, lx, ly, s * 0.24, ang + sg * 0.95 + sw * 2,
                          base=(48 + rnd.randint(0, 20), 120 + rnd.randint(0, 25), 48),
                          sick=sick * rnd.random(), seed=seed * 10 + i * 3 + k, veins=s > 220)
        if fruits and i % 3 == 0:
            cv.drawCircle(ex, ey + s * 0.06, s * 0.055, rad((ex - s * 0.02, ey + s * 0.04), s * 0.07,
                                                        [(240, 90, 60), (190, 30, 20)]))
    pot = skia.Path()
    pot.moveTo(x - s * 0.26, y - s * 0.32)
    pot.lineTo(x + s * 0.26, y - s * 0.32)
    pot.lineTo(x + s * 0.2, y)
    pot.lineTo(x - s * 0.2, y)
    pot.close()
    cv.drawOval(skia.Rect(x - s * 0.3, y - s * 0.03, x + s * 0.3, y + s * 0.04), fill((0, 0, 0), 80, blur=10))
    cv.drawPath(pot, lin((x - s * 0.26, 0), (x + s * 0.26, 0), [(200, 110, 70), (150, 75, 45)]))
    cv.drawRRect(rrect(x - s * 0.3, y - s * 0.37, s * 0.6, s * 0.07, s * 0.02), fill((175, 90, 55)))


def swarm(cv, t, n, box, seed, size, dof=True):
    rnd = random.Random(seed)
    x0, y0, x1, y1 = box
    for i in range(n):
        bx, by = rnd.uniform(x0, x1), rnd.uniform(y0, y1)
        f1, f2, ph = rnd.uniform(0.6, 1.5), rnd.uniform(0.7, 1.6), rnd.uniform(0, 6.3)
        depth = rnd.random()
        x = bx + 50 * math.sin(t * f1 + ph) + 16 * math.sin(t * 3.7 * f2 + ph)
        y = by + 40 * math.cos(t * f2 + ph) + 14 * math.sin(t * 4.1 + ph)
        s = size * (0.6 + depth * 1.3)
        near = dof and depth > 0.88
        draw_insect(cv, x, y, s * (2.2 if near else 1), rnd.choice(["whitefly", "whitefly", "gnat"]), t,
                    ang=math.sin(t + ph) * 0.6, a=150 if near else 255, blur=s * 0.25 if near else 0)


# ------------------------------------------------------------------ overlays: letterbox, lower-third, captions
def letterbox(cv, k=1.0):
    bh = 150 * k
    cv.drawRect(skia.Rect(0, 0, W, bh), fill((0, 0, 0)))


def lower_third(cv, t, t0, title, sub, y=1180, x=70):
    a = ease((t - t0) / 0.5) * (1 - ease((t - t0 - 2.8) / 0.4))
    if a <= 0:
        return
    al = 255 * a
    lw = 560 * eout((t - t0) / 0.6)
    cv.drawRect(skia.Rect(x, y, x + lw, y + 3), fill((255, 255, 255), al))
    text(cv, title, x, y - 22, "serif", 52, (255, 255, 255), al, shadow=6)
    text(cv, sub, x, y + 52, "serif_i", 32, (235, 235, 225), al, shadow=6)


SPEAKER_COL = {"NARRATOR": (240, 236, 220), "MEERA": hexc("#F06292"), "RAJU KAKA": hexc("#FFB74D")}


def captions(cv, t):
    for li, (a, b, sp, s) in enumerate(LINES):
        if a - 0.1 <= t <= b + 0.2 and WORDS[li]:
            wl = WORDS[li]
            words = [w for _, _, w in wl]
            cur = max([k for k, (wa, wb, _) in enumerate(wl) if t >= wa - 0.02] or [0])
            fade = ease((t - (a - 0.1)) / 0.12) * (1 - ease((t - b - 0.08) / 0.12))
            size = 58
            f = font("sans", size)
            lines, cur_line = [], []
            for i, w in enumerate(words):
                trial = " ".join([words[j] for j in cur_line] + [w])
                if cur_line and f.measureText(trial) > 900:
                    lines.append(cur_line)
                    cur_line = []
                cur_line.append(i)
            lines.append(cur_line)
            y0 = 1480 - (len(lines) - 1) * 36
            tc = SPEAKER_COL[sp]
            tf = font("mono", 26)
            tw = tf.measureText(sp)
            cv.drawRRect(rrect(W_ / 2 - tw / 2 - 18, y0 - 112, tw + 36, 44, 22), fill(tc, 235 * fade))
            cv.drawString(sp, W_ / 2 - tw / 2, y0 - 80, tf, fill((25, 25, 25), 255 * fade))
            for ln, idxs in enumerate(lines):
                lw = f.measureText(" ".join(words[i] for i in idxs))
                x = W_ / 2 - lw / 2
                y = y0 + ln * 76
                for i in idxs:
                    w = words[i]
                    ww = f.measureText(w)
                    on = i == cur
                    if on:
                        cv.drawRRect(rrect(x - 8, y - 52, ww + 16, 68, 12), fill(YEL, 245 * fade))
                    cv.drawString(w, x + 2, y + 3, f, fill((0, 0, 0), 200 * fade, blur=5))
                    cv.drawString(w, x, y, f, fill((20, 20, 20) if on else (255, 255, 255), 255 * fade))
                    x += ww + f.measureText(" ")
            return


def corner_mark(cv):
    text(cv, "buildingshop.in", W - 40, 205, "sans", 28, (255, 255, 255), 170, anchor="r", shadow=4)


# ------------------------------------------------------------------ scenes
def sc_macro_fly(cv, lt, t):
    # extreme macro: leaf surface, whitefly, bokeh
    cam = 1.0 + 0.12 * ease(lt / 3.5)
    cv.save()
    cv.translate(W / 2, H / 2)
    cv.scale(cam, cam)
    cv.translate(-W / 2, -H / 2)
    cv.drawRect(skia.Rect(0, 0, W, H), lin((0, 0), (W, H), [(30, 70, 35), (12, 35, 18)]))
    blur_layer(cv, 18)
    bokeh(cv, t, 4, 26, [(140, 200, 90), (230, 240, 160), (90, 150, 70)], 40, 120, 90)
    cv.restore()
    if AMAZON:  # product present from frame 1: a card hanging, defocused, behind the leaf
        blur_layer(cv, 10)
        draw_trap(cv, 860, 560, 260, YEL, hang=True, hang_len=600, glow=0.3)
        cv.restore()
    draw_leaf(cv, -200, 1250, 1700, -0.45, base=(62, 140, 58), sick=0.35, seed=4)
    # the specimen
    fx = 560 + math.sin(lt * 1.3) * 10
    fy = 950 + math.cos(lt * 0.9) * 6
    draw_insect(cv, fx, fy, 260, "whitefly", t, ang=-0.35, stuck=False)
    # tiny legs + proboscis detail
    sp = stroke((210, 200, 150), 4)
    for k in (-1, 0, 1):
        cv.drawLine(fx + k * 40, fy + 20, fx + k * 55 - 10, fy + 70, sp)
    cv.restore()
    # foreground out-of-focus leaf edge (depth)
    blur_layer(cv, 26)
    draw_leaf(cv, 700, 1900, 900, -1.9, base=(30, 80, 30))
    cv.restore()
    lower_third(cv, lt, 0.5, "WHITEFLY", "terrace predator  ·  ~1.5 mm")


def sc_leaf_reveal(cv, lt, t):
    cam = 1.18 - 0.16 * ease(lt / 4.0)
    cv.save()
    cv.translate(W / 2, H * 0.55)
    cv.scale(cam, cam)
    cv.translate(-W / 2, -H * 0.55)
    terrace_plate(cv, t, sick=0.9)
    swarm(cv, t, 46, (60, 650, 1020, 1250), 21, 16)
    cv.restore()
    lower_third(cv, lt, 0.6, "Day 14", "the tomato colony is losing colour", y=1150)


def sc_meera_worried(cv, lt, t):
    cam = 1.05 + 0.05 * ease(lt / 3)
    cv.save()
    cv.translate(W / 2, H * 0.6)
    cv.scale(cam, cam)
    cv.translate(-W / 2 - 10 * min(lt, 4.0), -H * 0.6)
    blur_layer(cv, 6)
    terrace_plate(cv, t, sick=0.9)
    cv.restore()
    sw = math.sin(lt * 6) * 0.25
    draw_person(cv, 560, 2050, 250, t, MEERA, arm_l=(-2.3 + sw, -0.6), arm_r=(0.35, 0.3),
                talk=talk_curve(t, "MEERA"), brow=0.9, tilt=-0.06, look=0.4, curl_l=0.2)
    # yellowed leaf she holds up
    draw_leaf(cv, 870, 760, 220, -0.8, sick=1.0, seed=9)
    swarm(cv, t, 22, (100, 400, 1000, 1100), 33, 14)
    cv.restore()


def sc_species(cv, lt, t):
    # dark undergrowth, god rays, the two new species descend
    cv.drawRect(skia.Rect(0, 0, W, H), lin((0, 0), (0, H), [(16, 40, 26), (5, 14, 9)]))
    god_rays(cv, t, (W * 0.5, -200), a=50 if t > CUE['peela'] else 22)
    blur_layer(cv, 14)
    rnd = random.Random(8)
    for i in range(14):
        draw_leaf(cv, rnd.uniform(-200, W), rnd.uniform(300, H), rnd.uniform(400, 800), rnd.uniform(-2.5, -0.5),
                  base=(25, 70, 35), veins=False, light=0.6)
    cv.restore()
    # dust motes
    rnd = random.Random(2)
    for i in range(60):
        x = rnd.uniform(0, W) + math.sin(t * 0.5 + i) * 30
        y = (rnd.uniform(0, H) - t * 25 * rnd.uniform(0.5, 1.5)) % H
        cv.drawCircle(x, y, rnd.uniform(1.5, 4), fill((255, 245, 210), 120))
    # entrance exactly on the words "Peela" and "neela"
    for k, (col, tin, x) in enumerate([(YEL, CUE["peela"], 380), (BLU, CUE["neela"], 720)]):
        p = bout((t - tin) / 0.9)
        if t < tin - 0.05:
            continue
        y = lerp(-500, 900, p) + math.sin(t * 1.5 + k) * 10
        draw_trap(cv, x, y, 310, col, glow=0.8 * ease((t - tin) / 0.6), rot=(1 - p) * 0.4 * (1 if k else -1),
                  hang=True, hang_len=900)
    if t > CUE["neela"] + 0.4:
        lower_third(cv, t - CUE["neela"] - 0.4, 0.0, "STICKY TRAP", "yellow & blue  ·  15 × 20 cm  ·  double-sided", y=1250)
    swarm(cv, t, 10, (100, 500, 1000, 1200), 70, 12)


def sc_meera_hangs(cv, lt, t):
    cam = 1.1 - 0.05 * ease(lt / 3.4)
    cv.save()
    cv.translate(W / 2, H / 2)
    cv.scale(cam, cam)
    cv.translate(-W / 2 + 6 * min(lt, 3.5), -H / 2)
    blur_layer(cv, 5)
    terrace_plate(cv, t, plants=False)
    cv.restore()
    pot_plant(cv, 760, 1420, 520, t, seed=31, sick=0.5)
    # bamboo stake + card being hung just above canopy
    cv.drawRRect(rrect(905, 620, 18, 800, 8), lin((905, 0), (923, 0), [(200, 165, 95), (150, 115, 60)]))
    cv.drawRRect(rrect(780, 610, 150, 14, 7), fill((180, 145, 80)))
    peel = ease((lt - 0.2) / 1.4)
    drop = eout((lt - 1.6) / 1.0)
    cy = lerp(520, 830, drop) if lt > 1.6 else 520
    cx = 800 if lt > 1.6 else 640
    draw_trap(cv, cx, cy, 200, YEL, peel=peel, hang=lt > 1.6, hang_len=cy - 620 - 133, rot=math.sin(lt * 3) * 0.04 * (1 - drop))
    # Meera reaching (near arm to card)
    hx = cx - 60
    reach = ease((lt - 0.1) / 0.6)
    hands = draw_person(cv, 380, 2000, 235, t, MEERA, arm_l=(lerp(0.3, 2.05, reach), lerp(0.2, 0.55, reach)),
                        arm_r=(0.3, 0.25), talk=talk_curve(t, "MEERA"), brow=-0.2, look=0.8, curl_l=0.6)
    if lt > 2.6:
        a = ease((lt - 2.6) / 0.3) * 255
        cv.drawLine(1000, 980, 1000, 1110, stroke((255, 255, 255), 4, a))
        text(cv, "just above", 985, 1050, "serif_i", 30, (255, 255, 255), a, anchor="r", shadow=5)


HUNT = []
_r = random.Random(77)
for i in range(30):
    HUNT.append(dict(t0=CUE['hunt'] + 0.05 + i * 0.09 + _r.random() * 0.2, dur=1.0 + _r.random() * 0.7,
                     sx=_r.choice([-60, W + 60]), sy=_r.uniform(250, 1700),
                     ex=_r.uniform(330, 750), ey=_r.uniform(560, 1250),
                     kind=_r.choice(["whitefly", "whitefly", "gnat", "aphid"])))


def sc_hunt(cv, lt, t):
    # macro on yellow card, slow-mo flight paths
    cam = 1.0 + 0.1 * ease(lt / 3.9)
    cv.save()
    cv.translate(W / 2, H * 0.47)
    cv.scale(cam, cam)
    cv.translate(-W / 2, -H * 0.47)
    cv.drawRect(skia.Rect(0, 0, W, H), lin((0, 0), (0, H), [(40, 90, 45), (15, 40, 20)]))
    blur_layer(cv, 20)
    bokeh(cv, t, 9, 20, [(150, 210, 100), (240, 240, 170)], 50, 140, 100)
    cv.restore()
    stuck = [b for b in HUNT if t >= b["t0"] + b["dur"]]
    draw_trap(cv, 540, 900, 560, YEL, glow=0.4)
    for b in stuck:
        draw_insect(cv, b["ex"], b["ey"], 38, b["kind"], t, ang=b["sx"] * 0.001, stuck=True)
    for b in HUNT:
        p = (t - b["t0"]) / b["dur"]
        if 0 < p < 1:
            e = ease(p)
            x = lerp(b["sx"], b["ex"], e) + math.sin(p * 10) * 70 * (1 - e)
            y = lerp(b["sy"], b["ey"], e) + math.cos(p * 8) * 50 * (1 - e)
            draw_insect(cv, x, y, 44, b["kind"], t * 0.35, ang=math.atan2(b["ey"] - b["sy"], b["ex"] - b["sx"]))
    cv.restore()
    # freeze label on first stick
    if len(stuck) > 0:
        first = min(HUNT, key=lambda b: b["t0"] + b["dur"])
        k = ease((t - first["t0"] - first["dur"]) / 0.3) * (1 - ease((t - (L(8) - 0.35)) / 0.3))
        if k > 0:
            text(cv, f"CAUGHT: {len(stuck)}", 70, 330, "mono", 44, (255, 255, 255), 255 * k, shadow=6)


def _farm_wide(cv, lt, t, parcel=False):
    cam = 1.04 + 0.07 * ease(lt / 4.1)
    cv.save()
    cv.translate(W / 2, H * 0.5)
    cv.scale(cam, cam)
    cv.translate(-W / 2 - 18 * min(lt, 4.0), -H * 0.5)
    sky(cv, (250, 175, 95), (255, 225, 160))
    cv.drawCircle(820, 620, 300, rad((820, 620), 300, [((255, 250, 220), 255), ((255, 230, 160), 0)]))
    blur_layer(cv, 8)
    rnd = random.Random(4)
    for i in range(30):
        cv.drawCircle(i * 45 - 40, 760 + rnd.uniform(-20, 10), rnd.uniform(40, 80), fill((70, 85, 45)))
    cv.restore()
    cv.drawRect(skia.Rect(-100, 760, W + 200, H), lin((0, 760), (0, H), [(150, 115, 70), (95, 65, 38)]))
    vx = W * 0.5
    for r in range(-10, 11):
        for d in range(1, 18):
            f = (d / 17) ** 1.8
            px = lerp(vx + r * 30, vx + r * 260, f)
            py = lerp(765, H + 50, f)
            cv.drawOval(skia.Rect(px - 6 - 60 * f, py - 10 - 55 * f, px + 6 + 60 * f, py + 5),
                        fill(mix((60, 120, 50), (90, 150, 60), ((r + d) % 3) / 3)))
    for d in (3, 6, 10, 14):
        f = (d / 17) ** 1.8
        for r in (-6, 2, 7):
            px = lerp(vx + r * 30 + 15, vx + r * 260 + 130, f)
            py = lerp(765, H + 50, f)
            cv.drawLine(px, py, px, py - 30 - 330 * f, stroke((185, 150, 85), 2 + 8 * f))
            draw_trap(cv, px, py - 30 - 330 * f, 16 + 150 * f, YEL if (r + d) % 2 else BLU, bugs=int(4 + 14 * f),
                      seed=d * 9 + r)
    # golden haze
    cv.drawRect(skia.Rect(0, 0, W, H), lin((0, 600), (0, 1100), [((255, 210, 140), 90), ((255, 210, 140), 0)]))
    cv.restore()
    if not parcel:
        draw_person(cv, 300, 1990, 240, t, RAJU, arm_l=(1.35 + 0.08 * math.sin(lt * 2), 0.5), arm_r=(0.3, 0.2),
                    talk=talk_curve(t, "RAJU KAKA"), brow=0.2, look=0.9, curl_l=0.3)
    else:  # proud, holding up the plain brown parcel it came in
        hands = draw_person(cv, 420, 1990, 250, t, RAJU, arm_l=(0.35, 1.1), arm_r=(0.35, 1.1),
                            talk=talk_curve(t, "RAJU KAKA"), brow=-0.3, look=0.3, curl_l=0.6, curl_r=0.6)
        bx = (hands[1][0] + hands[-1][0]) / 2
        by = (hands[1][1] + hands[-1][1]) / 2 + 20
        draw_trap(cv, bx + 45, by - 95, 110, YEL, rot=0.18)
        draw_trap(cv, bx - 45, by - 85, 110, BLU, rot=-0.15)
        cv.drawRRect(rrect(bx - 150, by - 70, 300, 170, 10), lin((0, by - 70), (0, by + 100), [(205, 160, 105), (165, 120, 72)]))
        cv.drawRect(skia.Rect(bx - 150, by - 10, bx + 150, by + 8), fill((225, 200, 150)))
    god_rays(cv, t, (820, 620), cols=(255, 230, 170), a=24, n=9, spread=6.0, length=1400)


def _farm_insert(cv, lt, t):
    # close insert: two cards on a stake in the crop row, real size callout
    cam = 1.12 - 0.08 * ease(lt / 3)
    cv.save()
    cv.translate(W / 2, H / 2)
    cv.scale(cam, cam)
    cv.translate(-W / 2, -H / 2)
    sky(cv, (250, 185, 110), (240, 210, 150))
    blur_layer(cv, 16)
    cv.drawRect(skia.Rect(0, 900, W, H), fill((110, 80, 45)))
    rnd = random.Random(14)
    for i in range(16):
        draw_leaf(cv, rnd.uniform(-100, W), rnd.uniform(1000, H), rnd.uniform(250, 450), rnd.uniform(-2.6, -0.6),
                  base=(60, 120, 50), veins=False)
    cv.restore()
    for k, (x, col, tin) in enumerate([(330, YEL, 0.0), (750, BLU, 0.0)]):
        cv.drawRRect(rrect(x - 9, 760, 18, 1200, 8), lin((x - 9, 0), (x + 9, 0), [(205, 170, 100), (150, 115, 60)]))
        draw_trap(cv, x, 700, 330, col, bugs=18 + 6 * k, seed=90 + k, rot=math.sin(t * 1.5 + k) * 0.02)
    a = 255 * ease((lt - 0.3) / 0.4)
    sp = stroke((255, 255, 255), 5, a)
    cv.drawLine(165, 950, 495, 950, sp)
    cv.drawLine(120, 480, 120, 920, sp)
    text(cv, "15 cm", 330, 1005, "serif", 40, (255, 255, 255), a, anchor="c", shadow=6)
    cv.save()
    cv.translate(95, 700)
    cv.rotate(-90)
    text(cv, "20 cm", 0, 0, "serif", 40, (255, 255, 255), a, anchor="c", shadow=6)
    cv.restore()
    cv.restore()


def sc_farm(cv, lt, t):
    if t < CUE["r2"] - 0.05:
        _farm_wide(cv, lt, t)
    elif t < CUE["r3"] - 0.05:
        _farm_insert(cv, t - CUE["r2"], t)
    else:
        _farm_wide(cv, t - CUE["r3"], t, parcel=True)


FIELD_NOTES = list(zip(["double-sided", "waterproof", "non-toxic", "indoor + outdoor"], CUE["notes"]))


def sc_field_notes(cv, lt, t):
    # greenhouse plate (soft) + field-journal cards pinned in sequence
    cam = 1.05 + 0.05 * ease(lt / 4.4)
    cv.save()
    cv.translate(W / 2, H / 2)
    cv.scale(cam, cam)
    cv.translate(-W / 2, -H / 2)
    sky(cv, (235, 245, 238), (175, 205, 175))
    blur_layer(cv, 7)
    for k in range(9):
        f = 0.25 + 0.75 * (k / 8) ** 1.5
        rw, rh = W * 1.6 * f, 1000 * f
        p = skia.Path()
        p.addArc(skia.Rect(W / 2 - rw / 2, 900 - rh + 300 * f, W / 2 + rw / 2, 900 + rh + 300 * f), 180, 180)
        cv.drawPath(p, stroke((200, 210, 210), 6))
    cv.drawRect(skia.Rect(0, 1000, W, H), lin((0, 1000), (0, H), [(130, 100, 70), (90, 65, 45)]))
    for r in range(-3, 4):
        for d in range(1, 12):
            f = (d / 11) ** 1.7
            px = lerp(W / 2 + r * 40, W / 2 + r * 380, f)
            py = lerp(1000, H, f)
            cv.drawCircle(px, py - 20 * f, 10 + 70 * f, fill((50, 130 + (d % 2) * 15, 55)))
    for r in (-2, 0, 2):
        for d in (4, 7, 10):
            f = (d / 11) ** 1.7
            px = lerp(W / 2 + r * 40, W / 2 + r * 380, f)
            py = lerp(950, 1200, f)
            draw_trap(cv, px, py - 60 * f, 20 + 120 * f, YEL if (r + d) % 2 else BLU, hang=True, hang_len=200 * f)
    cv.restore()
    cv.restore()
    cv.drawRect(skia.Rect(0, 0, W, H), fill((10, 30, 20), 90))
    # journal page
    pg = rrect(110, 380, 860, 800, 18)
    cv.drawRRect(rrect(120, 395, 860, 800, 18), fill((0, 0, 0), 90, blur=14))
    cv.drawRRect(pg, lin((110, 380), (970, 1180), [(250, 244, 226), (236, 226, 200)]))
    for k in range(10):
        cv.drawLine(150, 500 + k * 68, 930, 500 + k * 68, stroke((170, 190, 210), 2, 120))
    text(cv, "Field notes — specimen: Sticky Trap", 150, 455, "serif_i", 34, (60, 50, 40))
    for i, (s, tin) in enumerate(FIELD_NOTES):
        a = ease((t - tin) / 0.35)
        if a <= 0:
            continue
        y = 590 + i * 140
        cv.save()
        cv.translate(170, y)
        cv.scale(lerp(1.6, 1, eout((t - tin) / 0.35)), lerp(1.6, 1, eout((t - tin) / 0.35)))
        cv.drawCircle(0, -14, 28, fill(YEL if i % 2 == 0 else BLU, 255 * a))
        tick = skia.Path()
        tick.moveTo(-12, -14)
        tick.lineTo(-3, -4)
        tick.lineTo(14, -26)
        cv.drawPath(tick, stroke((255, 255, 255), 6, 255 * a))
        text(cv, s, 55, 0, "serif", 58, (40, 35, 30), 255 * a)
        cv.restore()


def sc_finale(cv, lt, t):
    # golden terrace wide, Meera with tomatoes, cards doing their job
    cam = 1.12 - 0.1 * ease(lt / 4.6)
    cv.save()
    cv.translate(W / 2, H * 0.55)
    cv.scale(cam, cam)
    cv.translate(-W / 2, -H * 0.55)
    terrace_plate(cv, t, warm=0.85, sick=0.1)
    for x, col, bugs in ((330, YEL, 22), (700, BLU, 14)):
        cv.drawLine(x, 820, x, 1150, stroke((185, 150, 85), 9))
        draw_trap(cv, x, 860, 150, col, bugs=bugs, seed=x)
    god_rays(cv, t, (W * 0.78, H * 0.17), cols=(255, 220, 160), a=26, n=9, spread=5.5, length=1800)
    cv.restore()
    hands = draw_person(cv, 560, 2060, 245, t, MEERA, arm_l=(0.35, 1.1), arm_r=(0.35, 1.1),
                        talk=0.0, brow=-0.3, look=0.2, curl_l=0.7, curl_r=0.7)
    # basket of tomatoes
    bx = (hands[1][0] + hands[-1][0]) / 2
    by = (hands[1][1] + hands[-1][1]) / 2 + 30
    cv.drawOval(skia.Rect(bx - 190, by - 40, bx + 190, by + 140), lin((0, by - 40), (0, by + 140), [(190, 140, 70), (130, 90, 40)]))
    for k in range(7):
        cv.drawCircle(bx - 150 + k * 50, by - 30 - (k % 2) * 22, 34,
                      rad((bx - 160 + k * 50, by - 45 - (k % 2) * 22), 42, [(250, 100, 70), (190, 30, 20)]))
    cv.drawOval(skia.Rect(bx - 190, by - 10, bx + 190, by + 40), fill((150, 105, 50)))


def sc_stuck(cv, lt, t):
    # specimen card: the whitefly, stamped STUCK, then cut to black
    if lt > 1.35 and not AMAZON:
        cv.drawRect(skia.Rect(0, 0, W, H), fill((0, 0, 0)))
        a = ease((lt - 1.5) / 0.3) * 255
        text(cv, "buildingshop.in", W / 2, H / 2, "serif", 44, (235, 235, 225), a, anchor="c")
        return
    cv.drawRect(skia.Rect(0, 0, W, H), lin((0, 0), (0, H), [(20, 30, 24), (8, 12, 10)]))
    cv.save()
    cv.translate(W / 2, H * 0.45)
    cv.rotate(-3)
    cv.drawRRect(rrect(-380, -470, 760, 940, 14), fill((0, 0, 0), 120, blur=16))
    cv.drawRRect(rrect(-380, -480, 760, 940, 14), fill((246, 240, 222)))
    draw_trap(cv, 0, -40, 420, YEL)
    draw_insect(cv, 20, -60, 150, "whitefly", 0, ang=-0.4, stuck=True)
    text(cv, "Specimen #1 — whitefly", 0, 400, "serif_i", 36, (60, 50, 40), anchor="c")
    k = bout((lt - 0.35) / 0.35)
    if k > 0:
        cv.save()
        cv.translate(40, -20)
        cv.rotate(-14)
        s = lerp(2.2, 1.0, k)
        cv.scale(s, s)
        al = 230 * clamp(k)
        cv.drawRRect(rrect(-210, -70, 420, 140, 14), stroke((200, 30, 30), 10, al))
        text(cv, "STUCK", 0, 38, "serif", 110, (200, 30, 30), al, anchor="c")
        cv.restore()
    cv.restore()


SCENE_FN = dict(macro_fly=sc_macro_fly, leaf_reveal=sc_leaf_reveal, meera_worried=sc_meera_worried,
                species_entrance=sc_species, meera_hangs=sc_meera_hangs, the_hunt=sc_hunt, farm=sc_farm,
                field_notes=sc_field_notes, finale=sc_finale, stuck_stamp=sc_stuck)


def render_frame(t, arr=None, overlays=True):
    if arr is None:
        arr = np.zeros((H, W, 4), np.uint8)
    surf = skia.Surface(arr)
    cv = surf.getCanvas()
    cv.clear(skia.ColorBLACK)
    for i, (a, b, name) in enumerate(SCENES):
        if a <= t < b or (i == len(SCENES) - 1 and t >= a):
            SCENE_FN[name](cv, t - a, t)
            # cut-on-action flash/punch: brief white dip on cuts into new scene
            k = 1 - ease((t - a) / 0.12)
            if i > 0 and k > 0 and name != "stuck_stamp":
                cv.drawRect(skia.Rect(0, 0, W, H), fill((255, 255, 255), 70 * k))
            break
    black_end = t >= CUE['black']
    if not black_end:
        film_finish(cv, t)
        if not overlays:
            return arr
        letterbox(cv)
        captions(cv, t)
        if t < STUCK_T:
            corner_mark(cv)
    return arr


# ------------------------------------------------------------------ music (documentary bed, synthesised)
SR = 48000


def music():
    n = int(DUR * SR)
    tt = np.arange(n) / SR
    out = np.zeros(n)

    def env(a, r, length):
        e = np.ones(length)
        ai, ri = int(a * SR), int(r * SR)
        e[:ai] = np.linspace(0, 1, ai)
        e[-ri:] *= np.linspace(1, 0, ri)
        return e

    def pad(f0, start, dur, amp):
        i0, L = int(start * SR), int(dur * SR)
        L = min(L, n - i0)
        x = np.arange(L) / SR
        s = sum(np.sin(2 * np.pi * f0 * m * x * (1 + 0.0015 * k)) / m for m in (1, 2, 3) for k in (-1, 1))
        out[i0:i0 + L] += amp * s * env(1.2, 1.2, L) / 6

    def pluck(f0, start, amp=0.25, dec=1.2):
        i0 = int(start * SR)
        L = min(int(dec * 2 * SR), n - i0)
        if L <= 0:
            return
        x = np.arange(L) / SR
        s = (np.sin(2 * np.pi * f0 * x) + 0.35 * np.sin(2 * np.pi * 2 * f0 * x)) * np.exp(-x * 4 / dec)
        out[i0:i0 + L] += amp * s

    def note(midi):
        return 440 * 2 ** ((midi - 69) / 12)

    rv = CUE["peela"]
    pad(note(38), 0, rv + 0.2, 0.18)
    pad(note(45), 0, rv + 0.2, 0.08)
    for k, s in enumerate(np.arange(0.4, rv - 0.2, 0.62)):
        pluck(note([62, 65, 62, 69][k % 4]), s, 0.10, 0.5)
    # reveal swell (14–) D major warmth
    chords = [[50, 57, 62, 66], [47, 54, 59, 62], [43, 50, 55, 59], [45, 52, 57, 61]]
    t0 = rv
    while t0 < DUR - 1.5:
        for c in chords:
            if t0 >= DUR - 1.5:
                break
            for m in c:
                pad(note(m), t0, 2.6, 0.09)
            for k, m in enumerate([c[2], c[3], c[2] + 12, c[3]]):
                pluck(note(m + 12), t0 + k * 0.6, 0.07, 0.9)
            t0 += 2.4
    # hits
    for th in (CUE['peela'], CUE['neela'], STUCK_T + 0.35):
        i0 = int(th * SR)
        L = min(int(1.5 * SR), n - i0)
        x = np.arange(L) / SR
        out[i0:i0 + L] += 0.35 * np.sin(2 * np.pi * 55 * x) * np.exp(-x * 3)
    # simple reverb
    for d, g in ((0.071, 0.35), (0.113, 0.28), (0.173, 0.2), (0.257, 0.14)):
        k = int(d * SR)
        out[k:] += g * out[:-k]
    out[int(CUE['black'] * SR):] *= 0.0
    if AMAZON:  # musical fade on the end card instead of a hard cut
        fl = int(1.6 * SR)
        out[-fl:] *= np.linspace(1, 0, fl) ** 1.5
    out[:int(0.3 * SR)] *= np.linspace(0, 1, int(0.3 * SR))
    out /= np.max(np.abs(out)) + 1e-9
    out *= 10 ** (-6 / 20)
    return out


def write_wav(path, x):
    import wave
    y = (np.clip(x, -1, 1) * 32767).astype(np.int16)
    st = np.stack([y, y], 1)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(st.tobytes())


# ------------------------------------------------------------------ VO track (real ElevenLabs files)
def _load(p):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", os.path.join(HERE, p), "-ac", "1", "-ar", str(SR),
                          "-f", "s16le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768


def build_vo():
    n = int(DUR * SR)
    vo = np.zeros(n, np.float32)
    per = {sp: np.zeros(n, np.float32) for sp in VO_FILES}
    src = {sp: _load(p) for sp, p in VO_FILES.items()}
    for g0, sp, a, b in CLIPS:
        clip = src[sp][max(0, int(a * SR)):int(b * SR)].copy()
        f = int(0.01 * SR)
        clip[:f] *= np.linspace(0, 1, f)
        clip[-f:] *= np.linspace(1, 0, f)
        i0 = int((g0 - 0.03) * SR)
        L = min(len(clip), n - i0)
        vo[i0:i0 + L] += clip[:L]
        per[sp][i0:i0 + L] += clip[:L]
    for sp, x in per.items():  # 100 Hz mouth envelope
        h = SR // 100
        m = len(x) // h
        e = np.sqrt(np.mean(x[:m * h].reshape(m, h) ** 2, 1))
        e = np.convolve(e, np.ones(4) / 4, "same")
        e = np.clip((e / (np.percentile(e[e > 1e-4], 95) + 1e-9)) ** 0.8, 0, 1) if np.any(e > 1e-4) else e
        _ENV[sp] = e
    return vo


def mix_audio(music_, vo):
    h = SR // 100
    m = len(vo) // h
    e = np.sqrt(np.mean(vo[:m * h].reshape(m, h) ** 2, 1))
    e = np.convolve((e > 0.01).astype(float), np.ones(25) / 25, "same")  # 250 ms smoothing
    duck = 1 - 0.6 * np.repeat(e, h)
    duck = np.pad(duck, (0, len(vo) - len(duck)), constant_values=1)
    vo_n = vo / (np.max(np.abs(vo)) + 1e-9) * 10 ** (-1.5 / 20)
    out = music_[:len(vo)] * 0.55 * duck + vo_n
    return out / max(1.0, np.max(np.abs(out)) / 10 ** (-1 / 20))


VO = build_vo()


def main():
    os.makedirs(OUT, exist_ok=True)
    if "--stills" in sys.argv:
        ts = [round(t, 2) for t in [0.8, (L(1) + L(2)) / 2, L(2) + 1.0, L(3) + 1.0, L(4) + 1.5, CUE["neela"] + 0.9,
              L(6) + 0.6, L(6) + 2.4, L(7) + 0.8, L(8) - 0.4, L(8) + 1.5, L(9) + 1.2, L(10) + 0.7, L(11) + 3.0,
              L(12) + 1.5, STUCK_T + 0.9, DUR - 0.3]]
        for t in ts:
            arr = render_frame(t)
            skia.Image.fromarray(arr, colorType=skia.kRGBA_8888_ColorType).save(
                os.path.join(OUT, f"still_{t:05.2f}.png"), skia.kPNG)
        return
    wav = os.path.join(OUT, "planet_gamla_mix.wav")
    m = music()
    write_wav(os.path.join(OUT, "planet_gamla_music.wav"), m)
    write_wav(wav, mix_audio(m, VO))
    raw = os.path.join(OUT, "planet_gamla_master.mp4")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "medium", "-crf", "17",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", raw]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    arr = np.zeros((H, W, 4), np.uint8)
    nfr = int(DUR * FPS)
    for f in range(nfr):
        render_frame(f / FPS, arr)
        p.stdin.write(arr.tobytes())
        if f % 150 == 0:
            print(f, "/", nfr, flush=True)
    p.stdin.close()
    p.wait()
    print("wrote", raw)


if __name__ == "__main__":
    main()
