"""画面の切り替わりを検出してスクショを撮る。
使い方: python3 shots.py <workdir> --mode fine|key|coarse
  fine   : 講義・スライド。一瞬しか映らない画面も拾う（5fps・差分12・間隔制限なし）
  key    : 画面共有の打ち合わせ。カーソル移動や入力で細かく変わるので要所だけ（2fps・差分16・12秒以上あける）
  coarse : 会場のプロジェクターをカメラで撮った映像など、ムラで毎フレーム変わるもの（2fps・差分14・15秒以上あける）
迷ったら fine で撮り、枚数が「長さ(分)×8」を超えたら key に切り替えて撮り直す。
meta.json の start/end 区間だけを対象にし、ファイル名は元動画の絶対秒（shot_1381.2.jpg）。
真っ黒・背景だけの画面と、直前60秒以内の同一画面は shots_drop/ に退避する（削除はしない）。
補助検出：画面の一部だけがスライドの録画（Zoomウェビナー等）では、文字だけの切り替えが画面全体の差分に
埋もれる。そこで全区間から「動かない画素」を自動で求め（顔映像・動画部分は除外）、その画素だけで変化を見る。
この補助検出は既存の3モード共通で、動かない画素が画面の30%未満（カメラ映像など）のときは自動でスキップする。
"""
import argparse, json, os, shutil, subprocess
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("workdir")
ap.add_argument("--mode", choices=["fine", "key", "coarse"], default="fine")
a = ap.parse_args()
wd = os.path.abspath(a.workdir)
meta = json.load(open(os.path.join(wd, "meta.json")))
S, E = float(meta["start"]), float(meta["end"])
video = os.path.join(wd, meta["media"])
FPS, TH, GAP = {"fine": (5, 12.0, 0), "key": (2, 16.0, 12), "coarse": (2, 14.0, 15)}[a.mode]
W, H = 160, 90
P_ON = 0.004          # 補助検出：静止画素のうち変化した画素の割合がこれを超えたら切り替わり（実データで調整）
MW, MH = 320, 180     # マスク・補助検出の解像度
PIX_TH = 25.0         # 補助検出の画素差分しきい値
STATIC_MIN = 0.30     # 静止画素がこれ未満なら補助検出をスキップ


def probe_duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return None


DUR = probe_duration(video) or float(meta.get("duration") or E)
E = min(E, DUR - 0.5)  # 終端ぎりぎりの時刻で ffmpeg が失敗しないようにする


def stream(fps, w, h):
    """区間を fps・w×h グレーで1枚ずつ読む（全部はメモリに溜めない）。"""
    pr = subprocess.Popen(["ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", str(S), "-to", str(E),
                           "-i", video, "-an", "-vf", f"fps={fps},scale={w}:{h},format=gray",
                           "-f", "rawvideo", "-"], stdout=subprocess.PIPE)
    k = 0
    while True:
        b = pr.stdout.read(w * h)
        if len(b) < w * h:
            break
        yield S + k / fps, np.frombuffer(b, np.uint8).astype(np.float32)
        k += 1
    pr.stdout.close()
    pr.wait()


def build_mask():
    """静止画素を求める。1fps で「2ペア連続して差が大きい」回数の割合が低い画素＝静止画素。
    連続変化だけ数えるのは、スライドの切り替え（1回きりの変化）で文字の画素が動く画素扱いにならないため。
    顔映像・動画のように変わり続ける部分だけが除外される。静止画素が少なすぎれば None。"""
    cnt, prev, pc, n = np.zeros(MW * MH, np.int32), None, None, 0
    for _, f in stream(1, MW, MH):
        if prev is not None:
            c = np.abs(f - prev) > 12
            if pc is not None:
                cnt += (c & pc)
                n += 1
            pc = c
        prev = f
    if n < 10:
        return None
    m = (cnt / n) < 0.03
    return m if m.mean() >= STATIC_MIN else None


def aux_times(mask):
    """静止画素だけで見た切り替わり。直前の採用から大きく変わり、2秒後も同じ画面（安定）なら採用。"""
    def ratio(x, y):
        return float((np.abs(x - y)[mask] > PIX_TH).mean())
    res, last, pend = [], None, []

    def judge(t, f, nxt):
        nonlocal last
        if f.mean() < 20:
            return
        if last is None:
            last = f
        elif ratio(f, last) > P_ON and ratio(nxt, f) < P_ON / 2:
            res.append(min(t + 0.5, E))  # 可変フレームレート録画だと切り替え時刻ちょうどは旧画面を返すことがあるので0.5秒後を撮る
            last = f

    for t, f in stream(2, MW, MH):
        pend.append((t, f))
        if len(pend) == 5:
            judge(pend[0][0], pend[0][1], pend[4][1])
            pend.pop(0)
    for t, f in pend:
        judge(t, f, pend[-1][1])
    return res


proc = subprocess.Popen(["ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", str(S), "-to", str(E),
                         "-i", video, "-an", "-vf", f"fps={FPS},scale={W}:{H},format=gray",
                         "-f", "rawvideo", "-"], stdout=subprocess.PIPE)
last, times, i = None, [], 0
while True:
    buf = proc.stdout.read(W * H)
    if len(buf) < W * H:
        break
    f = np.frombuffer(buf, np.uint8).astype(np.float32)
    t, i = S + i / FPS, i + 1
    if f.mean() < 20:
        continue
    if last is None or (np.abs(f - last).mean() > TH and (not times or t - times[-1] >= GAP)):
        times.append(t)
        last = f
proc.wait()
if a.mode == "fine":  # 切り替え直後のブレ（0.4秒以内の連続採用）は後ろ側だけ残す
    merged = []
    for t in times:
        if merged and t - merged[-1] <= 0.4:
            merged[-1] = t
        else:
            merged.append(t)
    times = merged

mask = build_mask()
added = 0
if mask is not None:
    # 既存の採用時刻の近くでも捨てない（既存側がフェード開始直後の中間フレームのことがある）。
    # 同じ画面かどうかは後段の重複判定（マスク付き）に任せる。
    extra = aux_times(mask)
    names = {f"{t:.1f}" for t in times}  # ファイル名が同じになる時刻は既存側だけ残す
    extra = [t for t in extra if f"{t:.1f}" not in names]
    added = len(extra)
    pairs = sorted([(t, False) for t in times] + [(t, True) for t in extra])
    times, is_aux = [p[0] for p in pairs], [p[1] for p in pairs]
else:
    is_aux = [False] * len(times)

out, drop = os.path.join(wd, "shots"), os.path.join(wd, "shots_drop")
for p in (out, drop):
    shutil.rmtree(p, ignore_errors=True)
    os.makedirs(p)
paths = []
for t in times:
    t = min(t, DUR - 0.5)
    p = os.path.join(out, f"shot_{t:.1f}.jpg")
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{t:.1f}", "-i", video,
                    "-frames:v", "1", "-vf", "scale=1280:-1", "-q:v", "4", p], check=True)
    paths.append(p)


def gray(p, w, h):
    b = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", p, "-vf", f"scale={w}:{h},format=gray",
                        "-f", "rawvideo", "-"], capture_output=True).stdout
    return np.frombuffer(b, np.uint8).astype(np.float32)


kept, empty, dup = [], 0, 0
thumbs = [gray(p, 64, 36) for p in paths]
fulls = {}


def changed_on_mask(i, j):
    """マスク上で2枚の画面が違うか。マスクなしなら False（従来どおり重複判定だけに任せる）。"""
    if mask is None:
        return False
    return float((np.abs(fulls[i] - fulls[j])[mask] > PIX_TH).mean()) >= P_ON


for i, (t, p) in enumerate(zip(times, paths)):
    gf = gray(p, MW, MH)
    g = gf.reshape(MH, MW)
    detail = np.abs(np.diff(g, axis=0)).mean() + np.abs(np.diff(g, axis=1)).mean()
    fulls[i] = gf
    if detail < 5:
        empty += 1
    elif any(abs(t - times[j]) <= 60 and np.abs(thumbs[i] - thumbs[j]).mean() < 6
             and not changed_on_mask(i, j) for j in kept[-8:]):
        dup += 1
    else:
        kept.append(i)
        if len(kept) > 9:
            fulls.pop(kept[-10], None)  # 重複判定に使う直近8枚以外は捨てる
        continue
    fulls.pop(i, None)
    shutil.move(p, os.path.join(drop, os.path.basename(p)))

# 補助側が安定した画面を撮れているとき、その直前2秒以内にある既存側の採用は切り替わり途中の
# 中間フレームなので、補助側を優先して退避する
superseded = 0
if mask is not None:
    for i in [i for i in kept if is_aux[i]]:
        for j in [j for j in kept if not is_aux[j] and 0 < times[i] - times[j] <= 2]:
            kept.remove(j)
            shutil.move(paths[j], os.path.join(drop, os.path.basename(paths[j])))
            superseded += 1

minutes = max((E - S) / 60, 1)
kept_aux = sum(1 for i in kept if is_aux[i]) if mask is not None else 0
print(f"mode={a.mode} candidates={len(times)} empty={empty} dup={dup} kept={len(kept)} "
      f"(目安上限 {int(minutes * 8)})")
print(f"補助検出で追加 {added} 枚（うち採用 {kept_aux} 枚、置き換えた中間フレーム {superseded} 枚）" if mask is not None
      else "補助検出はスキップ（静止画素が少ない映像）")
if a.mode == "fine" and len(kept) > minutes * 8:
    print("枚数が多すぎる。画面共有なら --mode key、投影のカメラ撮影なら --mode coarse で撮り直すこと")
