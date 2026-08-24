# -*- coding: utf-8 -*-
"""从 seeds.txt / entries.jsonl 生成 artifact 页面，句库不手抄。"""
import html, json, os, sys
sys.path.insert(0, "/Users/zliu/IdeaProjects/ai-note")
import store

E = html.escape
seeds = store.seeds()
queued = {e["zh"] for e in store.queue()}

# 页面里要收的题：练过的那条 + 2026-08-23 追加的 10 条
TARGETED = [
    "这个改动的风险太大了，我建议先灰度。",
    "这个模块的复杂度已经超过我们能维护的程度了。",
    "这次排查的工作量比我预估的大三倍。",
    "这个告警的误报率太高，运维已经开始忽略它了。",
    "这个方案对现有部署的侵入性太强。",
    "这个漏洞的利用门槛很低，必须这周修。",
    "这块的技术债已经开始拖慢交付了。",
    "这个接口在高并发下响应时间会翻倍。",
    "我们的检测覆盖率还不够，先补最关键的那几类。",
    "这个性能问题的根因不在代码，在部署方式。",
]
ORDER = ["这个方案的迁移成本太高，我倾向于分阶段做。"] + TARGETED

# 八次尝试拆成三个格子
ATTEMPTS = [
    ("This solution moving",        "is so high cost",             "separete multiple stages"),
    ("there",                       "is so high cost on this plan", "separete multiple sessions"),
    ("the proposal",                "has hard cost",               "conside that multile steps"),
    ("This magration",              "is so high cost",             "seperate multiple stagings"),
    ("This solution for magration", "has high cost",               "seperate multiple sessions"),
    ("this plan for moving",        "is so very cost",             "finish based on a few sessions"),
    ("this magration solution",     "is high cost",                "seperate multiple stagings"),
    ("this modification",           "is high risk",                "do the gray test"),
]

SYMPTOMS = [
    ("名词硬塞进形容词位和动词位",
     "中文说「XX 的 YY 太高」，你就写 <code>the YY is high</code>。"
     "<code>cost</code> 是名词，形容词位要 <code>expensive</code>，"
     "要用 <code>cost</code> 就让它当动词 <code>costs too much</code>。",
     ["is so high cost", "has hard cost", "is so very cost", "is high risk", "I advice to do"]),
    ("主语是名词堆，谓语只有 is / has",
     "主语永远是「这个方案 / 迁移 / 改动」这类名词，动词永远是 <code>is</code> 或 <code>has</code>。"
     "名词堆越长，后面越接不上。",
     ["This solution for magration has high cost", "this magration solution is high cost"]),
    ("中文概念逐词直译，对方听不懂",
     "这条比语法错严重得多——前面那些顶多让人觉得你英语一般，这个直接让沟通失败。",
     ["separate multiple stagings　←　分阶段", "the gray test　←　灰度"]),
]

BREAK = [("We", "can't", "We can't do this all at once."),
         ("Moving this", "costs", "Moving this costs too much."),
         ("I", "want", "I want to break this into steps.")]


def rows():
    out = []
    for i, (a, b, c) in enumerate(ATTEMPTS, 1):
        new = i == 8
        chip = '<span class="chip">新题</span>' if new else ""
        out.append(
            '<tr%s><td class="n">%d</td><td>%s%s</td><td class="hot">%s</td>'
            '<td class="hot">%s</td></tr>'
            % (' data-new="1"' if new else "", i, chip, E(a), E(b), E(c)))
    return "\n".join(out)


def symptoms():
    out = []
    for i, (title, desc, ex) in enumerate(SYMPTOMS, 1):
        items = "".join("<li>%s</li>" % E(x) for x in ex)
        out.append('''<section class="sym">
  <h3><span class="tag">%d</span>%s</h3>
  <p>%s</p>
  <ul class="ex">%s</ul>
</section>''' % (i, E(title), desc, items))
    return "\n".join(out)


def phrasebook():
    out = []
    for zh in ORDER:
        refs = seeds.get(zh)
        if not refs:
            continue
        badge = '<span class="q">在队列</span>' if zh in queued else ""
        lis = "".join("<li>%s</li>" % E(r) for r in refs)
        out.append('<article><h4>%s%s</h4><ol>%s</ol></article>' % (E(zh), badge, lis))
    return "\n".join(out)


def breaks():
    return "\n".join(
        '<tr><td class="s">%s</td><td class="v">%s</td><td>%s</td></tr>' % (E(a), E(b), E(c))
        for a, b, c in BREAK)


HTML = '''<title>绕道手册</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&family=Newsreader:opsz,wght@6..72,400;6..72,500;6..72,600&display=swap">
<style>
:root{
  --bg:#f2f2f4; --card:#fdfdfd; --line:#dfe0e5; --fg:#1a1b20; --dim:#6a6c76;
  --hot:#b5372f; --hot-bg:#f6dedb; --go:#4a7333; --warn:#96631a;
  --mono:"JetBrains Mono",ui-monospace,SFMono-Regular,Menlo,monospace;
  --serif:"Newsreader","Songti SC",Georgia,serif;
  --han:"PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;
  --sp:clamp(1rem,3.5vw,1.6rem);
}
@media (prefers-color-scheme:dark){
  :root:not([data-theme="light"]){
    --bg:#131419; --card:#1b1d24; --line:#2c2f38; --fg:#e6e5e1; --dim:#8b8d97;
    --hot:#e8746a; --hot-bg:#3a1f1d; --go:#8ec06d; --warn:#ddab5e;
  }
}
:root[data-theme="dark"]{
  --bg:#131419; --card:#1b1d24; --line:#2c2f38; --fg:#e6e5e1; --dim:#8b8d97;
  --hot:#e8746a; --hot-bg:#3a1f1d; --go:#8ec06d; --warn:#ddab5e;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
  font:400 17px/1.7 var(--serif);
  -webkit-font-smoothing:antialiased}
h1,h2,h3,h4,p,.sub,.cap,.rule{font-family:var(--serif),var(--han)}
table td,table th{font-family:var(--mono),var(--han)}
.wrap{max-width:70ch;margin:0 auto;padding:clamp(2rem,6vw,4.5rem) var(--sp) 6rem;
  display:flex;flex-direction:column;gap:clamp(2.4rem,6vw,3.6rem)}
code{font:500 .88em/1.5 var(--mono);background:var(--hot-bg);color:var(--hot);
  padding:.1em .35em;border-radius:3px}

header{display:flex;flex-direction:column;gap:.7rem}
.eyebrow{font:500 11px/1 var(--mono);letter-spacing:.18em;text-transform:uppercase;
  color:var(--dim)}
h1{font:600 clamp(2rem,7vw,2.9rem)/1.15 var(--serif);margin:0;text-wrap:balance;
  letter-spacing:-.01em}
.sub{margin:0;color:var(--dim);font-size:1.02rem;max-width:52ch}

h2{font:500 12px/1 var(--mono);letter-spacing:.16em;text-transform:uppercase;
  color:var(--dim);margin:0 0 1.1rem;padding-bottom:.7rem;
  border-bottom:1px solid var(--line)}
h3{font:600 1.12rem/1.4 var(--serif);margin:0 0 .45rem;display:flex;gap:.6rem;
  align-items:baseline;text-wrap:balance}
p{margin:0 0 .9rem}
p:last-child{margin-bottom:0}

.scroll{overflow-x:auto;margin-inline:calc(var(--sp)*-1);padding-inline:var(--sp)}
table{border-collapse:collapse;width:100%;min-width:34rem;
  font:400 13.5px/1.5 var(--mono);font-variant-numeric:tabular-nums}
th{font:500 10.5px/1 var(--mono);letter-spacing:.11em;text-transform:uppercase;
  color:var(--dim);text-align:left;padding:0 1rem .6rem 0;white-space:nowrap;
  font-family:var(--mono),var(--han)}
td{padding:.42rem 1rem .42rem 0;vertical-align:top;border-top:1px solid var(--line)}
td.n{color:var(--dim);width:1.6rem;padding-right:.7rem}
td.hot{color:var(--hot)}
tr[data-new] td{background:var(--hot-bg)}
tr[data-new] td:first-child{box-shadow:inset 2px 0 0 var(--hot)}
.chip{font:500 9.5px/1.5 var(--mono);font-family:var(--mono),var(--han);
  letter-spacing:.09em;color:var(--hot);border:1px solid currentColor;
  border-radius:2px;padding:0 .3rem;margin-right:.45rem;white-space:nowrap}
.cap{margin-top:.9rem;color:var(--dim);font-size:.92rem}

.sym{background:var(--card);border:1px solid var(--line);border-radius:2px;
  border-left:2px solid var(--hot);padding:1.15rem 1.3rem;margin-bottom:.9rem}
.sym:last-child{margin-bottom:0}
.sym p{font-size:.97rem;color:var(--dim);margin-bottom:.75rem}
.tag{font:500 11px/1.45 var(--mono);color:var(--hot);background:var(--hot-bg);
  border-radius:2px;padding:0 .42rem;flex:none}
ul.ex{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:.28rem}
ul.ex li{font:400 13px/1.55 var(--mono);color:var(--hot);
  font-family:var(--mono),var(--han)}

table.brk td.s{color:var(--go)}
table.brk td.v{color:var(--go);font-weight:700}

.book{display:flex;flex-direction:column;gap:1.5rem}
.book article{display:flex;flex-direction:column;gap:.55rem}
.book h4{font:600 1.03rem/1.5 var(--serif);margin:0;display:flex;gap:.55rem;
  align-items:baseline;flex-wrap:wrap}
.q{font:500 9.5px/1.5 var(--mono);letter-spacing:.09em;color:var(--go);
  border:1px solid currentColor;border-radius:2px;padding:0 .35rem;flex:none}
.book ol{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:.34rem}
.book ol li{font:400 14.5px/1.65 var(--mono);padding-left:1rem;
  border-left:2px solid var(--line)}
.book ol li:hover{border-left-color:var(--go)}

.rule{background:var(--card);border:1px solid var(--line);border-radius:2px;
  padding:1.2rem 1.35rem;font-size:1rem}
.rule strong{color:var(--go)}
footer{color:var(--dim);font-size:.9rem;border-top:1px solid var(--line);
  padding-top:1.2rem}
a{color:var(--go)}
@media (prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}
</style>

<div class="wrap">
<header>
  <div class="eyebrow">eng · 2026-08-23</div>
  <h1>你说了八遍，是同一句话</h1>
  <p class="sub">八次尝试拆开看，三个格子里填的东西没变过。问题不在词汇量，
  在你把中文逐词查表、再按中文语序拼装。</p>
</header>

<section>
  <h2>八次尝试，同一个骨架</h2>
  <div class="scroll"><table>
    <thead><tr><th></th><th>主语（名词堆）</th><th>is / has + 抽象名词</th><th>中文概念直译</th></tr></thead>
    <tbody>
__ROWS__
    </tbody>
  </table></div>
  <p class="cap">前七行是同一道题。第八行是从没练过的新题——三个格子照样全中，
  所以要纠的不是某一句的错，是默认的拼装方式。</p>
</section>

<section>
  <h2>三个症状</h2>
__SYM__
</section>

<section>
  <h2>破局动作 · 只有一个</h2>
  <div class="rule">
    <p><strong>开口前先定两件事：主语是谁，动词是什么。</strong></p>
    <p style="margin-bottom:0;color:var(--dim);font-size:.95rem">
    主语换成人或动作，谓语换成真动词——名词堆自己就消失了。别记第二个动作，记两个等于没记。</p>
  </div>
  <div class="scroll" style="margin-top:1rem"><table class="brk">
    <thead><tr><th>主语</th><th>动词</th><th>说出来是这样</th></tr></thead>
    <tbody>
__BRK__
    </tbody>
  </table></div>
</section>

<section>
  <h2>句库 · 开会前扫一眼</h2>
  <p style="color:var(--dim);font-size:.95rem;margin-bottom:1.4rem">
  每句都不用抽象名词当表语，主语是人或动作。挑一句背，只挑一句——记三句等于没记。</p>
  <div class="book">
__BOOK__
  </div>
</section>

<footer>
  <p>划掉的唯一条件：在真实会议里说出来过一次。练多少遍都不算完成。</p>
  <p style="margin-bottom:0">当前 <code>used = 0</code>。这页要等的就是这个数字变成 1。</p>
</footer>
</div>
'''

page = (HTML.replace("__ROWS__", rows()).replace("__SYM__", symptoms())
            .replace("__BRK__", breaks()).replace("__BOOK__", phrasebook()))
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "detour.html")
open(out, "w", encoding="utf-8").write(page)
print("写了", out, len(page), "字节")
print("句库条目:", page.count("<article>"))
