"""纯算法层：词干化、重复检测、停顿检测。

不做 IO，不 import 项目里其他模块 —— 脱离麦克风就能完整测试。
"""
import re

# ---------- 停用词：不参与"是不是又用了同一个词"的比对 ----------
STOP = set("""
a an the this that these those there here
i me my we us our you your he she it they them their
is am are was were be been being do does did done
have has had will would shall should can could may might must
to of in on at by for with from into over under about as
and or but so if then than that which who what when where how why
not no nor too very just really quite only also even still yet
one two three all some any each every much many more most less
thing things way ways lot lots kind sort
""".split())

# ---------- 词干化：目标不是语言学正确，是"他是不是又用了同一个词" ----------
# 宁可粗糙，不可复杂。
IRREG = {
    "went": "go", "gone": "go", "goes": "go",
    "took": "take", "taken": "take",
    "made": "make", "said": "say", "thought": "think",
    "got": "get", "gotten": "get",
    "built": "build", "broke": "break", "broken": "break",
    "wrote": "write", "written": "write",
    "ran": "run", "spent": "spend", "kept": "keep",
    "left": "leave", "meant": "mean", "felt": "feel",
    "cost": "cost", "put": "put", "cut": "cut",
    "better": "good", "best": "good", "worse": "bad", "worst": "bad",
    "people": "person", "men": "man", "women": "woman",
}

SUFFIXES = ("ization", "ations", "ation", "ements", "ement", "ingly",
            "ing", "edly", "ed", "ly", "es", "s")

def _drop_e(w):
    """move -> mov，好和 moving/moved 归一。"""
    return w[:-1] if len(w) > 3 and w.endswith("e") else w

def stem(w):
    w = w.lower()
    if w in IRREG:
        return IRREG[w]
    for suf, repl in (("ies", "y"), ("ied", "y"), ("ying", "y")):
        if w.endswith(suf) and len(w) > len(suf) + 2:
            return w[:-len(suf)] + repl
    for suf in SUFFIXES:
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            base = w[:-len(suf)]
            # 还原重复辅音: shipping -> shipp -> ship
            if len(base) > 3 and base[-1] == base[-2] and base[-1] not in "aeiou":
                base = base[:-1]
            return _drop_e(base)
    return _drop_e(w)

def same(a, b, minlen=4):
    """松匹配：相等，或短的是长的前缀（且长的至少多出 2 个字符）。

    规则剥离没法把 migration(migr) 和 migrating(migrat) 归一，前缀匹配可以。
    最短长度 4 是防 mov 误匹配 movie；多出 2 个字符是防 plan 误匹配 plant。
    仍会有极少数误判（cost / costume），本场景可接受。
    """
    if a == b:
        return True
    short, long = (a, b) if len(a) <= len(b) else (b, a)
    return (len(short) >= minlen
            and len(long) - len(short) >= 2
            and long.startswith(short))

WORD = re.compile(r"[A-Za-z][A-Za-z'\-]*")

MARK_ON = "\x1b[41;97m"   # 红底白字
MARK_OFF = "\x1b[0m"

def content_words(text):
    """只要实词：不在停用词表里，且原词长度 >= 3。返回 [(原词, 词干)]。"""
    return [(m.group(0), stem(m.group(0))) for m in WORD.finditer(text)
            if m.group(0).lower() not in STOP and len(m.group(0)) >= 3]

def find_repeats(text, previous_texts, on=MARK_ON, off=MARK_OFF):
    """本遍里哪些实词在前几遍中已经用过了？

    返回 (标红后的文本, 重复的原词列表, 未重复实词数)。
    """
    used = set()
    for prev in previous_texts:
        used |= {s for _, s in content_words(prev)}

    repeated, fresh = [], 0
    parts, last = [], 0
    for m in WORD.finditer(text):
        w = m.group(0)
        if w.lower() in STOP or len(w) < 3:
            continue
        if any(same(stem(w), u) for u in used):
            parts.append(text[last:m.start()])
            parts.append(on + w + off)
            last = m.end()
            repeated.append(w)
        else:
            fresh += 1
    parts.append(text[last:])
    return "".join(parts), repeated, fresh

# ---------- 停顿检测 ----------

def find_pauses(segments, threshold=2.0):
    """segments: [{'start': float, 'end': float, 'text': str}]，来自 whisper。

    相邻两段间隔 >= threshold 秒即一个卡壳点。
    """
    hits = []
    for a, b in zip(segments, segments[1:]):
        gap = b["start"] - a["end"]
        if gap >= threshold:
            hits.append({
                "gap": round(gap, 1),
                "before": a["text"].strip(),
                "after": b["text"].strip(),
            })
    return hits
