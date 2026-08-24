#!/usr/bin/env python3
"""eng skill 的薄壳：复用 web.py 的 action 函数，输出 JSON 给 Claude 读。

重复判定必须走这里，不许靠眼睛看 —— 词干化 + loose match 是确定性算法，
和 CLI、网页版完全一致，三个界面共用 ~/.eng/entries.jsonl 一份数据。

  python3 drill.py review                   复习清单：今天练没练、哪些该用出来了
  python3 drill.py next                     下一题
  python3 drill.py say <id> <text>          存一遍，返回重复分析
  python3 drill.py finish <id> [better]     收尾，返回内置参考说法
  python3 drill.py add <zh>                 加一条
  python3 drill.py used <id>                划掉
  python3 drill.py list                     看队列
"""
import json
import os
import pathlib
import sys

# skill 模式下 Claude 自己就是那个 LLM，别再花钱调 DeepSeek
os.environ["ENG_LLM"] = "off"
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))

import remind  # noqa: E402
import store   # noqa: E402
import web     # noqa: E402


def out(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def main():
    a = sys.argv[1:]
    cmd = a[0] if a else "next"

    if cmd == "review":
        return out(remind.review())

    if cmd == "next":
        s = web.state()
        e = s["entry"]
        if not e:
            return out({"empty": True, "hint": "队列空了，用 add 加一条"})
        return out({"id": e["id"], "zh": e["zh"], "source": e.get("source", ""),
                    "past": [x["text"] for x in e.get("attempts", [])],
                    "better": e.get("better", ""), "queue_len": len(s["queue"])})

    if cmd == "say":
        r = web.attempt({"id": a[1], "text": " ".join(a[2:])})
        if "error" in r:
            return out(r)
        marked = r["html"].replace("<mark>", "【").replace("</mark>", "】")
        return out({"marked": marked, "repeated": r["repeated"], "fresh": r["fresh"]})

    if cmd == "finish":
        r = web.finish({"id": a[1], "better": a[2] if len(a) > 2 else ""})
        return out({"seed_refs": r["refs"]})

    if cmd == "add":
        return out(web.add({"zh": " ".join(a[1:])}))

    if cmd == "used":
        return out(web.used({"id": a[1]}))

    if cmd == "list":
        return out([{"id": e["id"][-6:], "zh": e["zh"], "n": len(e.get("attempts", [])),
                     "better": e.get("better", "")} for e in store.queue()])

    return out({"error": "未知命令 " + cmd})


if __name__ == "__main__":
    main()
