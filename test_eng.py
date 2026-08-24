"""覆盖设计文档第 6 节的全部测试向量 + 存储层 + CLI 冒烟（--typed 全程无 traceback）。

    python3 -m unittest
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

import store
import text
import web

ROOT = os.path.dirname(os.path.abspath(__file__))


# ---------- 6.1 stemming ----------

class TestStem(unittest.TestCase):
    GROUPS = [
        ["migration", "migrating", "migrate"],
        ["move", "moving", "moved"],
        ["phase", "phases"],
        ["rewrite", "rewriting"],
        ["ship", "shipped", "shipping"],
        ["go", "went", "goes"],
        ["think", "thought"],
    ]
    DIFFERENT = [("cost", "coast"), ("plan", "plant"), ("mov", "movie")]

    def test_groups_match(self):
        for group in self.GROUPS:
            for a in group:
                for b in group:
                    self.assertTrue(
                        text.same(text.stem(a), text.stem(b)),
                        "%s (%s) 应等于 %s (%s)" % (a, text.stem(a), b, text.stem(b)))

    def test_different_do_not_match(self):
        for a, b in self.DIFFERENT:
            self.assertFalse(
                text.same(text.stem(a), text.stem(b)),
                "%s (%s) 不应等于 %s (%s)" % (a, text.stem(a), b, text.stem(b)))

    def test_same_needs_min_length(self):
        self.assertTrue(text.same("abc", "abc"))          # 相等永远算
        self.assertFalse(text.same("mov", "movie"))       # 短于 4 不做前缀匹配

    def test_content_words_skip_stopwords_and_short(self):
        got = [w for w, _ in text.content_words("The cat is on it, we go up.")]
        self.assertEqual(got, ["cat"])                    # go 在停用词表，up 只有 2 个字母
        got = [w for w, _ in text.content_words("we ship code fast")]
        self.assertEqual(got, ["ship", "code", "fast"])


# ---------- 6.2 重复检测 ----------

R1 = "The migration cost is too high, I would prefer to do it in phases."
R2 = "Moving everything over at once takes too much work, so let's break it up."
R3 = ("We would have to rewrite too much in one shot, "
      "I would rather migrate a piece at a time.")
R4 = "The migrating is expensive so we should move it in phase steps."


class TestRepeats(unittest.TestCase):
    def test_round1_no_repeats(self):
        marked, rep, fresh = text.find_repeats(R1, [])
        self.assertEqual(rep, [])
        self.assertEqual(fresh, 5)
        self.assertNotIn(text.MARK_ON, marked)

    def test_round2_no_repeats(self):
        _, rep, fresh = text.find_repeats(R2, [R1])
        self.assertEqual(rep, [])
        self.assertEqual(fresh, 7)

    def test_round3_catches_migrate(self):
        marked, rep, _ = text.find_repeats(R3, [R1, R2])
        self.assertEqual(rep, ["migrate"])
        self.assertIn(text.MARK_ON + "migrate" + text.MARK_OFF, marked)

    def test_round4_catches_three(self):
        _, rep, _ = text.find_repeats(R4, [R1, R2, R3])
        self.assertEqual(rep, ["migrating", "move", "phase"])

    def test_marking_preserves_original_text(self):
        marked, _, _ = text.find_repeats(R4, [R1, R2, R3])
        stripped = marked.replace(text.MARK_ON, "").replace(text.MARK_OFF, "")
        self.assertEqual(stripped, R4)


# ---------- 6.3 停顿检测 ----------

class TestPauses(unittest.TestCase):
    SEGS = [
        {"start": 0.0, "end": 3.0, "text": " So the main tradeoff here is"},
        {"start": 5.8, "end": 8.0, "text": " that we would need to "},
        {"start": 8.4, "end": 10.0, "text": " rewrite the indexer."},
        {"start": 12.0, "end": 14.0, "text": " Which nobody wants."},
    ]

    def test_finds_gaps_over_threshold(self):
        hits = text.find_pauses(self.SEGS, threshold=2.0)
        self.assertEqual([h["gap"] for h in hits], [2.8, 2.0])
        self.assertEqual(hits[0]["before"], "So the main tradeoff here is")
        self.assertEqual(hits[0]["after"], "that we would need to")

    def test_threshold_is_inclusive(self):
        self.assertEqual(len(text.find_pauses(self.SEGS, threshold=2.1)), 1)

    def test_empty_and_single(self):
        self.assertEqual(text.find_pauses([]), [])
        self.assertEqual(text.find_pauses(self.SEGS[:1]), [])


# ---------- 存储 ----------

class TestStore(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        os.environ["ENG_HOME"] = self.dir

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)
        os.environ.pop("ENG_HOME", None)

    def test_add_fills_defaults_and_roundtrips(self):
        e = store.add({"zh": "分阶段迁移", "source": "manual"})
        self.assertEqual(len(e["id"]), 18)
        self.assertFalse(e["used"])
        self.assertEqual(e["attempts"], [])
        self.assertEqual(store.load()[0]["zh"], "分阶段迁移")

    def test_chinese_not_escaped(self):
        store.add({"zh": "回滚计划", "source": "manual"})
        with open(store.data_path(), encoding="utf-8") as f:
            raw = f.read()
        self.assertIn("回滚计划", raw)
        self.assertNotIn("\\u", raw)

    def test_one_json_object_per_line(self):
        store.add({"zh": "一", "source": "manual"})
        store.add({"zh": "二", "source": "manual"})
        with open(store.data_path(), encoding="utf-8") as f:
            lines = f.read().splitlines()
        self.assertEqual([json.loads(x)["zh"] for x in lines], ["一", "二"])

    def test_queue_skips_used_and_sorts_by_attempts_then_created(self):
        store.save_all([
            {"id": "3", "zh": "c", "used": False, "created": "2026-01-03", "attempts": []},
            {"id": "1", "zh": "a", "used": False, "created": "2026-01-01",
             "attempts": [{"text": "x"}]},
            {"id": "2", "zh": "b", "used": False, "created": "2026-01-02", "attempts": []},
            {"id": "4", "zh": "d", "used": True, "created": "2026-01-00", "attempts": []},
        ])
        self.assertEqual([e["id"] for e in store.queue()], ["2", "3", "1"])

    def test_update_replaces_in_place(self):
        e = store.add({"zh": "题", "source": "seed"})
        e["better"] = "Let's move the date."
        store.update(e)
        rows = store.load()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["better"], "Let's move the date.")

    def test_save_all_is_atomic(self):
        store.add({"zh": "题", "source": "seed"})
        store.save_all(store.load())
        self.assertFalse(os.path.exists(store.data_path() + ".tmp"))

    def test_seeds_parses_topics_and_refs(self):
        with open(store.seeds_path(), "w", encoding="utf-8") as f:
            f.write("# 注释\n\n第一句\n  ref one\n  ref two\n第二句\n")
        self.assertEqual(store.seeds(), {"第一句": ["ref one", "ref two"], "第二句": []})


# ---------- CLI 冒烟：--typed 全流程，管道输入 ----------

class TestCli(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.env = dict(os.environ, ENG_HOME=self.dir, ENG_LLM="off")
        shutil.copy(os.path.join(ROOT, "engdata", "seeds.txt"), os.path.join(self.dir, "seeds.txt"))

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def run_eng(self, *args, stdin=""):
        r = subprocess.run([sys.executable, os.path.join(ROOT, "eng.py"), *args],
                           input=stdin, env=self.env, cwd=ROOT,
                           capture_output=True, text=True)
        self.assertNotIn("Traceback", r.stderr, r.stderr)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def entries(self):
        with open(os.path.join(self.dir, "entries.jsonl"), encoding="utf-8") as f:
            return [json.loads(x) for x in f if x.strip()]

    def test_m2_full_loop(self):
        out = self.run_eng("drill", "--typed",
                           stdin="attempt one text\nattempt two text\nattempt three text\n\n")
        self.assertIn("绕道练习", out)
        rows = self.entries()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["source"], "seed")
        self.assertEqual(len(rows[0]["attempts"]), 3)
        self.assertEqual(rows[0]["attempts"][0]["repeated"], [])
        self.assertEqual(rows[0]["attempts"][1]["repeated"], ["attempt", "text"])

        eid = rows[0]["id"]
        self.assertIn(eid[-6:], self.run_eng("list"))
        self.run_eng("used", eid[-6:])
        self.assertTrue(self.entries()[0]["used"])
        self.assertIn("队列空的", self.run_eng("list"))

    def test_add_then_drill_prefers_queue(self):
        self.run_eng("add", stdin="推迟发布\nwe postpone\n\n")
        rows = self.entries()
        self.assertEqual(rows[0]["zh"], "推迟发布")
        self.assertEqual(rows[0]["said"], "we postpone")
        out = self.run_eng("drill", "--typed", stdin="\n\n\n\n")
        self.assertIn("推迟发布", out)

    def test_mono_typed_archives_and_skips_pause_analysis(self):
        out = self.run_eng("mono", "1", "--typed",
                           stdin="索引重写\nwe should rewrite the indexer first\n")
        self.assertIn("跳过卡壳分析", out)
        self.assertIn("结束。不用听回放。", out)
        mono = [e for e in self.entries() if e["source"] == "mono"][0]
        self.assertTrue(mono["used"])
        self.assertEqual(mono["zh"], "[独白] 索引重写")

    def test_shows_seed_refs_after_three_rounds(self):
        out = self.run_eng("drill", "--typed", stdin="one\ntwo\nthree\n\n")
        self.assertIn("参考说法", out)
        self.assertIn("Let's do it in steps.", out)
        # 参考说法必须出现在 better 提问之后，不能提前泄题
        self.assertLess(out.index("better>"), out.index("参考说法"))

    def test_llm_off_makes_no_network_call(self):
        out = self.run_eng("drill", "--typed", stdin="one\ntwo\nthree\n\n")
        self.assertNotIn("问一下", out)
        with open(os.path.join(self.dir, "entries.jsonl"), encoding="utf-8") as f:
            self.assertNotIn("coach", f.read())

    def test_empty_stdin_never_crashes(self):
        self.run_eng("drill", "--typed", stdin="")
        self.run_eng("mono", "1", "--typed", stdin="")
        self.run_eng("add", stdin="")
        self.run_eng("used", "nosuch")
        self.run_eng("nonsense")


# ---------- 网页层：直接调 action 函数，不起 socket，不联网 ----------

class TestWebActions(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        os.environ["ENG_HOME"] = self.dir
        os.environ["ENG_LLM"] = "off"
        shutil.copy(os.path.join(ROOT, "engdata", "seeds.txt"), os.path.join(self.dir, "seeds.txt"))

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)
        os.environ.pop("ENG_HOME", None)
        os.environ.pop("ENG_LLM", None)

    def test_repeat_detection_matches_cli(self):
        eid = web.state()["entry"]["id"]
        web.attempt({"id": eid, "text": "we should move it in phases"})
        r = web.attempt({"id": eid, "text": "moving it in phases costs less"})
        self.assertEqual(r["repeated"], ["moving", "phases"])
        self.assertIn("<mark>moving</mark>", r["html"])

    def test_transcript_is_html_escaped(self):
        r = web.attempt({"id": web.state()["entry"]["id"], "text": "drop <script> tags"})
        self.assertIn("&lt;script&gt;", r["html"])
        self.assertNotIn("<script>", r["html"])

    def test_finish_uses_seed_refs_when_llm_off(self):
        eid = web.state()["entry"]["id"]
        web.attempt({"id": eid, "text": "one two three"})
        r = web.finish({"id": eid, "better": "let us move the date"})
        self.assertEqual(r["note"], "")
        self.assertTrue(any("steps" in x for x in r["refs"]))
        self.assertEqual(store.load()[0]["better"], "let us move the date")
        self.assertNotIn("coach", store.load()[0])

    def test_mono_is_archived_used_and_never_drillable(self):
        r = web.mono({"topic": "索引", "text": "a b c", "segments": [
            {"start": 0.0, "end": 3.0, "text": " so the tradeoff is"},
            {"start": 6.0, "end": 8.0, "text": " that we rewrite it"}]})
        self.assertEqual(len(r["pauses"]), 1)
        mono = [e for e in store.load() if e["source"] == "mono"][0]
        self.assertTrue(mono["used"])
        self.assertNotIn(mono["id"], [e["id"] for e in store.queue()])

    def test_stuck_add_used(self):
        web.stuck({"zh": "想说的那句"})
        self.assertIn("想说的那句", [e["zh"] for e in store.queue()])
        web.add({"zh": "手动一条"})
        e = [x for x in store.queue() if x["zh"] == "手动一条"][0]
        web.used({"id": e["id"]})
        self.assertNotIn("手动一条", [x["zh"] for x in store.queue()])

    def test_empty_input_is_rejected_not_crashed(self):
        self.assertIn("error", web.attempt({"id": "nope", "text": ""}))
        self.assertEqual(web.used({"id": "nope"}), {"ok": False})
        self.assertEqual(web.add({"zh": "  "}), {"ok": False})


if __name__ == "__main__":
    unittest.main()
