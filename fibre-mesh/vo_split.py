"""Split each VO file into its script lines: voiced runs -> DP alignment to text-length-proportional durations
(with a bonus for cutting at long pauses). Writes vo/segments.json {voice: [{start,end,runs}]}."""
import json, subprocess
import numpy as np

SR = 16000
SCRIPT = {
    "ANCHOR": ("vo/devi.mp3", [
        "breaking news baarish ke baad shehar ki har doosri chhat se tapak raha hai paani",
        "chaliye seedhe chalte hain hamare reporter ke paas",
        "toh aakhir galti kahan ho rahi hai",
        "toh is monsoon leakage ki nahi sirf mausam ki khabar"]),
    "REPORTER": ("vo/anika.mp3", [
        "ji main is waqt ek terrace par hoon dekhiye ye cracks",
        "har saal waterproofing phir bhi leakage wapas",
        "aur ye hai buildingshop ka fiberglass mesh ek sau paintalis gsm chaubees inch chauda pachaas meter roll",
        "terrace deewar ke cracks plaster sab jagah kaam aata hai"]),
    "MISTRI": ("vo/ravikant.mp3", [
        "galti ye hai ki sirf coating lagate ho usko pakadne wala kuch nahi",
        "pehli coat lagao mesh bichhao dabao phir doosri coat",
        "coating mazboot rehti hai crack ke upar bhi pakad bani rehti hai"]),
}


def load(p):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", p, "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768


def runs(x, thr_db=-40):
    h = SR // 100
    n = len(x) // h
    db = 20 * np.log10(np.sqrt(np.mean(x[:n * h].reshape(n, h) ** 2, 1)) + 1e-9)
    out, s = [], None
    for i, v in enumerate(db > thr_db):
        if v and s is None:
            s = i
        if not v and s is not None:
            out.append([s / 100, i / 100]); s = None
    if s is not None:
        out.append([s / 100, n / 100])
    m = [out[0]]
    for a, b in out[1:]:
        if a - m[-1][1] < 0.06:
            m[-1][1] = b
        else:
            m.append([a, b])
    return [r for r in m if r[1] - r[0] > 0.05]


res = {}
for voice, (p, texts) in SCRIPT.items():
    rs = runs(load(p))
    w = np.array([len(t.replace(" ", "")) for t in texts], float)
    exp = w / w.sum() * sum(b - a for a, b in rs)
    N, K = len(rs), len(texts)
    best = np.full((K + 1, N + 1), 1e9)
    arg = np.zeros((K + 1, N + 1), int)
    best[0, 0] = 0
    for k in range(1, K + 1):
        for j in range(1, N + 1):
            for i in range(k - 1, j):
                if best[k - 1, i] >= 1e9:
                    continue
                dur = sum(b - a for a, b in rs[i:j])
                gap = rs[j][0] - rs[j - 1][1] if j < N else 1.0
                c = best[k - 1, i] + ((dur - exp[k - 1]) / exp[k - 1]) ** 2 - 1.2 * gap
                if c < best[k, j]:
                    best[k, j], arg[k, j] = c, i
    j, bounds = N, []
    for k in range(K, 0, -1):
        i = arg[k, j]; bounds.append((i, j)); j = i
    bounds.reverse()
    res[voice] = [dict(start=rs[i][0], end=rs[j - 1][1], runs=rs[i:j]) for i, j in bounds]
    print(voice)
    for L, t, e in zip(res[voice], texts, exp):
        sp = sum(b - a for a, b in L["runs"])
        print(f"  {L['start']:6.2f}-{L['end']:6.2f} speech={sp:.2f} exp={e:.2f} | {t[:60]}")
json.dump(res, open("vo/segments.json", "w"), indent=1)
