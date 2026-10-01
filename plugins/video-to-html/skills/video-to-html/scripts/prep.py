"""整形用に書き起こしをブロック分けし、clean/in_N.json に分割する。
使い方: python3 prep.py <workdir> [chunk数]
chunk数を省略すると 1チャンク≒1.8万字 を目安に自動で決める（Sonnet 1体が確実に読み切れる量）。
"""
import json, math, os, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import blocks

wd = os.path.abspath(sys.argv[1])
meta, segs, shots = blocks.load(wd)
gs = blocks.groups(meta, shots)
tx = blocks.texts(gs, segs)
items = [{"t": int(g[0][0]), "text": x} for g, x in zip(gs, tx)]
assert len({b["t"] for b in items}) == len(items), "ブロックの秒キーが重複"

total = sum(len(b["text"]) for b in items)
n = int(sys.argv[2]) if len(sys.argv) > 2 else max(1, math.ceil(total / 18000))
cd = os.path.join(wd, "clean")
shutil.rmtree(cd, ignore_errors=True)
os.makedirs(cd)
target, chunks, acc = total / n, [[]], 0
for b in items:
    if acc >= target and len(chunks) < n:
        chunks.append([])
        acc = 0
    chunks[-1].append(b)
    acc += len(b["text"])
for i, c in enumerate(chunks, 1):
    json.dump(c, open(os.path.join(cd, f"in_{i}.json"), "w"), ensure_ascii=False, indent=1)
print(f"shots={len(shots)} blocks={len(items)} chars={total} chunks={[len(c) for c in chunks]}")
