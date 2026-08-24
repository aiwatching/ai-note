"""事后反馈。三遍全说完、better 也填完之后调用一次，结果落盘缓存，不重复调用。

为什么破了设计文档「不调 LLM」这一条：seeds 只有 20 条，用完之后队列全是
mono-stuck —— 你自己写的中文，静态参考说法覆盖不到。没有它，"绕道示范"
这件事在第 21 天就断了。

为什么它只在最后出现：训练的是"卡住时自己绕"，任何提前介入都会变成等答案。
它不聊天、不打断、不逐句纠错，只回答"母语者会怎么绕"，外加一处最要命的问题。

隐私：只发题面中文 + 你的三遍英文。音频永不外发；mono 独白转录也永不外发
（结构上就发不出去：mono 条目 used=true，进不了 drill，coach 只在 drill 里调）。
关掉：ENG_LLM=off
Key：环境变量 DEEPSEEK_API_KEY / ZHIPU_API_KEY，或 ~/.eng/config 里 KEY=value。
~/.eng/config 刻意放在仓库外 —— 数据可以进 git，key 不行。
"""
import json
import os
import ssl
import urllib.error
import urllib.request

import store

PROVIDERS = {
    "deepseek": ("https://api.deepseek.com/chat/completions",
                 "deepseek-chat", "DEEPSEEK_API_KEY"),
    "zhipu": ("https://open.bigmodel.cn/api/paas/v4/chat/completions",
              "glm-4.5", "ZHIPU_API_KEY"),
}

SYSTEM = """你在帮一个在美国工作的中国资深工程师练英语口语输出。
他词汇量够、阅读没问题，卡的是"意思 → 英文"这条检索路径。
他的训练法是：一句中文，用三种不同说法讲出来，不许重复实词。

你只做两件事，别的一概不做：
1. refs：给 3 个母语者在真实工作场景里会说的版本。硬性要求：
   - 只用最普通的词。不许出现 leverage / mitigate / bandwidth / align 这类"聪明词"。
   - 三个版本的句子骨架必须彼此不同，不是同一句换同义词。
   - 每个不超过两句话，像人在会议上真的会说出口的那样。
2. note：一句中文，只挑他三遍里最要命的**一处**说，格式固定：
   先原样引用出问题的那个英文片段（加引号），再说它为什么站不住，
   再给一个最小改法。全部合起来不超过两句话。
   只看"句子怎么搭"：主谓宾错位、动名词乱挂、缺谓语、从句接不上、
   形容词当名词用。不看拼写、不看冠词、不看时态、不看用词高不高级。
   判断标准是"母语者听到会不会卡一下"，不是"语法书允不允许"。
   只有当三遍在母语者听来全都自然时，才写"三遍都站得住"——
   只要有一遍读起来别扭，就必须把那一遍拎出来，不许放过。

绝对不要：逐句批改、罗列语法错误、打分、鼓励、寒暄、解释你的理由。
只输出 JSON，不要 markdown 代码块：{"refs": ["...", "...", "..."], "note": "..."}"""


def _ctx():
    """python.org 版 Python 常常没装 CA，certifi 在就用它兜底。绝不关校验。"""
    ctx = ssl.create_default_context()
    if not ctx.cert_store_stats()["x509_ca"]:
        try:
            import certifi
            ctx.load_verify_locations(certifi.where())
        except Exception:
            pass
    return ctx


def provider():
    name = os.environ.get("ENG_LLM_PROVIDER", "deepseek").lower()
    return name if name in PROVIDERS else "deepseek"


def key(env_name):
    k = os.environ.get(env_name, "").strip()
    if k:
        return k
    # ~/.eng/config 在仓库外 —— key 永远不会被 git add 进去
    for cfg in (os.path.expanduser("~/.eng/config"), store.path("config")):
        try:
            with open(cfg, encoding="utf-8") as f:
                for line in f:
                    if line.strip().startswith(env_name + "="):
                        return line.split("=", 1)[1].strip()
        except OSError:
            continue
    return ""


def enabled():
    if os.environ.get("ENG_LLM", "on").lower() == "off":
        return False
    return bool(key(PROVIDERS[provider()][2]))


def coach(zh, attempts, timeout=60):
    """三遍说完之后叫一次。任何失败都返回 None，不打断流程，不抛异常。"""
    url, model, env_name = PROVIDERS[provider()]
    k = key(env_name)
    if not k or not zh or not attempts:
        return None
    user = "中文题面：%s\n\n%s" % (zh, "\n".join(
        "第 %d 遍：%s" % (i, t) for i, t in enumerate(attempts, 1)))
    body = json.dumps({
        "model": os.environ.get("ENG_LLM_MODEL", model),
        "messages": [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": user}],
        "temperature": 1.0,
        "max_tokens": 1200,
    }, ensure_ascii=False).encode()
    req = urllib.request.Request(url, data=body, headers={
        "Content-Type": "application/json", "Authorization": "Bearer " + k})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_ctx()) as r:
            raw = json.load(r)["choices"][0]["message"]["content"]
        out = json.loads(raw[raw.find("{"):raw.rfind("}") + 1])
    except (urllib.error.URLError, OSError, ValueError, KeyError, IndexError):
        return None
    refs = [str(x).strip() for x in out.get("refs", []) if str(x).strip()][:3]
    note = str(out.get("note", "")).strip()
    return {"refs": refs, "note": note} if refs or note else None
