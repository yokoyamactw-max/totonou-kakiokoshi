"""prep.py と build.py が共有するブロック分けのルール（両者がずれると整形文が表示されない）。
- スクショあり：8秒未満で続くスクショは1ブロック（最大6枚・60秒まで）
- スクショなし（音声）：3分ごと
- 画面が6分以上変わらない区間は、5分ごとに文章だけのブロックを挟む
- 区間の開始（meta.start）より前にブロックを作らない
"""
import json, os, re


def load(wd):
    meta = json.load(open(os.path.join(wd, "meta.json")))
    segs = json.load(open(os.path.join(wd, "transcript.json")))["segments"]
    shots = []
    sd = os.path.join(wd, "shots")
    if os.path.isdir(sd):
        for n in os.listdir(sd):
            m = re.search(r"_(\d+(?:\.\d+)?)\.jpg$", n)
            if m:
                shots.append((float(m.group(1)), os.path.join(sd, n)))
    shots.sort()
    return meta, segs, shots


def groups(meta, shots):
    S, E = float(meta["start"]), float(meta["end"])
    if shots:
        gs = []
        for t, p in shots:
            g = gs[-1] if gs else None
            if g and t - g[-1][0] < 8 and len(g) < 6 and t - g[0][0] < 60:
                g.append((t, p))
            else:
                gs.append([(t, p)])
        if gs[0][0][0] > S + 1:
            gs.insert(0, [(S, None)])
    else:
        gs = [[(float(t), None)] for t in range(int(S), int(E), 180)]
    out = []
    for i, g in enumerate(gs):
        out.append(g)
        nxt = gs[i + 1][0][0] if i + 1 < len(gs) else E
        t = g[0][0] + 300
        while nxt - g[0][0] > 360 and t < nxt - 60:
            out.append([(float(t), None)])
            t += 300
    return out


def texts(groups_, segs):
    res = []
    for i, g in enumerate(groups_):
        t = g[0][0]
        nx = groups_[i + 1][0][0] if i + 1 < len(groups_) else float("inf")
        res.append("".join(s["text"] for s in segs if t <= s["start"] < nx).strip())
    return res


def ts(sec):
    s = int(sec)
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}"
