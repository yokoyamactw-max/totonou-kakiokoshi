"""音声を取り出して文字起こしし、transcript.json / transcript.txt を作る。
使い方: python3 transcribe.py <workdir> [--engine auto|mlx|faster]
        python3 transcribe.py <workdir> --redo 開始秒 終了秒   # その区間だけ large-v3 で聞き直して表示
- 文字起こしエンジン（auto の選び方）
    Apple シリコンの Mac で mlx_whisper があれば mlx-whisper（速い）
    それ以外（Windows・Intel Mac など）は faster-whisper（check_env.py --setup で入れる専用環境）
- meta.json の start/end 区間だけを処理し、時刻は元動画の絶対時刻にそろえる
- 無音で入る幻覚行（ご視聴ありがとうございました）を除去
- 取り出した音声が想定より短ければ警告（途中切れの検知）
- 同じ文が5回以上続く「ループ区間」を一覧表示（あとで --redo で聞き直す候補）
"""
import argparse, json, os, platform, subprocess, sys

for _s in (sys.stdout, sys.stderr):
    _s.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine

ap = argparse.ArgumentParser()
ap.add_argument("workdir")
ap.add_argument("--engine", choices=["auto", "mlx", "faster"], default="auto")
ap.add_argument("--redo", nargs=2, type=float, metavar=("START", "END"))
a = ap.parse_args()

wd = os.path.abspath(a.workdir)
meta = json.load(open(os.path.join(wd, "meta.json"), encoding="utf-8"))
S, E = float(meta["start"]), float(meta["end"])
media = os.path.join(wd, meta["media"])

eng = engine.pick(a.engine)
if eng is None:
    sys.exit("文字起こしエンジンが見つかりません。`python3 check_env.py` で必要なソフトを確認してください")


def cut(src_start, src_end, wav):
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", str(src_start), "-to", str(src_end),
                    "-i", media, "-vn", "-ac", "1", "-ar", "16000", wav], check=True)


# ---- 一部区間の聞き直し（ループ区間・桁のおかしい数字の確認用） ----
if a.redo:
    rs, re_ = a.redo
    part = os.path.join(wd, f"redo_{int(rs)}_{int(re_)}.wav")
    cut(rs, re_, part)
    print(f"[{eng}・large-v3 で聞き直し {int(rs)}s〜{int(re_)}s]")
    print(engine.redo_text(eng, part))
    sys.exit(0)

wav = os.path.join(wd, "audio.wav")
cut(S, E, wav)
got = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", wav],
                           capture_output=True, text=True).stdout.strip() or 0)
if got + 5 < (E - S):
    print(f"警告: 音声が {got:.0f}s しか取れていない（想定 {E-S:.0f}s）。素材の途中切れを疑うこと")

print(f"文字起こしエンジン: {eng}（{platform.system()} {platform.machine()}）", flush=True)
segs_raw = engine.transcribe(eng, wav, got or (E - S))

bad = {"ご視聴ありがとうございました", "ご視聴ありがとうございました。"}
segs = []
for s in segs_raw:
    if s["text"].strip() in bad:
        continue
    s["start"] += S
    s["end"] += S
    segs.append(s)
json.dump({"engine": eng, "segments": segs}, open(os.path.join(wd, "transcript.json"), "w", encoding="utf-8"),
          ensure_ascii=False)


def mmss(t):
    t = int(t)
    return f"{t // 60}:{t % 60:02d}"


open(os.path.join(wd, "transcript.txt"), "w", encoding="utf-8").write(
    "".join(f"[{mmss(x['start'])}] {x['text'].strip()}\n" for x in segs))

# ループ区間の検出
loops, cur = [], None
for s in segs:
    t = s["text"].strip()
    if cur and t == cur[0]:
        cur[2], cur[3] = s["end"], cur[3] + 1
    else:
        if cur and cur[3] >= 5:
            loops.append(cur)
        cur = [t, s["start"], s["end"], 1]
if cur and cur[3] >= 5:
    loops.append(cur)

print(f"segments={len(segs)} chars={sum(len(x['text']) for x in segs)} "
      f"covers={mmss(segs[0]['start']) if segs else '-'}→{mmss(segs[-1]['end']) if segs else '-'}")
for t, s0, s1, n in loops:
    print(f"ループ区間 {mmss(s0)}-{mmss(s1)} x{n}: {t[:30]}  → 聞き直し: --redo {int(s0)} {int(s1)}")
