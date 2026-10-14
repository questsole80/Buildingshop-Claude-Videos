"""BuildingShop folding platform trolley — 16:9 Amazon product demo (no captions, no border).

Real demo footage (supplier clip, upscaled to 1080p in work/frames) + Runway photoreal use-case plates (plates/)
+ clean motion-graphic callouts, an animated 500 kg load gauge, music and sound design.
Amazon rules: no URLs / prices / phone numbers, product visible from frame 1, claims = listing facts only.

usage: python3 demo16x9.py [--stills] [--vo vo/voice.mp3]
"""
import math, os, random, subprocess, sys, wave
import numpy as np
import skia

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
W, H, FPS, SR = 1920, 1080, 30, 48000
SRC_FPS, SRC_N = 30, 499
YEL = (255, 196, 0)
INK = (14, 22, 32)
WHITE = (255, 255, 255)
BLUE = (64, 170, 230)


# ------------------------------------------------------------------ basics
def C(rgb, a=255):
    return skia.ColorSetARGB(int(max(0, min(255, a))), *[int(c) for c in rgb])


def fill(rgb, a=255, blur=0.0):
    p = skia.Paint(AntiAlias=True, Color=C(rgb, a))
    if blur:
        p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    return p


def stroke(rgb, w, a=255):
    return skia.Paint(AntiAlias=True, Color=C(rgb, a), Style=skia.Paint.kStroke_Style, StrokeWidth=w,
                      StrokeCap=skia.Paint.kRound_Cap, StrokeJoin=skia.Paint.kRound_Join)


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def eoe(x):
    x = clamp(x)
    return 1 - 2 ** (-10 * x) if x < 1 else 1.0


def bout(x):
    x = clamp(x)
    c = 1.4
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


def lerp(a, b, t):
    return a + (b - a) * t


def rrect(x, y, w, h, r):
    return skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, w, h), r, r)


TF = {"bold": skia.Typeface("DejaVu Sans", skia.FontStyle.Bold()),
      "reg": skia.Typeface("DejaVu Sans", skia.FontStyle.Normal()),
      "cond": skia.Typeface("DejaVu Sans Condensed", skia.FontStyle.Bold())}


def font(k, s):
    f = skia.Font(TF[k], s)
    f.setEdging(skia.Font.Edging.kAntiAlias)
    return f


def text(cv, s, x, y, k, size, rgb=WHITE, a=255, anchor="l", shadow=True, track=0):
    f = font(k, size)
    w = f.measureText(s) + track * len(s)
    if anchor == "c":
        x -= w / 2
    elif anchor == "r":
        x -= w
    if shadow:
        cv.drawString(s, x + 2, y + 3, f, fill((0, 0, 0), a * 0.55, blur=6))
    if track:
        cx = x
        for ch in s:
            cv.drawString(ch, cx, y, f, fill(rgb, a))
            cx += f.measureText(ch) + track
    else:
        cv.drawString(s, x, y, f, fill(rgb, a))
    return w


# ------------------------------------------------------------------ media
_cache = {}


def footage(src_t):
    i = int(round(src_t * SRC_FPS)) + 1
    i = max(1, min(SRC_N, i))
    if i not in _cache:
        if len(_cache) > 40:
            _cache.clear()
        _cache[i] = skia.Image.MakeFromEncoded(skia.Data.MakeFromFileName(os.path.join(HERE, "work", "frames", f"{i:04d}.jpg")))
    return _cache[i]


_plates = {}


def plate(name):
    if name not in _plates:
        _plates[name] = skia.Image.MakeFromEncoded(skia.Data.MakeFromFileName(os.path.join(HERE, "plates", name + ".png")))
    return _plates[name]


SAMP = skia.SamplingOptions(skia.CubicResampler.Mitchell())


def draw_img(cv, img, zoom=1.0, fx=0.5, fy=0.5, dx=0.0, dy=0.0, a=255):
    s = max(W / img.width(), H / img.height()) * zoom
    cv.save()
    cv.translate(W * fx + dx - img.width() * s * fx, H * fy + dy - img.height() * s * fy)
    cv.scale(s, s)
    p = skia.Paint(Alphaf=a / 255)
    cv.drawImage(img, 0, 0, SAMP, p)
    cv.restore()


def grade(cv, warm=0.0):
    g = skia.Paint()
    g.setShader(skia.GradientShader.MakeRadial(skia.Point(W / 2, H / 2), W * 0.75,
                                               [C((0, 0, 0), 0), C((0, 0, 0), 0), C((0, 0, 0), 120)], [0, 0.55, 1]))
    cv.drawRect(skia.Rect(0, 0, W, H), g)
    if warm:
        cv.drawRect(skia.Rect(0, 0, W, H), fill((255, 170, 90), 18 * warm))


_rng = np.random.default_rng(5)
GRAIN = []
for _ in range(5):
    n = _rng.normal(128, 30, (H // 2, W // 2)).clip(0, 255).astype(np.uint8)
    GRAIN.append(skia.Image.fromarray(np.ascontiguousarray(np.dstack([n, n, n, np.full_like(n, 255)])),
                                      colorType=skia.kRGBA_8888_ColorType))


def film(cv, t):
    p = skia.Paint(Alphaf=0.05, BlendMode=skia.BlendMode.kOverlay)
    cv.drawImageRect(GRAIN[int(t * FPS) % 5], skia.Rect(0, 0, W, H), skia.SamplingOptions(skia.FilterMode.kLinear), p)


# ------------------------------------------------------------------ motion graphics
def title_block(cv, t, t0, eyebrow, title, x=110, y=870, dur=99):
    k = eoe((t - t0) / 0.6)
    ko = 1 - ease((t - t0 - dur) / 0.35)
    if k <= 0 or ko <= 0:
        return
    a = 255 * ko
    cv.drawRect(skia.Rect(x, y - 120, x + 10, y + 20), fill(YEL, a))
    cv.save()
    cv.clipRect(skia.Rect(x + 20, y - 150, W, y + 40))
    off = (1 - k) * 80
    text(cv, eyebrow, x + 34, y - 82 + off, "bold", 30, YEL, a, track=6)
    text(cv, title, x + 30, y + off, "bold", 78, WHITE, a)
    cv.restore()


def callout(cv, t, t0, anchor, label, side=-1, length=260, rise=-120, dur=99):
    """Dot on the product + leader line drawn on + label chip."""
    k = (t - t0) / 0.7
    ko = 1 - ease((t - t0 - dur) / 0.3)
    if k <= 0 or ko <= 0:
        return
    a = 255 * ko
    ax, ay = anchor
    # pulsing dot
    r = 11 + 4 * math.sin((t - t0) * 6)
    cv.drawCircle(ax, ay, r + 10, fill(YEL, 70 * ko * clamp(k * 3)))
    cv.drawCircle(ax, ay, 9, fill(YEL, a * clamp(k * 3)))
    ex, ey = ax + side * length * 0.45, ay + rise
    fx, fy = ex + side * length * 0.55, ey
    path = skia.Path()
    path.moveTo(ax, ay)
    path.lineTo(ex, ey)
    path.lineTo(fx, fy)
    pm = skia.PathMeasure(path, False)
    seg = skia.Path()
    pm.getSegment(0, pm.getLength() * eoe(k * 1.4), seg, True)
    cv.drawPath(seg, stroke(WHITE, 4, a))
    kc = eoe((t - t0 - 0.35) / 0.45)
    if kc > 0:
        f = font("bold", 38)
        w = f.measureText(label) + 56
        h = 72
        x = fx if side > 0 else fx - w
        cv.save()
        cv.clipRect(skia.Rect(x - 4, fy - h / 2 - 4, x + w * kc + 4, fy + h / 2 + 4))
        cv.drawRRect(rrect(x, fy - h / 2, w, h, 14), fill((10, 16, 24), 200 * ko))
        cv.drawRect(skia.Rect(x if side > 0 else x + w - 8, fy - h / 2, (x + 8) if side > 0 else x + w, fy + h / 2), fill(YEL, a))
        cv.drawString(label, x + 28, fy + 13, f, fill(WHITE, a))
        cv.restore()


def chip(cv, t, t0, label, x, y, dur=99, size=40):
    k = (t - t0) / 0.45
    ko = 1 - ease((t - t0 - dur) / 0.3)
    if k <= 0 or ko <= 0:
        return
    f = font("bold", size)
    w = f.measureText(label) + 60
    h = size * 1.8
    s = bout(k)
    cv.save()
    cv.translate(x + w / 2, y)
    cv.scale(s, s)
    cv.drawRRect(rrect(-w / 2 + 4, -h / 2 + 7, w, h, h / 2), fill((0, 0, 0), 90 * ko, blur=10))
    cv.drawRRect(rrect(-w / 2, -h / 2, w, h, h / 2), fill((10, 16, 24), 205 * ko))
    cv.drawCircle(-w / 2 + h / 2, 0, h * 0.16, fill(YEL, 255 * ko))
    cv.drawString(label, -w / 2 + h * 0.75, size * 0.36, f, fill(WHITE, 255 * ko))
    cv.restore()


def load_gauge(cv, t, t0, cx, cy, r=190, t_end=99):
    k = (t - t0) / 1.6
    if k <= 0 or t > t_end:
        return
    ko = 1 - ease((t - (t_end - 0.35)) / 0.35)
    cv.saveLayerAlpha(None, int(255 * ko))
    _gauge(cv, t, t0, cx, cy, r, k)
    cv.restore()


def _gauge(cv, t, t0, cx, cy, r, k):
    v = 500 * eoe(k)
    cv.drawCircle(cx, cy, r + 40, fill((8, 12, 18), 200, blur=2))
    arc = skia.Rect(cx - r, cy - r, cx + r, cy + r)
    p = skia.Path()
    p.addArc(arc, 135, 270)
    cv.drawPath(p, stroke((255, 255, 255), 22, 50))
    p2 = skia.Path()
    p2.addArc(arc, 135, 270 * (v / 500))
    cv.drawPath(p2, stroke(YEL, 22))
    for i in range(11):
        an = math.radians(135 + 27 * i)
        cv.drawLine(cx + math.cos(an) * (r - 34), cy + math.sin(an) * (r - 34), cx + math.cos(an) * (r - 50),
                    cy + math.sin(an) * (r - 50), stroke(WHITE, 3, 160))
    text(cv, f"{int(v)}", cx, cy + 34, "bold", 120, WHITE, anchor="c")
    text(cv, "KG", cx, cy + 96, "bold", 40, YEL, anchor="c", track=4)
    text(cv, "LOAD CAPACITY", cx, cy + r + 96, "bold", 34, WHITE, anchor="c", track=5)
    # impact flash when it lands
    hit = t - (t0 + 1.0)
    if 0 < hit < 0.5:
        cv.drawCircle(cx, cy, r + 40 + 120 * hit, stroke(YEL, 6, 255 * (1 - hit / 0.5)))


def floor_arrow(cv, t, t0, pts, label=None, t_end=99):
    k = (t - t0) / 1.0
    if k <= 0 or t > t_end:
        return
    path = skia.Path()
    path.moveTo(*pts[0])
    path.cubicTo(*pts[1], *pts[2], *pts[3])
    pm = skia.PathMeasure(path, False)
    Ln = pm.getLength() * eoe(k)
    seg = skia.Path()
    pm.getSegment(0, Ln, seg, True)
    cv.drawPath(seg, stroke(YEL, 10, 230))
    r_ = pm.getPosTan(Ln)
    if r_:
        pos, tan = r_
        ang = math.atan2(tan.y(), tan.x())
        ah = skia.Path()
        ah.moveTo(pos.x() + math.cos(ang) * 30, pos.y() + math.sin(ang) * 30)
        ah.lineTo(pos.x() + math.cos(ang + 2.5) * 30, pos.y() + math.sin(ang + 2.5) * 30)
        ah.lineTo(pos.x() + math.cos(ang - 2.5) * 30, pos.y() + math.sin(ang - 2.5) * 30)
        ah.close()
        cv.drawPath(ah, fill(YEL))


# ------------------------------------------------------------------ edit (time in seconds)
# (start, end, kind, params)
EDIT = [
    (0.0, 3.4, "clip", dict(src=(0.0, 2.65), zoom=(1.12, 1.04), fy=0.6)),            # handle unfolds + locks
    (3.4, 8.4, "clip", dict(src=(2.75, 6.05), zoom=(1.0, 1.08), fy=0.62)),           # hero, callouts
    (8.4, 12.8, "plate", dict(name="load", zoom=(1.04, 1.12), fx=0.4)),               # 500 kg
    (12.8, 17.8, "clip", dict(src=(6.6, 11.6), zoom=(1.06, 1.0), fy=0.6)),           # rolls smoothly
    (17.8, 20.3, "clip", dict(src=(2.6, 0.05), zoom=(1.0, 1.1), fy=0.62)),           # folds (reverse)
    (20.3, 23.6, "plate", dict(name="folded", zoom=(1.12, 1.04), fx=0.62)),          # stores flat
    (23.6, 26.8, "plate", dict(name="shop", zoom=(1.03, 1.12), fx=0.35)),            # shops & godowns
    (26.8, 30.0, "plate", dict(name="home", zoom=(1.12, 1.03), fx=0.65)),            # home shifting
    (30.0, 35.0, "clip", dict(src=(12.0, 16.55), zoom=(1.32, 1.26), fx=0.78, fy=0.55)),  # end card (crop past other brand's crate)
]
DUR = 35.0
XF = 0.35  # cross-dissolve length


def draw_shot(cv, i, t):
    a, b, kind, p = EDIT[i]
    lt = clamp((t - a) / (b - a))
    z = lerp(p["zoom"][0], p["zoom"][1], ease(lt))
    if kind == "clip":
        s0, s1 = p["src"]
        img = footage(lerp(s0, s1, lt))
    else:
        img = plate(p["name"])
    draw_img(cv, img, zoom=z, fx=p.get("fx", 0.5), fy=p.get("fy", 0.5))


def graphics(cv, t):
    # 1 hook title
    title_block(cv, t, 0.35, "BUILDINGSHOP", "Folding Platform Trolley", dur=2.7)
    # 2 hero callouts (positions match the hero frame)
    callout(cv, t, 3.9, (1268, 330), "Folding steel handle", side=-1, length=360, rise=-110, dur=4.2)
    callout(cv, t, 4.8, (880, 700), "Wide, flat platform", side=-1, length=380, rise=-110, dur=3.3)
    callout(cv, t, 5.7, (1325, 905), "Smooth-rolling wheels", side=-1, length=380, rise=95, dur=2.4)
    # 3 load gauge
    load_gauge(cv, t, 8.9, 1450, 470, t_end=12.75)
    # 4 rolling
    floor_arrow(cv, t, 13.3, [(380, 1010), (700, 1050), (1100, 980), (1500, 1000)], t_end=17.6)
    chip(cv, t, 13.6, "Rolls smoothly, less effort", 110, 150, dur=3.8)
    # 5 folds
    chip(cv, t, 18.1, "Handle folds flat", 110, 150, dur=1.9)
    chip(cv, t, 20.6, "Stores flat in any corner", 110, 150, dur=2.7)
    # 6 uses
    chip(cv, t, 23.9, "Shops & godowns", 110, 150, dur=2.6)
    chip(cv, t, 24.3, "Warehouses", 110, 250, dur=2.2)
    chip(cv, t, 27.1, "Home & office shifting", 110, 150, dur=2.6)
    # 7 end card
    k = eoe((t - 30.4) / 0.7)
    if k > 0:
        g = skia.Paint()
        g.setShader(skia.GradientShader.MakeLinear([skia.Point(0, 0), skia.Point(W * 0.62, 0)],
                                                   [C((6, 10, 16), 230 * k), C((6, 10, 16), 0)]))
        cv.drawRect(skia.Rect(0, 0, W, H), g)
        title_block(cv, t, 30.5, "BUILDINGSHOP", "Folding Platform Trolley", x=110, y=430)
        chip(cv, t, 31.2, "Up to 500 kg load", 140, 560)
        chip(cv, t, 31.45, "Folding handle", 140, 660)
        chip(cv, t, 31.7, "Easy to push & store", 140, 760)


def render_frame(t, arr):
    cv = skia.Surface(arr).getCanvas()
    cv.clear(skia.ColorBLACK)
    for i, (a, b, kind, p) in enumerate(EDIT):
        if a <= t < b or (i == len(EDIT) - 1 and t >= a):
            draw_shot(cv, i, t)
            # dissolve into the next shot
            if i + 1 < len(EDIT) and t > b - XF:
                cv.saveLayerAlpha(None, int(255 * ease((t - (b - XF)) / XF)))
                draw_shot(cv, i + 1, t)
                cv.restore()
            break
    grade(cv, warm=0.4 if 20.3 <= t < 30 else 0.0)
    film(cv, t)
    graphics(cv, t)
    # fade in / out
    if t < 0.25:
        cv.drawRect(skia.Rect(0, 0, W, H), fill((0, 0, 0), 255 * (1 - t / 0.25)))
    if t > DUR - 0.6:
        cv.drawRect(skia.Rect(0, 0, W, H), fill((0, 0, 0), 255 * ease((t - (DUR - 0.6)) / 0.6)))
    return arr


# ------------------------------------------------------------------ audio: music + SFX (original, synthesised)
def music(n):
    out = np.zeros(n)
    bpm = 112
    beat = 60 / bpm

    def note(m):
        return 440 * 2 ** ((m - 69) / 12)

    def add(sig, t0):
        i0 = int(t0 * SR)
        L = min(len(sig), n - i0)
        if L > 0:
            out[i0:i0 + L] += sig[:L]

    def tone(f0, dur, amp, kind):
        L = int(dur * SR)
        x = np.arange(L) / SR
        if kind == "pad":
            s = sum(np.sin(2 * np.pi * f0 * m * x * (1 + 0.002 * k)) / m for m in (1, 2, 3) for k in (-1, 1)) / 6
            e = np.minimum(1, x / 0.15) * np.minimum(1, (dur - x) / 0.3)
        elif kind == "pluck":
            s = np.sin(2 * np.pi * f0 * x) + 0.4 * np.sin(4 * np.pi * f0 * x)
            e = np.exp(-x * 7)
        elif kind == "bass":
            s = np.sin(2 * np.pi * f0 * x) + 0.3 * np.sin(4 * np.pi * f0 * x)
            e = np.minimum(1, x / 0.01) * np.exp(-x * 2.5)
        elif kind == "kick":
            s = np.sin(2 * np.pi * (50 + 90 * np.exp(-x * 30)) * x)
            e = np.exp(-x * 9)
        else:  # hat
            s = np.random.default_rng(int(f0)).normal(0, 1, L)
            s = s - np.convolve(s, np.ones(4) / 4, "same")
            e = np.exp(-x * 40)
        return amp * s * e

    prog = [[57, 61, 64], [52, 56, 59], [54, 57, 61], [50, 54, 57]]  # A E F#m D (bright)
    t0, ci = 0.0, 0
    while t0 < DUR:
        c = prog[ci % 4]
        add(tone(note(c[0] - 12), beat * 4, 0.05, "pad"), t0)
        for m in c:
            add(tone(note(m), beat * 4, 0.035, "pad"), t0)
        for k in range(4):
            tb = t0 + k * beat
            add(tone(note(c[0] - 24), beat * 0.9, 0.16, "bass"), tb)
            if t0 > 0.4:
                add(tone(1, 0.3, 0.32, "kick"), tb)
            add(tone(1000 + k, 0.06, 0.035, "hat"), tb + beat / 2)
            add(tone(note(c[(k + 1) % 3] + 12), 0.5, 0.045, "pluck"), tb + beat / 2)
        t0 += beat * 4
        ci += 1
    for d, g in ((0.11, 0.25), (0.19, 0.15)):
        k = int(d * SR)
        out[k:] += g * out[:-k]
    fl = int(1.2 * SR)
    out[-fl:] *= np.linspace(1, 0, fl)
    out[:int(0.3 * SR)] *= np.linspace(0, 1, int(0.3 * SR))
    return out / (np.max(np.abs(out)) + 1e-9)


def sfx(n):
    out = np.zeros(n)
    rng = np.random.default_rng(9)

    def put(t0, sig):
        i0 = int(t0 * SR)
        L = min(len(sig), n - i0)
        if i0 >= 0 and L > 0:
            out[i0:i0 + L] += sig[:L]

    def whoosh(d=0.45, amp=0.22):
        L = int(d * SR)
        x = np.arange(L) / SR
        s = np.convolve(rng.normal(0, 1, L), np.ones(18) / 18, "same")
        return s * np.sin(np.pi * x / x[-1]) ** 2 * amp

    def click(amp=0.5):
        L = int(0.09 * SR)
        x = np.arange(L) / SR
        return (np.sin(2 * np.pi * 2400 * x) * 0.5 + rng.normal(0, 1, L) * 0.5) * np.exp(-x * 70) * amp

    def pop(amp=0.18):
        L = int(0.12 * SR)
        x = np.arange(L) / SR
        return np.sin(2 * np.pi * (700 + 2200 * x) * x) * np.exp(-x * 38) * amp

    def impact(amp=0.7):
        L = int(1.2 * SR)
        x = np.arange(L) / SR
        return (np.sin(2 * np.pi * (45 + 60 * np.exp(-x * 12)) * x) + 0.3 * rng.normal(0, 1, L) * np.exp(-x * 25)) \
            * np.exp(-x * 3.5) * amp

    def roll(d, amp=0.06):
        L = int(d * SR)
        x = np.arange(L) / SR
        s = np.convolve(rng.normal(0, 1, L), np.ones(60) / 60, "same") * (1 + 0.4 * np.sin(2 * np.pi * 9 * x))
        e = np.minimum(1, x / 0.3) * np.minimum(1, (d - x) / 0.4)
        return s * e * amp * 8

    for a, b, kind, p in EDIT[1:]:
        put(a - 0.3, whoosh())
    put(2.75, click(0.6))           # handle locks up
    put(19.9, click(0.5))           # handle folds down
    for t0 in (3.9, 4.8, 5.7, 13.6, 18.1, 20.6, 23.9, 24.3, 27.1, 31.2, 31.45, 31.7):
        put(t0 + 0.35, pop())
    put(8.9 + 1.0, impact())        # 500 kg lands
    put(12.8, roll(5.0))
    put(30.0, roll(3.5, 0.04))
    return out


def build_audio(path, vo_path=None):
    n = int(DUR * SR)
    mus = music(n)
    mix = mus * 0.42 + sfx(n)
    if vo_path:  # optional voiceover: duck music under it
        raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", vo_path, "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
                             capture_output=True, check=True).stdout
        vo = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
        vo = np.pad(vo, (int(0.4 * SR), 0))[:n]
        vo = np.pad(vo, (0, n - len(vo)))
        h = SR // 100
        m = n // h
        e = np.sqrt(np.mean(vo[:m * h].reshape(m, h) ** 2, 1))
        e = np.convolve((e > 0.01).astype(float), np.ones(25) / 25, "same")
        duck = np.pad(1 - 0.6 * np.repeat(e, h), (0, n - m * h), constant_values=1)
        mix = mus * 0.42 * duck + sfx(n) + vo / (np.max(np.abs(vo)) + 1e-9) * 0.9
    mix /= max(1.0, np.max(np.abs(mix)) / 0.89)
    y = (mix * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(np.stack([y, y], 1).tobytes())


def main():
    os.makedirs(OUT, exist_ok=True)
    arr = np.zeros((H, W, 4), np.uint8)
    if "--stills" in sys.argv:
        for t in (1.2, 2.9, 6.2, 7.4, 10.6, 15.0, 19.0, 22.0, 25.0, 28.5, 31.0, 33.5):
            render_frame(t, arr)
            skia.Image.fromarray(arr, colorType=skia.kRGBA_8888_ColorType).save(os.path.join(OUT, f"demo_{t:05.2f}.png"), skia.kPNG)
        return
    vo = sys.argv[sys.argv.index("--vo") + 1] if "--vo" in sys.argv else None
    tag = "_vo" if vo else ""
    wav = os.path.join(OUT, f"trolley_demo{tag}.wav")
    build_audio(wav, vo)
    dst = os.path.join(OUT, f"buildingshop_folding_trolley_amazon_16x9{tag}.mp4")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-profile:v", "high",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
           "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-shortest", "-movflags", "+faststart", dst]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f in range(int(DUR * FPS)):
        render_frame(f / FPS, arr)
        p.stdin.write(arr.tobytes())
    p.stdin.close()
    p.wait()
    print("wrote", dst)


if __name__ == "__main__":
    main()
