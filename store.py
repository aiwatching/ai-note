"""存储层：~/.eng/entries.jsonl 读写 + 队列排序。纯 stdlib，不用数据库。

数据量四位数以内，全量读进内存就行。默认放仓库的 engdata/，ENG_HOME 可覆盖。
"""
import datetime
import json
import os

def path(name):
    """数据默认在仓库的 engdata/ 里，这样云端会话 clone 下来就能直接用。
    ENG_HOME 可覆盖（测试用）。"""
    home = os.environ.get("ENG_HOME")
    if not home:
        home = os.path.join(os.path.dirname(os.path.abspath(__file__)), "engdata")
    return os.path.join(os.path.expanduser(home), name)

def data_path():
    return path("entries.jsonl")

def seeds_path():
    return path("seeds.txt")

def _ensure():
    p = data_path()
    os.makedirs(os.path.dirname(p), exist_ok=True)
    if not os.path.exists(p):
        open(p, "w").close()
    return p

def load():
    with open(_ensure(), encoding="utf-8") as f:
        return [json.loads(x) for x in f if x.strip()]

def save_all(entries):
    """原子写：先写 .tmp 再 os.replace。"""
    p = _ensure()
    with open(p + ".tmp", "w", encoding="utf-8") as f:
        f.writelines(json.dumps(e, ensure_ascii=False) + "\n" for e in entries)
    os.replace(p + ".tmp", p)

def add(entry):
    entry.setdefault("id", datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")[:18])
    entry.setdefault("created", datetime.date.today().isoformat())
    entry.setdefault("said", "")
    entry.setdefault("better", "")
    entry.setdefault("used", False)
    entry.setdefault("attempts", [])
    save_all(load() + [entry])
    return entry

def update(entry):
    """按 id 覆盖已有条目；没有就追加。"""
    entries = load()
    for i, e in enumerate(entries):
        if e.get("id") == entry.get("id"):
            entries[i] = entry
            break
    else:
        entries.append(entry)
    save_all(entries)
    return entry

def queue():
    """未划掉的条目：练得少的、早加的排前面。就这样，没有 SRS。"""
    return sorted([e for e in load() if not e.get("used")],
                  key=lambda e: (len(e.get("attempts", [])), e.get("created", "")))

def seeds():
    """冷启动题库 {中文题面: [参考说法]}。顶格行是题面，缩进行是它的参考说法。"""
    out, cur = {}, None
    if not os.path.exists(seeds_path()):
        return out
    with open(seeds_path(), encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if raw[:1].isspace() and cur:
                out[cur].append(line)
            else:
                cur = line
                out[cur] = []
    return out
