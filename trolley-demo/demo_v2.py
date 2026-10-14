"""BuildingShop folding platform trolley — v2 motion-designed 16:9 Amazon video.

Problem -> turn -> reveal -> hero -> proof -> uses -> end card, cut on a 123 BPM grid.
Motion: 2.5D parallax (rembg cut-outs over inpainted plates), speed ramps on the real clip, whip pans with
directional blur, camera shake on impacts, dust particles + light leaks, kinetic type, perspective product turn
with floor reflection, animated 500 kg counter. Original synthesised music + SFX. No captions, no border.
Generated clips (Veo/Kling/Runway) can replace any plate: drop work/clips/<shot>.mp4 (see CLIP_SLOTS).

usage: python3 demo_v2.py [--stills] [--vo vo/narrator.mp3]
"""
import math, os, random, subprocess, sys, wave
import numpy as np
import skia
import demo16x9 as D
from demo16x9 import (W, H, FPS, SR, C, fill, stroke, clamp, ease, eoe, bout, lerp, rrect, font, text, footage,
                      SAMP, YEL, WHITE)

HERE = D.HERE
OUT = D.OUT
BPM = 123
BEAT = 60 / BPM
BAR = BEAT * 4
RED = (235, 64, 52)
NAVY = (10, 18, 34)


def bars(n):
    return n * BAR


# ------------------------------------------------------------------ timeline (bar grid)
T = {}
_t = 0.0
for name, nb in [("problem", 2), ("turn", 1), ("reveal", 2), ("hero", 3), ("load", 2), ("push", 2), ("fold", 2),
                 ("uses", 3), ("end", 2.5)]:
    T[name] = (_t, _t + bars(nb))
    _t += bars(nb)
DUR = round(_t, 2)


# ------------------------------------------------------------------ assets
def img(path):
    return skia.Image.MakeFromEncoded(skia.Data.MakeFromFileName(os.path.join(HERE, path)))


IM = {k: img(p) for k, p in {
    "manual_bg": "work/cut/manual_bg.png", "manual_fg": "work/cut/manual.png", "manual": "plates/manual.jpg",
    "load_bg": "work/cut/load_bg.png", "load_fg": "work/cut/load.png",
    "shop_bg": "work/cut/shop_bg.png", "shop_fg": "work/cut/shop.png",
    "home_bg": "work/cut/home_bg.png", "home_fg": "work/cut/home.png",
    "folded_bg": "work/cut/folded_bg.png", "folded_fg": "work/cut/folded.png",
    "hero_cut": "work/cut/hero.png"}.items()}


def cover(cv, im, z=1.0, fx=0.5, fy=0.5, dx=0.0, dy=0.0, alpha=1.0):
    s = max(W / im.width(), H / im.height()) * z
    cv.save()
    cv.translate(W * fx + dx - im.width() * s * fx, H * fy + dy - im.height() * s * fy)
    cv.scale(s, s)
    cv.drawImage(im, 0, 0, SAMP, skia.Paint(Alphaf=alpha))
    cv.restore()


def parallax(cv, key, lt, dur, z_bg=(1.04, 1.10), z_fg=(1.06, 1.18), pan=(-30, 30), fg_pan=(-70, 70), fx=0.5, fy=0.55):
    """2.5D: inpainted background moves slowly, cut-out subject moves more -> depth."""
    k = ease(lt / dur)
    cover(cv, IM[key + "_bg"], lerp(*z_bg, k), fx, fy, dx=lerp(*pan, k))
    # soft contact shadow follows the subject
    cover(cv, IM[key + "_fg"], lerp(*z_fg, k), fx, fy, dx=lerp(*fg_pan, k))


def clip_slot(name):
    p = os.path.join(HERE, "work", "clips", name + ".mp4")
    return p if os.path.exists(p) else None


# ------------------------------------------------------------------ fx layers
RND = random.Random(7)
DUST = [(RND.random(), RND.random(), RND.uniform(1.5, 5.5), RND.uniform(0.2, 1.0), RND.random() * 6.28) for _ in range(140)]


def dust(cv, t, a=1.0, warm=(255, 230, 190)):
    for x, y, r, d, ph in DUST:
        px = (x * W + math.sin(t * 0.4 + ph) * 40 * d + t * 18 * d) % (W + 40) - 20
        py = (y * H + math.cos(t * 0.3 + ph) * 30 * d - t * 10 * d) % (H + 40) - 20
        al = (0.35 + 0.65 * (0.5 + 0.5 * math.sin(t * 2 + ph))) * 150 * a * d
        cv.drawCircle(px, py, r * (1.5 - d), fill(warm, al, blur=r * (1.2 - d) * 1.5))


def light_beams(cv, t, origin=(W * 0.35, -100), a=40):
    ox, oy = origin
    for i in range(5):
        ang = math.radians(62 + i * 7 + math.sin(t * 0.3 + i) * 1.5)
        w = math.radians(2.2 + (i % 2))
        p = skia.Path()
        p.moveTo(ox, oy)
        p.lineTo(ox + math.cos(ang - w) * 2600, oy + math.sin(ang - w) * 2600)
        p.lineTo(ox + math.cos(ang + w) * 2600, oy + math.sin(ang + w) * 2600)
        p.close()
        pt = skia.Paint(AntiAlias=True)
        pt.setShader(skia.GradientShader.MakeRadial(skia.Point(ox, oy), 1800, [C((255, 235, 200), a), C((255, 235, 200), 0)]))
        pt.setBlendMode(skia.BlendMode.kScreen)
        cv.drawPath(p, pt)


def light_leak(cv, t, t0, dur=0.9, col=(255, 150, 60)):
    k = (t - t0) / dur
    if not 0 < k < 1:
        return
    a = math.sin(k * math.pi)
    x = lerp(-300, W + 300, k)
    p = skia.Paint()
    p.setShader(skia.GradientShader.MakeRadial(skia.Point(x, H * 0.4), 900, [C(col, 160 * a), C(col, 0)]))
    p.setBlendMode(skia.BlendMode.kScreen)
    cv.drawRect(skia.Rect(0, 0, W, H), p)


def flash(cv, t, t0, dur=0.25, a=200):
    k = (t - t0) / dur
    if 0 <= k < 1:
        cv.drawRect(skia.Rect(0, 0, W, H), fill(WHITE, a * (1 - k) ** 2))


def shake(t, hits, amp=18):
    dx = dy = 0.0
    for h in hits:
        d = t - h
        if 0 <= d < 0.6:
            e = math.exp(-9 * d)
            dx += amp * e * math.sin(d * 90)
            dy += amp * 0.7 * e * math.cos(d * 77)
    return dx, dy


def vignette(cv, a=130):
    p = skia.Paint()
    p.setShader(skia.GradientShader.MakeRadial(skia.Point(W / 2, H / 2), W * 0.72,
                                               [C((0, 0, 0), 0), C((0, 0, 0), 0), C((0, 0, 0), a)], [0, 0.5, 1]))
    cv.drawRect(skia.Rect(0, 0, W, H), p)


def grade_layer(cv, mode):
    if mode == "cold":
        cv.drawRect(skia.Rect(0, 0, W, H), fill((40, 70, 110), 40))
    elif mode == "warm":
        cv.drawRect(skia.Rect(0, 0, W, H), fill((255, 160, 80), 22))


# ------------------------------------------------------------------ kinetic type
def slam_words(cv, t, t0, words, x, y, size, each=BEAT, colors=None, anchor="l", tracking=0):
    """Words slam in one per beat: scale overshoot + blur-in."""
    f = font("bold", size)
    cx = x
    widths = [f.measureText(w) for w in words]
    total = sum(widths) + f.measureText(" ") * (len(words) - 1)
    if anchor == "c":
        cx = x - total / 2
    for i, w in enumerate(words):
        k = (t - t0 - i * each) / 0.28
        if k > 0:
            s = lerp(1.9, 1.0, eoe(k))
            a = 255 * clamp(k * 2.5)
            col = (colors[i] if colors else WHITE)
            cv.save()
            cv.translate(cx + widths[i] / 2, y - size * 0.35)
            cv.scale(s, s)
            cv.drawString(w, -widths[i] / 2 + 3, size * 0.35 + 5, f, fill((0, 0, 0), a * 0.6, blur=8))
            cv.drawString(w, -widths[i] / 2, size * 0.35, f, fill(col, a))
            cv.restore()
        cx += widths[i] + f.measureText(" ")


def mask_reveal(cv, t, t0, s, x, y, size, col=WHITE, dur=0.5, k_out=1.0):
    f = font("bold", size)
    w = f.measureText(s)
    k = eoe((t - t0) / dur)
    if k <= 0:
        return
    cv.save()
    cv.clipRect(skia.Rect(x - 10, y - size * 1.1, x + w + 10, y + size * 0.35))
    off = (1 - k) * size * 1.2
    cv.drawString(s, x + 3, y + off + 4, f, fill((0, 0, 0), 150 * k_out, blur=7))
    cv.drawString(s, x, y + off, f, fill(col, 255 * k_out))
    cv.restore()


def typewriter(cv, t, t0, s, x, y, size, col=WHITE, cps=26, anchor="c"):
    n = int(clamp((t - t0) * cps, 0, len(s)))
    if n <= 0:
        return
    f = font("bold", size)
    full = f.measureText(s)
    sx = x - full / 2 if anchor == "c" else x
    sub = s[:n]
    cv.drawString(sub, sx + 3, y + 4, f, fill((0, 0, 0), 150, blur=7))
    cv.drawString(sub, sx, y, f, fill(col))
    if n < len(s) or int(t * 3) % 2 == 0:
        cx = sx + f.measureText(sub) + 6
        cv.drawRect(skia.Rect(cx, y - size * 0.8, cx + 6, y + 8), fill(YEL))


def chip(cv, t, t0, label, x, y, size=36, icon=None, t_out=99):
    k = (t - t0) / 0.4
    ko = 1 - ease((t - t_out) / 0.25)
    if k <= 0 or ko <= 0:
        return
    f = font("bold", size)
    w = f.measureText(label) + 70
    h = size * 1.9
    s = bout(k)
    cv.save()
    cv.translate(x, y)
    cv.scale(s, s)
    cv.drawRRect(rrect(4, -h / 2 + 8, w, h, 16), fill((0, 0, 0), 110 * ko, blur=12))
    cv.drawRRect(rrect(0, -h / 2, w, h, 16), fill((12, 18, 28), 215 * ko))
    cv.drawRect(skia.Rect(0, -h / 2, 8, h / 2), fill(YEL, 255 * ko))
    cv.drawString(label, 34, size * 0.36, f, fill(WHITE, 255 * ko))
    cv.restore()


# ------------------------------------------------------------------ product hero (perspective turn + reflection)
def hero_turn(cv, t, lt, dur, cx_frac=0.42):
    # studio background
    g = skia.Paint()
    g.setShader(skia.GradientShader.MakeRadial(skia.Point(W * 0.5, H * 0.45), W * 0.8,
                                               [C((28, 52, 86)), C((10, 18, 34)), C((4, 8, 14))], [0, 0.55, 1]))
    cv.drawRect(skia.Rect(0, 0, W, H), g)
    # floor glow + grid
    fl = skia.Paint()
    fl.setShader(skia.GradientShader.MakeRadial(skia.Point(W * 0.5, H * 0.86), 900, [C((80, 170, 230), 70), C((80, 170, 230), 0)]))
    cv.drawRect(skia.Rect(0, H * 0.6, W, H), fl)
    for i in range(-12, 13):
        cv.drawLine(W / 2 + i * 40, H * 0.66, W / 2 + i * 260, H, stroke((120, 180, 230), 1.5, 30))
    im = IM["hero_cut"]
    # crop the cut-out to the trolley's bounding box (precomputed lazily)
    bx = HERO_BOX
    k = ease(lt / dur)
    ang = math.radians(lerp(-16, 16, k))           # slow turn
    sc = lerp(0.95, 1.08, k)
    cx, cy = W * cx_frac, H * 0.54
    w, h = bx[2] - bx[0], bx[3] - bx[1]
    S = min(640 / h, 900 / w) * sc
    dw = w * S
    dh = h * S
    squeeze = math.cos(ang)
    lean = math.sin(ang) * 0.18
    src = [skia.Point(bx[0], bx[1]), skia.Point(bx[2], bx[1]), skia.Point(bx[2], bx[3]), skia.Point(bx[0], bx[3])]

    def quad(yflip=1, yoff=0.0):
        x0, x1 = cx - dw * squeeze / 2, cx + dw * squeeze / 2
        top = cy - dh / 2
        bot = cy + dh / 2
        l_up = dh * lean
        if yflip > 0:
            return [skia.Point(x0, top - l_up), skia.Point(x1, top + l_up), skia.Point(x1, bot + l_up * 0.2),
                    skia.Point(x0, bot - l_up * 0.2)]
        base = bot
        return [skia.Point(x0, base + dh - l_up * 0.2), skia.Point(x1, base + dh + l_up * 0.2),
                skia.Point(x1, base + l_up * 0.2), skia.Point(x0, base - l_up * 0.2)]

    # reflection
    m = skia.Matrix()
    m.setPolyToPoly(src, quad(-1))
    cv.saveLayer(None, None)
    cv.save()
    cv.concat(m)
    cv.drawImage(im, 0, 0, SAMP, skia.Paint(Alphaf=0.28))
    cv.restore()
    rp = skia.Paint()
    rp.setShader(skia.GradientShader.MakeLinear([skia.Point(0, cy + dh / 2), skia.Point(0, cy + dh * 0.95)],
                                                [C((0, 0, 0), 0), C((0, 0, 0), 255)]))
    rp.setBlendMode(skia.BlendMode.kDstOut)
    cv.drawRect(skia.Rect(0, cy + dh / 2, W, H), rp)
    cv.restore()
    # contact shadow + product
    cv.drawOval(skia.Rect(cx - dw * squeeze * 0.48, cy + dh * 0.44, cx + dw * squeeze * 0.48, cy + dh * 0.56),
                fill((0, 0, 0), 150, blur=26))
    m2 = skia.Matrix()
    m2.setPolyToPoly(src, quad(1))
    cv.save()
    cv.concat(m2)
    cv.drawImage(im, 0, 0, SAMP)
    cv.restore()
    # rim light sweep
    sx = lerp(cx - dw, cx + dw, ((lt * 0.45) % 1))
    sw = skia.Path()
    sw.moveTo(sx, cy - dh); sw.lineTo(sx + 70, cy - dh); sw.lineTo(sx - 90, cy + dh); sw.lineTo(sx - 160, cy + dh); sw.close()
    p = fill(WHITE, 40, blur=24)
    p.setBlendMode(skia.BlendMode.kScreen)
    cv.drawPath(sw, p)
    return cx, cy, dw * squeeze, dh


def _bbox(im):
    a = im.toarray()[:, :, 3]
    ys, xs = np.where(a > 40)
    return (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))


HERO_BOX = _bbox(IM["hero_cut"])


def counter_500(cv, t, t0, x, y):
    k = (t - t0) / 1.1
    if k <= 0:
        return
    v = int(500 * eoe(k))
    land = t - (t0 + 0.95)
    s = 1 + (0.18 * math.exp(-10 * land) if land > 0 else 0)
    f = font("bold", 230)
    sv = f"{v}"
    w = f.measureText(sv)
    cv.save()
    cv.translate(x, y)
    cv.scale(s, s)
    cv.drawString(sv, -w / 2 + 6, 10, f, fill((0, 0, 0), 150, blur=14))
    cv.drawString(sv, -w / 2, 0, f, fill(YEL))
    text(cv, "KG", w / 2 + 20, 0, "bold", 90, WHITE)
    cv.restore()
    text(cv, "LOAD CAPACITY", x, y + 80, "bold", 40, WHITE, 255 * clamp(k * 2), anchor="c", track=8)
    if 0 < land < 0.6:
        cv.drawCircle(x, y - 70, 160 + 520 * land, stroke(YEL, 8, 255 * (1 - land / 0.6)))


def spec_callout(cv, t, t0, ax, ay, lx, ly, label):
    k = (t - t0) / 0.6
    if k <= 0:
        return
    cv.drawCircle(ax, ay, 10, fill(YEL, 255 * clamp(k * 3)))
    cv.drawCircle(ax, ay, 18 + 6 * math.sin(t * 6), stroke(YEL, 3, 160 * clamp(k * 3)))
    p = skia.Path()
    p.moveTo(ax, ay)
    p.lineTo(lx, ly)
    pm = skia.PathMeasure(p, False)
    seg = skia.Path()
    pm.getSegment(0, pm.getLength() * eoe(k * 1.5), seg, True)
    cv.drawPath(seg, stroke(WHITE, 3, 220))
    wl = font("bold", 34).measureText(label) + 70
    x = lx + 8 if lx > ax else lx - 8 - wl
    x = max(70, min(W - 70 - wl, x))
    chip(cv, t, t0 + 0.3, label, x, ly, size=34)


# ------------------------------------------------------------------ whip transition (directional blur)
def whip_layer(cv, k, direction=1):
    """Call between saveLayer/restore: apply heavy horizontal blur for a whip."""
    sig = 60 * math.sin(clamp(k) * math.pi)
    p = skia.Paint()
    p.setImageFilter(skia.ImageFilters.Blur(max(0.1, sig), 0.1))
    return p


# ------------------------------------------------------------------ scenes
def s_problem(cv, t, lt, dur):
    dx, dy = shake(t, [0.0 + BEAT * i for i in (0, 2, 4, 6)], amp=5)
    cv.save()
    cv.translate(dx, dy)
    # heavy walk: fg bobs on each step
    bob = abs(math.sin(lt * math.pi / BEAT)) * 10
    k = ease(lt / dur)
    cover(cv, IM["manual_bg"], lerp(1.05, 1.12, k), 0.5, 0.5)
    light_beams(cv, t, origin=(W * 0.4, -120), a=46)
    cover(cv, IM["manual_fg"], lerp(1.06, 1.22, k), 0.5, 0.55, dy=-bob)
    cv.restore()
    grade_layer(cv, "cold")
    dust(cv, t, 1.0)
    vignette(cv, 170)
    slam_words(cv, t, 0.25, ["LIFTING", "HEAVY", "LOADS"], 110, 760, 96)
    slam_words(cv, t, 0.25 + BEAT * 3, ["BY", "HAND?"], 110, 880, 120, colors=[WHITE, RED])


def s_turn(cv, t, lt, dur):
    # freeze the last problem frame, desaturate, radial zoom, then the line
    k = ease(lt / dur)
    cv.saveLayer(None, None)
    cover(cv, IM["manual"], lerp(1.22, 1.45, k), 0.5, 0.55)
    gp = skia.Paint()
    gp.setColorFilter(skia.ColorFilters.Matrix([0.3, 0.59, 0.11, 0, 0, 0.3, 0.59, 0.11, 0, 0,
                                                0.3, 0.59, 0.11, 0, 0, 0, 0, 0, 1, 0]))
    cv.drawPaint(skia.Paint(Color=C((0, 0, 0), 0)))
    cv.restore()
    cv.saveLayer(None, gp)
    cover(cv, IM["manual"], lerp(1.22, 1.45, k), 0.5, 0.55)
    cv.restore()
    cv.drawRect(skia.Rect(0, 0, W, H), fill(NAVY, 170))
    typewriter(cv, t, T["turn"][0] + 0.1, "There's a smarter way.", W / 2, H / 2 + 30, 92, cps=30)


def speed_ramp(lt, dur, s0, s1, slow_at=0.8, slow=0.35):
    """Map local time to source time with a slow-mo zone near slow_at (fraction of the source move)."""
    # piecewise: fast to slow_at, slow afterwards
    n = 400
    xs = np.linspace(0, 1, n)
    speed = np.where(xs < slow_at, 1.0, slow)
    cum = np.cumsum(speed)
    cum = cum / cum[-1]
    u = np.interp(lt / dur, cum, xs)
    return lerp(s0, s1, u)


def s_reveal(cv, t, lt, dur):
    dx, dy = shake(t, [T["reveal"][0] + dur * 0.62], amp=14)
    src = speed_ramp(lt, dur, 0.0, 2.75, slow_at=0.7, slow=0.3)
    cv.save()
    cv.translate(dx, dy)
    cover(cv, footage(src), lerp(1.18, 1.06, ease(lt / dur)), 0.5, 0.62)
    cv.restore()
    vignette(cv, 120)
    flash(cv, t, T["reveal"][0] + dur * 0.62, 0.3, 230)
    light_leak(cv, t, T["reveal"][0] + dur * 0.55, 1.0)
    k0 = T["reveal"][0] + dur * 0.62
    mask_reveal(cv, t, k0 + 0.05, "BUILDINGSHOP", 112, 820, 34, YEL)
    mask_reveal(cv, t, k0 + 0.15, "Folding Platform", 110, 920, 96)
    mask_reveal(cv, t, k0 + 0.3, "Trolley", 110, 1015, 96, YEL)


def s_hero(cv, t, lt, dur):
    cx, cy, dw, dh = hero_turn(cv, t, lt, dur)
    dust(cv, t, 0.4, (180, 220, 255))
    t0 = T["hero"][0]
    spec_callout(cv, t, t0 + 0.5, cx + dw * 0.33, cy - dh * 0.32, cx + dw * 0.55 + 120, cy - dh * 0.42, "Folding steel handle")
    spec_callout(cv, t, t0 + 0.5 + BEAT * 2, cx - dw * 0.1, cy + dh * 0.05, cx - dw * 0.55 - 40, cy - dh * 0.1, "Wide, flat platform")
    spec_callout(cv, t, t0 + 0.5 + BEAT * 4, cx + dw * 0.2, cy + dh * 0.42, cx + dw * 0.55 + 120, cy + dh * 0.42, "Smooth-rolling wheels")
    # 500 kg slam on the 3rd bar
    tk = t0 + bars(2)
    if t >= tk - 0.05:
        dim = ease((t - tk) / 0.3)
        cv.drawRect(skia.Rect(0, 0, W, H), fill(NAVY, 150 * dim))
        counter_500(cv, t, tk, W * 0.62, H * 0.52)


def s_load(cv, t, lt, dur):
    parallax(cv, "load", lt, dur, z_bg=(1.03, 1.08), z_fg=(1.04, 1.14), pan=(20, -20), fg_pan=(-50, 50), fx=0.45)
    grade_layer(cv, "warm")
    dust(cv, t, 0.7)
    vignette(cv, 120)
    chip(cv, t, T["load"][0] + 0.3, "UP TO 500 KG", 110, 160, size=44)
    slam_words(cv, t, T["load"][0] + BEAT * 4, ["HEAVY", "LOADS.", "EASY", "MOVES."], 110, 990, 70,
               colors=[WHITE, WHITE, YEL, YEL], each=BEAT / 2)


def s_push(cv, t, lt, dur):
    # speed ramp: quick start, then real-time glide
    src = speed_ramp(lt, dur, 6.4, 11.8, slow_at=0.35, slow=0.55)
    cover(cv, footage(src), lerp(1.08, 1.0, ease(lt / dur)), 0.5, 0.6)
    vignette(cv, 120)
    # motion streaks along the floor
    for i in range(14):
        y = 860 + (i * 37) % 200
        x = (W - ((t * 900 + i * 260) % (W + 400)))
        cv.drawLine(x, y, x + 180, y, stroke(WHITE, 3, 50))
    slam_words(cv, t, T["push"][0] + 0.2, ["ONE", "PUSH."], 110, 200, 100, each=BEAT)
    slam_words(cv, t, T["push"][0] + 0.2 + BEAT * 3, ["LESS", "EFFORT."], 110, 320, 100, colors=[YEL, YEL], each=BEAT)


def s_fold(cv, t, lt, dur):
    half = dur * 0.5
    if lt < half:
        src = speed_ramp(lt, half, 2.6, 0.05, slow_at=0.5, slow=0.5)
        cover(cv, footage(src), lerp(1.0, 1.12, ease(lt / half)), 0.5, 0.62)
        flash(cv, t, T["fold"][0] + half * 0.8, 0.2, 140)
        mask_reveal(cv, t, T["fold"][0] + 0.2, "FOLDS FLAT", 110, 200, 100)
    else:
        l2 = lt - half
        parallax(cv, "folded", l2, half, z_bg=(1.10, 1.03), z_fg=(1.12, 1.04), pan=(-30, 10), fg_pan=(-60, 20), fx=0.6)
        grade_layer(cv, "warm")
        # slim-profile measure graphic beside the folded trolley
        k = eoe((l2 - 0.2) / 0.6)
        if k > 0:
            x0 = 1300
            cv.drawLine(x0, 300, x0, 300 + 520 * k, stroke(YEL, 6))
            for yy in (300, 300 + 520 * k):
                cv.drawLine(x0 - 22, yy, x0 + 22, yy, stroke(YEL, 6))
        mask_reveal(cv, t, T["fold"][0] + half + 0.2, "STORES IN", 110, 200, 90)
        mask_reveal(cv, t, T["fold"][0] + half + 0.35, "ANY CORNER", 110, 300, 90, YEL)
    vignette(cv, 120)


USES = [("shop", "SHOPS & GODOWNS"), ("home", "HOME SHIFTING"), ("load", "WAREHOUSES")]


def s_uses(cv, t, lt, dur):
    seg = dur / 3
    i = min(2, int(lt // seg))
    l2 = lt - i * seg
    key, label = USES[i]
    parallax(cv, key, l2, seg, z_bg=(1.12, 1.04), z_fg=(1.16, 1.05), pan=(40, -40), fg_pan=(90, -60),
             fx=[0.4, 0.6, 0.45][i])
    grade_layer(cv, "warm")
    vignette(cv, 120)
    mask_reveal(cv, t, T["uses"][0] + i * seg + 0.15, label, 110, 990, 84)
    # beat counter dots
    for j in range(3):
        cv.drawCircle(120 + j * 34, 1040, 8, fill(YEL if j == i else WHITE, 230))


def s_end(cv, t, lt, dur):
    cx, cy, dw, dh = hero_turn(cv, t, lt * 0.6 + 2.5, dur, cx_frac=0.33)
    cv.drawRect(skia.Rect(0, 0, W, H), fill(NAVY, 60))
    g = skia.Paint()
    g.setShader(skia.GradientShader.MakeLinear([skia.Point(W * 0.55, 0), skia.Point(W, 0)],
                                               [C(NAVY, 0), C(NAVY, 235)]))
    cv.drawRect(skia.Rect(0, 0, W, H), g)
    t0 = T["end"][0]
    x = 1180
    mask_reveal(cv, t, t0 + 0.2, "BUILDINGSHOP", x, 330, 36, YEL)
    mask_reveal(cv, t, t0 + 0.3, "Folding Platform", x, 425, 72)
    mask_reveal(cv, t, t0 + 0.45, "Trolley", x, 505, 72, YEL)
    chip(cv, t, t0 + 0.9, "Up to 500 kg load", x, 620, 34)
    chip(cv, t, t0 + 0.9 + BEAT, "Folding steel handle", x, 715, 34)
    chip(cv, t, t0 + 0.9 + BEAT * 2, "Easy to push & store", x, 810, 34)
    light_leak(cv, t, t0 + 0.1, 1.2, (90, 170, 255))


SCENES = [("problem", s_problem), ("turn", s_turn), ("reveal", s_reveal), ("hero", s_hero), ("load", s_load),
          ("push", s_push), ("fold", s_fold), ("uses", s_uses), ("end", s_end)]
WHIPS = {"load", "push", "fold", "uses", "end"}  # scenes entered with a whip pan


def render_frame(t, arr):
    cv = skia.Surface(arr).getCanvas()
    cv.clear(skia.ColorBLACK)
    for i, (name, fn) in enumerate(SCENES):
        a, b = T[name]
        if a <= t < b or (i == len(SCENES) - 1 and t >= a):
            lt = t - a
            wk = lt / 0.22
            if name in WHIPS and wk < 1:
                cv.saveLayer(None, whip_layer(cv, wk))
                cv.translate((1 - eoe(wk)) * 260, 0)
                fn(cv, t, lt, b - a)
                cv.restore()
            else:
                fn(cv, t, lt, b - a)
            # outgoing whip blur on the last 0.12 s
            ok = (b - t) / 0.12
            if i + 1 < len(SCENES) and SCENES[i + 1][0] in WHIPS and ok < 1:
                cv.drawRect(skia.Rect(0, 0, W, H), fill(WHITE, 40 * (1 - ok)))
            break
    D.film(cv, t)
    if t < 0.2:
        cv.drawRect(skia.Rect(0, 0, W, H), fill((0, 0, 0), 255 * (1 - t / 0.2)))
    if t > DUR - 0.7:
        cv.drawRect(skia.Rect(0, 0, W, H), fill((0, 0, 0), 255 * ease((t - (DUR - 0.7)) / 0.7)))
    return arr


# ------------------------------------------------------------------ music: 123 BPM energetic corporate/EDM (original)
def music(n):
    out = np.zeros(n)
    rng = np.random.default_rng(1)

    def add(sig, t0, g=1.0):
        i0 = int(t0 * SR)
        L = min(len(sig), n - i0)
        if L > 0 and i0 >= 0:
            out[i0:i0 + L] += sig[:L] * g

    def env(L, a, r):
        e = np.ones(L)
        ai, ri = max(1, int(a * SR)), max(1, int(r * SR))
        e[:ai] = np.linspace(0, 1, ai)
        e[-ri:] *= np.linspace(1, 0, ri)
        return e

    def note(m):
        return 440 * 2 ** ((m - 69) / 12)

    def saw(f, dur, det=(-0.12, 0, 0.12)):
        L = int(dur * SR)
        x = np.arange(L) / SR
        s = sum(2 * ((x * f * 2 ** (d / 12)) % 1) - 1 for d in det) / len(det)
        # simple one-pole low-pass for warmth
        y = np.empty_like(s)
        acc = 0.0
        a = 0.18
        for i in range(0, L, 64):  # vectorised-ish smoothing per block
            blk = s[i:i + 64]
            yb = np.empty_like(blk)
            for j, v in enumerate(blk):
                acc += a * (v - acc)
                yb[j] = acc
            y[i:i + 64] = yb
        return y

    def kick():
        L = int(0.35 * SR)
        x = np.arange(L) / SR
        return np.sin(2 * np.pi * (48 + 120 * np.exp(-x * 35)) * x) * np.exp(-x * 7)

    def clap():
        L = int(0.22 * SR)
        x = np.arange(L) / SR
        s = rng.normal(0, 1, L)
        s = s - np.convolve(s, np.ones(6) / 6, "same")
        e = np.exp(-x * 22) * (1 + 0.6 * (np.sin(2 * np.pi * 90 * x) > 0))
        return s * e * 0.5

    def hat(open_=False):
        L = int((0.18 if open_ else 0.05) * SR)
        x = np.arange(L) / SR
        s = rng.normal(0, 1, L)
        s = s - np.convolve(s, np.ones(3) / 3, "same")
        return s * np.exp(-x * (18 if open_ else 70)) * 0.35

    prog = [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]]  # Am F C G
    drop = T["reveal"][0] + (T["reveal"][1] - T["reveal"][0]) * 0.62
    t_end = DUR
    # chord stabs + pads
    t0, ci = 0.0, 0
    while t0 < t_end:
        c = prog[ci % 4]
        energy = 0.35 if t0 < T["turn"][0] else (0.15 if t0 < drop else 1.0)
        for m in c:  # pad
            L = int(BAR * SR)
            x = np.arange(L) / SR
            p = sum(np.sin(2 * np.pi * note(m) * x * 2 ** (d / 1200)) for d in (-8, 0, 8)) / 3
            add(p * env(L, 0.2, 0.3) * 0.05, t0)
        for k in range(8):
            tb = t0 + k * BEAT / 2
            if energy > 0.5 and k % 2 == 1:   # offbeat supersaw stab
                for m in c:
                    s = saw(note(m + 12), 0.16)
                    add(s * env(len(s), 0.005, 0.1) * 0.06, tb)
            if energy > 0.2 and k % 2 == 0:   # pluck arp
                m = c[(k // 2) % 3] + 24
                L = int(0.3 * SR)
                x = np.arange(L) / SR
                add((np.sin(2 * np.pi * note(m) * x) + 0.3 * np.sin(4 * np.pi * note(m) * x)) * np.exp(-x * 12) * 0.05 * energy, tb)
        # bass (sidechained feel)
        if t0 >= drop - 0.01 or t0 < T["turn"][0]:
            for k in range(4):
                L = int(BEAT * SR)
                x = np.arange(L) / SR
                b = np.sin(2 * np.pi * note(c[0] - 24) * x) + 0.4 * np.sin(4 * np.pi * note(c[0] - 24) * x)
                duck = np.minimum(1, x / (BEAT * 0.45)) ** 1.5
                add(b * duck * 0.18 * (1 if t0 >= drop else 0.6), t0 + k * BEAT)
        # drums
        for k in range(4):
            tb = t0 + k * BEAT
            if t0 >= drop - 0.01:
                add(kick(), tb, 0.55)
                if k % 2 == 1:
                    add(clap(), tb, 0.5)
                add(hat(True), tb + BEAT / 2, 0.5)
                add(hat(), tb + BEAT / 4, 0.4)
                add(hat(), tb + 3 * BEAT / 4, 0.4)
            elif t0 < T["turn"][0]:
                add(kick(), tb, 0.35)          # heavy heartbeat-like pulse in the problem section
        t0 += BAR
        ci += 1
    # riser into the drop (noise sweep + rising tone)
    rs, re_ = T["turn"][0], drop
    L = int((re_ - rs) * SR)
    x = np.arange(L) / SR
    sweep = np.convolve(rng.normal(0, 1, L), np.ones(8) / 8, "same") * (x / x[-1]) ** 2 * 0.25
    tone = np.sin(2 * np.pi * (200 * x + 600 * x ** 2 / (2 * x[-1]))) * (x / x[-1]) ** 2 * 0.08
    add(sweep + tone, rs)
    # impacts
    def boom():
        L = int(1.6 * SR)
        x = np.arange(L) / SR
        return (np.sin(2 * np.pi * (40 + 70 * np.exp(-x * 10)) * x) + 0.25 * rng.normal(0, 1, L) * np.exp(-x * 18)) * np.exp(-x * 3)
    add(boom(), drop, 0.8)
    add(boom(), T["hero"][0] + bars(2) + 0.95, 0.7)
    add(boom(), T["end"][0], 0.6)
    # reverb + master
    for d, g in ((0.09, 0.22), (0.15, 0.14), (0.23, 0.08)):
        k = int(d * SR)
        out[k:] += g * out[:-k]
    fl = int(1.0 * SR)
    out[-fl:] *= np.linspace(1, 0, fl)
    return out / (np.max(np.abs(out)) + 1e-9)


def sfx(n):
    out = np.zeros(n)
    rng = np.random.default_rng(4)

    def put(t0, sig, g=1.0):
        i0 = int(t0 * SR)
        L = min(len(sig), n - i0)
        if i0 >= 0 and L > 0:
            out[i0:i0 + L] += sig[:L] * g

    def whoosh(d=0.4):
        L = int(d * SR)
        x = np.arange(L) / SR
        return np.convolve(rng.normal(0, 1, L), np.ones(14) / 14, "same") * np.sin(np.pi * x / x[-1]) ** 2 * 0.35

    def click():
        L = int(0.08 * SR)
        x = np.arange(L) / SR
        return (np.sin(2 * np.pi * 2600 * x) * 0.6 + rng.normal(0, 1, L) * 0.4) * np.exp(-x * 80)

    def thud():
        L = int(0.4 * SR)
        x = np.arange(L) / SR
        return np.sin(2 * np.pi * (60 + 40 * np.exp(-x * 20)) * x) * np.exp(-x * 12)

    def tick():
        L = int(0.025 * SR)
        x = np.arange(L) / SR
        return np.sin(2 * np.pi * 3200 * x) * np.exp(-x * 200)

    def roll(d):
        L = int(d * SR)
        x = np.arange(L) / SR
        s = np.convolve(rng.normal(0, 1, L), np.ones(70) / 70, "same") * (1 + 0.5 * np.sin(2 * np.pi * 11 * x))
        return s * np.minimum(1, x / 0.3) * np.minimum(1, (d - x) / 0.4) * 0.5

    for name in WHIPS:
        put(T[name][0] - 0.2, whoosh())
    for i in range(5):                                 # heavy footsteps in the problem shot
        put(i * BEAT * 2 + 0.05, thud(), 0.35)
    for i in range(22):                                # typewriter
        put(T["turn"][0] + 0.1 + i / 30, tick(), 0.3)
    drop = T["reveal"][0] + (T["reveal"][1] - T["reveal"][0]) * 0.62
    put(drop - 0.02, click(), 0.8)                     # handle locks on the drop
    tk = T["hero"][0] + bars(2)
    for i in range(18):                                # counter ticks
        put(tk + i * 0.05, tick(), 0.25)
    put(T["push"][0], roll(bars(2)), 0.6)
    put(T["fold"][0] + (T["fold"][1] - T["fold"][0]) * 0.4, click(), 0.6)
    return out


def build_audio(path, vo_path=None):
    n = int(DUR * SR)
    mus = music(n) * 0.5
    fx = sfx(n)
    mix = mus + fx
    if vo_path:
        raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", vo_path, "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
                             capture_output=True, check=True).stdout
        vo = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
        vo = np.pad(vo, (int(0.3 * SR), 0))[:n]
        vo = np.pad(vo, (0, n - len(vo)))
        h = SR // 100
        m = n // h
        e = np.sqrt(np.mean(vo[:m * h].reshape(m, h) ** 2, 1))
        e = np.convolve((e > 0.01).astype(float), np.ones(25) / 25, "same")
        duck = np.pad(1 - 0.6 * np.repeat(e, h), (0, n - m * h), constant_values=1)
        mix = mus * duck + fx + vo / (np.max(np.abs(vo)) + 1e-9) * 0.9
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
    print("DUR", DUR, {k: (round(a, 2), round(b, 2)) for k, (a, b) in T.items()})
    if "--stills" in sys.argv:
        pts = []
        for k, (a, b) in T.items():
            pts += [a + (b - a) * 0.3, a + (b - a) * 0.8]
        for t in pts:
            render_frame(t, arr)
            skia.Image.fromarray(arr, colorType=skia.kRGBA_8888_ColorType).save(os.path.join(OUT, f"v2_{t:05.2f}.png"), skia.kPNG)
        return
    vo = sys.argv[sys.argv.index("--vo") + 1] if "--vo" in sys.argv else None
    tag = "_vo" if vo else ""
    wav = os.path.join(OUT, f"trolley_v2{tag}.wav")
    build_audio(wav, vo)
    dst = os.path.join(OUT, f"buildingshop_folding_trolley_amazon_16x9_v2{tag}.mp4")
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
