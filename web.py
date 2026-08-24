#!/usr/bin/env python3
"""eng 的本地网页版。只监听 127.0.0.1。

    python3 web.py            # 打开 http://127.0.0.1:8765

浏览器录音 → POST 到本机 → ffmpeg 转 16k wav → 本地 whisper.cpp → 文字。
音频不出这台机器，转完就删，不落盘。CLI 版照常可用，两边共用同一份数据。
"""
import datetime
import json
import os
import shutil
import subprocess
import tempfile
import webbrowser
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import audio
import eng
import llm
import store
import text

ROOT = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.environ.get("ENG_PORT", "8765"))


def _find(entries, eid):
    return next((x for x in entries if x.get("id") == eid), None)


def state():
    e = eng.pick_topic()
    return {
        "entry": e,
        "queue": [{"id": x.get("id", ""), "zh": x.get("zh", ""),
                   "n": len(x.get("attempts", [])), "said": x.get("said", ""),
                   "better": x.get("better", ""), "source": x.get("source", "")}
                  for x in store.queue()],
        "mic": bool(shutil.which("ffmpeg")) and bool(shutil.which(audio.WHISPER))
               and os.path.exists(audio.MODEL),
        "llm": llm.enabled(),
    }


def attempt(b):
    """存一遍，并和"本条全部历史 attempts"比对 —— 和 CLI 完全一致。"""
    entries = store.load()
    e = _find(entries, b.get("id"))
    said = (b.get("text") or "").strip()
    if not e or not said:
        return {"error": "空的"}
    marked, rep, fresh = text.find_repeats(
        said, [a["text"] for a in e.get("attempts", [])], "\x00", "\x01")
    e.setdefault("attempts", []).append(
        {"date": datetime.date.today().isoformat(), "text": said,
         "repeated": rep, "fresh": fresh})
    store.save_all(entries)
    return {"html": escape(marked).replace("\x00", "<mark>").replace("\x01", "</mark>"),
            "repeated": rep, "fresh": fresh}


def finish(b):
    """三遍全说完、better 也填完之后才调这里。顺序不能反：先自己想，再看示范。"""
    entries = store.load()
    e = _find(entries, b.get("id"))
    if not e:
        return {}
    if b.get("better"):
        e["better"] = b["better"]
    if not e.get("coach") and llm.enabled():
        e["coach"] = llm.coach(e.get("zh", ""),
                               [a["text"] for a in e.get("attempts", [])])
    store.save_all(entries)
    c = e.get("coach") or {}
    return {"note": c.get("note", ""),
            "refs": c.get("refs") or store.seeds().get(e.get("zh", ""), [])}


def used(b):
    entries = store.load()
    e = _find(entries, b.get("id"))
    if e:
        e["used"] = True
        store.save_all(entries)
    return {"ok": bool(e)}


def add(b):
    zh = (b.get("zh") or "").strip()
    if zh:
        store.add({"zh": zh, "said": b.get("said", ""),
                   "better": b.get("better", ""), "source": "manual"})
    return {"ok": bool(zh)}


def mono(b):
    """独白存档。source=mono 的条目 used=true，永远进不了 drill —— 所以转录不会外发。"""
    said, segs = b.get("text", ""), b.get("segments", [])
    pauses = text.find_pauses(segs, 2.0)
    store.add({"zh": "[独白] " + (b.get("topic") or ""), "source": "mono",
               "said": said, "pauses": pauses, "used": True})
    return {"pauses": pauses, "words": len(said.split())}


def stuck(b):
    zh = (b.get("zh") or "").strip()
    if zh:
        store.add({"zh": zh, "source": "mono-stuck"})
    return {"ok": bool(zh)}


def to_wav(data):
    """浏览器录的 webm/mp4 → 16k 单声道 wav。只在本机走一趟，转完就删。"""
    if not shutil.which("ffmpeg") or len(data) < 2000:
        return None
    src = tempfile.mktemp()
    with open(src, "wb") as f:
        f.write(data)
    wav = tempfile.mktemp(suffix=".wav")
    subprocess.run(["ffmpeg", "-loglevel", "quiet", "-y", "-i", src,
                    "-ar", "16000", "-ac", "1", wav],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    audio.remove(src)
    return wav if os.path.exists(wav) and os.path.getsize(wav) > 1000 else None


def transcribe(raw):
    wav = to_wav(raw)
    said, segs = audio.transcribe(wav)
    if wav:
        audio.remove(wav)          # 不保留音频
    if said is None:
        return {"error": "转不了：ffmpeg 或 whisper 没配好。直接打字。"}
    return {"text": said, "segments": segs}


POSTS = {"/api/attempt": attempt, "/api/finish": finish, "/api/used": used,
         "/api/add": add, "/api/mono": mono, "/api/stuck": stuck}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj):
        self._send(200, json.dumps(obj, ensure_ascii=False).encode(),
                   "application/json; charset=utf-8")

    def do_GET(self):
        if self.path.split("?")[0] == "/":
            with open(os.path.join(ROOT, "web.html"), "rb") as f:
                self._send(200, f.read(), "text/html; charset=utf-8")
        elif self.path == "/api/state":
            self._json(state())
        else:
            self._send(404, b"404", "text/plain; charset=utf-8")

    def do_POST(self):
        raw = self.rfile.read(int(self.headers.get("Content-Length") or 0))
        if self.path == "/api/transcribe":
            self._json(transcribe(raw))
            return
        fn = POSTS.get(self.path)
        if not fn:
            self._send(404, b"404", "text/plain; charset=utf-8")
            return
        try:
            self._json(fn(json.loads(raw or b"{}")))
        except (ValueError, KeyError, OSError) as ex:
            self._json({"error": "%s: %s" % (type(ex).__name__, ex)})


def main():
    url = "http://127.0.0.1:%d/" % PORT
    try:
        srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    except OSError:
        print("端口 %d 被占了。换一个：ENG_PORT=8800 python3 web.py" % PORT)
        return
    print("eng 网页版 → " + url + "    只监听本机，Ctrl-C 退出")
    webbrowser.open(url)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print()


if __name__ == "__main__":
    main()
