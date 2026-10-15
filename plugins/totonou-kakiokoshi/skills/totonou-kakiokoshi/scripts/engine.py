"""文字起こしエンジンの選択と実行（transcribe.py と check_env.py が使う）。

- mlx    : Apple シリコンの Mac 専用。pipx で入れた mlx_whisper コマンドを呼ぶ（速い）
- faster : Windows・Intel Mac・Linux 用。faster-whisper を専用環境（venv）に入れて CPU で動かす
           専用環境の場所は ~/.totonou-kakiokoshi/venv（環境変数 TOTONOU_KAKIOKOSHI_HOME で変更可）
"""
import json, os, platform, shutil, subprocess, sys, tempfile

HOME = os.path.abspath(os.path.expanduser(os.environ.get("TOTONOU_KAKIOKOSHI_HOME", "~/.totonou-kakiokoshi")))
VENV = os.path.join(HOME, "venv")
WORKER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fw_worker.py")

MODELS = {
    "mlx": ("mlx-community/whisper-large-v3-turbo", "mlx-community/whisper-large-v3-mlx"),
    "faster": ("large-v3-turbo", "large-v3"),
}


def apple_silicon():
    return platform.system() == "Darwin" and platform.machine() == "arm64"


def venv_python():
    if os.name == "nt":
        return os.path.join(VENV, "Scripts", "python.exe")
    return os.path.join(VENV, "bin", "python")


def has_mlx():
    return shutil.which("mlx_whisper") is not None


def has_faster():
    py = venv_python()
    if not os.path.exists(py):
        return False
    r = subprocess.run([py, "-c", "import faster_whisper"], capture_output=True)
    return r.returncode == 0


def pick(name="auto"):
    if name == "mlx":
        return "mlx" if apple_silicon() and has_mlx() else None
    if name == "faster":
        return "faster" if has_faster() else None
    if apple_silicon() and has_mlx():
        return "mlx"
    if has_faster():
        return "faster"
    return None


def _env():
    e = dict(os.environ)
    e.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
    e.setdefault("HF_HUB_VERBOSITY", "error")
    e["PYTHONIOENCODING"] = "utf-8"
    return e


def _mlx(wav, model, fmt):
    out_dir = tempfile.mkdtemp(prefix="tk_mlx_")
    subprocess.run(["mlx_whisper", wav, "--model", model, "--language", "ja",
                    "--output-format", fmt, "--output-name", "out", "--output-dir", out_dir,
                    "--condition-on-previous-text", "False"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    return os.path.join(out_dir, f"out.{fmt}")


def _faster(wav, model, total):
    out = os.path.join(tempfile.mkdtemp(prefix="tk_fw_"), "out.json")
    subprocess.run([venv_python(), WORKER, wav, model, out, str(total)], env=_env(), check=True)
    return json.load(open(out, encoding="utf-8"))


def transcribe(eng, wav, total):
    """[{start, end, text}, ...] を返す（時刻は wav の先頭からの秒）。"""
    if eng == "mlx":
        d = json.load(open(_mlx(wav, MODELS["mlx"][0], "json"), encoding="utf-8"))
        return [{"start": s["start"], "end": s["end"], "text": s["text"]} for s in d["segments"]]
    return _faster(wav, MODELS["faster"][0], total)


def redo_text(eng, wav):
    """短い区間を精度の高いモデル（large-v3）で聞き直し、本文だけ返す。"""
    if eng == "mlx":
        return open(_mlx(wav, MODELS["mlx"][1], "txt"), encoding="utf-8").read().strip()
    return "".join(s["text"] for s in _faster(wav, MODELS["faster"][1], 0)).strip()
