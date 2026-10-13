"""Chhat Se Breaking News — BuildingShop 145 GSM fiberglass mesh reel (Director #5: The Newsroom).

9:16 1080x1920 30fps. Semi-real filmic plates (textured plaster, rain, DOF, grain) + broadcast motion graphics
(breaking banner, LIVE bug, ticker, lower-thirds, split screens, cross-section diagrams) + cel-shaded characters.
Real ElevenLabs VO (vo/*.mp3, split by vo_split.py); long in-line pauses are trimmed to keep the reel <= 45 s.
Signature BuildingShop yellow wavy frame on top.

usage: python3 reel_mesh.py [--stills]
"""
import json, math, os, random, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "sticky-traps"))
import numpy as np
import skia
import reel as K  # shared kit: paints, text, characters, film look, border, wav writer
from reel import (C, fill, stroke, lin, rad, rrect, text, font, ease, eout, bout, clamp, lerp, mix, shade, hexc,
                  blur_layer, bokeh, film_finish, draw_person, draw_hand, draw_leaf, write_wav)

W, H, FPS = 1080, 1920, 30
SR = 48000
OUT = os.path.join(HERE, "out")
RED = hexc("#D7262E")
NAVY = hexc("#0E1A2B")
YEL = (255, 214, 0)
MESH_WHITE = (238, 240, 236)

# ------------------------------------------------------------------ cast
ANCHOR = dict(skin=hexc("#C99067"), skin_sh=hexc("#A66E4A"), hair=hexc("#1A1210"), hair_hi=hexc("#5B3B2B"),
              top=hexc("#1F2F57"), top_sh=hexc("#141F3C"), trim=hexc("#E8E2D0"), dupatta=hexc("#C8102E"),
              bottom=hexc("#1F2F57"), lips=hexc("#A2403E"), kind="f")
REPORTER = dict(skin=hexc("#BE845A"), skin_sh=hexc("#9B6340"), hair=hexc("#20140F"), hair_hi=hexc("#62402C"),
                top=hexc("#C62828"), top_sh=hexc("#8E1B1B"), trim=hexc("#F4D35E"), dupatta=hexc("#222222"),
                bottom=hexc("#2B2B33"), lips=hexc("#9A3B36"), kind="f")
MISTRI = dict(skin=hexc("#8E5A3A"), skin_sh=hexc("#6E4229"), hair=hexc("#2A221E"), hair_hi=hexc("#5E544E"),
              top=hexc("#5B7A99"), top_sh=hexc("#435C75"), trim=hexc("#F28C1B"), dupatta=hexc("#F28C1B"),
              bottom=hexc("#3C3F46"), lips=hexc("#6E3B2C"), turban=hexc("#F7C531"), turban_sh=hexc("#C99A16"),
              helmet=True, kind="m")

# ------------------------------------------------------------------ VO timeline
VO_FILES = {"ANCHOR": "vo/devi.mp3", "REPORTER": "vo/anika.mp3", "MISTRI-JI": "vo/ravikant.mp3"}
SEG = json.load(open(os.path.join(HERE, "vo", "segments.json")))
SEG["MISTRI-JI"] = SEG.pop("MISTRI")
ORDER = [  # speaker, line idx, caption, gap before
    ("ANCHOR", 0, "Breaking news! Baarish ke baad shehar ki har doosri chhat se tapak raha hai paani!", 0.12),
    ("ANCHOR", 1, "Chaliye seedhe chalte hain hamare reporter ke paas!", 0.15),
    ("REPORTER", 0, "Ji, main is waqt ek terrace par hoon… dekhiye ye cracks!", 0.15),
    ("REPORTER", 1, "Har saal waterproofing, phir bhi leakage wapas!", 0.12),
    ("ANCHOR", 2, "Toh aakhir galti kahan ho rahi hai?", 0.12),
    ("MISTRI-JI", 0, "Galti ye hai ki sirf coating lagate ho… usko pakadne wala kuch nahi!", 0.12),
    ("REPORTER", 2, "Aur ye hai BuildingShop ka fiberglass mesh! 145 GSM, 24 inch chauda, 50 meter roll!", 0.15),
    ("MISTRI-JI", 1, "Pehli coat lagao, mesh bichhao, dabao… phir doosri coat!", 0.12),
    ("MISTRI-JI", 2, "Coating mazboot rehti hai, crack ke upar bhi pakad bani rehti hai!", 0.12),
    ("REPORTER", 3, "Terrace, deewar ke cracks, plaster… sab jagah kaam aata hai!", 0.12),
    ("ANCHOR", 3, "Toh is monsoon… leakage ki nahi, sirf mausam ki khabar!", 0.15),
]
MAX_PAUSE = 0.28   # in-line pauses longer than this are trimmed
TAIL = 1.4

LINES, CLIPS, WORDS, RUNS = [], [], [], []   # CLIPS: (global_start, speaker, src_a, src_b) per voiced run
_t = 0.0
for sp, idx, txt, gap in ORDER:
    seg = SEG[sp][idx]
    _t += gap
    g0 = _t
    gr = []
    cur = g0
    for k, (ra, rb) in enumerate(seg["runs"]):
        if k > 0:
            cur += min(MAX_PAUSE, ra - seg["runs"][k - 1][1])
        CLIPS.append((cur, sp, ra - 0.02, rb + 0.04))
        gr.append((cur, cur + rb - ra))
        cur += rb - ra
    LINES.append((g0, cur, sp, txt))
    RUNS.append(gr)
    tot = sum(b - a for a, b in gr)
    words = txt.split()
    lens = [max(1, len(w.strip(".,!?…"))) for w in words]

    def at(frac, gr=gr, tot=tot):
        s = frac * tot
        for a, b in gr:
            if s <= b - a:
                return a + s
            s -= b - a
        return gr[-1][1]
    acc, wl = 0, []
    for w, Lw in zip(words, lens):
        f0 = acc / sum(lens)
        acc += Lw
        wl.append((at(f0), at(acc / sum(lens)), w))
    WORDS.append(wl)
    _t = cur
DUR = round(_t + TAIL, 2)


def L(i):
    return LINES[i][0]


def LE(i):
    return LINES[i][1]


def WT(i, needle):
    for a, b, w in WORDS[i]:
        if needle.lower() in w.lower():
            return a
    return L(i)


SCENES = [(0.0, L(1) - 0.06, "breaking"), (L(1) - 0.06, L(2) - 0.06, "studio"),
          (L(2) - 0.06, L(4) - 0.06, "rooftop"), (L(4) - 0.06, L(5) - 0.06, "split"),
          (L(5) - 0.06, L(6) - 0.06, "mistri_why"), (L(6) - 0.06, L(7) - 0.06, "product"),
          (L(7) - 0.06, L(8) - 0.06, "howto"), (L(8) - 0.06, L(9) - 0.06, "crack_test"),
          (L(9) - 0.06, L(10) - 0.06, "uses"), (L(10) - 0.06, DUR, "signoff")]

# ------------------------------------------------------------------ VO track + lip-sync envelopes
_ENV = {}


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
        f = int(0.008 * SR)
        clip[:f] *= np.linspace(0, 1, f)
        clip[-f:] *= np.linspace(1, 0, f)
        i0 = int((g0 - 0.02) * SR)
        Ln = min(len(clip), n - i0)
        vo[i0:i0 + Ln] += clip[:Ln]
        per[sp][i0:i0 + Ln] += clip[:Ln]
    for sp, x in per.items():
        h = SR // 100
        m = len(x) // h
        e = np.sqrt(np.mean(x[:m * h].reshape(m, h) ** 2, 1))
        e = np.convolve(e, np.ones(4) / 4, "same")
        e = np.clip((e / (np.percentile(e[e > 1e-4], 95) + 1e-9)) ** 0.8, 0, 1)
        _ENV[sp] = e
    return vo


def talk(t, sp):
    e = _ENV.get(sp)
    i = int(t * 100)
    return float(e[i]) if e is not None and 0 <= i < len(e) else 0.0


VO = build_vo()

# ------------------------------------------------------------------ textures / realism helpers
_rng = np.random.default_rng(11)


def _noise_img(w, h, base, var, seed):
    r = np.random.default_rng(seed)
    n = r.normal(0, 1, (h // 4, w // 4))
    n = np.kron(n, np.ones((4, 4)))[:h, :w]
    n2 = r.normal(0, 1, (h, w)) * 0.35
    v = (n * 0.65 + n2) * var
    a = np.clip(np.dstack([base[0] + v, base[1] + v * 0.95, base[2] + v * 0.9, np.full_like(v, 255)]), 0, 255)
    return skia.Image.fromarray(np.ascontiguousarray(a.astype(np.uint8)), colorType=skia.kRGBA_8888_ColorType)


PLASTER = _noise_img(1080, 1920, (226, 220, 206), 7, 1)
CONCRETE = _noise_img(1080, 1920, (150, 146, 138), 12, 2)


def tex(cv, img, rect, alpha=255):
    p = skia.Paint(Alphaf=alpha / 255)
    cv.drawImageRect(img, rect, skia.SamplingOptions(skia.FilterMode.kLinear), p)


def cam(cv, z, cx=W / 2, cy=H / 2, dx=0, dy=0):
    cv.save()
    cv.translate(cx + dx, cy + dy)
    cv.scale(z, z)
    cv.translate(-cx, -cy)


def rain(cv, t, n=160, seed=3, a=110, slant=0.18, speed=2400, length=60):
    rnd = random.Random(seed)
    p = stroke((220, 230, 240), 2.2, a)
    for i in range(n):
        x0 = rnd.uniform(-200, W + 100)
        y0 = rnd.uniform(0, H)
        sp = speed * rnd.uniform(0.8, 1.2)
        y = (y0 + t * sp) % (H + 200) - 100
        x = x0 + y * slant
        Ln = length * rnd.uniform(0.6, 1.3)
        cv.drawLine(x, y, x + Ln * slant, y + Ln, p)


def ripples(cv, t, box, n=18, seed=5):
    rnd = random.Random(seed)
    x0, y0, x1, y1 = box
    for i in range(n):
        ph = rnd.random()
        x, y = rnd.uniform(x0, x1), rnd.uniform(y0, y1)
        k = (t * 1.6 + ph) % 1
        r = 6 + 34 * k
        cv.drawOval(skia.Rect(x - r, y - r * 0.35, x + r, y + r * 0.35), stroke((220, 230, 240), 2, 120 * (1 - k)))


def drip(cv, x, y_top, y_bot, t, period=0.9, ph=0.0, scale=1.0):
    """Water droplet forming at y_top, falling to y_bot, splash."""
    k = ((t + ph) % period) / period
    if k < 0.35:  # forming
        r = 6 + 6 * (k / 0.35)
        cv.drawOval(skia.Rect(x - r * scale, y_top, x + r * scale, y_top + r * 2.2 * scale),
                    lin((x, y_top), (x, y_top + r * 2), [((200, 220, 235), 220), ((120, 150, 175), 220)]))
    elif k < 0.8:
        f = (k - 0.35) / 0.45
        y = lerp(y_top, y_bot, f * f)
        cv.drawOval(skia.Rect(x - 8 * scale, y, x + 8 * scale, y + 20 * scale), fill((190, 215, 235), 230))
    else:
        f = (k - 0.8) / 0.2
        for s in (-1, 1):
            cv.drawCircle(x + s * 30 * f * scale, y_bot - 20 * math.sin(f * math.pi) * scale, 4 * scale,
                          fill((200, 220, 240), 200 * (1 - f)))
        cv.drawOval(skia.Rect(x - 40 * f * scale, y_bot - 6, x + 40 * f * scale, y_bot + 6),
                    stroke((200, 220, 240), 2, 200 * (1 - f)))


def crack_path(x0, y0, x1, y1, seed, rough=24, branches=2):
    rnd = random.Random(seed)
    p = skia.Path()
    n = 14
    pts = []
    for i in range(n + 1):
        f = i / n
        pts.append((lerp(x0, x1, f) + (rnd.uniform(-rough, rough) if 0 < i < n else 0),
                    lerp(y0, y1, f) + (rnd.uniform(-rough, rough) if 0 < i < n else 0)))
    p.moveTo(*pts[0])
    for q in pts[1:]:
        p.lineTo(*q)
    for b in range(branches):
        i = rnd.randint(3, n - 3)
        bx, by = pts[i]
        p.moveTo(bx, by)
        ang = rnd.uniform(0, 6.28)
        for k in range(4):
            bx += math.cos(ang) * rough * 1.6
            by += math.sin(ang) * rough * 1.6
            ang += rnd.uniform(-0.6, 0.6)
            p.lineTo(bx, by)
    return p


def draw_crack(cv, path, k=1.0, w=5, col=(55, 50, 45), a=255):
    pm = skia.PathMeasure(path, False)
    seg = skia.Path()
    # draw the main contour progressively; branches appear once k>0.6
    total = 0
    cont = True
    while cont:
        Lc = pm.getLength()
        s = skia.Path()
        pm.getSegment(0, Lc * clamp(k), s, True)
        seg.addPath(s)
        cont = pm.nextContour()
    cv.drawPath(seg, stroke((255, 255, 255), w + 3, 60 * a / 255))
    cv.drawPath(seg, stroke(col, w, a))


def mesh_patch(cv, rect, cell=26, a=235, warp=0.0, t=0.0):
    """Fiberglass mesh: woven square grid of slightly glossy white strands."""
    x0, y0, x1, y1 = rect
    cv.save()
    cv.clipRect(skia.Rect(x0, y0, x1, y1))
    cv.drawRect(skia.Rect(x0, y0, x1, y1), fill(MESH_WHITE, 25 * a / 255))
    sp = stroke(MESH_WHITE, max(2.0, cell * 0.16), a)
    sh = stroke((150, 150, 145), max(1.0, cell * 0.08), 90 * a / 255)
    x = x0 - (x0 % cell)
    while x <= x1:
        wob = math.sin(x * 0.05 + t) * warp
        cv.drawLine(x + 2, y0, x + 2 + wob, y1, sh)
        cv.drawLine(x, y0, x + wob, y1, sp)
        x += cell
    y = y0 - (y0 % cell)
    while y <= y1:
        cv.drawLine(x0, y + 2, x1, y + 2, sh)
        cv.drawLine(x0, y, x1, y, sp)
        y += cell
    cv.restore()


def mesh_roll(cv, cx, cy, r, length, ang=0.0, a=255):
    """Side view of a roll: cylinder end + body (light grid texture)."""
    cv.save()
    cv.translate(cx, cy)
    cv.rotate(math.degrees(ang))
    body = skia.Rect(-length / 2, -r, length / 2, r)
    cv.drawRect(skia.Rect(-length / 2 + 10, r - 6, length / 2 + 10, r + 22), fill((0, 0, 0), 60, blur=14))
    cv.drawRect(body, lin((0, -r), (0, r), [(252, 252, 248), (205, 205, 198), (240, 240, 235)], [0, 0.6, 1]))
    mesh_patch(cv, (-length / 2, -r, length / 2, r), cell=16, a=120)
    cv.drawOval(skia.Rect(length / 2 - r * 0.45, -r, length / 2 + r * 0.45, r), fill((235, 235, 228)))
    for k in range(6):
        rr = r * (1 - k * 0.15)
        cv.drawOval(skia.Rect(length / 2 - rr * 0.45, -rr, length / 2 + rr * 0.45, rr), stroke((190, 190, 182), 2))
    cv.drawOval(skia.Rect(length / 2 - r * 0.12, -r * 0.25, length / 2 + r * 0.12, r * 0.25), fill((120, 110, 95)))
    cv.restore()


# ------------------------------------------------------------------ broadcast graphics
TICKER = ("  •  MONSOON ALERT: terrace leakage ki shikayatein badh rahi hain  •  Mistri-ji ki salah: coating ke beech "
          "fiberglass mesh  •  145 GSM  ·  24 inch  ·  50 m roll  •  Terrace · Deewar · Plaster  ")


def live_bug(cv, t, x=90, y=250):
    cv.drawRRect(rrect(x, y, 150, 54, 10), fill(RED))
    cv.drawCircle(x + 30, y + 27, 9, fill((255, 255, 255), 255 * (0.55 + 0.45 * math.sin(t * 6))))
    text(cv, "LIVE", x + 50, y + 41, "sans", 32, (255, 255, 255))


def channel_bug(cv, t):
    x, y = W - 300, 240
    cv.drawRRect(rrect(x, y, 210, 70, 12), fill(NAVY, 230))
    cv.drawRRect(rrect(x, y, 70, 70, 12), fill(RED))
    text(cv, "CL", x + 35, y + 48, "sans", 34, (255, 255, 255), anchor="c")
    text(cv, "CHHAT LIVE", x + 82, y + 46, "sans", 26, (255, 255, 255))


def ticker(cv, t):
    y = 1745
    cv.drawRect(skia.Rect(0, y, W, y + 64), fill(NAVY, 240))
    cv.drawRect(skia.Rect(0, y, 220, y + 64), fill(RED))
    text(cv, "NEWS", 110, y + 45, "sans", 32, (255, 255, 255), anchor="c")
    f = font("sans", 30)
    tw = f.measureText(TICKER)
    x = 230 - (t * 170) % tw
    cv.save()
    cv.clipRect(skia.Rect(220, y, W, y + 64))
    while x < W:
        cv.drawString(TICKER, x, y + 43, f, fill((255, 255, 255)))
        x += tw
    cv.restore()


def lower_third(cv, t, t0, title, sub, y=1170, col=RED, dur=99):
    k = clamp((t - t0) / 0.45)
    ko = 1 - ease((t - t0 - dur) / 0.3)
    if k <= 0 or ko <= 0:
        return
    w = 760 * eout(k)
    a = 255 * ko
    cv.save()
    cv.clipRect(skia.Rect(80, y - 80, 80 + w + 20, y + 70))
    cv.drawRect(skia.Rect(80, y - 70, 80 + 760, y), fill(col, a))
    cv.drawRect(skia.Rect(80, y, 80 + 640, y + 52), fill((255, 255, 255), a))
    text(cv, title, 105, y - 20, "sans", 44, (255, 255, 255), a)
    text(cv, sub, 105, y + 38, "sans", 28, NAVY, a)
    cv.restore()


def breaking_banner(cv, t, t0):
    k = (t - t0) / 0.5
    if k <= 0:
        return
    s = bout(k)
    shake = 8 * math.exp(-8 * max(0, t - t0 - 0.35)) * math.sin(t * 90)
    cv.save()
    cv.translate(W / 2 + shake, 400)
    cv.scale(s, s)
    cv.rotate(-3)
    cv.drawRect(skia.Rect(-470, -90, 470, 90), fill((0, 0, 0), 120, blur=20))
    cv.drawRect(skia.Rect(-470, -95, 470, 25), fill(RED))
    cv.drawRect(skia.Rect(-470, 25, 470, 95), fill((255, 255, 255)))
    text(cv, "BREAKING NEWS", 0, -8, "sans", 82, (255, 255, 255), anchor="c")
    text(cv, "Chhat se tapak raha hai paani!", 0, 74, "sans", 40, NAVY, anchor="c")
    # light sweep
    sx = lerp(-700, 700, ((t - t0) % 2.2) / 1.1)
    sw = skia.Path()
    sw.moveTo(sx, -95); sw.lineTo(sx + 50, -95); sw.lineTo(sx - 10, 95); sw.lineTo(sx - 60, 95); sw.close()
    cv.save()
    cv.clipRect(skia.Rect(-470, -95, 470, 95))
    cv.drawPath(sw, fill((255, 255, 255), 80, blur=6))
    cv.restore()
    cv.restore()


def spec_chip(cv, t, t0, label, x, y, col=YEL, size=46):
    k = (t - t0) / 0.4
    if k <= 0:
        return
    s = bout(k)
    f = font("sans", size)
    w = f.measureText(label) + 60
    h = size * 1.7
    cv.save()
    cv.translate(x + w / 2, y)
    cv.scale(s, s)
    cv.drawRRect(rrect(-w / 2 + 5, -h / 2 + 8, w, h, 16), fill((0, 0, 0), 90, blur=10))
    cv.drawRRect(rrect(-w / 2, -h / 2, w, h, 16), fill(col))
    cv.drawString(label, -w / 2 + 30, size * 0.35, f, fill(NAVY))
    cv.restore()


# ------------------------------------------------------------------ plates (semi-real)
def ceiling_plate(cv, t, stain=1.0):
    tex(cv, PLASTER, skia.Rect(0, 0, W, H))
    # cornice + shadow gradient (room light from below-left)
    cv.drawRect(skia.Rect(0, 0, W, H), lin((0, 0), (W, H), [((255, 250, 235), 30), ((0, 0, 0), 70)]))
    cv.drawRect(skia.Rect(0, 1150, W, 1190), fill((200, 194, 180)))
    cv.drawRect(skia.Rect(0, 1190, W, H), lin((0, 1190), (0, H), [(205, 198, 182), (165, 158, 142)]))
    # damp stain: layered blotches with tide-mark rings
    rnd = random.Random(4)
    for i in range(7):
        x, y = 540 + rnd.uniform(-160, 160), 520 + rnd.uniform(-120, 120)
        r = rnd.uniform(150, 260) * stain
        cv.drawCircle(x, y, r, fill((150, 120, 70), 46, blur=r * 0.25))
        cv.drawCircle(x, y, r * 0.98, stroke((120, 92, 55), 5, 60, ))
    cv.drawCircle(540, 520, 120 * stain, fill((95, 80, 60), 70, blur=30))
    # hairline crack through the stain
    draw_crack(cv, crack_path(300, 380, 820, 660, 9, rough=18, branches=3), 1.0, w=4, col=(70, 60, 50), a=210)
    # peeling paint flakes
    for i in range(6):
        x, y = 540 + rnd.uniform(-200, 200), 520 + rnd.uniform(-150, 150)
        p = skia.Path()
        p.moveTo(x, y); p.lineTo(x + 30, y + 6); p.lineTo(x + 18, y + 28); p.close()
        cv.drawPath(p, fill((240, 236, 225)))
        cv.drawPath(p, stroke((150, 140, 120), 2, 160))


def bucket(cv, x, y, t):
    cv.drawOval(skia.Rect(x - 150, y + 150, x + 150, y + 185), fill((0, 0, 0), 90, blur=12))
    b = skia.Path()
    b.moveTo(x - 140, y); b.lineTo(x + 140, y); b.lineTo(x + 110, y + 170); b.lineTo(x - 110, y + 170); b.close()
    cv.drawPath(b, lin((x - 140, 0), (x + 140, 0), [(40, 110, 200), (20, 70, 150)]))
    cv.drawOval(skia.Rect(x - 140, y - 22, x + 140, y + 22), fill((25, 80, 160)))
    cv.drawOval(skia.Rect(x - 124, y - 14, x + 124, y + 16), lin((0, y - 14), (0, y + 16), [(150, 190, 220), (90, 140, 190)]))
    k = (t * 1.1) % 1
    cv.drawOval(skia.Rect(x - 90 * k, y - 6 * k, x + 90 * k, y + 6 * k), stroke((230, 240, 250), 3, 200 * (1 - k)))


def studio_plate(cv, t):
    cv.drawRect(skia.Rect(0, 0, W, H), lin((0, 0), (0, H), [(16, 28, 54), (6, 10, 22)]))
    blur_layer(cv, 18)
    bokeh(cv, t, 7, 30, [(60, 120, 220), (200, 40, 60), (240, 240, 255)], 30, 90, 110)
    cv.restore()
    for i in range(6):  # light panels
        x = 60 + i * 175
        cv.drawRRect(rrect(x, 330, 120, 560, 14), lin((x, 330), (x, 890), [((90, 140, 230), 90), ((90, 140, 230), 10)]))
    cv.drawRect(skia.Rect(0, 1240, W, H), lin((0, 1240), (0, H), [(30, 38, 60), (10, 14, 26)]))
    # desk
    d = skia.Path()
    d.moveTo(-40, 1260); d.lineTo(W + 40, 1260); d.lineTo(W + 40, 1500); d.lineTo(-40, 1500); d.close()
    cv.drawPath(d, lin((0, 1260), (0, 1500), [(230, 235, 245), (150, 160, 180)]))
    cv.drawRect(skia.Rect(-40, 1252, W + 40, 1268), fill(RED))


def video_wall(cv, t, rect, content):
    x0, y0, x1, y1 = rect
    cv.drawRRect(rrect(x0 - 10, y0 - 10, x1 - x0 + 20, y1 - y0 + 20, 16), fill((0, 0, 0), 160, blur=14))
    cv.save()
    cv.clipRRect(rrect(x0, y0, x1 - x0, y1 - y0, 12), doAntiAlias=True)
    content(cv, t)
    cv.restore()
    cv.drawRRect(rrect(x0, y0, x1 - x0, y1 - y0, 12), stroke((120, 160, 230), 4, 200))


def terrace_plate(cv, t, wet=1.0, cracks=1.0, sky_dark=1.0, crack_k=1.0):
    top = mix((140, 160, 185), (95, 108, 128), sky_dark)
    cv.drawRect(skia.Rect(0, 0, W, 900), lin((0, 0), (0, 900), [top, mix(top, (200, 205, 210), 0.5)]))
    blur_layer(cv, 10)  # distant city in haze
    rnd = random.Random(2)
    x = -40
    while x < W + 40:
        w = rnd.uniform(90, 200); h = rnd.uniform(160, 420)
        cv.drawRect(skia.Rect(x, 820 - h, x + w, 820), fill(mix((120, 130, 145), top, 0.35)))
        x += w + rnd.uniform(5, 25)
    cv.restore()
    # parapet
    cv.drawRect(skia.Rect(0, 760, W, 900), fill((176, 170, 158)))
    cv.drawRect(skia.Rect(0, 748, W, 772), fill((150, 144, 132)))
    # roof slab in perspective with texture
    slab = skia.Path()
    slab.moveTo(-200, 900); slab.lineTo(W + 200, 900); slab.lineTo(W + 600, H); slab.lineTo(-600, H); slab.close()
    cv.save()
    cv.clipPath(slab, doAntiAlias=True)
    tex(cv, CONCRETE, skia.Rect(-200, 900, W + 200, H))
    cv.drawRect(skia.Rect(0, 900, W, H), lin((0, 900), (0, H), [((60, 70, 85), int(110 * wet)), ((20, 25, 35), int(60 * wet))]))
    # wet sheen
    cv.drawOval(skia.Rect(150, 1150, 950, 1500), fill((200, 215, 230), 40 * wet, blur=60))
    if cracks > 0:
        for i, (a, b) in enumerate([((180, 1000), (620, 1500)), ((560, 1100), (980, 1650)), ((90, 1450), (430, 1820))]):
            draw_crack(cv, crack_path(a[0], a[1], b[0], b[1], 20 + i, rough=30, branches=2), crack_k, w=7,
                       col=(40, 38, 36), a=int(255 * cracks))
    cv.restore()


def mistri_plate(cv, t):
    terrace_plate(cv, t, wet=0.4, cracks=1.0, sky_dark=0.3)


# ------------------------------------------------------------------ scenes
def sc_breaking(cv, lt, t):
    z = 1.0 + 0.08 * ease(lt / 5.5)
    cam(cv, z, cy=800)
    tex(cv, PLASTER, skia.Rect(0, -300, W, H))
    cv.save()
    cv.translate(0, 230)
    ceiling_plate(cv, t)
    cv.restore()
    for i, (x, ph) in enumerate([(540, 0.0), (470, 0.37), (610, 0.63)]):
        drip(cv, x, 770, 1110, t, period=1.1, ph=ph)
    bucket(cv, 540, 1100, t)
    cv.restore()
    breaking_banner(cv, t, 0.05)
    live_bug(cv, t)
    channel_bug(cv, t)


def anchor_shot(cv, t, wall_content, signoff=False):
    studio_plate(cv, t)
    video_wall(cv, t, (90, 330, 990, 840), wall_content)
    hands = draw_person(cv, 540, 2280, 245, t, ANCHOR, arm_l=(1.0, 0.9), arm_r=(0.25, 0.8),
                        talk=talk(t, "ANCHOR"), brow=(-0.2 if signoff else 0.5), look=(0.0 if signoff else -0.3),
                        curl_l=0.3, curl_r=0.5)
    # desk front over the body
    d = skia.Path()
    d.moveTo(-40, 1400); d.lineTo(W + 40, 1400); d.lineTo(W + 40, 1720); d.lineTo(-40, 1720); d.close()
    cv.drawPath(d, lin((0, 1400), (0, 1720), [(235, 238, 246), (160, 170, 190)]))
    cv.drawRect(skia.Rect(-40, 1392, W + 40, 1408), fill(RED))
    text(cv, "CHHAT LIVE", W / 2, 1600, "sans", 54, (170, 180, 200), 120, anchor="c")


def wall_rooftop(cv, t):
    cv.save()
    s = 900 / W
    cv.translate(90, 330 - 700 * s)
    cv.scale(s, s)
    terrace_plate(cv, t, wet=1.0)
    rain(cv, t, n=120, a=90)
    cv.restore()


def sc_studio(cv, lt, t):
    z = 1.04 - 0.04 * ease(lt / 2.4)
    cam(cv, z)
    anchor_shot(cv, t, wall_rooftop)
    cv.restore()
    lower_third(cv, t, L(1) + 0.1, "SHEHAR MEIN LEAKAGE", "Har doosri chhat se tapak raha paani", y=1200)
    live_bug(cv, t)
    channel_bug(cv, t)


def sc_rooftop(cv, lt, t):
    z = 1.0 + 0.05 * ease(lt / 6)
    crack_zoom = ease((t - WT(2, "cracks") + 0.1) / 0.5) * (1 - ease((t - L(3) + 0.3) / 0.4))
    cam(cv, z + 0.25 * crack_zoom, cy=1300, dx=-60 * crack_zoom)
    terrace_plate(cv, t, wet=1.0)
    ripples(cv, t, (80, 1000, 1000, 1700))
    cv.restore()
    # reporter (medium shot) under a dark sky, holding the mic
    hands = draw_person(cv, 330, 2150, 230, t, REPORTER, arm_l=(1.25, 1.15), arm_r=(0.2, 0.3),
                        talk=talk(t, "REPORTER"), brow=0.6, look=0.6, curl_l=0.8)
    hx, hy = hands[-1]
    cv.drawLine(hx, hy, hx + 30, hy - 110, stroke((30, 30, 30), 18))
    cv.drawCircle(hx + 34, hy - 128, 32, fill((40, 40, 40)))
    cv.drawRRect(rrect(hx - 22, hy - 92, 104, 46, 6), fill(RED))
    text(cv, "CL", hx + 30, hy - 58, "sans", 30, (255, 255, 255), anchor="c")
    rain(cv, t, n=220, a=120)
    # crack callout ring
    if crack_zoom > 0.05:
        r = 150 + 10 * math.sin(t * 6)
        cv.drawCircle(760, 1300, r, stroke(YEL, 8, 255 * crack_zoom))
        text(cv, "CRACKS", 760, 1300 - r - 26, "sans", 44, YEL, 255 * crack_zoom, anchor="c", shadow=6)
    # 'every year' calendar flips on line 4
    k = (t - L(3)) / 0.4
    if k > 0:
        for i, yr in enumerate(["2023", "2024", "2025"]):
            kk = bout((t - L(3) - i * 0.45) / 0.4)
            if kk <= 0:
                continue
            x = 560 + i * 160
            cv.save()
            cv.translate(x, 620)
            cv.scale(kk, kk)
            cv.drawRRect(rrect(-70, -80, 140, 160, 14), fill((255, 255, 255)))
            cv.drawRRect(rrect(-70, -80, 140, 44, 14), fill(RED))
            text(cv, yr, 0, 25, "sans", 36, NAVY, anchor="c")
            text(cv, "LEAK", 0, 66, "mono", 22, RED, anchor="c")
            cv.restore()
    lower_third(cv, t, L(2) + 0.1, "LIVE: ROOFTOP", "Reporter  ·  baarish mein terrace se", y=1180, dur=2.6)
    live_bug(cv, t)
    channel_bug(cv, t)


def sc_split(cv, lt, t):
    # classic news split: anchor top, reporter bottom, big '?'
    cv.drawRect(skia.Rect(0, 0, W, H), fill(NAVY))
    for half, (y0, y1) in enumerate([(240, 1010), (1010, 1720)]):
        cv.save()
        cv.clipRect(skia.Rect(60, y0 + 10, W - 60, y1 - 10))
        if half == 0:
            cv.translate(0, y0 - 380)
            studio_plate(cv, t)
            draw_person(cv, 540, 2280 - 520, 200, t, ANCHOR, arm_l=(0.9, 0.9), arm_r=(0.25, 0.8),
                        talk=talk(t, "ANCHOR"), brow=0.8, look=0.2)
        else:
            cv.translate(0, y0 - 780)
            terrace_plate(cv, t, wet=1.0)
            draw_person(cv, 540, 2150, 200, t, REPORTER, arm_l=(1.2, 1.1), talk=0, brow=0.4, look=-0.3)
            rain(cv, t, n=120, a=110)
        cv.restore()
        cv.drawRect(skia.Rect(60, y0 + 10, W - 60, y1 - 10), stroke((255, 255, 255), 4, 200))
    k = bout((lt - 0.2) / 0.4)
    if k > 0:
        cv.save()
        cv.translate(W / 2, 1010)
        cv.scale(k * (1 + 0.06 * math.sin(t * 8)), k * (1 + 0.06 * math.sin(t * 8)))
        cv.drawCircle(0, 0, 110, fill(RED))
        text(cv, "?", 0, 50, "sans", 150, (255, 255, 255), anchor="c")
        cv.restore()
    live_bug(cv, t)


def cross_section(cv, x0, y0, w, h, t, layers, crack_k=0.0, gap=0.0, mesh=False, label=None):
    """Isometric-ish slab cross-section: concrete + coating layers; optional crack opening underneath."""
    d = 70  # depth for the top face
    # concrete block (split by crack)
    for side in (-1, 1):
        off = side * gap / 2
        xs = x0 + (0 if side < 0 else w / 2) + off
        cv.drawRect(skia.Rect(xs, y0 + 120, xs + w / 2, y0 + h), lin((xs, 0), (xs + w / 2, 0), [(170, 166, 158), (130, 126, 118)]))
        tex(cv, CONCRETE, skia.Rect(xs, y0 + 120, xs + w / 2, y0 + h), 120)
    ty = y0 + 120
    for i, (name, col, th) in enumerate(layers):
        ty -= th
        cv.drawRect(skia.Rect(x0, ty, x0 + w, ty + th), fill(col))
        if name == "mesh" and mesh:
            mesh_patch(cv, (x0, ty, x0 + w, ty + th), cell=18, a=255)
        text(cv, name.upper(), x0 + w + 20, ty + th / 2 + 12, "mono", 26, (255, 255, 255))
    if crack_k > 0:
        cp = crack_path(x0 + w / 2, y0 + h, x0 + w / 2 + 10, y0 + 120 - crack_k * (sum(l[2] for l in layers) if not mesh else 0),
                        3, rough=10, branches=0)
        draw_crack(cv, cp, crack_k, w=6, col=(30, 28, 26))
    if label:
        text(cv, label, x0 + w / 2, y0 - 40 - sum(l[2] for l in layers), "sans", 40, (255, 255, 255), anchor="c", shadow=6)


def sc_mistri_why(cv, lt, t):
    z = 1.03 + 0.04 * ease(lt / 4.6)
    cam(cv, z)
    mistri_plate(cv, t)
    cv.restore()
    draw_person(cv, 300, 2100, 235, t, MISTRI, arm_l=(1.6 + 0.1 * math.sin(t * 2.5), 0.9), arm_r=(0.3, 0.2),
                talk=talk(t, "MISTRI-JI"), brow=0.7, look=0.7, curl_l=0.2)
    # diagram card: coating only -> crack telegraphs through
    k = eout((lt - 0.3) / 0.5)
    if k > 0:
        cv.save()
        cv.translate(0, (1 - k) * 60)
        cv.drawRRect(rrect(520, 360, 500, 560, 22), fill(NAVY, 220 * k))
        cross_section(cv, 560, 560, 300, 300, t, [("coating", (90, 140, 200), 26)],
                      crack_k=ease((lt - 1.2) / 1.8), gap=10 * ease((lt - 1.2) / 1.8), label="SIRF COATING")
        if lt > 2.6:
            kk = bout((lt - 2.6) / 0.4)
            cv.save()
            cv.translate(910, 830)
            cv.scale(kk, kk)
            cv.drawCircle(0, 0, 42, fill(RED))
            cv.drawLine(-18, -18, 18, 18, stroke((255, 255, 255), 8))
            cv.drawLine(18, -18, -18, 18, stroke((255, 255, 255), 8))
            cv.restore()
        cv.restore()
    lower_third(cv, t, L(5) + 0.1, "MISTRI-JI", "Waterproofing expert", y=1180, col=hexc("#E07B00"), dur=3.0)
    rain(cv, t, n=60, a=60)
    live_bug(cv, t)


def sc_product(cv, lt, t):
    # roll unrolls across the wet slab, then spec chips land on the words
    z = 1.0 + 0.06 * ease(lt / 7.6)
    cam(cv, z, cy=1200)
    terrace_plate(cv, t, wet=0.7, sky_dark=0.5)
    un = eout((lt - 0.2) / 1.8)
    x_end = lerp(140, 980, un)
    # laid sheet in perspective (trapezoid), mesh texture
    sheet = skia.Path()
    sheet.moveTo(140, 1080); sheet.lineTo(x_end, 1080); sheet.lineTo(x_end + 40, 1440); sheet.lineTo(100, 1440); sheet.close()
    cv.save()
    cv.clipPath(sheet, doAntiAlias=True)
    cv.drawRect(skia.Rect(0, 1080, W, 1440), fill((255, 255, 255), 40))
    mesh_patch(cv, (60, 1060, W, 1460), cell=22, a=230)
    cv.restore()
    mesh_roll(cv, x_end + 30, 1260, 70, 330, ang=math.pi / 2 * 0.98)
    cv.restore()
    # macro inset of the weave (real-looking close-up)
    k = eout((lt - 1.4) / 0.5)
    if k > 0:
        cx, cy, r = 760, 560, 220 * k
        cv.drawCircle(cx + 6, cy + 10, r + 8, fill((0, 0, 0), 100, blur=14))
        cv.save()
        clip = skia.Path(); clip.addCircle(cx, cy, r)
        cv.clipPath(clip, doAntiAlias=True)
        tex(cv, CONCRETE, skia.Rect(cx - r, cy - r, cx + r, cy + r))
        mesh_patch(cv, (cx - r, cy - r, cx + r, cy + r), cell=58, a=255, warp=3, t=t)
        cv.restore()
        cv.drawCircle(cx, cy, r, stroke((255, 255, 255), 8))
        text(cv, "fiberglass weave", cx, cy + r + 50, "serif_i", 34, (255, 255, 255), 255 * k, anchor="c", shadow=6)
    # name + specs on the spoken words
    lower_third(cv, t, WT(6, "BuildingShop") - 0.1, "FIBERGLASS MESH", "BuildingShop", y=1180, col=hexc("#1565C0"))
    spec_chip(cv, t, WT(6, "145"), "145 GSM", 90, 420)
    spec_chip(cv, t, WT(6, "24"), "24 inch wide", 90, 540)
    spec_chip(cv, t, WT(6, "50"), "50 m roll", 90, 660)
    live_bug(cv, t)


def sc_howto(cv, lt, t):
    cv.drawRect(skia.Rect(0, 0, W, H), lin((0, 0), (0, H), [(22, 34, 56), (8, 12, 22)]))
    steps = [("1", "Pehli coat", WT(7, "Pehli")), ("2", "Mesh bichhao + dabao", WT(7, "mesh")),
             ("3", "Doosri coat", WT(7, "doosri"))]
    k1 = ease((t - steps[0][2]) / 0.6)
    k2 = ease((t - steps[1][2]) / 0.6)
    k3 = ease((t - steps[2][2]) / 0.6)
    layers = []
    if k1 > 0:
        layers.append(("coat 1", (90, 140, 200), 44 * k1))
    if k2 > 0:
        layers.append(("mesh", (235, 235, 228), 40 * k2))
    if k3 > 0:
        layers.append(("coat 2", (110, 160, 215), 46 * k3))
    cv.save()
    cv.translate(W / 2, 760)
    sc = 1 + 0.04 * ease(lt / 3.8)
    cv.scale(sc, sc)
    cv.translate(-W / 2, -760)
    cross_section(cv, 170, 520, 560, 420, t, layers, mesh=True, label="TERRACE SLAB")
    cv.restore()
    # brush / hand doing the current step
    cur = 2 if t >= steps[2][2] else (1 if t >= steps[1][2] else 0)
    hx = lerp(220, 680, (t * 0.9) % 1)
    hy = 520 + 120 - sum(l[2] for l in layers) - 30
    draw_hand(cv, hx, hy - 40, 160, math.pi, MISTRI, curl=0.2 if cur == 1 else 0.7)
    if cur != 1:
        cv.drawRRect(rrect(hx - 50, hy - 10, 100, 26, 6), fill((150, 105, 60)))
    for i, (n, s, tin) in enumerate(steps):
        kk = bout((t - tin) / 0.4)
        if kk <= 0:
            continue
        y = 1110 + i * 105
        cv.save()
        cv.translate(130, y)
        cv.scale(kk, kk)
        cv.drawCircle(0, 0, 40, fill(YEL if i == cur else (255, 255, 255)))
        text(cv, n, 0, 16, "sans", 44, NAVY, anchor="c")
        text(cv, s, 70, 16, "sans", 48, (255, 255, 255))
        cv.restore()
    live_bug(cv, t)


def sc_crack_test(cv, lt, t):
    cv.drawRect(skia.Rect(0, 0, W, H), lin((0, 0), (0, H), [(20, 30, 50), (6, 10, 20)]))
    crack = ease((lt - 0.4) / 2.2)
    text(cv, "BINA MESH", 290, 360, "sans", 48, (255, 150, 140), anchor="c")
    text(cv, "MESH KE SAATH", 790, 360, "sans", 48, YEL, anchor="c")
    cross_section(cv, 120, 520, 330, 380, t, [("coating", (90, 140, 200), 30)], crack_k=crack, gap=14 * crack)
    cross_section(cv, 610, 520, 330, 380, t, [("coat", (90, 140, 200), 14), ("mesh", (235, 235, 228), 14),
                                              ("coat", (110, 160, 215), 14)], crack_k=crack * 0.55, gap=14 * crack, mesh=True)
    # drops getting through on the left only
    if crack > 0.7:
        for ph in (0.0, 0.5):
            drip(cv, 285, 640, 960, t, period=0.8, ph=ph, scale=0.8)
    for x, ok in ((290, False), (790, True)):
        kk = bout((lt - 2.4) / 0.4)
        if kk <= 0:
            continue
        cv.save()
        cv.translate(x, 1090)
        cv.scale(kk, kk)
        cv.drawCircle(0, 0, 58, fill((40, 160, 80) if ok else RED))
        if ok:
            p = skia.Path(); p.moveTo(-26, 0); p.lineTo(-6, 22); p.lineTo(28, -20)
            cv.drawPath(p, stroke((255, 255, 255), 11))
        else:
            cv.drawLine(-22, -22, 22, 22, stroke((255, 255, 255), 11))
            cv.drawLine(22, -22, -22, 22, stroke((255, 255, 255), 11))
        cv.restore()
    cv.drawLine(W / 2, 330, W / 2, 1200, stroke((255, 255, 255), 3, 80))
    live_bug(cv, t)


USES = [("TERRACE", "terrace"), ("DEEWAR KE CRACKS", "wall"), ("PLASTER", "plaster")]


def sc_uses(cv, lt, t):
    i = 0 if t < WT(9, "deewar") else (1 if t < WT(9, "plaster") else 2)
    tin = [L(9), WT(9, "deewar"), WT(9, "plaster")][i]
    k = eout((t - tin) / 0.35)
    z = 1.08 - 0.06 * ease((t - tin) / 1.6)
    cam(cv, z, dx=(1 - k) * 160)
    if i == 0:
        terrace_plate(cv, t, wet=0.2, cracks=0, sky_dark=0.0)
        sheet = skia.Path()
        sheet.moveTo(100, 1080); sheet.lineTo(980, 1080); sheet.lineTo(1040, 1500); sheet.lineTo(40, 1500); sheet.close()
        cv.save(); cv.clipPath(sheet, doAntiAlias=True)
        cv.drawRect(skia.Rect(0, 1080, W, 1500), fill((120, 165, 215), 200))
        mesh_patch(cv, (0, 1080, W, 1500), cell=24, a=110)
        cv.restore()
    elif i == 1:
        tex(cv, PLASTER, skia.Rect(0, 0, W, H))
        cv.drawRect(skia.Rect(0, 0, W, H), lin((0, 0), (W, 0), [((0, 0, 0), 20), ((0, 0, 0), 80)]))
        draw_crack(cv, crack_path(260, 300, 720, 1500, 31, rough=26, branches=3), 1.0, w=6, col=(80, 70, 60))
        band = skia.Path()
        band.moveTo(330, 280); band.lineTo(520, 280); band.lineTo(800, 1520); band.lineTo(610, 1520); band.close()
        cv.save(); cv.clipPath(band, doAntiAlias=True)
        mesh_patch(cv, (300, 260, 820, 1540), cell=22, a=230)
        cv.restore()
    else:
        tex(cv, PLASTER, skia.Rect(0, 0, W, H))
        cv.drawRect(skia.Rect(0, 0, W, 900), fill((205, 200, 188)))
        mesh_patch(cv, (0, 900, W, 1600), cell=26, a=200)
        cv.drawRect(skia.Rect(0, 900, W * ease((t - tin - 0.3) / 1.2), 1600), fill((215, 208, 192), 230))
    cv.restore()
    for j in range(3):
        kk = bout((t - [L(9), WT(9, "deewar"), WT(9, "plaster")][j]) / 0.35)
        if kk <= 0:
            continue
        f = font("sans", 38)
        s = USES[j][0]
        w = f.measureText(s) + 50
        y = 330 + j * 90
        cv.save()
        cv.translate(90 + w / 2, y)
        cv.scale(kk, kk)
        cv.drawRRect(rrect(-w / 2, -32, w, 64, 12), fill(YEL if j == i else (255, 255, 255)))
        cv.drawString(s, -w / 2 + 25, 13, f, fill(NAVY))
        cv.restore()
    live_bug(cv, t)


def wall_weather(cv, t):
    k = ease((t - WT(10, "mausam") + 0.2) / 0.6)
    cv.drawRect(skia.Rect(90, 330, 990, 840), lin((0, 330), (0, 840), [mix((95, 108, 128), (90, 170, 240), k),
                                                                       mix((140, 150, 160), (200, 230, 250), k)]))
    sx, sy = 760, 520
    cv.drawCircle(sx, sy, 90 * k, fill((255, 210, 60), 255 * k))
    for i in range(10):
        a = i * math.pi / 5 + t * 0.5
        cv.drawLine(sx + math.cos(a) * 110 * k, sy + math.sin(a) * 110 * k, sx + math.cos(a) * 140 * k,
                    sy + math.sin(a) * 140 * k, stroke((255, 210, 60), 8, 255 * k))
    if k < 1:
        rain_k = 1 - k
        cv.save(); cv.clipRect(skia.Rect(90, 330, 990, 840))
        rain(cv, t, n=80, a=int(110 * rain_k))
        cv.restore()
    text(cv, "MAUSAM: SAAF", 160, 790, "sans", 52, (255, 255, 255), 255 * k, shadow=6)
    text(cv, "Leakage: koi khabar nahi", 160, 420, "sans", 34, (255, 255, 255), 255 * k, shadow=6)


def sc_signoff(cv, lt, t):
    z = 1.0 + 0.05 * ease(lt / 5)
    cam(cv, z)
    anchor_shot(cv, t, wall_weather, signoff=True)
    cv.restore()
    live_bug(cv, t)
    channel_bug(cv, t)
    end = t - LE(10)
    if end > 0.1:  # news-style freeze + sign-off card
        k = eout((end - 0.1) / 0.4)
        cv.drawRect(skia.Rect(0, 0, W, H), fill((255, 255, 255), 60 * (1 - k)))
        cv.save()
        cv.translate(W / 2, 1180)
        cv.scale(k, k)
        cv.drawRRect(rrect(-360, -70, 720, 140, 16), fill(RED))
        text(cv, "buildingshop.in", 0, 18, "sans", 56, (255, 255, 255), anchor="c")
        cv.restore()


SCENE_FN = dict(breaking=sc_breaking, studio=sc_studio, rooftop=sc_rooftop, split=sc_split,
                mistri_why=sc_mistri_why, product=sc_product, howto=sc_howto, crack_test=sc_crack_test,
                uses=sc_uses, signoff=sc_signoff)


# ------------------------------------------------------------------ captions: news-style, word highlight
SP_COL = {"ANCHOR": RED, "REPORTER": hexc("#1565C0"), "MISTRI-JI": hexc("#E07B00")}


def captions(cv, t):
    for li, (a, b, sp, s) in enumerate(LINES):
        if not (a - 0.08 <= t <= b + 0.15):
            continue
        wl = WORDS[li]
        words = [w for _, _, w in wl]
        cur = max([k for k, (wa, wb, _) in enumerate(wl) if t >= wa - 0.02] or [0])
        fade = ease((t - (a - 0.08)) / 0.1) * (1 - ease((t - b - 0.05) / 0.1))
        f = font("sans", 52)
        lines, cl = [], []
        for i, w in enumerate(words):
            if cl and f.measureText(" ".join([words[j] for j in cl] + [w])) > 860:
                lines.append(cl); cl = []
            cl.append(i)
        lines.append(cl)
        lh = 70
        y0 = 1500 - (len(lines) - 1) * lh / 2
        bw = max(f.measureText(" ".join(words[i] for i in l)) for l in lines) + 60
        cv.drawRRect(rrect(W / 2 - bw / 2, y0 - 60, bw, len(lines) * lh + 30, 10), fill((255, 255, 255), 238 * fade))
        tf = font("sans", 26)
        tw = tf.measureText(sp)
        cv.drawRect(skia.Rect(W / 2 - bw / 2, y0 - 104, W / 2 - bw / 2 + tw + 30, y0 - 60), fill(SP_COL[sp], 255 * fade))
        cv.drawString(sp, W / 2 - bw / 2 + 15, y0 - 72, tf, fill((255, 255, 255), 255 * fade))
        for ln, idxs in enumerate(lines):
            lw = f.measureText(" ".join(words[i] for i in idxs))
            x = W / 2 - lw / 2
            y = y0 + ln * lh
            for i in idxs:
                w = words[i]
                ww = f.measureText(w)
                on = i == cur
                cv.drawString(w, x, y, f, fill(RED if on else NAVY, 255 * fade))
                if on:
                    cv.drawRect(skia.Rect(x, y + 8, x + ww, y + 14), fill(RED, 255 * fade))
                x += ww + f.measureText(" ")
        return


# ------------------------------------------------------------------ frame
def render_frame(t, arr=None):
    if arr is None:
        arr = np.zeros((H, W, 4), np.uint8)
    cv = skia.Surface(arr).getCanvas()
    cv.clear(skia.ColorBLACK)
    for i, (a, b, name) in enumerate(SCENES):
        if a <= t < b or (i == len(SCENES) - 1 and t >= a):
            SCENE_FN[name](cv, t - a, t)
            k = 1 - ease((t - a) / 0.14)  # news 'whip' flash on each cut
            if i > 0 and k > 0:
                cv.drawRect(skia.Rect(0, 0, W, H), fill((255, 255, 255), 80 * k))
            break
    film_finish(cv, t, vign=0.45, grain=12)
    ticker(cv, t)
    captions(cv, t)
    K.draw_border(cv)
    return arr


# ------------------------------------------------------------------ music + sfx (news theme)
def music(n):
    tt = np.arange(n) / SR
    out = np.zeros(n)
    bpm = 120
    beat = 60 / bpm

    def note(m):
        return 440 * 2 ** ((m - 69) / 12)

    def tone(f0, start, dur, amp, kind="pad"):
        i0 = int(start * SR)
        Ln = min(int(dur * SR), n - i0)
        if Ln <= 0:
            return
        x = np.arange(Ln) / SR
        if kind == "pad":
            s = sum(np.sin(2 * np.pi * f0 * m * x * (1 + 0.002 * k)) / m for m in (1, 2, 3) for k in (-1, 1)) / 6
            e = np.minimum(1, x / 0.3) * np.minimum(1, (dur - x) / 0.4)
        elif kind == "pluck":
            s = np.sign(np.sin(2 * np.pi * f0 * x)) * 0.3 + np.sin(2 * np.pi * f0 * x)
            e = np.exp(-x * 9)
        else:  # timpani-ish hit
            s = np.sin(2 * np.pi * f0 * x * (1 - 0.15 * x))
            e = np.exp(-x * 4)
        out[i0:i0 + Ln] += amp * s * e

    end_tension = L(10) - 0.1
    prog = [[50, 53, 57], [46, 50, 53], [48, 52, 55], [45, 49, 52]]  # Dm Bb C A
    t0, ci = 0.0, 0
    while t0 < end_tension:
        c = prog[ci % 4]
        for m in c:
            tone(note(m), t0, beat * 4 + 0.2, 0.06)
        for k in range(8):  # news 'urgency' 8th-note pulse
            tone(note(c[0] + 12 if k % 2 else c[0] + 24), t0 + k * beat / 2, 0.15, 0.05, "pluck")
        t0 += beat * 4
        ci += 1
    # bright resolve for the sign-off (D major)
    for m in (50, 54, 57, 62):
        tone(note(m), end_tension, DUR - end_tension, 0.09)
    for k, m in enumerate([74, 78, 81, 86]):
        tone(note(m), end_tension + k * 0.18, 0.6, 0.06, "pluck")
    for th in (0.05, L(2), L(6), end_tension):
        tone(55, th, 1.5, 0.35, "hit")
    for d, g in ((0.09, 0.3), (0.15, 0.22), (0.23, 0.15)):
        k = int(d * SR)
        out[k:] += g * out[:-k]
    fl = int(1.0 * SR)
    out[-fl:] *= np.linspace(1, 0, fl)
    out /= np.max(np.abs(out)) + 1e-9
    return out * 10 ** (-6 / 20)


def sfx(n):
    out = np.zeros(n)
    rng = np.random.default_rng(3)

    def put(t0, sig):
        i0 = int(t0 * SR)
        Ln = min(len(sig), n - i0)
        if Ln > 0 and i0 >= 0:
            out[i0:i0 + Ln] += sig[:Ln]

    # rain ambience in rooftop scenes
    for a, b, name in SCENES:
        if name in ("rooftop", "split", "mistri_why", "product"):
            Ln = int((b - a) * SR)
            r = rng.normal(0, 1, Ln)
            r = np.convolve(r, np.ones(6) / 6, "same") * 0.05
            e = np.minimum(1, np.arange(Ln) / (0.2 * SR)) * np.minimum(1, (Ln - np.arange(Ln)) / (0.2 * SR))
            put(a, r * e)
        # whoosh on each cut
        Ln = int(0.35 * SR)
        x = np.arange(Ln) / SR
        put(a - 0.2, np.convolve(rng.normal(0, 1, Ln), np.ones(20) / 20, "same") * np.sin(np.pi * x / x[-1]) ** 2 * 0.16)
    # drips in the opening
    for k in range(5):
        Ln = int(0.08 * SR)
        x = np.arange(Ln) / SR
        put(0.6 + k * 1.1, np.sin(2 * np.pi * (1400 - 6000 * x) * x) * np.exp(-x * 60) * 0.18)
    # chip pops
    for tp in (WT(6, "145"), WT(6, "24"), WT(6, "50"), WT(7, "Pehli"), WT(7, "mesh"), WT(7, "doosri")):
        Ln = int(0.1 * SR)
        x = np.arange(Ln) / SR
        put(tp, np.sin(2 * np.pi * (900 + 2000 * x) * x) * np.exp(-x * 45) * 0.12)
    return out


def mix_audio():
    n = int(DUR * SR)
    vo = VO[:n]
    m = music(n)
    h = SR // 100
    mm = len(vo) // h
    e = np.sqrt(np.mean(vo[:mm * h].reshape(mm, h) ** 2, 1))
    e = np.convolve((e > 0.01).astype(float), np.ones(25) / 25, "same")
    duck = np.pad(1 - 0.65 * np.repeat(e, h), (0, n - mm * h), constant_values=1)
    vo_n = vo / (np.max(np.abs(vo)) + 1e-9) * 10 ** (-1.5 / 20)
    out = m * 0.5 * duck + vo_n + sfx(n)
    return out / max(1.0, np.max(np.abs(out)) / 10 ** (-1 / 20))


def main():
    os.makedirs(OUT, exist_ok=True)
    print("DUR", DUR)
    if "--stills" in sys.argv:
        ts = [0.9, 3.5, L(1) + 1.0, L(2) + 1.0, WT(2, "cracks") + 0.6, L(3) + 1.6, L(4) + 0.8, L(5) + 3.0,
              L(6) + 1.2, WT(6, "50") + 0.6, WT(7, "mesh") + 0.6, WT(7, "doosri") + 0.8, L(8) + 3.0,
              WT(9, "deewar") + 0.5, WT(9, "plaster") + 0.8, LE(10) - 0.5, DUR - 0.3]
        for t in ts:
            a = render_frame(t)
            skia.Image.fromarray(a, colorType=skia.kRGBA_8888_ColorType).save(
                os.path.join(OUT, f"still_{t:05.2f}.png"), skia.kPNG)
        return
    wav = os.path.join(OUT, "chhat_news_mix.wav")
    write_wav(wav, mix_audio())
    dst = os.path.join(OUT, "buildingshop_fiber_mesh_chhat_news_9x16.mp4")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "medium", "-crf", "18",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
           "-shortest", "-movflags", "+faststart", dst]
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
    print("wrote", dst)


if __name__ == "__main__":
    main()
