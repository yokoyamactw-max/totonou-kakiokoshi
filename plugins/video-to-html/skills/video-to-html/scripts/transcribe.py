"""音声を取り出して mlx-whisper で文字起こしし、transcript.json / transcript.txt を作る。
使い方: python3 transcribe.py <workdir>
- meta.json の start/end 区間だけを処理し、時刻は元動画の絶対時刻にそろえる
- 無音で入る幻覚行（ご視聴ありがとうございました）を除去
- 取り出した音声が想定より短ければ警告（途中切れの検知）
- 同じ文が5回以上続く「ループ区間」を一覧表示（あとで large-v3 で聞き直す候補）
"""
import json, os, shutil, subprocess, sys

wd = os.path.abspath(sys.argv[1])
meta = json.load(open(os.path.join(wd, "meta.json")))
S, E = float(meta["start"]), float(meta["end"])
wav = os.path.join(wd, "audio.wav")
subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", str(S), "-to", str(E),
                "-i", os.path.join(wd, meta["media"]), "-vn", "-ac", "1", "-ar", "16000", wav], check=True)
got = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", wav],
                           capture_output=True, text=True).stdout.strip() or 0)
if got + 5 < (E - S):
    print(f"警告: 音声が {got:.0f}s しか取れていない（想定 {E-S:.0f}s）。素材の途中切れを疑うこと")

if not shutil.which("mlx_whisper"):
    sys.exit("mlx_whisper が見つかりません。`python3 check_env.py` で必要なソフトを確認してください")
subprocess.run(["mlx_whisper", wav, "--model", "mlx-community/whisper-large-v3-turbo", "--language", "ja",
                "--output-format", "json", "--output-name", "transcript", "--output-dir", wd,
                "--condition-on-previous-text", "False"],
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

tj = os.path.join(wd, "transcript.json")
d = json.load(open(tj))
bad = {"ご視聴ありがとうございました", "ご視聴ありがとうございました。"}
segs = []
for s in d["segments"]:
    if s["text"].strip() in bad:
        continue
    s["start"] += S
    s["end"] += S
    segs.append(s)
d["segments"] = segs
json.dump(d, open(tj, "w"), ensure_ascii=False)


def mmss(t):
    t = int(t)
    return f"{t // 60}:{t % 60:02d}"


open(os.path.join(wd, "transcript.txt"), "w").write(
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
for t, a, b, n in loops:
    print(f"ループ区間 {mmss(a)}-{mmss(b)} x{n}: {t[:30]}")
