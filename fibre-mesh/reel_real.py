"""Chhat Se Breaking News — REALISTIC cut. Runway photoreal plates + light motion graphics.

Each shot is a real-looking Runway image (fibre-mesh/plates/<name>.png|jpg) shown full-frame with a slow camera
move (push / pull / drift), a filmic grade, rain + light VFX, and only a light broadcast layer on top: breaking
banner, LIVE bug, lower-thirds, spec chips on the spoken words, step chips, one before/after diagram, word
captions and the BuildingShop yellow frame. Same VO timeline and music as reel_mesh.py.

If a plate is missing, that shot falls back to the drawn version so the edit always renders.

usage: python3 reel_real.py [--stills]
"""
import math, os, subprocess, sys
import numpy as np
import skia
import reel_mesh as M
from reel_mesh import (W, H, FPS, L, LE, WT, DUR, RED, NAVY, YEL, fill, stroke, lin, rad, rrect, text, font,
                       ease, eout, bout, clamp, lerp, film_finish, rain, live_bug, channel_bug, ticker,
                       lower_third, breaking_banner, spec_chip, captions, cross_section)

HERE = M.HERE
PLATES = os.path.join(HERE, "plates")
SHOTS = {  # plate name -> Runway prompt it came from (see RUNWAY_SHOTS.md)
    "01_ceiling": "leaking ceiling + bucket",
    "02_anchor": "anchor at news desk",
    "03_reporter": "reporter on rooftop in rain",
    "04_cracks": "cracked wet terrace close-up",
    "05_mistri": "mason in yellow helmet",
    "06_mesh_roll": "mesh roll unrolling on coated roof",
    "07_press": "gloved hands pressing mesh into coat",
    "08_wall": "mesh over wall crack + plaster",
    "09_sunny": "dry terrace under sunny sky",
}
_IMG = {}


def plate(name):
    if name not in _IMG:
        _IMG[name] = None
        for ext in (".png", ".jpg", ".jpeg", ".webp"):
            p = os.path.join(PLATES, name + ext)
            if os.path.exists(p):
                d = skia.Data.MakeFromFileName(p)
                _IMG[name] = skia.Image.MakeFromEncoded(d)
                break
    return _IMG[name]


def shot(cv, name, lt, dur, move="push", fx=0.5, fy=0.5, amt=0.10, grade=None, rect=None):
    """Draw a plate cover-fit with a camera move. Returns False if the plate is missing."""
    img = plate(name)
    if img is None:
        return False
    x0, y0, w, h = rect or (0, 0, W, H)
    k = ease(clamp(lt / max(dur, 0.1)))
    z = {"push": 1.0 + amt * k, "pull": 1.0 + amt * (1 - k), "drift": 1.0 + amt * 0.6}.get(move, 1.0)
    dx = {"drift": (k - 0.5) * 60}.get(move, 0)
    s = max(w / img.width(), h / img.height()) * z
    cv.save()
    cv.clipRect(skia.Rect.MakeXYWH(x0, y0, w, h))
    cv.translate(x0 + w * fx + dx - img.width() * s * fx, y0 + h * fy - img.height() * s * fy)
    cv.scale(s, s)
    cv.drawImage(img, 0, 0, skia.SamplingOptions(skia.CubicResampler.Mitchell()))
    cv.restore()
    if grade:
        cv.drawRect(skia.Rect.MakeXYWH(x0, y0, w, h), fill(grade[:3], grade[3]))
    return True


def light_flicker(cv, t, a=18):
    f = 0.5 + 0.5 * math.sin(t * 13) * math.sin(t * 3.1)
    cv.drawRect(skia.Rect(0, 0, W, H), fill((255, 240, 220), a * f))


# ------------------------------------------------------------------ scenes (photo first, graphics light)
def s_breaking(cv, lt, t):
    dur = L(1) - 0.06
    if not shot(cv, "01_ceiling", lt, dur, "push", fy=0.35, amt=0.12):
        return M.sc_breaking(cv, lt, t)
    light_flicker(cv, t)
    breaking_banner(cv, t, 0.05)
    live_bug(cv, t)
    channel_bug(cv, t)


def s_studio(cv, lt, t):
    if not shot(cv, "02_anchor", lt, L(2) - L(1), "pull", fy=0.4, amt=0.08):
        return M.sc_studio(cv, lt, t)
    lower_third(cv, t, L(1) + 0.1, "SHEHAR MEIN LEAKAGE", "Har doosri chhat se tapak raha paani", y=1200)
    live_bug(cv, t)
    channel_bug(cv, t)


def s_rooftop(cv, lt, t):
    tc = WT(2, "cracks") - 0.05
    if t < tc:
        ok = shot(cv, "03_reporter", lt, tc - L(2), "push", fy=0.4, amt=0.08)
    else:
        ok = shot(cv, "04_cracks", t - tc, L(4) - tc, "push", fy=0.55, amt=0.14)
    if not ok:
        return M.sc_rooftop(cv, lt, t)
    rain(cv, t, n=170, a=95)
    if t < tc:
        lower_third(cv, t, L(2) + 0.1, "LIVE: ROOFTOP", "Reporter  ·  baarish mein terrace se", y=1180)
    else:  # light graphics: crack ring, then 'every year' cards
        k = ease((t - tc) / 0.4) * (1 - ease((t - L(3) + 0.2) / 0.3))
        if k > 0:
            r = 170 + 10 * math.sin(t * 6)
            cv.drawCircle(540, 1000, r, stroke(YEL, 8, 255 * k))
            text(cv, "CRACKS", 540, 1000 - r - 26, "sans", 48, YEL, 255 * k, anchor="c", shadow=6)
        for i, yr in enumerate(["2023", "2024", "2025"]):
            kk = bout((t - L(3) - i * 0.45) / 0.4)
            if kk <= 0:
                continue
            cv.save()
            cv.translate(260 + i * 280, 640)
            cv.scale(kk, kk)
            cv.drawRRect(rrect(-90, -95, 180, 190, 16), fill((255, 255, 255), 240))
            cv.drawRRect(rrect(-90, -95, 180, 52, 16), fill(RED))
            text(cv, yr, 0, 30, "sans", 44, NAVY, anchor="c")
            text(cv, "LEAK", 0, 78, "mono", 26, RED, anchor="c")
            cv.restore()
    live_bug(cv, t)
    channel_bug(cv, t)


def s_split(cv, lt, t):
    if plate("02_anchor") is None or plate("03_reporter") is None:
        return M.sc_split(cv, lt, t)
    cv.drawRect(skia.Rect(0, 0, W, H), fill(NAVY))
    shot(cv, "02_anchor", lt, 2, "drift", fy=0.35, rect=(60, 250, W - 120, 750))
    shot(cv, "03_reporter", lt, 2, "drift", fy=0.4, rect=(60, 1010, W - 120, 700))
    rain(cv, t, n=60, a=80)
    for y0, h in ((250, 750), (1010, 700)):
        cv.drawRect(skia.Rect.MakeXYWH(60, y0, W - 120, h), stroke((255, 255, 255), 4, 220))
    k = bout((lt - 0.2) / 0.4)
    if k > 0:
        cv.save()
        cv.translate(W / 2, 1005)
        s = k * (1 + 0.06 * math.sin(t * 8))
        cv.scale(s, s)
        cv.drawCircle(0, 0, 105, fill(RED))
        text(cv, "?", 0, 50, "sans", 150, (255, 255, 255), anchor="c")
        cv.restore()
    live_bug(cv, t)


def s_mistri(cv, lt, t):
    if not shot(cv, "05_mistri", lt, L(6) - L(5), "push", fy=0.35, amt=0.07):
        return M.sc_mistri_why(cv, lt, t)
    # one small explainer card: coating alone cracks
    k = eout((lt - 0.6) / 0.5)
    if k > 0:
        cv.save()
        cv.translate(0, (1 - k) * 40)
        cv.drawRRect(rrect(560, 330, 450, 470, 22), fill(NAVY, 215 * k))
        cross_section(cv, 600, 520, 260, 240, t, [("coating", (90, 140, 200), 24)],
                      crack_k=ease((lt - 1.3) / 1.6), gap=10 * ease((lt - 1.3) / 1.6), label="SIRF COATING")
        if lt > 2.6:
            kk = bout((lt - 2.6) / 0.4)
            cv.save()
            cv.translate(950, 740)
            cv.scale(kk, kk)
            cv.drawCircle(0, 0, 38, fill(RED))
            cv.drawLine(-16, -16, 16, 16, stroke((255, 255, 255), 8))
            cv.drawLine(16, -16, -16, 16, stroke((255, 255, 255), 8))
            cv.restore()
        cv.restore()
    lower_third(cv, t, L(5) + 0.1, "MISTRI-JI", "Waterproofing expert", y=1180, col=M.hexc("#E07B00"), dur=3.0)
    live_bug(cv, t)


def s_product(cv, lt, t):
    if not shot(cv, "06_mesh_roll", lt, L(7) - L(6), "push", fy=0.55, amt=0.10):
        return M.sc_product(cv, lt, t)
    # light sweep across the mesh on reveal
    sx = lerp(-300, W + 300, clamp((lt - 0.3) / 1.2))
    sw = skia.Path()
    sw.moveTo(sx, 0); sw.lineTo(sx + 120, 0); sw.lineTo(sx - 180, H); sw.lineTo(sx - 300, H); sw.close()
    p = fill((255, 255, 255), 45, blur=30)
    p.setBlendMode(skia.BlendMode.kScreen)
    cv.drawPath(sw, p)
    lower_third(cv, t, WT(6, "BuildingShop") - 0.1, "FIBERGLASS MESH", "BuildingShop", y=1180, col=M.hexc("#1565C0"))
    spec_chip(cv, t, WT(6, "145"), "145 GSM", 90, 420)
    spec_chip(cv, t, WT(6, "24"), "24 inch wide", 90, 540)
    spec_chip(cv, t, WT(6, "50"), "50 m roll", 90, 660)
    live_bug(cv, t)


def s_howto(cv, lt, t):
    if not shot(cv, "07_press", lt, L(8) - L(7), "push", fy=0.5, amt=0.12):
        return M.sc_howto(cv, lt, t)
    cv.drawRect(skia.Rect(0, 900, W, 1400), lin((0, 900), (0, 1400), [((0, 0, 0), 0), ((0, 0, 0), 120)]))
    steps = [("1", "Pehli coat", WT(7, "Pehli")), ("2", "Mesh bichhao + dabao", WT(7, "mesh")),
             ("3", "Doosri coat", WT(7, "doosri"))]
    cur = 2 if t >= steps[2][2] else (1 if t >= steps[1][2] else 0)
    for i, (n, s, tin) in enumerate(steps):
        kk = bout((t - tin) / 0.4)
        if kk <= 0:
            continue
        y = 360 + i * 110
        cv.save()
        cv.translate(130, y)
        cv.scale(kk, kk)
        f = font("sans", 46)
        wpx = f.measureText(s) + 130
        cv.drawRRect(rrect(-50, -44, wpx, 88, 44), fill(NAVY, 200))
        cv.drawCircle(0, 0, 38, fill(YEL if i == cur else (255, 255, 255)))
        text(cv, n, 0, 16, "sans", 42, NAVY, anchor="c")
        text(cv, s, 60, 16, "sans", 46, (255, 255, 255))
        cv.restore()
    live_bug(cv, t)


def s_crack_test(cv, lt, t):
    # the one fully-graphic beat: before/after over a blurred real plate
    img_ok = plate("07_press") is not None
    if img_ok:
        bp = skia.Paint()
        bp.setImageFilter(skia.ImageFilters.Blur(30, 30))
        cv.saveLayer(None, bp)
        shot(cv, "07_press", lt, 3, "drift")
        cv.restore()
        cv.drawRect(skia.Rect(0, 0, W, H), fill((8, 14, 26), 190))
        cv.save()
        cv.clipRect(skia.Rect(0, 300, W, 1300))
        M.sc_crack_test(_NoBg(cv), lt, t)
        cv.restore()
    else:
        M.sc_crack_test(cv, lt, t)


class _NoBg:
    """Canvas proxy that skips sc_crack_test's full-frame background fill so the blurred photo shows through."""

    def __init__(self, cv):
        self._cv = cv
        self._first = True

    def drawRect(self, r, p):
        if self._first and r.width() >= W and r.height() >= H:
            self._first = False
            return
        return self._cv.drawRect(r, p)

    def __getattr__(self, k):
        return getattr(self._cv, k)


def s_uses(cv, lt, t):
    i = 0 if t < WT(9, "deewar") else (1 if t < WT(9, "plaster") else 2)
    tin = [L(9), WT(9, "deewar"), WT(9, "plaster")][i]
    name = ["06_mesh_roll", "08_wall", "08_wall"][i]
    if not shot(cv, name, t - tin, 1.8, "push" if i != 2 else "pull", fy=0.5, amt=0.10):
        return M.sc_uses(cv, lt, t)
    for j, s in enumerate(["TERRACE", "DEEWAR KE CRACKS", "PLASTER"]):
        kk = bout((t - [L(9), WT(9, "deewar"), WT(9, "plaster")][j]) / 0.35)
        if kk <= 0:
            continue
        f = font("sans", 38)
        w = f.measureText(s) + 50
        cv.save()
        cv.translate(90 + w / 2, 330 + j * 90)
        cv.scale(kk, kk)
        cv.drawRRect(rrect(-w / 2, -32, w, 64, 12), fill(YEL if j == i else (255, 255, 255)))
        cv.drawString(s, -w / 2 + 25, 13, f, fill(NAVY))
        cv.restore()
    live_bug(cv, t)


def s_signoff(cv, lt, t):
    tm = WT(10, "mausam") - 0.15
    if t < tm:
        ok = shot(cv, "02_anchor", lt, tm - L(10), "push", fy=0.4, amt=0.06)
    else:
        ok = shot(cv, "09_sunny", t - tm, DUR - tm, "pull", fy=0.5, amt=0.12)
        if ok:  # warm sun bloom
            cv.drawCircle(W * 0.75, H * 0.12, 600, rad((W * 0.75, H * 0.12), 600, [((255, 230, 160), 90), ((255, 230, 160), 0)]))
            k = eout((t - tm) / 0.5)
            cv.drawRRect(rrect(90, 330, 560 * k, 96, 14), fill((255, 255, 255), 235))
            if k > 0.6:
                text(cv, "MAUSAM: SAAF", 120, 395, "sans", 52, NAVY)
    if not ok:
        return M.sc_signoff(cv, lt, t)
    live_bug(cv, t)
    channel_bug(cv, t)
    end = t - LE(10)
    if end > 0.1:
        k = eout((end - 0.1) / 0.4)
        cv.save()
        cv.translate(W / 2, 1180)
        cv.scale(k, k)
        cv.drawRRect(rrect(-360, -70, 720, 140, 16), fill(RED))
        text(cv, "buildingshop.in", 0, 18, "sans", 56, (255, 255, 255), anchor="c")
        cv.restore()


FN = dict(breaking=s_breaking, studio=s_studio, rooftop=s_rooftop, split=s_split, mistri_why=s_mistri,
          product=s_product, howto=s_howto, crack_test=s_crack_test, uses=s_uses, signoff=s_signoff)


def render_frame(t, arr=None):
    if arr is None:
        arr = np.zeros((H, W, 4), np.uint8)
    cv = skia.Surface(arr).getCanvas()
    cv.clear(skia.ColorBLACK)
    for i, (a, b, name) in enumerate(M.SCENES):
        if a <= t < b or (i == len(M.SCENES) - 1 and t >= a):
            FN[name](cv, t - a, t)
            k = 1 - ease((t - a) / 0.14)
            if i > 0 and k > 0:
                cv.drawRect(skia.Rect(0, 0, W, H), fill((255, 255, 255), 70 * k))
            break
    film_finish(cv, t, vign=0.4, grain=10)
    ticker(cv, t)
    captions(cv, t)
    M.K.draw_border(cv)
    return arr


def main():
    os.makedirs(M.OUT, exist_ok=True)
    have = [n for n in SHOTS if plate(n) is not None]
    print("plates found:", len(have), "/", len(SHOTS), have)
    if "--stills" in sys.argv:
        ts = [0.9, L(1) + 1.0, L(2) + 1.0, WT(2, "cracks") + 0.6, L(3) + 1.6, L(4) + 0.8, L(5) + 3.0,
              WT(6, "50") + 0.6, WT(7, "doosri") + 0.5, L(8) + 3.0, WT(9, "deewar") + 0.5, LE(10) - 0.6, DUR - 0.3]
        for t in ts:
            a = render_frame(t)
            skia.Image.fromarray(a, colorType=skia.kRGBA_8888_ColorType).save(
                os.path.join(M.OUT, f"real_{t:05.2f}.png"), skia.kPNG)
        return
    wav = os.path.join(M.OUT, "chhat_news_mix.wav")
    M.write_wav(wav, M.mix_audio())
    dst = os.path.join(M.OUT, "buildingshop_fiber_mesh_REAL_9x16.mp4")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "medium", "-crf", "18",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
           "-shortest", "-movflags", "+faststart", dst]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    arr = np.zeros((H, W, 4), np.uint8)
    for f in range(int(DUR * FPS)):
        render_frame(f / FPS, arr)
        p.stdin.write(arr.tobytes())
    p.stdin.close()
    p.wait()
    print("wrote", dst)


if __name__ == "__main__":
    main()
