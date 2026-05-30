# -*- coding: utf-8 -*-
"""Core module tests for monitor v2"""
import sys, os, tempfile, pathlib, shutil
os.environ["MONITOR_DATA_DIR"] = os.path.join(tempfile.gettempdir(), "codex_monitor_pytest")
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

import pytest
from monitor.storage.db import init_db, make_hash, is_seen, mark_seen, _connect, backup_db
from monitor.engine.classifier import classify_multi, quality_score, is_worth_sending
from monitor.engine.llm_analyzer import _build_prompt, _parse_response, is_busy, batch_analyze
from monitor.engine.health import HealthTracker
from monitor.notify.throttle import Throttle
from datetime import datetime


@pytest.fixture(autouse=True)
def setup_db():
    d = os.environ["MONITOR_DATA_DIR"]
    if os.path.exists(d):
        shutil.rmtree(d)
    init_db()


class TestClassifier:
    def test_critical(self):
        assert classify_multi("cable cut")["primary"] == "CRITICAL"
        assert classify_multi("DE-CIX outage")["primary"] == "CRITICAL"

    def test_important(self):
        r = classify_multi("new data center investment")
        assert r["primary"] == "IMPORTANT"

    def test_overload(self):
        assert "CRITICAL" not in classify_multi("investment")["levels"]

    def test_unrelated(self):
        assert classify_multi("festival")["primary"] is None

    def test_quality(self):
        s, f = quality_score("n", "c", "https://reuters.com/x")
        assert s == 0
        s2, _ = quality_score("Here is", "As an AI", "https://spam.com")
        assert s2 >= 3

    def test_worth(self):
        assert is_worth_sending(4, "CRITICAL")
        assert not is_worth_sending(5, "CRITICAL")


class TestLLM:
    def test_prompt(self):
        items = [{"t":"x", "s":"y", "n":"z", "level":"CRITICAL", "kw":["x"]}]
        assert "[0]" in _build_prompt(items)

    def test_parse(self):
        r1 = _parse_response('[{"index":0,"i":5}]')
        assert r1[0]["i"] == 5
        r2 = _parse_response('{"analyses":[{"index":0}]}')
        assert r2[0]["index"] == 0
        assert len(_parse_response("no json")) == 0

    def test_busy(self):
        assert not is_busy()
        assert batch_analyze([]) == []


class TestHealth:
    def test_silent(self):
        ht = HealthTracker()
        for _ in range(3):
            ht.record_node_result("D", 0)
        assert len(ht.get_silent_nodes()) == 1

    def test_source(self):
        ht = HealthTracker()
        for _ in range(3):
            ht.record_source_health("g", False, "e")
        assert len(ht.get_dead_sources()) == 1


class TestThrottle:
    def test_critical_send(self):
        assert Throttle().should_send("N", "CRITICAL")[0]

    def test_watch(self):
        s, r = Throttle().should_send("N", "WATCH")
        assert not s
        assert "\u6c47\u603b" in r

    def test_hb(self):
        t = Throttle()
        assert t.should_send_watch_digest() is not None


class TestDB:
    def test_dedup(self):
        h = make_hash("same")
        assert make_hash("same") == h
        assert not is_seen(h)
        mark_seen(h)
        assert is_seen(h)

    def test_wal(self):
        c = _connect()
        assert "wal" in str(c.execute("PRAGMA journal_mode").fetchone()[0]).lower()
        c.close()

    def test_backup(self):
        bp = backup_db(output_dir=os.environ["MONITOR_DATA_DIR"])
        assert os.path.exists(bp) and os.path.getsize(bp) > 0


class TestTopicRoute:
    """KB topic ??? ? _get_topic ????????? node tags ??? 4 ??? topic"""

    def test_policy_regulation(self):
        from monitor.storage.kb_sync import _get_topic
        assert _get_topic(["ixp", "europe"]) == "policy_regulation"
        assert _get_topic(["ixp", "asia"]) == "policy_regulation"
        assert _get_topic(["policy", "geo"]) == "policy_regulation"

    def test_tech_breakthrough(self):
        from monitor.storage.kb_sync import _get_topic
        assert _get_topic(["cable", "infra"]) == "tech_breakthrough"
        assert _get_topic(["satellite", "infra"]) == "tech_breakthrough"

    def test_market_trend(self):
        from monitor.storage.kb_sync import _get_topic
        assert _get_topic(["dc", "investment"]) == "market_trend"
        assert _get_topic(["dc", "north-america"]) == "market_trend"
        assert _get_topic(["middle-east", "infra"]) == "market_trend"
        assert _get_topic(["africa", "emerging"]) == "market_trend"

    def test_enterprise_competition(self):
        from monitor.storage.kb_sync import _get_topic
        assert _get_topic(["ai", "infra"]) == "enterprise_competition"
        assert _get_topic(["ai"]) == "enterprise_competition"

    def test_fallback(self):
        from monitor.storage.kb_sync import _get_topic
        assert _get_topic([]) == "market_trend"
        assert _get_topic(None) == "market_trend"

    def test_kb_add_signature(self):
        from monitor.storage.kb_sync import _kb_add
        import inspect
        sig = inspect.signature(_kb_add)
        params = list(sig.parameters.keys())
        assert "topic" in params, "_kb_add ????? topic ??"
        assert params == ["content", "topic", "section"], f"????: {params}"
