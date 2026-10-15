"""faster-whisper で文字起こしする（engine.py が専用環境の Python で呼ぶ。直接は使わない）。
使い方: <専用環境の python> fw_worker.py <音声.wav> <モデル名> <出力.json> [<音声の長さ秒>]
CPU で動かすので時間がかかる。5分ぶん進むごとに進捗と残り時間の目安を表示する。
"""
import json, os, sys, time

for _s in (sys.stdout, sys.stderr):
    _s.reconfigure(encoding="utf-8")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
from faster_whisper import WhisperModel

wav, model, out = sys.argv[1:4]
total = float(sys.argv[4]) if len(sys.argv) > 4 else 0.0

print(f"モデル {model} を読み込み中（初回は約1.6GBをダウンロード）", flush=True)
m = WhisperModel(model, device="cpu", compute_type="int8", cpu_threads=os.cpu_count() or 4)
segments, _ = m.transcribe(wav, language="ja", beam_size=1, condition_on_previous_text=False)

res, t0, last = [], time.time(), 0.0
for s in segments:
    res.append({"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text})
    if total > 600 and s.end - last >= 300:
        last = s.end
        spent = time.time() - t0
        left = spent / s.end * (total - s.end)
        print(f"進捗 {s.end / 60:.0f}/{total / 60:.0f}分（経過 {spent / 60:.1f}分・残り目安 {left / 60:.0f}分）", flush=True)
json.dump(res, open(out, "w", encoding="utf-8"), ensure_ascii=False)
