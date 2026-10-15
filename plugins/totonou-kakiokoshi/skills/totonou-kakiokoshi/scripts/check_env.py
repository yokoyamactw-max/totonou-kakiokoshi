"""必要なソフトがそろっているかを確認し、足りないものの入れ方を表示する。
使い方: python3 check_env.py           # 確認だけ（Windows では python check_env.py）
        python3 check_env.py --setup   # 文字起こし用の専用環境（faster-whisper）を作る。Windows・Intel Mac で使う
すべてそろっていれば「OK」、足りなければ「NG」と入れ方を出して終了コード1。
"""
import argparse, importlib.util, os, platform, shutil, subprocess, sys, venv

for _s in (sys.stdout, sys.stderr):
    _s.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine

ap = argparse.ArgumentParser()
ap.add_argument("--setup", action="store_true", help="faster-whisper の専用環境を作り、モデルも用意する")
a = ap.parse_args()

OS = platform.system()
WIN = OS == "Windows"
MAC = OS == "Darwin"
PY = "python" if WIN else "python3"
here = os.path.dirname(os.path.abspath(__file__))


def run(cmd):
    print("$ " + " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, env=engine._env())


if a.setup:
    if sys.version_info < (3, 10):
        sys.exit("Python 3.10 以上が必要です。新しい Python を入れてから、もう一度実行してください")
    print(f"専用環境を作ります: {engine.VENV}", flush=True)
    if not os.path.exists(engine.venv_python()):
        venv.EnvBuilder(with_pip=True, clear=False).create(engine.VENV)
    vp = engine.venv_python()
    run([vp, "-m", "pip", "install", "--upgrade", "--quiet", "pip"])
    # onnxruntime は音声区間検出（使っていない）にしか要らず、Intel Mac 用が配布されていないので入れない。
    # av 19 は faster-whisper と組み合わせると落ちるので 18 以下に固定する。
    run([vp, "-m", "pip", "install", "--quiet", "ctranslate2", "tokenizers", "huggingface_hub", "tqdm", "av<19"])
    run([vp, "-m", "pip", "install", "--quiet", "--no-deps", "faster-whisper"])
    if subprocess.run([vp, "-c", "import ctranslate2"], capture_output=True).returncode != 0:
        sys.exit("文字起こしの部品（ctranslate2）が読み込めません。"
                 + ("Visual C++ 再頒布可能パッケージを入れてから、もう一度 --setup を実行してください:\n"
                    "  winget install --id Microsoft.VCRedist.2015+.x64 -e" if WIN else
                    "表示されたエラーを確認してください"))
    print("文字起こしモデル（約1.6GB）を準備します。回線によって数分〜20分ほどかかります", flush=True)
    run([vp, "-c", "from faster_whisper import WhisperModel; WhisperModel('large-v3-turbo', device='cpu', compute_type='int8'); print('モデルの準備ができました')"])
    print("専用環境の用意ができました。続けて確認します\n", flush=True)

missing = []
if WIN and platform.machine().upper() in ("ARM64", "AARCH64"):
    missing.append(("x64 版の Windows", "Windows on ARM（Snapdragon 搭載機など）では文字起こしエンジンが動きません"))
for cmd in ("ffmpeg", "ffprobe"):
    if not shutil.which(cmd):
        missing.append((cmd, "winget install --id yt-dlp.yt-dlp -e（ffmpeg も一緒に入る。それでも見つからなければ"
                        " winget install --id Gyan.FFmpeg -e）" if WIN else
                        "brew install ffmpeg" if MAC else "sudo apt install ffmpeg"))
if not shutil.which("yt-dlp"):
    missing.append(("yt-dlp（Loom・YouTube などのURLから取り込むときだけ必要）",
                    "winget install --id yt-dlp.yt-dlp -e" if WIN else
                    "brew install yt-dlp" if MAC else f"{PY} -m pip install --user yt-dlp"))
if importlib.util.find_spec("numpy") is None:
    missing.append((f"numpy（{PY} から使えること）",
                    f"{PY} -m pip install numpy" if WIN else
                    "brew install numpy" if MAC else "sudo apt install python3-numpy"))
if sys.version_info < (3, 10):
    missing.append(("Python 3.10 以上", "winget install --id Python.Python.3.12 -e" if WIN else "brew install python"))

eng = engine.pick()
if eng is None:
    if engine.rosetta():
        missing.append(("文字起こしエンジン", f"Intel 用の Python（{sys.executable}）で動いています。"
                        "/opt/homebrew の Homebrew と Python を入れると速い mlx-whisper が使えます。"
                        f"今のままでも python3 \"{os.path.join(here, 'check_env.py')}\" --setup で faster-whisper が使えます"))
    elif engine.apple_silicon():
        missing.append(("文字起こしエンジン mlx-whisper",
                        "brew install pipx && pipx install mlx-whisper && pipx ensurepath（そのあとターミナルを開き直す）"))
    else:
        missing.append(("文字起こしエンジン faster-whisper", f"{PY} \"{os.path.join(here, 'check_env.py')}\" --setup"
                        "（専用環境を作ってモデルを準備する。10〜20分ほど）"
                        + ("。先に winget install --id Microsoft.VCRedist.2015+.x64 -e も必要" if WIN else "")))

print(f"パソコン: {OS} {platform.machine()} / Python {platform.python_version()}（{sys.executable}）")
if not missing:
    note = "（Apple シリコンの Mac 用・速い）" if eng == "mlx" else "（CPU で動かすので時間がかかる。1時間半の動画で30分〜1時間半ほど）"
    print(f"文字起こしエンジン: {eng}{note}")
    print("OK: 必要なソフトはすべてそろっています")
    sys.exit(0)

print("NG: 次のものが足りません")
for name, how in missing:
    print(f"- {name}: {how}")
if WIN:
    print("\nwinget で入れたあとは、Claude Code（またはターミナル）を一度閉じて開き直してください。"
          "\nまとめて入れるなら（PowerShell）: winget install --id Python.Python.3.12 -e ;"
          " winget install --id Microsoft.VCRedist.2015+.x64 -e ; winget install --id yt-dlp.yt-dlp -e"
          f"\n→ 開き直してから: python -m pip install numpy ; python \"{os.path.join(here, 'check_env.py')}\" --setup")
elif MAC:
    print("\nHomebrew が未導入なら https://brew.sh の手順で先に入れてください。")
    if engine.apple_silicon():
        print("まとめて入れるなら: brew install python ffmpeg yt-dlp numpy pipx && pipx install mlx-whisper && pipx ensurepath")
    else:
        print(f"まとめて入れるなら: brew install python ffmpeg yt-dlp numpy && python3 \"{os.path.join(here, 'check_env.py')}\" --setup")
sys.exit(1)
