"""BuildingShop Sticky Traps — 45s hybrid ad ("The Bug Route").

Real-looking plates (generated stills in plates/) + code-drawn motion graphics,
insect VFX, captions and an original synthesised soundtrack.

usage: python3 render.py [16x9|9x16] [--preview]
"""
import math, os, random, subprocess, sys, wave
import cairo
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
PLATES = os.path.join(HERE, "plates")
FPS, DUR = 30, 45.0
SW, SH = 1920, 1080  # scene canvas (always 16:9)
FONT = "DejaVu Sans"

YEL = (1.0, 0.83, 0.0)
BLU = (0.10, 0.42, 0.85)
DKG = (0.07, 0.24, 0.16)
CRM = (0.98, 0.96, 0.90)


# ---------------------------------------------------------------- helpers
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def ease_out(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def back_out(x):
    x = clamp(x)
    c = 1.4
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


def lerp(a, b, t):
    return a + (b - a) * t


def rgb(c, a=1.0):
    return (*c, a)


def rrect(cr, x, y, w, h, r):
    r = min(r, w / 2, h / 2)
    cr.new_sub_path()
    cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    cr.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
    cr.close_path()


def text(cr, s, x, y, size, color=(1, 1, 1), a=1.0, bold=True, anchor="c"):
    cr.select_font_face(FONT, cairo.FONT_SLANT_NORMAL,
                        cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL)
    cr.set_font_size(size)
    ext = cr.text_extents(s)
    if anchor == "c":
        tx = x - ext.width / 2 - ext.x_bearing
    elif anchor == "l":
        tx = x - ext.x_bearing
    else:
        tx = x - ext.width - ext.x_bearing
    ty = y - ext.height / 2 - ext.y_bearing
    cr.set_source_rgba(*color, a)
    cr.move_to(tx, ty)
    cr.show_text(s)
    return ext.width


def text_w(cr, s, size):
    cr.select_font_face(FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    cr.set_font_size(size)
    return cr.text_extents(s).width


def vgrad(cr, x, y, w, h, c1, c2):
    g = cairo.LinearGradient(0, y, 0, y + h)
    g.add_color_stop_rgb(0, *c1)
    g.add_color_stop_rgb(1, *c2)
    cr.set_source(g)
    cr.rectangle(x, y, w, h)
    cr.fill()


# ---------------------------------------------------------------- plates
_plate_cache = {}


def plate(name):
    if name in _plate_cache:
        return _plate_cache[name]
    p = os.path.join(PLATES, name + ".png")
    s = cairo.ImageSurface.create_from_png(p) if os.path.exists(p) else None
    _plate_cache[name] = s
    return s


def draw_plate(cr, name, zoom=1.0, fx=0.5, fy=0.5, grade=None, x=0, y=0, w=SW, h=SH):
    """Cover-fit a plate into (x,y,w,h) with Ken-Burns zoom around focus fx,fy."""
    s = plate(name)
    if s is None:  # no photo plate available -> code-drawn version of the same scene
        cr.save()
        cr.rectangle(x, y, w, h)
        cr.clip()
        sc = max(w / SW, h / SH) * zoom
        cr.translate(x + w / 2 - SW * sc * fx + (fx - 0.5) * w, y + h / 2 - SH * sc * fy + (fy - 0.5) * h)
        cr.scale(sc, sc)
        VECTOR_PLATES[name](cr)
        cr.restore()
        if grade:
            cr.save()
            cr.rectangle(x, y, w, h)
            cr.clip()
            cr.set_source_rgba(*grade)
            cr.paint()
            cr.restore()
        return
    iw, ih = s.get_width(), s.get_height()
    sc = max(w / iw, h / ih) * zoom
    cr.save()
    cr.rectangle(x, y, w, h)
    cr.clip()
    ox = x + w / 2 - iw * sc * fx + (fx - 0.5) * w
    oy = y + h / 2 - ih * sc * fy + (fy - 0.5) * h
    cr.translate(ox, oy)
    cr.scale(sc, sc)
    cr.set_source_surface(s, 0, 0)
    cr.get_source().set_filter(cairo.FILTER_GOOD)
    cr.paint()
    cr.restore()
    if grade:
        cr.save()
        cr.rectangle(x, y, w, h)
        cr.clip()
        cr.set_source_rgba(*grade)
        cr.paint()
        cr.restore()


# ---------------------------------------------------------------- props
def draw_trap(cr, cx, cy, w, color, bugs=0, seed=1, peel=0.0, flipx=1.0, glow=0.0,
              tie=True, a=1.0):
    """Sticky card 15x20 (portrait). bugs = count of stuck insects."""
    h = w * 20 / 15
    cr.save()
    cr.translate(cx, cy)
    cr.scale(max(abs(flipx), 0.02), 1)
    x, y = -w / 2, -h / 2
    if glow > 0:
        for i in range(6):
            r = w * (0.75 + i * 0.18)
            cr.set_source_rgba(*color, 0.06 * glow * (6 - i) / 6)
            rrect(cr, -r / 2 * 1.3, -r / 2 * 1.3 * 1.33, r * 1.3, r * 1.33 * 1.3, r * 0.2)
            cr.fill()
    # shadow
    cr.set_source_rgba(0, 0, 0, 0.18 * a)
    rrect(cr, x + w * 0.04, y + w * 0.05, w, h, w * 0.05)
    cr.fill()
    # card
    dark = tuple(c * 0.86 for c in color)
    g = cairo.LinearGradient(x, y, x + w, y + h)
    g.add_color_stop_rgba(0, *color, a)
    g.add_color_stop_rgba(1, *dark, a)
    cr.set_source(g)
    rrect(cr, x, y, w, h, w * 0.05)
    cr.fill()
    # printed grid
    cr.set_source_rgba(*(c * 0.7 for c in color), 0.45 * a)
    cr.set_line_width(max(1, w * 0.006))
    n = 6
    for i in range(1, n):
        cr.move_to(x + w * i / n, y + h * 0.1)
        cr.line_to(x + w * i / n, y + h)
        cr.stroke()
    for j in range(1, 8):
        yy = y + h * 0.1 + (h * 0.9) * j / 8
        cr.move_to(x, yy)
        cr.line_to(x + w, yy)
        cr.stroke()
    # hanging hole
    cr.set_source_rgba(1, 1, 1, 0.95 * a)
    cr.arc(0, y + h * 0.05, w * 0.035, 0, 2 * math.pi)
    cr.fill()
    # stuck bugs
    rnd = random.Random(seed)
    for i in range(bugs):
        bx = x + w * (0.08 + 0.84 * rnd.random())
        by = y + h * (0.14 + 0.82 * rnd.random())
        draw_bug(cr, bx, by, w * 0.022 * (0.7 + 0.6 * rnd.random()),
                 rnd.choice(["white", "gnat", "gnat", "white", "thrip"]), 0, rnd.random() * 6, stuck=True, a=a)
    # gloss
    g2 = cairo.LinearGradient(x, y, x + w * 0.8, y + h * 0.6)
    g2.add_color_stop_rgba(0, 1, 1, 1, 0.0)
    g2.add_color_stop_rgba(0.45, 1, 1, 1, 0.28 * a)
    g2.add_color_stop_rgba(0.6, 1, 1, 1, 0.0)
    cr.set_source(g2)
    rrect(cr, x, y, w, h, w * 0.05)
    cr.fill()
    # protective film: covers the card, peels back from the bottom-right corner
    if peel < 1.0:
        p = ease(peel)
        d = (w + h) * p  # how far the fold line has travelled from the corner
        c1 = (x + w, y + h - d) if d <= h else (x + w - (d - h), y)
        c2 = (x + w - d, y + h) if d <= w else (x, y + h - (d - w))
        cr.save()
        rrect(cr, x, y, w, h, w * 0.05)
        cr.clip()
        # film still on the card = card minus the peeled corner triangle-ish region
        cr.move_to(x, y)
        cr.line_to(x + w, y)
        cr.line_to(*c1)
        cr.line_to(*c2)
        cr.line_to(x, y + h)
        cr.close_path()
        cr.set_source_rgba(1, 1, 1, 0.38 * a)
        cr.fill()
        cr.restore()
        if p > 0.01:
            # curled flap reflected over the fold line
            mx, my = (c1[0] + c2[0]) / 2, (c1[1] + c2[1]) / 2
            nx, ny = -(c2[1] - c1[1]), (c2[0] - c1[0])
            L = math.hypot(nx, ny) or 1
            nx, ny = nx / L, ny / L
            tipx, tipy = mx - nx * d * 0.35, my - ny * d * 0.35
            cr.move_to(*c1)
            cr.curve_to(tipx, tipy, tipx, tipy, *c2)
            cr.close_path()
            cr.set_source_rgba(0.96, 0.98, 1.0, 0.92 * a)
            cr.fill_preserve()
            cr.set_source_rgba(0.55, 0.6, 0.66, 0.7 * a)
            cr.set_line_width(2)
            cr.stroke()
    cr.restore()
    if tie:
        cr.set_source_rgba(0.55, 0.42, 0.25, a)
        cr.set_line_width(3)
        cr.move_to(cx, cy - h / 2 + h * 0.05)
        cr.line_to(cx, cy - h / 2 - w * 0.35)
        cr.stroke()


def draw_bug(cr, x, y, s, kind, t, phase=0.0, stuck=False, a=1.0, blur=0.0):
    flap = 0.35 if stuck else 0.5 + 0.5 * math.sin(t * 60 + phase * 7)
    cr.save()
    cr.translate(x, y)
    cr.rotate(phase)
    if kind == "white":
        wing = (1, 1, 1)
        body = (0.95, 0.92, 0.6)
    elif kind == "thrip":
        wing = (0.8, 0.8, 0.75)
        body = (0.25, 0.18, 0.1)
    else:  # gnat
        wing = (0.75, 0.8, 0.85)
        body = (0.12, 0.12, 0.12)
    wa = (0.55 if kind != "white" else 0.95) * a * (1 - 0.5 * blur)
    for sgn in (-1, 1):
        cr.save()
        cr.rotate(sgn * (0.5 + 0.7 * flap))
        cr.scale(1.0, 0.5)
        cr.arc(sgn * s * 0.0, -s * 1.1, s * (1.0 + blur), 0, 2 * math.pi)
        cr.restore()
        cr.set_source_rgba(*wing, wa)
        cr.fill()
    cr.save()
    cr.scale(0.45 if kind != "thrip" else 0.3, 1.0)
    cr.arc(0, 0, s * (1.0 if kind != "thrip" else 1.4), 0, 2 * math.pi)
    cr.restore()
    cr.set_source_rgba(*body, a)
    cr.fill()
    cr.restore()


def draw_leaf(cr, x, y, L, ang, col=(0.22, 0.55, 0.25)):
    cr.save()
    cr.translate(x, y)
    cr.rotate(ang)
    cr.move_to(0, 0)
    cr.curve_to(L * 0.3, -L * 0.28, L * 0.75, -L * 0.22, L, 0)
    cr.curve_to(L * 0.75, L * 0.22, L * 0.3, L * 0.28, 0, 0)
    cr.set_source_rgb(*col)
    cr.fill()
    cr.set_source_rgba(1, 1, 1, 0.25)
    cr.set_line_width(L * 0.03)
    cr.move_to(0, 0)
    cr.line_to(L * 0.9, 0)
    cr.stroke()
    cr.restore()


def draw_pot_plant(cr, x, y, s, t, kind="tomato", seed=3):
    """Pot base centre at (x,y). Returns canopy top y."""
    rnd = random.Random(seed)
    # stems & leaves
    top = y - s * 2.1
    sway = math.sin(t * 1.3 + seed) * 0.04
    cr.set_line_width(s * 0.06)
    cr.set_source_rgb(0.25, 0.45, 0.2)
    for i in range(5):
        ang = -math.pi / 2 + (i - 2) * 0.32 + sway
        L = s * (1.4 + 0.5 * rnd.random())
        cr.move_to(x, y - s * 0.75)
        ex, ey = x + math.cos(ang) * L, y - s * 0.75 + math.sin(ang) * L
        cr.curve_to(x, y - s * 1.2, ex, ey + s * 0.3, ex, ey)
        cr.stroke()
        for k in range(3):
            f = 0.45 + k * 0.25
            lx = lerp(x, ex, f)
            ly = lerp(y - s * 0.75, ey, f)
            for sg in (-1, 1):
                draw_leaf(cr, lx, ly, s * 0.45, ang + sg * 1.0 + sway * 3,
                          (0.18 + 0.08 * rnd.random(), 0.5 + 0.1 * rnd.random(), 0.22))
        if kind == "tomato" and i % 2 == 0:
            cr.set_source_rgb(0.86, 0.18, 0.12)
            cr.arc(ex, ey + s * 0.25, s * 0.16, 0, 2 * math.pi)
            cr.fill()
            cr.set_source_rgb(0.25, 0.45, 0.2)
        if kind == "chilli" and i % 2 == 1:
            cr.save()
            cr.translate(ex, ey + s * 0.2)
            cr.rotate(0.3)
            cr.scale(0.35, 1)
            cr.arc(0, 0, s * 0.22, 0, 2 * math.pi)
            cr.restore()
            cr.set_source_rgb(0.85, 0.1, 0.08)
            cr.fill()
            cr.set_source_rgb(0.25, 0.45, 0.2)
    # pot
    cr.move_to(x - s * 0.6, y - s * 0.8)
    cr.line_to(x + s * 0.6, y - s * 0.8)
    cr.line_to(x + s * 0.45, y)
    cr.line_to(x - s * 0.45, y)
    cr.close_path()
    g = cairo.LinearGradient(x - s * 0.6, 0, x + s * 0.6, 0)
    g.add_color_stop_rgb(0, 0.72, 0.38, 0.22)
    g.add_color_stop_rgb(1, 0.55, 0.27, 0.15)
    cr.set_source(g)
    cr.fill()
    cr.set_source_rgb(0.62, 0.32, 0.18)
    rrect(cr, x - s * 0.68, y - s * 0.92, s * 1.36, s * 0.18, s * 0.05)
    cr.fill()
    return top


# ---------------------------------------------------------------- character
MEERA = dict(skin=(0.78, 0.55, 0.36), hair=(0.11, 0.08, 0.06), kurta=(0.76, 0.09, 0.36),
             dupatta=(0.18, 0.49, 0.2), pants=(0.95, 0.9, 0.7))


def draw_person(cr, x, y, s, t, arm_l=0.3, arm_r=-0.3, fore_l=0.3, fore_r=-0.3, look=0.0, P=MEERA):
    """Feet at (x,y); s = scale (~ head radius). Angles in radians from hanging-down."""
    blink = 1.0 if (t % 3.7) > 0.12 else 0.1
    breath = math.sin(t * 2.2) * s * 0.03
    cr.save()
    cr.translate(x, y)
    # legs
    cr.set_source_rgb(*P["pants"])
    rrect(cr, -s * 0.55, -s * 3.2, s * 0.5, s * 3.2, s * 0.2)
    cr.fill()
    rrect(cr, s * 0.05, -s * 3.2, s * 0.5, s * 3.2, s * 0.2)
    cr.fill()
    cr.set_source_rgb(0.35, 0.2, 0.12)
    rrect(cr, -s * 0.65, -s * 0.22, s * 0.62, s * 0.24, s * 0.1)
    cr.fill()
    rrect(cr, s * 0.03, -s * 0.22, s * 0.62, s * 0.24, s * 0.1)
    cr.fill()

    def arm(sx, ang, fang, side):
        cr.save()
        cr.translate(sx, -s * 6.0 + breath)
        cr.rotate(ang)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.set_line_width(s * 0.42)
        cr.set_source_rgb(*P["kurta"])
        cr.move_to(0, 0)
        cr.line_to(0, s * 1.4)
        cr.stroke()
        cr.translate(0, s * 1.4)
        cr.rotate(fang)
        cr.set_line_width(s * 0.32)
        cr.set_source_rgb(*P["skin"])
        cr.move_to(0, 0)
        cr.line_to(0, s * 1.3)
        cr.stroke()
        cr.arc(0, s * 1.4, s * 0.22, 0, 2 * math.pi)
        cr.fill()
        cr.restore()

    arm(s * 0.95, arm_r, fore_r, 1)  # back arm
    # kurta
    cr.move_to(-s * 0.95, -s * 6.2 + breath)
    cr.line_to(s * 0.95, -s * 6.2 + breath)
    cr.line_to(s * 1.25, -s * 2.4)
    cr.line_to(-s * 1.25, -s * 2.4)
    cr.close_path()
    cr.set_source_rgb(*P["kurta"])
    cr.fill()
    # dupatta sash / gamchha
    cr.move_to(-s * 0.9, -s * 6.1 + breath)
    cr.line_to(-s * 0.4, -s * 6.2 + breath)
    cr.line_to(s * 1.1, -s * 3.6)
    cr.line_to(s * 0.7, -s * 3.3)
    cr.close_path()
    cr.set_source_rgb(*P["dupatta"])
    cr.fill()
    if "turban" in P:  # dhoti hem over the kurta
        cr.set_source_rgb(*P["pants"])
        rrect(cr, -s * 1.1, -s * 2.6, s * 2.2, s * 0.5, s * 0.1)
        cr.fill()
    # neck + head
    cr.set_source_rgb(*P["skin"])
    rrect(cr, -s * 0.22, -s * 6.7 + breath, s * 0.44, s * 0.6, s * 0.1)
    cr.fill()
    hx, hy = look * s * 0.15, -s * 7.4 + breath
    if "turban" not in P:
        cr.set_source_rgb(*P["hair"])
        cr.arc(hx - s * 0.75, hy - s * 0.2, s * 0.42, 0, 2 * math.pi)  # bun
        cr.fill()
    cr.set_source_rgb(*P["skin"])
    cr.arc(hx, hy, s * 0.85, 0, 2 * math.pi)
    cr.fill()
    if "turban" in P:
        cr.set_source_rgb(*P["turban"])
        cr.save()
        cr.translate(hx, hy - s * 0.45)
        cr.scale(1.15, 0.7)
        cr.arc(0, 0, s * 0.85, math.pi, 2 * math.pi)
        cr.restore()
        cr.fill()
        rrect(cr, hx - s * 0.98, hy - s * 0.62, s * 1.96, s * 0.34, s * 0.15)
        cr.fill()
        cr.set_source_rgb(0.15, 0.1, 0.08)
        cr.save()
        cr.translate(hx + s * 0.05, hy + s * 0.28)
        cr.scale(1, 0.35)
        cr.arc(0, 0, s * 0.3, 0, 2 * math.pi)
        cr.restore()
        cr.fill()
    else:
        cr.set_source_rgb(*P["hair"])
        cr.arc(hx, hy - s * 0.05, s * 0.88, math.pi * 1.02, math.pi * 1.98)
        cr.fill()
    # face
    ex = hx + s * 0.25 + look * s * 0.1
    cr.set_source_rgb(0.1, 0.07, 0.05)
    for dx in (-0.28, 0.28):
        cr.save()
        cr.translate(ex + dx * s - s * 0.2, hy + s * 0.05)
        cr.scale(1, blink)
        cr.arc(0, 0, s * 0.09, 0, 2 * math.pi)
        cr.restore()
        cr.fill()
    if "turban" not in P:
        cr.set_source_rgb(0.8, 0.1, 0.15)
        cr.arc(ex - s * 0.2, hy - s * 0.3, s * 0.05, 0, 2 * math.pi)  # bindi
        cr.fill()
    cr.set_source_rgb(0.55, 0.2, 0.15)
    cr.set_line_width(s * 0.07)
    cr.arc(ex - s * 0.2, hy + s * 0.3, s * 0.22, 0.25 * math.pi, 0.75 * math.pi)
    cr.stroke()
    arm(-s * 0.95, arm_l, fore_l, -1)  # front arm
    cr.restore()


RAJU = dict(skin=(0.62, 0.40, 0.25), hair=(0.1, 0.08, 0.06), kurta=(0.97, 0.96, 0.92),
            dupatta=(0.78, 0.15, 0.12), pants=(0.93, 0.92, 0.86), turban=(0.96, 0.5, 0.05))


def draw_hand(cr, x, y, s, ang=0.0, skin=MEERA["skin"]):
    cr.save()
    cr.translate(x, y)
    cr.rotate(ang)
    cr.set_source_rgb(*MEERA["kurta"])
    rrect(cr, -s * 0.5, s * 0.9, s * 1.0, s * 3.0, s * 0.3)
    cr.fill()
    cr.set_source_rgb(*skin)
    rrect(cr, -s * 0.45, -s * 0.2, s * 0.9, s * 1.3, s * 0.4)
    cr.fill()
    for i in range(4):
        rrect(cr, -s * 0.42 + i * s * 0.22, -s * 0.85, s * 0.18, s * 0.8, s * 0.09)
        cr.fill()
    rrect(cr, s * 0.35, -s * 0.1, s * 0.5, s * 0.22, s * 0.11)  # thumb
    cr.fill()
    cr.restore()


# ---------------------------------------------------------------- swarm VFX
def swarm(cr, t, n, region, seed=7, size=7, attract=None, t_attract=0.0):
    rnd = random.Random(seed)
    x0, y0, x1, y1 = region
    for i in range(n):
        bx, by = rnd.uniform(x0, x1), rnd.uniform(y0, y1)
        f1, f2, ph = rnd.uniform(0.6, 1.4), rnd.uniform(0.7, 1.6), rnd.uniform(0, 6.28)
        kind = rnd.choice(["white", "white", "gnat"])
        depth = rnd.random()
        x = bx + 40 * math.sin(t * f1 + ph) + 18 * math.sin(t * 3.1 * f2 + ph)
        y = by + 30 * math.cos(t * f2 + ph) + 12 * math.sin(t * 4.3 + ph)
        s = size * (0.7 + depth * 1.4)
        blur = 0.6 if depth > 0.85 else 0.0
        draw_bug(cr, x, y, s * (1.8 if blur else 1), kind, t, ph, a=0.9 if not blur else 0.45, blur=blur)


# ---------------------------------------------------------------- code-drawn plates
def _buildings(cr, base, col, seed):
    rnd = random.Random(seed)
    x = -40
    while x < SW:
        w = rnd.uniform(140, 260)
        h = rnd.uniform(160, 380)
        cr.set_source_rgb(*col)
        cr.rectangle(x, base - h, w, h)
        cr.fill()
        cr.set_source_rgba(1, 1, 1, 0.25)
        for wy in range(int(base - h + 25), int(base - 20), 46):
            for wx in range(int(x + 18), int(x + w - 30), 44):
                cr.rectangle(wx, wy, 20, 22)
                cr.fill()
        x += w + rnd.uniform(10, 40)


def vp_terrace(cr, warm=0.0):
    vgrad(cr, 0, 0, SW, SH, (0.62 + 0.3 * warm, 0.80 + 0.05 * warm, 0.95 - 0.3 * warm), (0.98, 0.92, 0.80))
    cr.set_source_rgba(1, 0.97, 0.85, 0.8)
    cr.arc(1550, 200, 90, 0, 2 * math.pi)
    cr.fill()
    _buildings(cr, 600, (0.76, 0.80, 0.86), 3)
    _buildings(cr, 640, (0.68, 0.72, 0.78), 9)
    # parapet
    cr.set_source_rgb(0.93, 0.88, 0.78)
    cr.rectangle(0, 560, SW, 150)
    cr.fill()
    cr.set_source_rgb(0.83, 0.76, 0.64)
    cr.rectangle(0, 545, SW, 26)
    cr.fill()
    # floor tiles in perspective
    vgrad(cr, 0, 700, SW, SH - 700, (0.86, 0.73, 0.6), (0.74, 0.58, 0.45))
    cr.set_source_rgba(0.5, 0.35, 0.25, 0.25)
    cr.set_line_width(3)
    for i in range(-12, 13):
        cr.move_to(SW / 2 + i * 60, 700)
        cr.line_to(SW / 2 + i * 260, SH)
        cr.stroke()
    for j, yy in enumerate([730, 775, 835, 915, 1020]):
        cr.move_to(0, yy); cr.line_to(SW, yy); cr.stroke()
    for i, (px, s, k) in enumerate([(860, 120, "tomato"), (1100, 140, "chilli"), (1370, 130, "tomato"),
                                    (1620, 110, "chilli"), (1820, 125, "tomato")]):
        draw_pot_plant(cr, px, 900 + (i % 2) * 40, s, 0.0, kind=k, seed=20 + i)
    # bamboo stake with a yellow card already in use
    cr.set_source_rgb(0.72, 0.58, 0.32)
    rrect(cr, 1238, 450, 12, 480, 5)
    cr.fill()
    draw_trap(cr, 1244, 470, 110, YEL, bugs=10, seed=8, tie=False)


def vp_greenhouse(cr):
    vgrad(cr, 0, 0, SW, SH, (0.95, 0.97, 0.96), (0.80, 0.88, 0.80))
    vx, vy = SW / 2, 470
    # poly tunnel ribs
    cr.set_line_width(5)
    for k in range(9):
        f = 0.25 + 0.75 * (k / 8) ** 1.6
        w, h = SW * 1.3 * f, 700 * f
        cr.set_source_rgba(0.75, 0.8, 0.82, 0.9)
        cr.save()
        cr.translate(vx, vy + 260 * f)
        cr.scale(w / 2, h)
        cr.arc(0, 0, 1, math.pi, 2 * math.pi)
        cr.restore()
        cr.stroke()
    # ground and rows
    vgrad(cr, 0, 600, SW, SH - 600, (0.58, 0.45, 0.33), (0.45, 0.33, 0.24))
    for r in range(-3, 4):
        cr.move_to(vx + r * 30, 600)
        cr.line_to(vx + r * 420 - 120, SH)
        cr.line_to(vx + r * 420 + 120, SH)
        cr.line_to(vx + r * 30 + 12, 600)
        cr.close_path()
        cr.set_source_rgb(0.24, 0.52, 0.24)
        cr.fill()
        for d in range(1, 12):
            f = (d / 11) ** 1.7
            px = lerp(vx + r * 30 + 6, vx + r * 420, f)
            py = lerp(600, SH, f)
            cr.set_source_rgb(0.2, 0.6 + 0.05 * (d % 2), 0.25)
            cr.arc(px, py - 20 * f - 4, 8 + 60 * f, 0, 2 * math.pi)
            cr.fill()
    # cards above rows
    for r in (-2, 0, 2):
        for d in (4, 7, 10):
            f = (d / 11) ** 1.7
            px = lerp(vx + r * 30, vx + r * 420, f)
            py = lerp(560, 760, f)
            cr.set_source_rgba(0.5, 0.5, 0.5, 0.7)
            cr.set_line_width(1 + 2 * f)
            cr.move_to(px, py - 120 * f - 30); cr.line_to(px, py - 40 * f); cr.stroke()
            draw_trap(cr, px, py - 40 * f + 40 * f + 10, 20 + 110 * f, YEL if (r + d) % 2 else BLU,
                      bugs=int(4 + 10 * f), seed=r * 10 + d, tie=False)


def vp_farm(cr):
    vgrad(cr, 0, 0, SW, 520, (0.98, 0.78, 0.45), (1.0, 0.92, 0.7))
    cr.set_source_rgba(1, 0.95, 0.75, 0.95)
    cr.arc(1450, 330, 110, 0, 2 * math.pi)
    cr.fill()
    rnd = random.Random(4)
    for i in range(40):  # tree line
        x = i * 52
        cr.set_source_rgb(0.25, 0.38, 0.2)
        cr.arc(x, 500, rnd.uniform(30, 60), 0, 2 * math.pi)
        cr.fill()
    vgrad(cr, 0, 500, SW, SH - 500, (0.62, 0.48, 0.3), (0.5, 0.36, 0.22))
    vx = SW * 0.45
    for r in range(-9, 10):
        for d in range(1, 16):
            f = (d / 15) ** 1.8
            px = lerp(vx + r * 40, vx + r * 300, f)
            py = lerp(505, SH + 40, f)
            cr.set_source_rgb(0.2, 0.5 + 0.08 * ((r + d) % 2), 0.2)
            cr.arc(px, py - 8 * f, 5 + 48 * f, math.pi, 2 * math.pi)
            cr.fill()
    for d in (3, 6, 9, 12):
        f = (d / 15) ** 1.8
        for r in (-5, 1, 6):
            px = lerp(vx + r * 40 + 20, vx + r * 300 + 150, f)
            py = lerp(505, SH + 40, f)
            cr.set_source_rgb(0.72, 0.58, 0.32)
            cr.set_line_width(2 + 6 * f)
            cr.move_to(px, py); cr.line_to(px, py - 30 - 260 * f); cr.stroke()
            draw_trap(cr, px, py - 30 - 260 * f, 14 + 120 * f, YEL, bugs=int(3 + 12 * f), seed=d * 7 + r, tie=False)
    draw_person(cr, 1180, 900, 26, 0.0, arm_l=0.15, arm_r=-0.15, P=RAJU)


def vp_macro(cr):
    vgrad(cr, 0, 0, SW, SH, (0.2, 0.45, 0.22), (0.1, 0.3, 0.15))
    for i in range(8):
        draw_leaf(cr, (i * 290) % SW, 100 + (i * 377) % 900, 380, i * 0.8, (0.18, 0.42, 0.2))
    cr.set_source_rgba(0, 0, 0, 0.25)
    cr.paint()
    cr.save()
    cr.translate(960, 560)
    cr.rotate(-0.08)
    w, h = 1500, 1500 * 20 / 15
    cr.translate(0, h * 0.18)
    draw_trap(cr, 0, 0, w, YEL, bugs=0, tie=False)
    rnd = random.Random(12)
    for i in range(170):
        draw_bug(cr, rnd.uniform(-w / 2 + 30, w / 2 - 30), rnd.uniform(-h / 2 + 120, h / 2 - 30),
                 rnd.uniform(9, 16), rnd.choice(["white", "white", "gnat", "gnat", "thrip"]), 0,
                 rnd.random() * 6.28, stuck=True)
    cr.restore()


VECTOR_PLATES = {"terrace": vp_terrace, "greenhouse": vp_greenhouse, "farm": vp_farm, "macro": vp_macro,
                 "terrace_warm": lambda cr: vp_terrace(cr, 1.0)}


# ---------------------------------------------------------------- captions
CAPTIONS = []  # (t_in, t_out, text)


def cap(t_in, t_out, s):
    CAPTIONS.append((t_in, t_out, s))


def caption_state(t):
    for t_in, t_out, s in CAPTIONS:
        if t_in <= t <= t_out:
            a_in = ease_out((t - t_in) / 0.4)
            a_out = 1 - ease((t - (t_out - 0.3)) / 0.3)
            return s, min(a_in, a_out), (1 - a_in)
    return None


def draw_caption(cr, t, W, H, vertical=False):
    st = caption_state(t)
    if not st:
        return
    s, a, off = st
    size = 66 if vertical else 58
    words = s.split(" ")
    lines = [s]
    if vertical and text_w(cr, s, size) > W - 140:
        best = None
        for k in range(1, len(words)):
            l1, l2 = " ".join(words[:k]), " ".join(words[k:])
            m = max(text_w(cr, l1, size), text_w(cr, l2, size))
            if best is None or m < best[0]:
                best = (m, [l1, l2])
        lines = best[1]
    lw = max(text_w(cr, l, size) for l in lines)
    lh = size * 1.3
    pw, ph = lw + 90, lh * len(lines) + 44
    cx = W / 2
    cy = (H * 0.73 if vertical else H * 0.865) + off * 30
    cr.save()
    cr.set_source_rgba(0, 0, 0, 0.25 * a)
    rrect(cr, cx - pw / 2 + 6, cy - ph / 2 + 8, pw, ph, ph / 2 if len(lines) == 1 else 40)
    cr.fill()
    cr.set_source_rgba(*DKG, 0.94 * a)
    rrect(cr, cx - pw / 2, cy - ph / 2, pw, ph, ph / 2 if len(lines) == 1 else 40)
    cr.fill()
    cr.set_source_rgba(*YEL, a)
    rrect(cr, cx - 50, cy + ph / 2 - 10, 100, 6, 3)
    cr.fill()
    for i, l in enumerate(lines):
        text(cr, l, cx, cy - (len(lines) - 1) * lh / 2 + i * lh, size, (1, 1, 1), a)
    cr.restore()


def draw_mark(cr, W, H, vertical=False):
    size = 34 if vertical else 30
    cr.select_font_face(FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    cr.set_font_size(size)
    ext = cr.text_extents("buildingshop")
    x = W - 48 - ext.width
    y = 60 if not vertical else 90
    cr.set_source_rgba(0, 0, 0, 0.25)
    cr.move_to(x + 2, y + 2)
    cr.show_text("buildingshop")
    cr.set_source_rgba(1, 1, 1, 0.7)
    cr.move_to(x, y)
    cr.show_text("buildingshop")


# ---------------------------------------------------------------- scenes
# timeline (s): S1 0-5.2 | S2 5.7-10.1 | S3 10.6-22.0 | S4 22.5-26.9 | S5 27.4-38.8 | S6 39.3-42.9 | S7 43.3-45
cap(0.4, 4.9, "Tiny flying pests on your plants?")
cap(6.0, 10.0, "Yellow & Blue Sticky Traps")
cap(10.8, 14.6, "1  Peel off the protective film")
cap(14.6 + 0.1, 18.3, "2  Hang just above the plants")
cap(18.4, 21.9, "3  Replace when it's covered")
cap(22.7, 26.8, "Bright colours lure flying pests")
cap(27.9, 31.4, "Balcony & terrace gardens")
cap(31.6, 35.1, "Greenhouses & nurseries")
cap(35.3, 38.7, "Farm fields too")


def s1_hook(cr, lt):
    z = 1.0 + 0.08 * ease(lt / 5.5)
    draw_plate(cr, "terrace", zoom=z, fx=0.62, fy=0.55)
    # vignette
    g = cairo.RadialGradient(SW / 2, SH / 2, SH * 0.3, SW / 2, SH / 2, SH * 1.0)
    g.add_color_stop_rgba(0, 0, 0, 0, 0)
    g.add_color_stop_rgba(1, 0, 0, 0, 0.45)
    cr.set_source(g)
    cr.paint()
    swarm(cr, lt, 30, (700, 250, 1500, 700), seed=11, size=12)
    if plate("terrace") is None:
        sw = math.sin(lt * 5) * 0.5
        draw_person(cr, 470, 880, 56, lt, arm_r=-2.4 + sw, fore_r=-0.6, arm_l=-0.4, fore_l=-2.2, look=1)


def s2_product(cr, lt):
    vgrad(cr, 0, 0, SW, SH, (0.93, 0.97, 0.90), (0.72, 0.86, 0.70))
    # soft leaf silhouettes
    for i in range(7):
        draw_leaf(cr, 80 + i * 300, SH + 30, 260, -1.2 - 0.2 * (i % 3), (0.62, 0.8, 0.6))
    p1 = back_out((lt - 0.0) / 1.1)
    p2 = back_out((lt - 0.25) / 1.1)
    spin1 = math.cos(clamp(1 - (lt - 0.0) / 1.4) * math.pi * 2)
    spin2 = math.cos(clamp(1 - (lt - 0.25) / 1.4) * math.pi * 2)
    bob = math.sin(lt * 1.6) * 8
    draw_trap(cr, lerp(-300, 720, p1), 470 + bob, 300, YEL, flipx=spin1, tie=False, glow=0.5)
    draw_trap(cr, lerp(SW + 300, 1200, p2), 470 - bob, 300, BLU, flipx=spin2, tie=False, glow=0.5)
    # dimension tag
    ta = ease((lt - 1.6) / 0.5)
    if ta > 0:
        cr.set_source_rgba(*DKG, ta)
        cr.set_line_width(4)
        x0, x1, yy = 570, 870, 700
        cr.move_to(x0, yy); cr.line_to(x1, yy); cr.stroke()
        for xx in (x0, x1):
            cr.move_to(xx, yy - 14); cr.line_to(xx, yy + 14); cr.stroke()
        text(cr, "15 cm", (x0 + x1) / 2, yy + 34, 34, DKG, ta)
        xx, y0, y1 = 520, 270, 670
        cr.move_to(xx, y0); cr.line_to(xx, y1); cr.stroke()
        for yv in (y0, y1):
            cr.move_to(xx - 14, yv); cr.line_to(xx + 14, yv); cr.stroke()
        cr.save()
        cr.translate(xx - 34, (y0 + y1) / 2)
        cr.rotate(-math.pi / 2)
        text(cr, "20 cm", 0, 0, 34, DKG, ta)
        cr.restore()
        # double-sided badge
        bx, by = 1200, 160
        cr.set_source_rgba(1, 1, 1, 0.9 * ta)
        rrect(cr, bx - 190, by - 34, 380, 68, 34)
        cr.fill()
        text(cr, "sticky on both sides", bx, by, 32, DKG, ta)


def s3_howto(cr, lt):
    vgrad(cr, 0, 0, SW, SH, (0.97, 0.95, 0.88), (0.86, 0.9, 0.78))
    step = 0 if lt < 4.0 else (1 if lt < 7.7 else 2)
    sl = lt - [0, 4.0, 7.7][step]
    # step dots
    for i in range(3):
        c = YEL if i == step else (0.8, 0.8, 0.75)
        cr.set_source_rgb(*c)
        cr.arc(SW / 2 - 40 + i * 40, 70, 11, 0, 2 * math.pi)
        cr.fill()
    if step == 0:
        peel = ease((sl - 0.6) / 2.0)
        draw_trap(cr, 960, 470, 330, YEL, peel=peel, tie=False)
        hh = 330 * 20 / 15
        p = ease(peel)
        hx = 960 + 165 - (330 + hh) * p * 0.5 + 40
        hy = 470 + hh / 2 - (330 + hh) * p * 0.5 + 60
        draw_hand(cr, hx, hy, 60, ang=-0.6)
        if sl > 2.6:
            a = ease((sl - 2.6) / 0.4)
            for k in range(5):
                ang = k * 1.25 + sl
                cr.set_source_rgba(1, 1, 1, a * 0.8)
                cr.arc(960 + math.cos(ang) * 230, 470 + math.sin(ang) * 260, 6, 0, 2 * math.pi)
                cr.fill()
    elif step == 1:
        # terrace floor
        cr.set_source_rgb(0.85, 0.78, 0.66)
        cr.rectangle(0, 820, SW, SH - 820)
        cr.fill()
        for i in range(3):
            draw_pot_plant(cr, 760 + i * 230, 900, 95, lt, kind=["tomato", "chilli", "tomato"][i], seed=4 + i)
        # bamboo stake
        cr.set_source_rgb(0.72, 0.58, 0.32)
        rrect(cr, 1006, 330, 14, 560, 6)
        cr.fill()
        drop = ease((sl - 0.3) / 1.4)
        ty = lerp(120, 470, drop)
        swing = math.sin(sl * 3) * 0.05 * (1 - drop)
        cr.save()
        cr.translate(1013, 340)
        cr.rotate(swing)
        cr.translate(-1013, -340)
        cr.set_source_rgb(0.72, 0.58, 0.32)
        rrect(cr, 900, 330, 240, 10, 5)
        cr.fill()
        draw_trap(cr, 1110, ty, 150, YEL, tie=False)
        cr.set_source_rgb(0.45, 0.35, 0.2)
        cr.set_line_width(3)
        cr.move_to(1110, 340); cr.line_to(1110, ty - 100); cr.stroke()
        cr.restore()
        if drop >= 1:
            a = ease((sl - 1.8) / 0.4)
            cr.set_source_rgba(*DKG, a)
            cr.set_line_width(3)
            cr.set_dash([10, 8])
            cr.move_to(1215, 570); cr.line_to(1215, 690); cr.stroke()
            cr.set_dash([])
            text(cr, "just above leaves", 1235, 630, 30, DKG, a, anchor="l")
        draw_person(cr, 470, 860, 52, lt, arm_r=-2.2 + 0.2 * math.sin(lt * 2), fore_r=-0.3, arm_l=0.2, look=1)
    else:
        out = ease((sl - 0.4) / 1.0)
        inn = back_out((sl - 1.0) / 1.0)
        draw_trap(cr, lerp(960, -300, out), 470 + out * 80, 300, YEL, bugs=70, seed=5, tie=False,
                  a=1 - out * 0.6)
        draw_trap(cr, lerp(SW + 300, 960, inn), 470, 300, YEL, tie=False, glow=0.6 * inn)
        if sl > 2.0:
            a = ease((sl - 2.0) / 0.4)
            for k in range(8):
                ang = k * 0.785 + sl * 0.5
                r = 260 + 10 * math.sin(sl * 4 + k)
                cr.set_source_rgba(1, 0.95, 0.5, a * 0.9)
                cr.arc(960 + math.cos(ang) * r * 0.8, 470 + math.sin(ang) * r, 5, 0, 2 * math.pi)
                cr.fill()


def s4_works(cr, lt):
    vgrad(cr, 0, 0, SW, SH, (0.08, 0.2, 0.14), (0.03, 0.1, 0.07))
    traps = [(700, 450, YEL, ["white", "gnat", "white", "gnat"]), (1220, 450, BLU, ["thrip"])]
    for k, (cx, cy, col, kinds) in enumerate(traps):
        # pulse rings
        for r in range(3):
            ph = (lt * 0.6 + r / 3) % 1
            cr.set_source_rgba(*col, 0.35 * (1 - ph))
            cr.set_line_width(5)
            rrect(cr, cx - 120 - ph * 220, cy - 160 - ph * 220, 240 + ph * 440, 320 + ph * 440, 40 + ph * 80)
            cr.stroke()
        rnd = random.Random(40 + k)
        n = 28
        stuck = 0
        for i in range(n):
            t0 = 0.2 + i * 0.16 + rnd.random() * 0.2
            dur = 1.4 + rnd.random() * 0.6
            sx = rnd.choice([-80, SW + 80]) if rnd.random() < 0.6 else rnd.uniform(0, SW)
            sy = rnd.uniform(-80, SH + 80) if sx in (-80, SW + 80) else rnd.choice([-80, SH + 80])
            ex = cx + rnd.uniform(-95, 95)
            ey = cy + rnd.uniform(-110, 140)
            p = (lt - t0) / dur
            kind = kinds[i % len(kinds)]
            if p >= 1:
                stuck += 1
                continue
            if p <= 0:
                continue
            e = ease(p)
            wob = math.sin(p * 12 + i) * 60 * (1 - e)
            x = lerp(sx, ex, e) + wob
            y = lerp(sy, ey, e) + math.cos(p * 9 + i) * 40 * (1 - e)
            draw_bug(cr, x, y, 14, kind, lt, i)
        draw_trap(cr, cx, cy, 240, col, bugs=stuck, seed=50 + k, tie=False)
        a = ease((lt - 1.0) / 0.5)
        lbl = "whiteflies · aphids · gnats" if col == YEL else "thrips"
        text(cr, lbl, cx, cy + 215, 30, (1, 1, 1), a * 0.92)


STOPS = [(430, 700, "terrace", (0.6, 0.55)), (960, 430, "greenhouse", (0.5, 0.5)),
         (1490, 690, "farm", (0.5, 0.55))]


def draw_map(cr, lt):
    vgrad(cr, 0, 0, SW, SH, (0.93, 0.9, 0.8), (0.88, 0.85, 0.74))
    # fields
    rnd = random.Random(2)
    for i in range(16):
        x, y = rnd.uniform(0, SW), rnd.uniform(0, SH)
        cr.set_source_rgba(0.55 + 0.15 * rnd.random(), 0.72, 0.45, 0.55)
        rrect(cr, x, y, rnd.uniform(140, 300), rnd.uniform(90, 200), 18)
        cr.fill()
    # river
    cr.set_source_rgba(0.55, 0.75, 0.9, 0.9)
    cr.set_line_width(46)
    cr.move_to(-50, 180)
    cr.curve_to(500, 320, 900, 60, 1400, 230)
    cr.curve_to(1700, 330, 1850, 250, SW + 50, 300)
    cr.stroke()
    # roads
    cr.set_source_rgba(1, 1, 1, 0.9)
    cr.set_line_width(22)
    cr.move_to(-50, 900); cr.curve_to(600, 820, 1300, 980, SW + 50, 860); cr.stroke()
    cr.move_to(1180, -50); cr.curve_to(1100, 400, 1300, 700, 1250, SH + 50); cr.stroke()
    # little houses
    for i in range(9):
        x, y = rnd.uniform(100, 900), rnd.uniform(450, 820)
        cr.set_source_rgb(0.85, 0.55, 0.45)
        rrect(cr, x, y, 34, 26, 4)
        cr.fill()


def route_pts():
    pts = [(80, 980)] + [(x, y) for x, y, _, _ in STOPS]
    out = []
    for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]):
        for k in range(40):
            f = k / 40
            out.append((lerp(x0, x1, f), lerp(y0, y1, f) - math.sin(f * math.pi) * 120))
    out.append(pts[-1])
    return out


ROUTE = route_pts()


def s5_uses(cr, lt):
    draw_map(cr, lt)
    stop = 0 if lt < 4.0 else (1 if lt < 7.6 else 2)
    sl = lt - [0, 4.0, 7.6][stop]
    seg_progress = stop + ease((sl - 0.0) / 0.7)
    n = int(clamp(seg_progress / 3) * (len(ROUTE) - 1))
    cr.set_source_rgba(*DKG, 0.9)
    for i in range(0, n, 2):
        cr.arc(ROUTE[i][0], ROUTE[i][1], 6, 0, 2 * math.pi)
        cr.fill()
    for i, (x, y, _, _) in enumerate(STOPS):
        if i <= stop and (i < stop or sl > 0.6):
            cr.set_source_rgb(*(YEL if i % 2 == 0 else BLU))
            cr.arc(x, y - 30, 22, 0, 2 * math.pi)
            cr.fill()
            cr.move_to(x - 16, y - 18); cr.line_to(x, y + 6); cr.line_to(x + 16, y - 18)
            cr.fill()
            cr.set_source_rgb(1, 1, 1)
            cr.arc(x, y - 30, 8, 0, 2 * math.pi)
            cr.fill()
    # vignette bubble
    x, y, name, (fx, fy) = STOPS[stop]
    pa = back_out((sl - 0.6) / 0.6)
    fade = 1 - ease((sl - 3.3) / 0.3)
    if pa > 0 and fade > 0:
        bx, by, r = 960 + (x - 960) * 0.35, 410, 300 * pa
        cr.save()
        cr.push_group()
        cr.set_source_rgba(0, 0, 0, 0.25)
        cr.arc(bx + 8, by + 12, r + 12, 0, 2 * math.pi)
        cr.fill()
        cr.set_source_rgb(1, 1, 1)
        cr.arc(bx, by, r + 12, 0, 2 * math.pi)
        cr.fill()
        cr.arc(bx, by, r, 0, 2 * math.pi)
        cr.clip()
        draw_plate(cr, name, zoom=1.05 + 0.06 * ease(sl / 3.6), fx=fx, fy=fy,
                   x=bx - r * 1.6, y=by - r, w=r * 3.2, h=r * 2)
        if name in ("greenhouse", "farm"):
            swarm(cr, lt, 8, (bx - r, by - r * 0.8, bx + r, by + r * 0.3), seed=60 + stop, size=5)
        cr.reset_clip()
        cr.pop_group_to_source()
        cr.paint_with_alpha(fade)
        cr.restore()


FEATS = [("no sprays needed", "leaf"), ("water-resistant card", "drop"),
         ("sticky on both sides", "card"), ("indoor & outdoor", "sun")]


def icon(cr, kind, x, y, s, col):
    cr.set_source_rgb(*col)
    if kind == "leaf":
        draw_leaf(cr, x - s * 0.6, y + s * 0.4, s * 1.3, -0.7, col)
    elif kind == "drop":
        cr.move_to(x, y - s * 0.7)
        cr.curve_to(x + s * 0.7, y, x + s * 0.5, y + s * 0.6, x, y + s * 0.6)
        cr.curve_to(x - s * 0.5, y + s * 0.6, x - s * 0.7, y, x, y - s * 0.7)
        cr.fill()
    elif kind == "card":
        rrect(cr, x - s * 0.55, y - s * 0.6, s * 0.7, s * 0.95, s * 0.1)
        cr.fill()
        cr.set_source_rgb(*BLU)
        rrect(cr, x - s * 0.15, y - s * 0.4, s * 0.7, s * 0.95, s * 0.1)
        cr.fill()
    else:
        cr.arc(x, y, s * 0.35, 0, 2 * math.pi)
        cr.fill()
        cr.set_line_width(s * 0.1)
        for k in range(8):
            a = k * math.pi / 4
            cr.move_to(x + math.cos(a) * s * 0.5, y + math.sin(a) * s * 0.5)
            cr.line_to(x + math.cos(a) * s * 0.7, y + math.sin(a) * s * 0.7)
            cr.stroke()


def s6_features(cr, lt):
    draw_plate(cr, "macro", zoom=1.08 - 0.05 * ease(lt / 3.6), fx=0.5, fy=0.5,
               grade=(0.02, 0.08, 0.05, 0.55))
    for i, (s, ic) in enumerate(FEATS):
        p = back_out((lt - 0.1 - i * 0.3) / 0.5)
        if p <= 0:
            continue
        col, row = i % 2, i // 2
        cx = 960 + (col - 0.5) * 680
        cy = 330 + row * 190
        w, h = 640, 140
        cr.save()
        cr.translate(cx, cy)
        cr.scale(p, p)
        cr.set_source_rgba(1, 1, 1, 0.95)
        rrect(cr, -w / 2, -h / 2, w, h, h / 2)
        cr.fill()
        cr.set_source_rgb(*DKG)
        cr.arc(-w / 2 + 70, 0, 48, 0, 2 * math.pi)
        cr.fill()
        icon(cr, ic, -w / 2 + 70, 0, 44, YEL)
        text(cr, s, -w / 2 + 135, 0, 36, DKG, anchor="l")
        cr.restore()


def s7_close(cr, lt):
    name = "terrace" if plate("terrace") is not None else "terrace_warm"
    draw_plate(cr, name, zoom=1.12 - 0.04 * ease(lt / 1.7), fx=0.6, fy=0.5,
               grade=(1.0, 0.7, 0.3, 0.12))
    if plate("terrace") is None:
        draw_person(cr, 520, 900, 50, lt + 3, arm_r=-0.3, fore_r=-1.6, arm_l=0.3, fore_l=-1.4, look=1)
        cr.set_source_rgb(0.6, 0.42, 0.2)  # basket of tomatoes
        cr.arc(575, 560, 80, 0, math.pi)
        cr.fill()
        for k in range(5):
            cr.set_source_rgb(0.88, 0.2, 0.12)
            cr.arc(522 + k * 27, 556 - (k % 2) * 14, 20, 0, 2 * math.pi)
            cr.fill()


SCENES = [(0.0, 5.2, s1_hook), (5.7, 10.1, s2_product), (10.6, 22.0, s3_howto),
          (22.5, 26.9, s4_works), (27.4, 38.8, s5_uses), (39.3, 42.9, s6_features),
          (43.3, 45.0, s7_close)]


def draw_route_wipe(cr, m):
    """Signature transition: a dotted route line + pin sweeps across the frame."""
    px = lerp(-120, SW + 120, m)
    cr.set_source_rgba(*DKG, 0.85 * math.sin(m * math.pi))
    for i in range(0, int(px), 34):
        y = SH * 0.5 + math.sin(i / 160) * 60
        cr.arc(i, y, 7, 0, 2 * math.pi)
        cr.fill()
    y = SH * 0.5 + math.sin(px / 160) * 60
    cr.set_source_rgba(*YEL, math.sin(m * math.pi))
    cr.arc(px, y - 34, 26, 0, 2 * math.pi)
    cr.fill()
    cr.move_to(px - 19, y - 20); cr.line_to(px, y + 6); cr.line_to(px + 19, y - 20)
    cr.fill()


def draw_scene(cr, t):
    for i, (a, b, fn) in enumerate(SCENES):
        if a <= t <= b:
            fn(cr, t - a)
            break
        nxt = SCENES[i + 1] if i + 1 < len(SCENES) else None
        if nxt and b < t < nxt[0]:
            m = ease((t - b) / (nxt[0] - b))
            fn(cr, t - a)
            cr.push_group()
            nxt[2](cr, 0.0)
            cr.pop_group_to_source()
            cr.paint_with_alpha(m)
            draw_route_wipe(cr, (t - b) / (nxt[0] - b))
            break
    # final fade
    if t > DUR - 1.0:
        cr.set_source_rgba(*CRM, ease((t - (DUR - 1.0)) / 1.0))
        cr.paint()


# ---------------------------------------------------------------- frames
def render_frame(t, fmt):
    if fmt == "16x9":
        surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, SW, SH)
        cr = cairo.Context(surf)
        draw_scene(cr, t)
        draw_caption(cr, t, SW, SH)
        if t < DUR - 1.0:
            draw_mark(cr, SW, SH)
        return surf
    W, H = 1080, 1920
    scene = cairo.ImageSurface(cairo.FORMAT_ARGB32, SW, SH)
    draw_scene(cairo.Context(scene), t)
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    cr = cairo.Context(surf)
    # blurred-fill backdrop: scene scaled to cover, darkened
    sc = H / SH
    cr.save()
    cr.translate(W / 2 - SW * sc / 2, 0)
    cr.scale(sc, sc)
    cr.set_source_surface(scene, 0, 0)
    cr.get_source().set_filter(cairo.FILTER_FAST)
    cr.paint()
    cr.restore()
    cr.set_source_rgba(*DKG, 0.82)
    cr.paint()
    # main window: centre 4:3 crop of the scene
    cw = 1440
    s2 = W / cw
    top = 330
    cr.save()
    rrect(cr, 0, top, W, SH * s2, 0)
    cr.clip()
    cr.translate(-(SW - cw) / 2 * s2, top)
    cr.scale(s2, s2)
    cr.set_source_surface(scene, 0, 0)
    cr.get_source().set_filter(cairo.FILTER_GOOD)
    cr.paint()
    cr.restore()
    draw_caption(cr, t, W, H, vertical=True)
    if t < DUR - 1.0:
        draw_mark(cr, W, H, vertical=True)
    return surf


def render(fmt, preview=False):
    os.makedirs(OUT, exist_ok=True)
    if preview:
        for t in [1.5, 4.5, 7.5, 9.0, 12.5, 16.5, 20.0, 24.5, 26.5, 29.5, 33.5, 37.0, 41.5, 44.0, 5.45, 22.25]:
            render_frame(t, fmt).write_to_png(os.path.join(OUT, f"preview_{fmt}_{t:05.2f}.png"))
        return
    W, H = (SW, SH) if fmt == "16x9" else (1080, 1920)
    audio = os.path.join(OUT, "sticky_traps_music.wav")
    dst = os.path.join(OUT, f"buildingshop_sticky_traps_{fmt}.mp4")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgra",
           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", audio,
           "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", dst]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    n = int(DUR * FPS)
    for f in range(n):
        surf = render_frame(f / FPS, fmt)
        p.stdin.write(bytes(surf.get_data()))
        if f % 150 == 0:
            print(fmt, f, "/", n, flush=True)
    p.stdin.close()
    p.wait()
    print("wrote", dst)


if __name__ == "__main__":
    fmt = sys.argv[1] if len(sys.argv) > 1 else "16x9"
    render(fmt, preview="--preview" in sys.argv)
