"""必要なソフトがそろっているかを確認し、足りないものの入れ方を表示する。
使い方: python3 check_env.py
すべてそろっていれば「OK」、足りなければ「NG」と入れ方を出して終了コード1。
"""
import importlib.util, platform, shutil, sys

missing = []

if platform.system() != "Darwin" or platform.machine() != "arm64":
    missing.append(("Apple シリコン（M1以降）の Mac",
                    "文字起こしに使う mlx-whisper は Apple シリコンの Mac でしか動きません"))

for cmd, how in [("ffmpeg", "brew install ffmpeg"),
                 ("ffprobe", "brew install ffmpeg"),
                 ("yt-dlp", "brew install yt-dlp（Loom・YouTube などのURLから取り込むときだけ必要）"),
                 ("mlx_whisper", "brew install pipx && pipx install mlx-whisper && pipx ensurepath（そのあとターミナルを開き直す）")]:
    if not shutil.which(cmd):
        missing.append((cmd, how))

if importlib.util.find_spec("numpy") is None:
    missing.append(("numpy（python3 から使えること）", "brew install numpy"))

if sys.version_info < (3, 9):
    missing.append(("Python 3.9 以上", "brew install python"))

if not missing:
    print("OK: 必要なソフトはすべてそろっています")
    sys.exit(0)

print("NG: 次のものが足りません")
for name, how in missing:
    print(f"- {name}: {how}")
print("\nHomebrew が未導入なら https://brew.sh の手順で先に入れてください。"
      "\nまとめて入れるなら: brew install python ffmpeg yt-dlp numpy pipx && pipx install mlx-whisper && pipx ensurepath")
sys.exit(1)
