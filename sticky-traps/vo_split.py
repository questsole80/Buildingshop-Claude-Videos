"""Split each VO mp3 into its lines using the N-1 longest pauses (no whisper available offline).
Writes vo/segments.json: {voice: [[start, end], ...]} in file-local seconds, plus voiced runs per line."""
import json, subprocess, sys
import numpy as np

SR = 16000
FILES = {"NARRATOR": ("vo/file_bunty_voice.mp3", 7), "MEERA": ("vo/file_zara_voice.mp3", 3),
         "RAJU KAKA": ("vo/file_raju_voice.mp3", 3)}


def load(p):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", p, "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768


def runs(x, hop=0.01, thr_db=-40):
    h = int(hop * SR)
    n = len(x) // h
    rms = np.sqrt(np.mean(x[:n * h].reshape(n, h) ** 2, 1) + 1e-12)
    db = 20 * np.log10(rms)
    on = db > thr_db
    out, start = [], None
    for i, v in enumerate(on):
        if v and start is None:
            start = i
        if not v and start is not None:
            out.append([start * hop, i * hop]); start = None
    if start is not None:
        out.append([start * hop, n * hop])
    # merge tiny gaps (<60 ms)
    m = [out[0]]
    for a, b in out[1:]:
        if a - m[-1][1] < 0.06:
            m[-1][1] = b
        else:
            m.append([a, b])
    return [r for r in m if r[1] - r[0] > 0.05], db


res = {}
for voice, (p, nlines) in FILES.items():
    x = load(p)
    rs, db = runs(x)
    gaps = sorted(range(len(rs) - 1), key=lambda i: rs[i + 1][0] - rs[i][1], reverse=True)[:nlines - 1]
    cuts = sorted(gaps)
    lines, s = [], 0
    for c in cuts + [len(rs) - 1]:
        lines.append(dict(start=rs[s][0], end=rs[c][1], runs=rs[s:c + 1]))
        s = c + 1
    res[voice] = lines
    print(voice, len(x) / SR)
    for L in lines:
        print(f"  {L['start']:.2f}-{L['end']:.2f}  runs={len(L['runs'])}")
    gl = [rs[i + 1][0] - rs[i][1] for i in range(len(rs) - 1)]
    print("  gaps sorted:", [round(g, 2) for g in sorted(gl, reverse=True)[:nlines + 2]])
json.dump(res, open("vo/segments.json", "w"), indent=1)


# --- narrator: DP alignment of runs -> 7 lines by expected length (text-proportional) + pause bonus
NARR_TXT = ["shhh dekhiye ye hai whitefly", "chhota sa par poore plant ka ras choos leta hai",
            "par jungle ka ek niyam hai kuch rang inse bardasht nahi hote", "peela aur neela",
            "aur phir shikari khud shikaar ban jaata hai",
            "dono taraf sticky waterproof non toxic indoor ho ya outdoor",
            "terrace ho greenhouse ya khet ye hai jungle ka naya kanoon"]
x = load(FILES["NARRATOR"][0])
rs, _ = runs(x)
print("narrator runs:", [(round(a, 2), round(b, 2)) for a, b in rs])
w = np.array([len(t.replace(" ", "")) for t in NARR_TXT], float)
speech = sum(b - a for a, b in rs)
exp = w / w.sum() * speech
N, K = len(rs), len(NARR_TXT)
INF = 1e9
best = np.full((K + 1, N + 1), INF)
arg = np.zeros((K + 1, N + 1), int)
best[0, 0] = 0
for k in range(1, K + 1):
    for j in range(1, N + 1):
        for i in range(k - 1, j):
            if best[k - 1, i] >= INF:
                continue
            dur = sum(b - a for a, b in rs[i:j])
            gap = rs[j][0] - rs[j - 1][1] if j < N else 1.0
            cost = best[k - 1, i] + ((dur - exp[k - 1]) / exp[k - 1]) ** 2 - 0.8 * gap
            if cost < best[k, j]:
                best[k, j], arg[k, j] = cost, i
j, bounds = N, []
for k in range(K, 0, -1):
    i = arg[k, j]
    bounds.append((i, j)); j = i
bounds.reverse()
lines = [dict(start=rs[i][0], end=rs[j - 1][1], runs=rs[i:j]) for i, j in bounds]
for L, t, e in zip(lines, NARR_TXT, exp):
    print(f"  {L['start']:.2f}-{L['end']:.2f} speech={sum(b-a for a,b in L['runs']):.2f} exp={e:.2f} | {t}")
res["NARRATOR"] = lines
json.dump(res, open("vo/segments.json", "w"), indent=1)
