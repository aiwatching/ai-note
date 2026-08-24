#!/usr/bin/env python3
"""复习检查 + 每天早上的提醒。

  python3 remind.py            打印复习清单
  python3 remind.py --notify   今天没练才弹 macOS 通知；练过了就闭嘴

设计文档第 1.4 节的次要问题：手写的练习列表"记完就沉底，一周后不会翻"。
所以出队条件只有一个 —— 在真实会议里用出来过。练得再多也不算完成，
这里就是把这件事顶到你脸上：练过 3 遍还没划掉的，说明你还没真的用出来。
"""
import datetime
import subprocess
import sys

import store


def _last(e):
    a = e.get("attempts", [])
    return a[-1].get("date", "") if a else e.get("created", "")


def review():
    today = datetime.date.today()
    entries = store.load()
    done = sum(1 for e in entries
               for a in e.get("attempts", []) if a.get("date") == today.isoformat())
    items = []
    for e in store.queue():
        try:
            idle = (today - datetime.date.fromisoformat(_last(e))).days
        except ValueError:
            idle = 0
        items.append({"id": e.get("id", "")[-6:], "zh": e.get("zh", ""),
                      "n": len(e.get("attempts", [])), "idle": idle})
    return {"done_today": done, "queue": len(items), "items": items,
            "ripe": [x for x in items if x["n"] >= 3]}


def notify(title, body):
    """macOS 通知。不在 mac 上或 osascript 没了就静默跳过。"""
    try:
        subprocess.run(["osascript", "-e",
                        'display notification %s with title %s sound name "Ping"'
                        % (json_str(body), json_str(title))],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        pass


def json_str(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ") + '"'


def main():
    r = review()
    quiet = "--notify" in sys.argv

    if not r["items"]:
        if not quiet:
            print("队列空的。python3 eng.py add，或往 ~/.eng/seeds.txt 加中文句子。")
        return

    top = r["items"][0]
    if r["done_today"]:
        if not quiet:
            print("今天练过了（%d 遍）。队列还剩 %d 条。" % (r["done_today"], r["queue"]))
        return

    if quiet:
        return notify("eng · 今天还没练　队列 %d 条" % r["queue"], top["zh"])

    print("今天还没练。队列 %d 条。\n" % r["queue"])
    print("  今天这题：%s" % top["zh"])
    print("             %s\n" % ("还没练过" if not top["n"]
                                 else "练过 %d 遍，%d 天没碰" % (top["n"], top["idle"])))
    if r["ripe"]:
        print("练过 3 遍以上、还没在真实会议里用出来的 %d 条 —— 找机会用掉它们：" % len(r["ripe"]))
        for x in r["ripe"]:
            print("  %s  %s　(%d 遍，%d 天前)" % (x["id"], x["zh"], x["n"], x["idle"]))
    print("\n  python3 web.py    或    /eng")


if __name__ == "__main__":
    main()
