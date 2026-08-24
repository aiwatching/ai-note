# eng — 英语输出练习工具

解决一个具体问题：词汇是从阅读进来的，路径是 `英文 → 意思`；说话需要反向的
`意思 → 英文`，这条路几乎没练过。所以想说"推迟发布"时脑子里搜 `postpone`，
搜不到，卡住，沉默三秒。

**这不是词汇量问题，是检索路径问题。** 卡住那一刻真正的错误动作，是在追求那一个
正确的词。母语者不追求最佳用词，用手边的词把意思绕出来：

> 想说"我们得推迟发布"
> - `We need more time before we ship this.`
> - `This can't go out next week.`
> - `Let's move the date.`

三个都不含 `postpone`，都是早就会的词。所以这个工具训练的不是词汇，是
**放弃最优解、绕道表达的习惯**。

每天 5 分钟。命令行和网页两个界面，同一份数据。

## 安装（10 分钟）

```bash
# 录音
brew install ffmpeg

# 转录（本地，音频不出机器）
brew install whisper-cpp
mkdir -p ~/whisper.cpp/models && cd ~/whisper.cpp/models
curl -LO https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.en.bin
```

macOS 第一次跑会弹麦克风权限，给了就行。
如果 `whisper-cli` 名字不对：`export WHISPER_BIN=whisper`（或你本地的实际命令名）。

**没装完也能先用**：任何命令后面加 `--typed`，改成手打。第一天可以这样开始。

## 用

网页版（推荐，浏览器点一下就能录音，不用管麦克风权限那一套）：

```bash
python3 web.py            # → http://127.0.0.1:8765
```

只监听 `127.0.0.1`。浏览器录的音 POST 回本机 → ffmpeg 转 16k wav → 本地 whisper → 文字，
转完就删。端口被占了就 `ENG_PORT=8800 python3 web.py`。

命令行版，功能一样：

```bash
python3 eng.py drill      # 绕道：一句中文，说三遍，重复用词标红   ← 每天这个
python3 eng.py mono 3     # 独白：讲 3 分钟，自动抽卡壳点
python3 eng.py list       # 看还没划掉的
python3 eng.py used 1a2b3c   # 在真实会议里用出来了 → 划掉
python3 eng.py add        # 手动加一条
```

## 事后反馈

三遍全说完、`better` 也填完**之后**，才会出现两样东西：

- **最要命的一处** —— 只挑一个句子结构问题，引用原句片段 + 最小改法。不逐句批改，不打分。
- **参考说法** —— 3 个母语者会说的版本，全部只用最普通的词。

顺序不能反：先自己想，再看示范。提前给答案就变成了「等 AI」，检索训练就没了。

前 20 条 seed 自带手写的参考说法，离线可用。之后的题目（`mono-stuck`，你自己写的中文）
靠 LLM 生成——这是允许调 LLM 的唯一理由：seeds 用完之后，静态参考说法覆盖不到。

**发出去的只有：题面中文 + 你的三遍英文。**
音频永不外发；`mono` 独白转录也永不外发（结构上就发不出去：`mono` 条目 `used=true`，
进不了 drill，反馈只在 drill 里调）。留神 `mono-stuck` 的中文题面是会发的，别在里面写内部代号。

配置 `~/.eng/config`（600 权限，别进 git）：

```
DEEPSEEK_API_KEY=sk-xxx
ZHIPU_API_KEY=xxx.xxx
```

```bash
ENG_LLM=off                  # 全关，退回内置参考说法，全程零网络
ENG_LLM_PROVIDER=zhipu       # 换智谱（默认 deepseek）
ENG_LLM_MODEL=glm-4.6        # 换模型
```

## 复习和提醒

```bash
python3 remind.py            # 今天练没练 + 哪些该在真实会议里用出来了
```

每天早上 7 点自动检查一次（macOS launchd）：今天没练就弹通知，练过了就闭嘴。

```bash
launchctl bootout gui/$(id -u)/com.zliu.eng.remind        # 不想要了
launchctl kickstart -k gui/$(id -u)/com.zliu.eng.remind   # 立刻试一次
```

提醒里会列出**练过 3 遍以上、还没划掉**的条目 —— 那些是"你已经会说，但还没真的用出来"的。
练得再多都不算完成，出队的唯一条件是在真实会议里说出来过一次。

## 手机上练

把这个仓库在 claude.ai/code 打开，`/eng` 直接开练 —— 就是本地 Claude Code 里那套流程，
机器判重、事后纠正、参考说法全在。输入用 iOS 键盘的听写（本地转文字，不出设备），
不用打字。练完的记录跟着 git 回到 Mac。

用的是 Claude 订阅额度，不额外走 API 计费。但它和你写代码共用同一个额度池，
练成习惯后留意别把额度用光。

## 规则（比代码重要）

1. **不许查词**。卡住就绕，绕不过去说个笨的，笨的也算完成。
2. **不许重录**。第一遍什么样就什么样。
3. **不听回放**。真的不用听。
4. **划掉的唯一条件**：在真实会议里说出来过一次。

数据存在仓库的 `engdata/entries.jsonl`，一行一条纯文本，跟着 git 走。

## 闭环

```
mono 讲 3 分钟  →  whisper 转录 + 时间戳  →  停顿 > 2s 的位置 = 卡壳点
  →  用中文写下"当时想说什么"（唯一需要手动输入的一步）  →  自动进队列
  →  第二天 drill：显示这句中文，说三遍，不许重复用词
  →  真实会议里说出来了  →  used 划掉
```

不需要主动记录任何东西。说话，回答一个中文问题，其余全自动。

## 结构

```
eng.py    CLI 入口 / 交互层
web.py    本地 HTTP 服务（127.0.0.1）
web.html  网页界面，单文件，无构建、无依赖
audio.py  录音 (ffmpeg) + 转录 (whisper.cpp)   ← 唯一有外部依赖的模块
llm.py    事后反馈（DeepSeek / 智谱），可关
text.py   词干化 / 重复检测 / 停顿检测          ← 纯函数，无 IO，可单测
store.py  JSONL 读写 / 队列排序                ← 纯 stdlib
```

Python 3.10+，纯标准库，不装任何第三方包（`certifi` 装了就用来兜 CA 证书，没有也能跑）。

```bash
python3 -m unittest      # 全绿
```

`ENG_HOME` 可覆盖数据目录（默认仓库里的 `engdata/`）。

## 明确不做

AI 对话陪练、发音评分、词汇卡片 / SRS、实时纠错 / 打断、进度图表 / 打卡、账号 / 云同步。
做了就是伤害 —— 详见设计文档第 2 节。

音频**不离开本机**：whisper 本地跑，录音文件用完立即删除，无遥测。
