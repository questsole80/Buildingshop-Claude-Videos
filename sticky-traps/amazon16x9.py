"""Planet Gamla — 16:9 Amazon cut (1920x1080, 30fps).

Split layout: the documentary story (reel.py scenes, rendered portrait) plays in a rounded panel on the left,
over a blurred copy of itself; the right side carries word-synced motion graphics (kinetic title, product
reveal with a self-drawing size diagram, numbered how-to, live counter, use-anywhere tiles, feature grid,
product end card) plus always-on captions for muted autoplay.

Amazon rules applied: no URLs / off-Amazon mentions (Raju's "buildingshop.in" line is dropped via AMAZON=1),
no letterbox bars, no black frames, product visible from the first frame, no price/CTA/reviews, claims only
from the product title.

usage: python3 amazon16x9.py [--stills]
"""
import math, os, subprocess, sys
os.environ["AMAZON"] = "1"
import numpy as np
import skia
import reel as R
from reel import (fill, stroke, lin, rad, rrect, text, font, ease, eout, bout, clamp, lerp, YEL, BLU,
                  draw_trap, draw_insect, draw_leaf, L, LE, WT, CUE, LINES, WORDS, SPEAKER_COL)

OUT = R.OUT
W, H, FPS = 1920, 1080, 30
DUR = R.DUR
PW, PH = 562, 1000          # portrait panel size
PX, PY = 110, 40
CX0, CX1 = 760, 1840        # right column
CXM = (CX0 + CX1) / 2
CREAM = (246, 240, 222)
INK = (18, 34, 26)


def eoe(x):  # ease_out_expo
    x = clamp(x)
    return 1 - 2 ** (-10 * x) if x < 1 else 1.0


# ------------------------------------------------------------------ icons (simple vector)
def icon(cv, kind, x, y, s, col=(255, 255, 255), a=255):
    p = fill(col, a)
    sp = stroke(col, s * 0.08, a)
    if kind == "drop":
        d = skia.Path()
        d.moveTo(x, y - s * 0.5)
        d.cubicTo(x + s * 0.45, y, x + s * 0.4, y + s * 0.42, x, y + s * 0.42)
        d.cubicTo(x - s * 0.4, y + s * 0.42, x - s * 0.45, y, x, y - s * 0.5)
        cv.drawPath(d, p)
    elif kind == "leaf":
        cv.save()
        cv.translate(x - s * 0.45, y + s * 0.3)
        cv.rotate(-40)
        lp = skia.Path()
        lp.moveTo(0, 0)
        lp.cubicTo(s * 0.25, -s * 0.4, s * 0.75, -s * 0.35, s, 0)
        lp.cubicTo(s * 0.75, s * 0.35, s * 0.25, s * 0.4, 0, 0)
        cv.drawPath(lp, p)
        cv.restore()
    elif kind == "cards":
        cv.drawRRect(rrect(x - s * 0.45, y - s * 0.4, s * 0.5, s * 0.66, s * 0.06), fill(YEL, a))
        cv.drawRRect(rrect(x - s * 0.05, y - s * 0.28, s * 0.5, s * 0.66, s * 0.06), fill(BLU, a))
    elif kind == "check":
        c = skia.Path()
        c.moveTo(x - s * 0.35, y)
        c.lineTo(x - s * 0.1, y + s * 0.25)
        c.lineTo(x + s * 0.4, y - s * 0.3)
        cv.drawPath(c, stroke(col, s * 0.13, a))
    elif kind == "sun":
        cv.drawCircle(x, y, s * 0.22, p)
        for k in range(8):
            an = k * math.pi / 4
            cv.drawLine(x + math.cos(an) * s * 0.32, y + math.sin(an) * s * 0.32,
                        x + math.cos(an) * s * 0.46, y + math.sin(an) * s * 0.46, sp)
    elif kind == "home":
        hp = skia.Path()
        hp.moveTo(x - s * 0.42, y - s * 0.02)
        hp.lineTo(x, y - s * 0.42)
        hp.lineTo(x + s * 0.42, y - s * 0.02)
        cv.drawPath(hp, stroke(col, s * 0.09, a))
        cv.drawRect(skia.Rect(x - s * 0.3, y - s * 0.05, x + s * 0.3, y + s * 0.38), sp)
    elif kind == "balcony":
        cv.drawRect(skia.Rect(x - s * 0.42, y - s * 0.45, x + s * 0.42, y + s * 0.1), sp)
        for k in range(5):
            xx = x - s * 0.4 + k * s * 0.2
            cv.drawLine(xx, y + s * 0.1, xx, y + s * 0.42, sp)
        cv.drawLine(x - s * 0.45, y + s * 0.1, x + s * 0.45, y + s * 0.1, sp)
    elif kind == "terrace":
        cv.drawRect(skia.Rect(x - s * 0.45, y + s * 0.15, x + s * 0.45, y + s * 0.42), sp)
        for k in (-0.25, 0.05, 0.3):
            cv.drawCircle(x + k * s, y - s * 0.05, s * 0.14, p)
            cv.drawLine(x + k * s, y + s * 0.05, x + k * s, y + s * 0.15, sp)
    elif kind == "greenhouse":
        g = skia.Path()
        g.addArc(skia.Rect(x - s * 0.45, y - s * 0.4, x + s * 0.45, y + s * 0.5), 180, 180)
        cv.drawPath(g, sp)
        cv.drawLine(x - s * 0.45, y + s * 0.05, x - s * 0.45, y + s * 0.4, sp)
        cv.drawLine(x + s * 0.45, y + s * 0.05, x + s * 0.45, y + s * 0.4, sp)
        cv.drawLine(x - s * 0.5, y + s * 0.4, x + s * 0.5, y + s * 0.4, sp)
        cv.drawLine(x, y - s * 0.4, x, y + s * 0.4, stroke(col, s * 0.05, a))
    elif kind == "farm":
        for k in range(4):
            yy = y - s * 0.25 + k * s * 0.2
            cv.drawLine(x - s * 0.45 + k * s * 0.05, yy, x + s * 0.45 - k * s * 0.05, yy, sp)
        cv.drawCircle(x + s * 0.3, y - s * 0.42, s * 0.12, p)


def chip(cv, x, y, label, k, col=YEL, ic=None, w=None, size=34, a=1.0):
    """Pill chip popping in with overshoot. x,y = left-centre."""
    if k <= 0:
        return
    f = font("sans", size)
    tw = f.measureText(label)
    w = w or tw + (110 if ic else 60)
    h = size * 2.0
    s = bout(k)
    cv.save()
    cv.translate(x + w / 2, y)
    cv.scale(s, s)
    cv.drawRRect(rrect(-w / 2 + 4, -h / 2 + 6, w, h, h / 2), fill((0, 0, 0), 70 * a, blur=8))
    cv.drawRRect(rrect(-w / 2, -h / 2, w, h, h / 2), fill(CREAM, 245 * a))
    tx = -w / 2 + 30
    if ic:
        cv.drawCircle(-w / 2 + h / 2 + 2, 0, h * 0.38, fill(col, 255 * a))
        icon(cv, ic, -w / 2 + h / 2 + 2, 0, h * 0.5, INK if col == YEL else (255, 255, 255), 255 * a)
        tx = -w / 2 + h + 18
    cv.drawString(label, tx, size * 0.36, f, fill(INK, 255 * a))
    cv.restore()


def eyebrow(cv, s, y, k, col=YEL):
    if k <= 0:
        return
    f = font("mono", 26)
    tw = f.measureText(s)
    x = CX0 + 40
    cv.drawRect(skia.Rect(x, y - 4, x + 50 * eoe(k), y), fill(col, 255 * k))
    cv.drawString(s, x + 64, y + 6, f, fill(col, 255 * k))


def slam(cv, s, x, y, size, t0, t, col=CREAM, kind="sans", each=0.045):
    """Kinetic type: letters drop in with stagger and overshoot."""
    f = font(kind, size)
    cx = x
    for i, ch in enumerate(s):
        k = (t - t0 - i * each) / 0.35
        if k > 0:
            s_ = bout(k)
            a = 255 * clamp(k * 2)
            cv.save()
            cv.translate(cx, y - (1 - eoe(k)) * 60)
            cv.drawString(ch, 0, 0, f, fill(col, a))
            cv.restore()
        cx += f.measureText(ch)
    return cx - x


def draw_line_on(cv, pts, k, paint):
    """Draw a polyline up to fraction k (PathMeasure segment)."""
    p = skia.Path()
    p.moveTo(*pts[0])
    for q in pts[1:]:
        p.lineTo(*q)
    pm = skia.PathMeasure(p, False)
    seg = skia.Path()
    pm.getSegment(0, pm.getLength() * clamp(k), seg, True)
    cv.drawPath(seg, paint)


# ------------------------------------------------------------------ sections (right column)
def word_t(i, needle):
    for (a, b, w) in WORDS[i]:
        if needle.lower() in w.lower():
            return a
    return LINES[i][0]


SECTIONS = [  # (start, end, fn)
    (0.0, L(2) - 0.05), (L(2) - 0.05, L(4) - 0.05), (L(4) - 0.05, L(6) + 0.9), (L(6) + 0.9, L(7) + 0.6),
    (L(7) + 0.6, L(8) - 0.05), (L(8) - 0.05, L(11) - 0.05), (L(11) - 0.05, L(12) - 0.05), (L(12) - 0.05, DUR + 1),
]


def sec_k(t, a, b):
    kin = eoe((t - a) / 0.5)
    kout = 1 - ease((t - (b - 0.22)) / 0.22) if b < DUR else 1
    return kin, kout


def g_whitefly(cv, t, a, b):
    eyebrow(cv, "SPECIMEN #1", 230, eoe((t - 0.2) / 0.4))
    slam(cv, "WHITEFLY", CX0 + 40, 360, 130, 0.35, t)
    text(cv, "a tiny flying plant pest  ·  ~1.5 mm", CX0 + 44, 430, "serif_i", 34, (220, 225, 210),
         255 * ease((t - 0.9) / 0.4))
    chip(cv, CX0 + 40, 560, "Sucks sap from leaves", (t - L(1) - 0.2) / 0.45, ic="drop")
    chip(cv, CX0 + 40, 660, "Leaves turn yellow", (t - L(1) - 1.4) / 0.45, ic="leaf")


def g_problem(cv, t, a, b):
    eyebrow(cv, "THE PROBLEM", 230, eoe((t - a - 0.1) / 0.4), col=(255, 140, 120))
    f = font("sans", 88)
    k = eoe((t - a - 0.15) / 0.5)
    cv.drawString("Your plants,", CX0 + 40 - (1 - k) * 80, 360, f, fill(CREAM, 255 * k))
    k2 = eoe((t - a - 0.45) / 0.5)
    cv.drawString("under attack.", CX0 + 40 - (1 - k2) * 80, 460, f, fill((255, 210, 120), 255 * k2))
    # buzzing pests around the headline
    import random
    rnd = random.Random(3)
    for i in range(14):
        bx, by = rnd.uniform(CX0 + 40, CX1 - 40), rnd.uniform(250, 720)
        ph = rnd.uniform(0, 6.3)
        draw_insect(cv, bx + 40 * math.sin(t * 1.3 + ph), by + 30 * math.cos(t * 1.1 + ph), 26,
                    rnd.choice(["whitefly", "gnat"]), t, ang=math.sin(t + ph) * 0.5, a=int(255 * k2))
    chip(cv, CX0 + 40, 600, "Yellow, weak leaves", (t - L(3) + 0.1) / 0.45, col=(255, 140, 120), ic="leaf")


def g_reveal(cv, t, a, b):
    pe, ne = CUE["peela"], CUE["neela"]
    if t < pe - 0.05:
        k = ease((t - a - 0.2) / 0.5)
        text(cv, "Nature has a rule…", CX0 + 40, 420, "serif_i", 64, CREAM, 255 * k)
        text(cv, "some colours pests can't resist.", CX0 + 44, 500, "serif_i", 40, (210, 215, 200),
             255 * ease((t - a - 1.2) / 0.5))
        return
    eyebrow(cv, "THE FIX", 200, eoe((t - pe) / 0.3))
    text(cv, "BuildingShop", CX0 + 40, 280, "sans", 40, (210, 220, 205), 255 * ease((t - pe) / 0.3))
    slam(cv, "Sticky Traps", CX0 + 36, 370, 100, pe + 0.05, t, each=0.03)
    # colour swatches pop on the words
    for i, (col, lbl, tin) in enumerate([(YEL, "YELLOW", pe), (BLU, "BLUE", ne)]):
        k = (t - tin) / 0.4
        if k <= 0:
            continue
        x = CX0 + 70 + i * 230
        cv.save()
        cv.translate(x + 60, 560)
        s = bout(k)
        cv.scale(s, s)
        cv.rotate(-6 + i * 10)
        draw_trap(cv, 0, 0, 120, col, glow=0.5)
        cv.restore()
        text(cv, lbl, x + 60, 690, "mono", 30, col, 255 * clamp(k), anchor="c")
    # self-drawing size diagram
    k = (t - ne - 0.35) / 0.9
    if k > 0:
        x0, y0 = CX0 + 560, 430
        w, h = 210, 280
        cv.drawRRect(rrect(x0, y0, w, h, 10), stroke((255, 255, 255), 3, 90 * clamp(k * 3)))
        sp = stroke(YEL, 5)
        draw_line_on(cv, [(x0, y0 + h + 34), (x0 + w, y0 + h + 34)], k * 1.6, sp)
        draw_line_on(cv, [(x0 + w + 34, y0 + h), (x0 + w + 34, y0)], k * 1.6 - 0.5, sp)
        text(cv, "15 cm", x0 + w / 2, y0 + h + 80, "sans", 36, CREAM, 255 * ease(k * 2 - 0.6), anchor="c")
        cv.save()
        cv.translate(x0 + w + 80, y0 + h / 2)
        cv.rotate(-90)
        text(cv, "20 cm", 0, 12, "sans", 36, CREAM, 255 * ease(k * 2 - 1.0), anchor="c")
        cv.restore()
        text(cv, "double-sided", x0 + w / 2, y0 + h / 2 + 12, "serif_i", 30, (230, 230, 220),
             255 * ease(k * 2 - 1.2), anchor="c")


def g_howto(cv, t, a, b):
    eyebrow(cv, "HOW TO USE", 200, eoe((t - a - 0.1) / 0.4))
    steps = [("Peel off the film", a + 0.15), ("Hang just above plants", max(a + 0.8, word_t(6, "upar") - 0.2)),
             ("Replace when covered", L(7) - 0.3)]
    for i, (s, tin) in enumerate(steps):
        k = (t - tin) / 0.5
        if k <= 0:
            continue
        y = 330 + i * 150
        cx = CX0 + 90
        ring = skia.Path()
        ring.addCircle(cx, y, 46)
        pm = skia.PathMeasure(ring, False)
        seg = skia.Path()
        pm.getSegment(0, pm.getLength() * eoe(k), seg, True)
        cv.drawCircle(cx, y, 46, fill(YEL, 255 * clamp(k * 2 - 0.6)))
        cv.drawPath(seg, stroke(YEL, 6))
        text(cv, str(i + 1), cx, y + 18, "sans", 50, INK, 255 * clamp(k * 2 - 0.8), anchor="c")
        kk = eoe(k - 0.2)
        text(cv, s, cx + 80 - (1 - kk) * 40, y + 18, "sans", 54, CREAM, 255 * kk)
        if i < 2:
            cv.drawLine(cx, y + 52, cx, y + 52 + 46 * eoe(k - 0.6), stroke((255, 255, 255), 3, 90))


def g_hunt(cv, t, a, b):
    eyebrow(cv, "THE HUNT", 200, eoe((t - a - 0.1) / 0.4))
    stuck = sum(1 for h in R.HUNT if t >= h["t0"] + h["dur"])
    k = eoe((t - a) / 0.4)
    text(cv, "CAUGHT", CX0 + 40, 330, "mono", 44, (220, 225, 210), 255 * k)
    f = font("sans", 260)
    num = f"{stuck:02d}"
    pulse = 1 + 0.06 * math.exp(-10 * max(0, t - max([h["t0"] + h["dur"] for h in R.HUNT if t >= h["t0"] + h["dur"]] or [0])))
    cv.save()
    cv.translate(CX0 + 40, 560)
    cv.scale(pulse, pulse)
    cv.drawString(num, 0, 0, f, fill(YEL, 255 * k))
    cv.restore()
    text(cv, "Bright colours attract flying pests.", CX0 + 44, 650, "serif_i", 40, CREAM,
         255 * ease((t - a - 0.8) / 0.4))


TILES = [("Balcony", "balcony"), ("Terrace", "terrace"), ("Greenhouse", "greenhouse"), ("Farm", "farm")]


def g_anywhere(cv, t, a, b):
    eyebrow(cv, "USE IT ANYWHERE", 200, eoe((t - a - 0.1) / 0.4))
    hl = 3 if t < L(9) else (2 if t < L(9) + 1.5 else 1)
    for i, (lbl, ic) in enumerate(TILES):
        k = (t - a - 0.2 - i * 0.12) / 0.45
        if k <= 0:
            continue
        x = CX0 + 40 + i * 255
        y = 290
        on = i == hl
        s = bout(k)
        cv.save()
        cv.translate(x + 110, y + 120)
        cv.scale(s * (1.06 if on else 1), s * (1.06 if on else 1))
        cv.drawRRect(rrect(-110, -120, 220, 240, 26), fill(YEL if on else (255, 255, 255), 235 if on else 30))
        cv.drawRRect(rrect(-110, -120, 220, 240, 26), stroke(YEL, 3, 200))
        icon(cv, ic, 0, -25, 110, INK if on else CREAM)
        text(cv, lbl, 0, 85, "sans", 28, INK if on else CREAM, anchor="c")
        cv.restore()
    k = eoe((t - L(9) - 0.2) / 0.5)
    if k > 0:
        chip(cv, CX0 + 40, 640, "Yellow & Blue  ·  15 × 20 cm", k, ic="cards")


FEATS = [("Double-sided", "cards"), ("Waterproof", "drop"), ("Non-toxic", "leaf"), ("Indoor & outdoor", "home")]


def g_features(cv, t, a, b):
    eyebrow(cv, "FIELD NOTES", 200, eoe((t - a - 0.1) / 0.4))
    for i, (lbl, ic) in enumerate(FEATS):
        tin = CUE["notes"][i]
        k = (t - tin + 0.1) / 0.45
        if k <= 0:
            continue
        col, row = i % 2, i // 2
        x = CX0 + 40 + col * 520
        y = 260 + row * 230
        s = bout(k)
        cv.save()
        cv.translate(x + 240, y + 95)
        cv.scale(s, s)
        cv.drawRRect(rrect(-240 + 5, -95 + 8, 480, 190, 28), fill((0, 0, 0), 80, blur=10))
        cv.drawRRect(rrect(-240, -95, 480, 190, 28), fill(CREAM))
        cv.drawCircle(-160, 0, 54, fill(YEL if i % 2 == 0 else BLU))
        icon(cv, ic, -160, 0, 62, INK if i % 2 == 0 else (255, 255, 255))
        fs = 40 if font("sans", 40).measureText(lbl) < 300 else 33
        text(cv, lbl, -90, 13, "sans", fs, INK)
        cv.restore()
        # tick sweep
        kk = (t - tin - 0.35) / 0.3
        if kk > 0:
            draw_line_on(cv, [(x + 430, y + 40), (x + 448, y + 58), (x + 478, y + 24)], kk, stroke((40, 160, 80), 7))


def g_endcard(cv, t, a, b):
    k = eoe((t - a - 0.1) / 0.6)
    # product hero: two cards fanned, slow float + push
    f = 1 + 0.04 * ease((t - a) / (DUR - a))
    fy = 8 * math.sin(t * 2)
    cv.save()
    cv.translate(CX0 + 230, 520 + fy)
    cv.scale(f * k, f * k)
    cv.drawOval(skia.Rect(-220, 230, 220, 270), fill((0, 0, 0), 90, blur=18))
    cv.save()
    cv.rotate(-9)
    draw_trap(cv, -80, 0, 230, YEL, glow=0.5)
    cv.restore()
    cv.save()
    cv.rotate(8)
    draw_trap(cv, 90, 20, 230, BLU, glow=0.5)
    cv.restore()
    cv.restore()
    tx = CX0 + 500
    text(cv, "BuildingShop", tx, 330, "sans", 36, (210, 220, 205), 255 * ease((t - a - 0.3) / 0.4))
    slam(cv, "Sticky Traps", tx - 4, 420, 76, a + 0.35, t, each=0.03)
    text(cv, "for plants", tx, 480, "serif_i", 44, CREAM, 255 * ease((t - a - 0.8) / 0.4))
    chip(cv, tx, 580, "Yellow & Blue", (t - a - 1.0) / 0.4, ic="cards", size=30)
    chip(cv, tx, 670, "15 × 20 cm · double-sided", (t - a - 1.2) / 0.4, ic="check", size=30)
    # light sweep across the cards
    sx = lerp(CX0 - 100, CX0 + 700, ((t - a - 0.8) % 3.2) / 1.2)
    sw = skia.Path()
    sw.moveTo(sx, 300)
    sw.lineTo(sx + 60, 300)
    sw.lineTo(sx - 60, 800)
    sw.lineTo(sx - 120, 800)
    sw.close()
    p = fill((255, 255, 255), 35, blur=12)
    p.setBlendMode(skia.BlendMode.kScreen)
    cv.drawPath(sw, p)


GFX = [g_whitefly, g_problem, g_reveal, g_howto, g_hunt, g_anywhere, g_features, g_endcard]


def right_column(cv, t):
    for i, ((a, b), fn) in enumerate(zip(SECTIONS, GFX)):
        if a - 0.01 <= t < b:
            kin, kout = sec_k(t, a, b)
            cv.saveLayerAlpha(None, int(255 * kout))
            cv.translate(-(1 - kout) * 120, 0)
            fn(cv, t, a, b)
            cv.restore()
            # yellow wipe bar sweeping in on each new section
            if i > 0:
                w = (t - a) / 0.45
                if 0 < w < 1:
                    x = lerp(CX0 - 40, CX1 + 40, eoe(w))
                    cv.drawRect(skia.Rect(x - 14, 150, x, 760), fill(YEL, 200 * (1 - w)))
            break


# ------------------------------------------------------------------ captions (right column, bottom band)
def captions(cv, t):
    for li, (a, b, sp, s) in enumerate(LINES):
        if not WORDS[li] or not (a - 0.1 <= t <= b + 0.2):
            continue
        wl = WORDS[li]
        words = [w for _, _, w in wl]
        cur = max([k for k, (wa, wb, _) in enumerate(wl) if t >= wa - 0.02] or [0])
        fade = ease((t - (a - 0.1)) / 0.12) * (1 - ease((t - b - 0.08) / 0.12))
        f = font("sans", 44)
        maxw = CX1 - CX0 - 60
        lines, cur_line = [], []
        for i, w in enumerate(words):
            if cur_line and f.measureText(" ".join([words[j] for j in cur_line] + [w])) > maxw:
                lines.append(cur_line)
                cur_line = []
            cur_line.append(i)
        lines.append(cur_line)
        y0 = 905 - (len(lines) - 1) * 30
        bh = len(lines) * 60 + 40
        cv.drawRRect(rrect(CX0 + 10, y0 - 70, CX1 - CX0 - 20, bh + 10, 22), fill((5, 15, 10), 150 * fade))
        tc = SPEAKER_COL[sp]
        tf = font("mono", 22)
        tw = tf.measureText(sp)
        cv.drawRRect(rrect(CX0 + 30, y0 - 112, tw + 30, 36, 18), fill(tc, 240 * fade))
        cv.drawString(sp, CX0 + 45, y0 - 87, tf, fill((25, 25, 25), 255 * fade))
        for ln, idxs in enumerate(lines):
            x = CX0 + 40
            y = y0 + ln * 60
            for i in idxs:
                w = words[i]
                ww = f.measureText(w)
                on = i == cur
                if on:
                    cv.drawRRect(rrect(x - 6, y - 40, ww + 12, 54, 10), fill(YEL, 245 * fade))
                cv.drawString(w, x, y, f, fill(INK if on else (255, 255, 255), 255 * fade))
                x += ww + f.measureText(" ")
        return


# ------------------------------------------------------------------ frame
_P = np.zeros((R.H, R.W, 4), np.uint8)


def render(t, arr):
    R.render_frame(t, _P, overlays=False)
    img = skia.Image.fromarray(_P, colorType=skia.kRGBA_8888_ColorType)
    cv = skia.Surface(arr).getCanvas()
    cv.clear(skia.ColorBLACK)
    # blurred backdrop from the same frame
    sc = W / R.W
    bp = skia.Paint()
    bp.setImageFilter(skia.ImageFilters.Blur(40, 40))
    cv.save()
    cv.translate(0, H / 2 - R.H * sc * 0.45)
    cv.scale(sc, sc)
    cv.drawImage(img, 0, 0, skia.SamplingOptions(skia.FilterMode.kLinear), bp)
    cv.restore()
    cv.drawRect(skia.Rect(0, 0, W, H), lin((0, 0), (W, 0), [((6, 20, 14), 150), ((6, 20, 14), 225)]))
    # portrait story panel (gentle float, entrance scale)
    k = eoe(t / 0.6)
    fy = 4 * math.sin(t * 0.9)
    cv.save()
    cv.translate(PX + PW / 2, PY + PH / 2 + fy)
    cv.scale(lerp(0.94, 1, k), lerp(0.94, 1, k))
    cv.translate(-PW / 2, -PH / 2)
    cv.drawRRect(rrect(8, 14, PW, PH, 28), fill((0, 0, 0), 140, blur=22))
    rr = rrect(0, 0, PW, PH, 28)
    cv.save()
    cv.clipRRect(rr, doAntiAlias=True)
    cv.drawImageRect(img, skia.Rect(0, 0, PW, PH), skia.SamplingOptions(skia.FilterMode.kLinear))
    cv.restore()
    cv.drawRRect(rr, stroke((255, 255, 255), 2, 70))
    cv.restore()
    right_column(cv, t)
    captions(cv, t)


# ------------------------------------------------------------------ audio: VO + music + SFX
SR = R.SR


def sfx_track(n):
    out = np.zeros(n, np.float32)
    rng = np.random.default_rng(7)

    def put(t0, sig):
        i0 = int(t0 * SR)
        if i0 < 0 or i0 >= n:
            return
        L_ = min(len(sig), n - i0)
        out[i0:i0 + L_] += sig[:L_]

    # whoosh 0.3 s before each section change
    for a, b in SECTIONS[1:]:
        L_ = int(0.45 * SR)
        x = np.arange(L_) / SR
        noise = rng.normal(0, 1, L_)
        # crude band sweep: moving-average of decreasing width
        env = np.sin(np.pi * x / x[-1]) ** 2
        sig = np.convolve(noise, np.ones(24) / 24, "same") * env * 0.18
        put(a - 0.3, sig.astype(np.float32))
    # pops on chips / feature tiles
    pops = [L(1) + 0.2, L(1) + 1.4, CUE["peela"], CUE["neela"]] + list(CUE["notes"])
    for tp in pops:
        L_ = int(0.12 * SR)
        x = np.arange(L_) / SR
        put(tp, (np.sin(2 * np.pi * (900 + 1800 * x) * x) * np.exp(-x * 40) * 0.12).astype(np.float32))
    return out


def build_audio(path):
    m = R.music()
    vo = R.VO
    mix = R.mix_audio(m, vo)
    mix = mix + sfx_track(len(mix))
    mix /= max(1.0, np.max(np.abs(mix)) / 10 ** (-1 / 20))
    R.write_wav(path, mix)


def main():
    os.makedirs(OUT, exist_ok=True)
    arr = np.zeros((H, W, 4), np.uint8)
    if "--stills" in sys.argv:
        ts = [0.2, 2.0, L(1) + 2.0, L(3) + 1.0, L(4) + 1.5, CUE["neela"] + 1.3, L(6) + 2.6, L(8) - 0.3,
              L(8) + 2.5, L(9) + 1.5, CUE["notes"][3] + 0.6, L(12) + 2.0, DUR - 0.4]
        for t in ts:
            render(t, arr)
            skia.Image.fromarray(arr, colorType=skia.kRGBA_8888_ColorType).save(
                os.path.join(OUT, f"amz_{t:05.2f}.png"), skia.kPNG)
        return
    wav = os.path.join(OUT, "amazon_mix.wav")
    build_audio(wav)
    dst = os.path.join(OUT, "buildingshop_sticky_traps_amazon_16x9.mp4")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "medium", "-crf", "18",
           "-profile:v", "high", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
           "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-shortest", "-movflags", "+faststart", dst]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    nfr = int(DUR * FPS)
    for f in range(nfr):
        render(f / FPS, arr)
        p.stdin.write(arr.tobytes())
        if f % 150 == 0:
            print(f, "/", nfr, flush=True)
    p.stdin.close()
    p.wait()
    print("wrote", dst)


if __name__ == "__main__":
    main()
