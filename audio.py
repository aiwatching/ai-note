"""音频层：ffmpeg 录音 + whisper.cpp 本地转录。唯一有外部依赖的模块。

隐私硬约束：音频和转录不出本机，无任何网络调用，whisper 本地跑，录完即删。
依赖缺失一律静默降级为键盘输入，不允许 traceback。
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

WHISPER = os.environ.get("WHISPER_BIN", "whisper-cli")
MODEL = os.environ.get(
    "WHISPER_MODEL", os.path.expanduser("~/whisper.cpp/models/ggml-small.en.bin"))

def record(seconds=None, ask=input):
    """录到临时 wav。返回路径，录不到返回 None。"""
    if not shutil.which("ffmpeg"):
        return None
    wav = tempfile.mktemp(suffix=".wav")
    src = ["-f", "avfoundation", "-i", ":0"] if sys.platform == "darwin" \
        else ["-f", "pulse", "-i", "default"]
    cmd = ["ffmpeg", "-loglevel", "quiet", "-y", *src, "-ar", "16000", "-ac", "1"]
    if seconds:
        cmd += ["-t", str(int(seconds))]
    cmd += [wav]
    proc = None
    try:
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        if seconds:
            for i in range(int(seconds), 0, -1):
                print("\r  ● 录音中 %3ds " % i, end="", flush=True)
                time.sleep(1)
            print("\r  ● 录音结束      ")
            proc.wait(timeout=10)
        else:
            ask("  ● 录音中… 按 Enter 停止")
            proc.communicate(b"q", timeout=10)
    except (KeyboardInterrupt, subprocess.TimeoutExpired, OSError):
        if proc: proc.kill()
    return wav if os.path.exists(wav) and os.path.getsize(wav) > 1000 else None

def transcribe(wav):
    """本地 whisper.cpp。返回 (全文, segments)；跑不了返回 (None, [])。"""
    if not wav or not shutil.which(WHISPER) or not os.path.exists(MODEL):
        return None, []
    out = tempfile.mktemp()
    try:
        subprocess.run([WHISPER, "-m", MODEL, "-f", wav, "-oj", "-of", out, "-ml", "24"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        return None, []
    jf = out + ".json"
    if not os.path.exists(jf):
        return None, []
    try:
        with open(jf, encoding="utf-8") as f:
            data = json.load(f)
    except (ValueError, OSError):
        return None, []
    finally:
        remove(jf)   # 转录中间文件也不留
    segs = []
    for s in data.get("transcription", []):
        o = s.get("offsets", {})   # whisper.cpp 的 offsets 单位是毫秒
        segs.append({"start": o.get("from", 0) / 1000.0,
                     "end": o.get("to", 0) / 1000.0,
                     "text": s.get("text", "")})
    return " ".join(" ".join(s["text"].split()) for s in segs).strip(), segs

def remove(path):
    try:
        os.remove(path)
    except OSError:
        pass

def capture(seconds=None, typed=False, ask=input, note=print):
    """拿到一段话的文本，能录就录，不能录就手打。返回 (text, segments)。"""
    ready = bool(shutil.which(WHISPER)) and os.path.exists(MODEL)
    if not typed and ready:      # 先查再录，别白讲 3 分钟才发现转不了
        wav = record(seconds, ask=ask)
        said, segs = transcribe(wav)
        if wav:
            remove(wav)             # 不保留音频
        if said is not None:
            return said, segs
        note("  (没录到，手打)")
    elif not typed:              # --typed 是一等公民：没装好也要能立刻开始练
        note("  (whisper 未配置，手打)")
    return ask("  > "), []
