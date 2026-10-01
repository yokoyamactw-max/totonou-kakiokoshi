"""素材を作業フォルダに取り込み、media.mp4 と meta.json を作る。

使い方（どれか1つ）:
  python3 fetch.py <workdir> --file /path/to/video.mp4
  python3 fetch.py <workdir> --hls  https://.../video.m3u8     # UTAGE など（audio.m3u8 も可）
  python3 fetch.py <workdir> --drive <DriveファイルID>          # 「リンクを知っている全員」共有が必要
  python3 fetch.py <workdir> --url  https://www.loom.com/share/... # Loom・YouTube・Vimeo など（yt-dlp）
オプション:
  --start 秒 --end 秒   一部区間だけ処理したいとき（例: 23:00〜25:40 → --start 1380 --end 1540）

取り込み後、実サイズ・再生時間・音声の長さを必ず突き合わせる。
（Driveからの取得が途中で切れ、末尾7分半を落としかけた事故の再発防止）
"""
import argparse, json, os, re, subprocess, sys, urllib.parse, urllib.request

ap = argparse.ArgumentParser()
ap.add_argument("workdir")
g = ap.add_mutually_exclusive_group(required=True)
g.add_argument("--file")
g.add_argument("--hls")
g.add_argument("--drive")
g.add_argument("--url")
ap.add_argument("--start", type=float, default=0.0)
ap.add_argument("--end", type=float, default=None)
a = ap.parse_args()

wd = os.path.abspath(os.path.expanduser(a.workdir))
os.makedirs(wd, exist_ok=True)
media = os.path.join(wd, "media.mp4")


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, **kw)


def probe(path, entries, stream=None):
    cmd = ["ffprobe", "-v", "error"]
    if stream:
        cmd += ["-select_streams", stream]
    cmd += ["-show_entries", entries, "-of", "csv=p=0", path]
    out = subprocess.run(cmd, capture_output=True, text=True).stdout.strip()
    return out


if a.file:
    src = os.path.abspath(os.path.expanduser(a.file))
    if os.path.exists(media) or os.path.islink(media):
        os.remove(media)
    os.symlink(src, media)
    expected_bytes = os.path.getsize(src)

elif a.url:  # Loom・YouTube・Vimeo など、yt-dlp が対応しているページ
    src_dir = os.path.join(wd, "src")
    os.makedirs(src_dir, exist_ok=True)
    try:
        run(["yt-dlp", "--no-warnings", "--no-playlist", "-f", "bv*+ba/b", "--merge-output-format", "mp4",
             "-o", os.path.join(src_dir, "source.%(ext)s"), a.url])
    except FileNotFoundError:
        sys.exit("yt-dlp が見つかりません。`brew install yt-dlp` で入れてください")
    except subprocess.CalledProcessError:
        sys.exit("このURLからは取得できませんでした。ログインが必要なページなら、動画を保存して --file で渡してください")
    got = [f for f in os.listdir(src_dir) if f.startswith("source.") and not f.endswith((".part", ".ytdl"))]
    if not got:
        sys.exit("取得したファイルが見つかりません（途中で止まった可能性）")
    src = os.path.join(src_dir, sorted(got, key=lambda f: os.path.getsize(os.path.join(src_dir, f)))[-1])
    if os.path.exists(media) or os.path.islink(media):
        os.remove(media)
    os.symlink(src, media)
    expected_bytes = os.path.getsize(src)

elif a.hls:
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", a.hls, "-c", "copy", media])
    expected_bytes = None

else:  # Google Drive（大容量はウイルススキャン確認画面を経由する）
    fid = a.drive
    cj = os.path.join(wd, "cookies.txt")
    probe_html = os.path.join(wd, "drive_probe.html")
    run(["curl", "-sL", "-c", cj, "-o", probe_html,
         f"https://drive.usercontent.google.com/download?id={fid}&export=download"])
    h = open(probe_html, encoding="utf-8", errors="ignore").read()
    if "<html" not in h[:200].lower():
        os.replace(probe_html, media)  # 小さいファイルは直接落ちてくる
        url = None
    else:
        act = re.search(r'<form[^>]+action="([^"]+)"', h)
        fields = dict(re.findall(r'<input[^>]+type="hidden"[^>]+name="([^"]+)"[^>]+value="([^"]*)"', h))
        if not act:
            sys.exit("Driveから取得できません。共有を『リンクを知っている全員』にしてもらってください")
        url = act.group(1) + "?" + urllib.parse.urlencode(fields)
    expected_bytes = None
    if url:
        head = subprocess.run(["curl", "-sI", "-b", cj, url], capture_output=True, text=True).stdout
        m = re.search(r"(?im)^content-length:\s*(\d+)", head)
        expected_bytes = int(m.group(1)) if m else None
        # 途中で切れても -C - で続きから取り直す（最大5回）
        for _ in range(5):
            subprocess.run(["curl", "-sL", "-b", cj, "-C", "-", "-o", media, url])
            if expected_bytes is None or os.path.getsize(media) >= expected_bytes:
                break

# ---- 検証 ----
size = os.path.getsize(os.path.realpath(media))
if expected_bytes and size < expected_bytes:
    sys.exit(f"取り込みが途中で切れています: {size} / {expected_bytes} bytes")
dur = float(probe(media, "format=duration") or 0)
adur = probe(media, "stream=duration", "a:0")
has_video = bool(probe(media, "stream=codec_type", "v:0"))
end = a.end if a.end else dur
meta = {"media": "media.mp4", "duration": dur, "start": a.start, "end": end,
        "kind": "video" if has_video else "audio", "bytes": size}
json.dump(meta, open(os.path.join(wd, "meta.json"), "w"), ensure_ascii=False, indent=1)
print(json.dumps(meta, ensure_ascii=False))
if adur:
    try:
        if float(adur) + 5 < dur:
            print(f"警告: 音声トラック({float(adur):.0f}s)が全体({dur:.0f}s)より短い。途中切れの可能性あり")
    except ValueError:
        pass
