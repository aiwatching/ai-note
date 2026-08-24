#!/usr/bin/env python3
"""eng — 英语输出练习。两个模式，一份数据。

  python3 eng.py drill [--typed]        绕道练习：一句中文，说三遍，不许重复用词
  python3 eng.py mono [分钟] [--typed]  架构独白：自由说，自动抽出卡壳点
  python3 eng.py list                   看未划掉的条目
  python3 eng.py used <id后6位>         标记"在真实会议里用过了"
  python3 eng.py add                    手动加一条

录音需要 ffmpeg，转录需要 whisper.cpp。都没装也能跑 —— 任何命令加 --typed 手打。
"""
import datetime
import sys

import audio
import llm
import store
import text

C = {"dim": "\x1b[2m", "b": "\x1b[1m", "g": "\x1b[32m",
     "y": "\x1b[33m", "r": "\x1b[31m", "x": "\x1b[0m"}

def p(s=""):
    for k, v in C.items():
        s = s.replace("{" + k + "}", v)
    print(s)

def ask(prompt=""):
    """管道输入下不能崩：EOF 一律当空串。"""
    try:
        return input(prompt).strip()
    except EOFError:
        print()
        return ""

def hint(s):
    p("{y}" + s + "{x}")

# ---------- 模式 A：绕道 ----------

def pick_topic():
    q = store.queue()
    if q:
        return q[0]
    done = {e.get("zh") for e in store.load()}
    for line in store.seeds():
        if line not in done:
            return store.add({"zh": line, "source": "seed"})
    return None

def drill(typed=False, rounds=3):
    e = pick_topic()
    if not e:
        p("{y}题库空了。{x}  python3 eng.py add   或往 " + store.seeds_path() + " 里加中文句子")
        return

    p()
    p("{b}绕道练习{x}  —— 说三遍，每遍不许重复上一遍的实词")
    p("{dim}不许查词。卡住就绕。8 秒内必须开口。{x}")
    p()
    p("  {b}" + e.get("zh", "") + "{x}")
    p()

    prev = [a["text"] for a in e.get("attempts", [])]
    this_round = []
    for i in range(1, rounds + 1):
        p("{dim}--- 第 %d 遍 ---{x}" % i)
        if not typed:
            ask("  按 Enter 开始（然后立刻说，别想）")
        said, _ = audio.capture(20, typed, ask=ask, note=hint)
        if not said:
            p("{dim}(空){x}")
            continue
        marked, rep, fresh = text.find_repeats(said, prev + this_round)
        p("  " + marked)
        if rep:
            p("  {r}重复用词: %s{x}   {dim}新词 %d{x}" % (", ".join(rep), fresh))
        else:
            p("  {g}✓ 完全没重复{x}   {dim}新词 %d{x}" % fresh)
        p()
        e.setdefault("attempts", []).append(
            {"date": datetime.date.today().isoformat(), "text": said, "repeated": rep, "fresh": fresh})
        this_round.append(said)

    store.update(e)

    if not e.get("better"):
        p("{dim}事后想到更好的说法就填，直接 Enter 跳过{x}")
        e["better"] = ask("  better> ")
    if not e.get("coach") and llm.enabled():
        p("{dim}（问一下别人会怎么说…）{x}")
        e["coach"] = llm.coach(e.get("zh", ""), [a["text"] for a in e.get("attempts", [])])
    store.update(e)
    p()
    show_refs(e)
    p("{g}存了。{x} id=%s" % e.get("id", ""))

def show_refs(e):
    """三遍全说完、better 也填完之后才展示。顺序不能反：先自己想，再看示范。"""
    c = e.get("coach") or {}
    if c.get("note"):
        p("{y}最要命的一处：{x}" + c["note"])
        p()
    refs = c.get("refs") or store.seeds().get(e.get("zh", ""), [])
    if refs:
        p("{dim}参考说法 —— 不是标准答案，只是示范手边的词怎么绕：{x}")
        for s in refs:
            p("   {g}·{x} " + s)
        p()

# ---------- 模式 B：独白 ----------

def mono(minutes=3, typed=False):
    p()
    p("{b}架构独白{x}  —— 讲一个你今天真正想清楚的技术问题")
    p("{dim}不评分，不纠错，不回放。只抽卡壳点。{x}")
    p()
    topic = ask("  今天讲什么（一句话，随便）> ")
    p()
    said, segs = audio.capture(int(minutes * 60), typed, ask=ask, note=hint)
    if not said:
        p("{y}没录到。{x}")
        return

    pauses = text.find_pauses(segs, threshold=2.0)
    p()
    p("{b}说了 %d 个词{x}" % len(said.split()))
    if not segs:
        p("{dim}没有时间戳（手打模式），跳过卡壳分析{x}")
    elif not pauses:
        p("{g}没有超过 2 秒的停顿。今天很顺。{x}")
    else:
        p("{y}卡壳 %d 处：{x}" % len(pauses))
        for h in pauses:
            p("  {dim}%.1fs{x}  …%s {r}▮{x} %s…"
              % (h["gap"], h["before"][-45:], h["after"][:45]))

    store.add({"zh": "[独白] " + topic, "source": "mono",
               "said": said, "pauses": pauses, "used": True})

    # 整个系统的价值来源就在这一步：把卡壳点翻成明天的题。
    if pauses:
        p()
        p("{dim}把卡壳的地方，用中文写下你当时想说什么。直接 Enter 跳过一条。{x}")
        for h in pauses:
            p("  {dim}…%s ▮ %s…{x}" % (h["before"][-40:], h["after"][:40]))
            zh = ask("  想说的中文> ")
            if zh:
                store.add({"zh": zh, "source": "mono-stuck"})
                p("  {g}✓ 进队列，明天的题{x}")
    p()
    p("{g}结束。不用听回放。{x}")

# ---------- 其他 ----------

def cmd_list():
    q = store.queue()
    if not q:
        p("{dim}队列空的{x}")
        return
    p()
    p("{b}未划掉 %d 条{x}  {dim}(用过了: python3 eng.py used <id>){x}" % len(q))
    p()
    for e in q:
        p("  {dim}%s{x}  %s" % (e.get("id", "")[-6:], e.get("zh", "")))
        if e.get("said"):
            p("      {dim}当时: %s{x}" % e["said"][:70])
        if e.get("better"):
            p("      {g}better: %s{x}" % e["better"])
        n = len(e.get("attempts", []))
        if n:
            p("      {dim}练过 %d 遍{x}" % n)

def cmd_used(sid):
    entries = store.load()
    hit = [e for e in entries if e.get("id", "").endswith(sid)]
    if not hit:
        p("{r}没找到 %s{x}" % sid)
        return
    for e in hit:
        e["used"] = True
        p("{g}✓ 划掉:{x} %s" % e.get("zh", ""))
    store.save_all(entries)

def cmd_add():
    zh = ask("  中文（想说的）> ")
    if not zh:
        return
    said = ask("  当时说的笨版本（可空）> ")
    better = ask("  更好的说法（可空）> ")
    store.add({"zh": zh, "said": said, "better": better, "source": "manual"})
    p("{g}✓{x}")

def main(argv=None):
    a = list(sys.argv[1:] if argv is None else argv)
    typed = "--typed" in a
    a = [x for x in a if x != "--typed"]
    cmd = a[0] if a else "drill"
    if cmd == "drill":
        drill(typed=typed)
    elif cmd == "mono":
        mono(float(a[1]) if len(a) > 1 else 3, typed=typed)
    elif cmd == "list":
        cmd_list()
    elif cmd == "used" and len(a) > 1:
        cmd_used(a[1])
    elif cmd == "add":
        cmd_add()
    else:
        print(__doc__)

if __name__ == "__main__":
    main()
