"""情报系统 v2 — 全局信息流动节点监控

Usage:
    python -m monitor scan             # 一次扫描
    python -m monitor test-config      # 验证配置
    python -m monitor heartbeat        # 发送系统心跳
    python -m monitor clean            # 清理过期数据
"""

import datetime

# 统一时区: Asia/Shanghai (UTC+8)
from monitor.utils import now as _now_c, now_str as _now_str_c, _TZ
import hashlib
import json
import os
import sys
import time

from monitor.config import get_enabled_nodes, get_enabled_feeds, validate_config, get_data_dir
from monitor.storage.db import (
    init_db, make_hash, is_seen, mark_seen,
    log_scan, track_hotwords, get_stats_24h,
    enqueue_mail, get_pending_mails, mark_mail_sent, mark_mail_failed,
    log_health, clean_old_data,
)
from monitor.engine.classifier import classify_multi, quality_score, is_worth_sending
from monitor.engine.health import HealthTracker
from monitor.notify.throttle import Throttle
from monitor.engine.llm_analyzer import batch_analyze, is_busy as llm_is_busy
from monitor.storage.kb_sync import sync_to_kb, sync_is_available

from monitor.collector.bing import bing_search
from monitor.collector.google_news import google_news_search
from monitor.collector.rss import search_feeds


# === 邮件发送 ===

def _send_mail(subject: str, html_body: str):
    """发送邮件，失败时缓存到队列"""
    smtp_host = os.environ.get("SMTP_HOST", "smtp.qq.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "465"))
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_pass = os.environ.get("SMTP_PASS", "")
    mail_to = os.environ.get("MAIL_TO", "")
    mail_from = os.environ.get("MAIL_FROM", smtp_user or "monitor@localhost")
    ssl_enabled = os.environ.get("SMTP_SSL", "1") == "1"

    if not mail_to:
        print("[Mail] No MAIL_TO configured, printing report...")
        print(html_body[:600])
        return

    # ????????user+pass ???????????
    if bool(smtp_user) != bool(smtp_pass):
        print(f"[Mail] WARN: SMTP_USER={'set' if smtp_user else 'unset'} but SMTP_PASS={'set' if smtp_pass else 'unset'} ? misconfiguration, skipping")
        log_health("smtp", "MISCONFIG", "SMTP_USER/PASS not in sync")
        print(html_body[:600])
        return

    import smtplib, email.utils, re as _re
    from email.message import EmailMessage

    m = EmailMessage()
    m["Subject"] = subject
    m["From"] = mail_from
    m["To"] = mail_to
    m["Date"] = email.utils.formatdate()
    m.set_content(_re.sub(r"<[^>]+>", "", html_body))
    m.add_alternative(html_body, subtype="html")

    try:
        if ssl_enabled:
            with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=15) as s:
                if smtp_user:
                    s.login(smtp_user, smtp_pass)
                s.send_message(m)
        else:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as s:
                s.starttls()
                if smtp_user:
                    s.login(smtp_user, smtp_pass)
                s.send_message(m)
        print(f"[Mail] Sent: {subject}")
        log_health("smtp", "OK", f"Sent: {subject[:60]}")
    except Exception as e:
        print(f"[Mail] Fail: {e}")
        log_health("smtp", "DOWN", str(e)[:200])
        # 缓存到队列
        enqueue_mail(subject, html_body)
        print(f"[Mail] Queued for retry")


def _retry_queued_mails():
    """重试队列中的邮件"""
    pending = get_pending_mails()
    for mail in pending:
        try:
            _send_mail(mail["subject"], mail["html_body"])
            mark_mail_sent(mail["id"])
            print(f"[Mail] Retry OK: {mail['subject'][:60]}")
        except Exception as e:
            mark_mail_failed(mail["id"], str(e)[:200])
            print(f"[Mail] Retry fail ({mail['retries']+1}/3): {e}")


# === 报告构建 ===

LEVEL_COLORS = {"CRITICAL": "#dc3545", "IMPORTANT": "#e67e22", "WATCH": "#3498db"}
LEVEL_LABELS = {"CRITICAL": "🔴 关键", "IMPORTANT": "🟠 重要", "WATCH": "🔵 关注"}
TRUSTED_SOURCES = [
    "reuters.com", "apnews.com", "bloomberg.com", "ft.com", "wsj.com",
    "nytimes.com", "bbc.com", "cnbc.com", "economist.com",
    "datacenterdynamics.com", "submarinenetworks.com",
]


def _get_source_domain(url: str) -> str:
    """从 URL 提取域名"""
    import re
    m = re.search(r"https?://([^/]+)", url)
    if m:
        return m.group(1).replace("www.", "")
    return url[:40]


def build_report(items: list[dict], health_summary: dict | None = None) -> str:
    """构建邮件 HTML 报告

    Args:
        items: 扫描结果条目列表
        health_summary: 系统健康摘要（可选）

    Returns:
        HTML 字符串
    """
    now = _now_c().strftime("%Y-%m-%d %H:%M")
    import html as html_module

    # 按级别分组
    by_level: dict[str, list] = {"CRITICAL": [], "IMPORTANT": [], "WATCH": []}
    for i in items:
        lv = i.get("level", "WATCH")
        by_level.setdefault(lv, []).append(i)

    parts = [f"<h1>🌍 Global Monitor</h1>",
             f"<p style='color:#888;margin:-8px 0 12px 0'>{now} | {len(items)} items</p>"]

    # === 内容简介 ===
    by_node_summary: dict[str, dict] = {}
    for i in items:
        n = i.get("n", "?")
        lv = i.get("level", "WATCH")
        by_node_summary.setdefault(n, {"CRITICAL": 0, "IMPORTANT": 0, "WATCH": 0})
        by_node_summary[n][lv] = by_node_summary[n].get(lv, 0) + 1

    summary_lines = []
    for n in sorted(by_node_summary.keys()):
        line_parts = []
        for lv in ["CRITICAL", "IMPORTANT", "WATCH"]:
            c = by_node_summary[n].get(lv, 0)
            if c:
                color = LEVEL_COLORS[lv]
                label = "关键" if lv == "CRITICAL" else "重要" if lv == "IMPORTANT" else "关注"
                line_parts.append(f'<span style="color:{color};font-weight:700">{c}{label}</span>')
        if line_parts:
            summary_lines.append(f"  • {html_module.escape(n)}: {' + '.join(line_parts)}")
    summary_html = "<br>".join(summary_lines) if summary_lines else "<em>无内容</em>"

    parts.append(
        f'<div style="padding:10px 14px;background:#f0f4f8;border-radius:6px;'
        f'margin-bottom:16px;font-size:13px;line-height:1.8">'
        f'<b style="font-size:14px">📋 本期概要</b><br>{summary_html}</div>'
    )

    # === 事件详情 ===
    for level in ["CRITICAL", "IMPORTANT", "WATCH"]:
        its = by_level.get(level, [])
        if not its:
            continue
        color = LEVEL_COLORS.get(level, "#666")
        label = LEVEL_LABELS.get(level, level)

        by_node = {}
        for i in its:
            by_node.setdefault(i.get("n", "?"), []).append(i)

        parts.append(f'<h2 style="color:{color}">{label} ({len(its)})</h2>')
        for n, nitems in by_node.items():
            parts.append(f'<h3 style="margin:6px 0;font-size:13px;color:#555">{html_module.escape(n)}</h3>')
            for i in nitems:
                t = html_module.escape(i.get("t", ""))
                s = html_module.escape(i.get("s", "")[:280])
                kw = " | ".join(i.get("kw", []))
                u_raw = i.get("u", "")
                src_raw = i.get("src", "")

                if "google-news" in src_raw:
                    link_display = f'<a href="{html_module.escape(u_raw)}">{html_module.escape(_get_source_domain(u_raw))}</a>'
                else:
                    display_trunc = u_raw[:50] + ("..." if len(u_raw) > 50 else "")
                    link_display = f'链接: <a href="{html_module.escape(u_raw)}">{html_module.escape(display_trunc)}</a>'

                src = html_module.escape(src_raw)
                flags_str = ""
                pol = i.get("pol_score", 0)
                if pol:
                    flags_str = f" | 污染:{pol}"

                # LLM 分析摘要（如果有）
                llm_extra = ""
                llm_summary = i.get("llm_summary", "")
                llm_importance = i.get("llm_importance", 0)
                if llm_summary:
                    llm_extra = f"<br><span style='color:#2c3e50;font-size:13px'>💡 {html_module.escape(llm_summary)}"
                    if llm_importance:
                        stars = "⭐" * llm_importance
                        llm_extra += f" <span style='color:#f39c12'>({stars})</span>"
                    llm_extra += "</span>"

                parts.append(
                    f'<div style="border-left:4px solid {color};margin:6px 0;'
                    f'padding:6px 10px;background:#f8f9fa">'
                    f'<b>{t}</b><br>{s}<br>{link_display}{llm_extra}<br>'
                    f'<span style="font-size:11px;color:#888">[{kw}] src:{src}{flags_str}</span></div>'
                )

    # === 系统健康 ===
    if health_summary:
        silent = health_summary.get("silent_nodes", [])
        dead = health_summary.get("dead_sources", [])
        if silent or dead:
            health_lines = ["<hr>", "<h3>🏥 系统状态</h3>"]
            if silent:
                health_lines.append(
                    f'<div style="padding:6px 10px;background:#f8d7da;border-radius:4px;margin:4px 0">'
                    f'⚠️ 静默节点: {", ".join(html_module.escape(s) for s in silent)}</div>'
                )
            if dead:
                health_lines.append(
                    f'<div style="padding:6px 10px;background:#fff3cd;border-radius:4px;margin:4px 0">'
                    f'⚠️ 故障源: {", ".join(html_module.escape(d) for d in dead)}</div>'
                )
            parts.extend(health_lines)

    html = "<html><meta charset='utf-8'><body style='max-width:700px;margin:20px auto;font:14px/1.5 system-ui'>"
    html += "".join(parts) + "</body></html>"
    return html


def build_heartbeat_mail(health_tracker: HealthTracker) -> str:
    """构建系统心跳邮件"""
    report = health_tracker.build_heartbeat_report()
    html = f"<html><meta charset='utf-8'><body style='max-width:600px;margin:20px auto;font:14px/1.5 system-ui'>"
    html += "<pre style='font-family:monospace;line-height:1.6'>"
    html += report
    html += "</pre></body></html>"
    return html


# === 米罗鱼 API 推送（P0+P2 全自动链路）===

MIROYU_API = "http://127.0.0.1:5001/api/graph/project/create"

def _push_to_miroyu(items: list[dict], max_push: int = 3):
    """筛选 CRITICAL+LLM分析 情报，推送至米罗鱼生成本体并启动推演"""
    import urllib.request
    import urllib.error

    pushed = 0
    for it in items:
        if pushed >= max_push:
            break
        if it.get("level") != "CRITICAL":
            continue
        if not it.get("llm_summary"):
            continue

        title = it.get("t", "未命名情报")
        summary = it.get("s", "")
        url = it.get("u", "")
        llm_summary = it.get("llm_summary", "")

        intel_text = f"标题: {title}\n摘要: {summary}\n来源: {url}\nLLM分析: {llm_summary}"
        sim_req = f"基于以下情报进行多Agent社会模拟推演：{llm_summary}"

        try:
            body = json.dumps({
                "name": title[:80],
                "simulation_requirement": sim_req,
                "intel_text": intel_text,
                "domain": "social_media",
                "auto_pipeline": True
            }).encode("utf-8")
            req = urllib.request.Request(MIROYU_API, data=body,
                headers={"Content-Type": "application/json"})
            resp = urllib.request.urlopen(req, timeout=60)
            result = json.loads(resp.read().decode("utf-8"))
            if result.get("success"):
                pid = result.get("data", {}).get("project_id", "?")
                et = len(result.get("data", {}).get("ontology", {}).get("entity_types", []))
                print(f"  [MiroFish] 项目 {pid} 已创建，{et} 实体类型: {title[:40]}")
                pushed += 1
            else:
                print(f"  [MiroFish] API 错误: {result.get('error','?')[:80]}")
        except Exception as e:
            print(f"  [MiroFish] 推送失败 [{title[:30]}]: {e}")

    if pushed:
        print(f"  [MiroFish] 本轮推送 {pushed} 条情报到米罗鱼")


# === 扫描主流程 ===

def scan():
    """执行一次完整扫描"""
    print(f"[{_now_c():%Y-%m-%d %H:%M}] Global Node Scan v2")
    print("=" * 50)

    # 初始化
    init_db()
    nodes = get_enabled_nodes(force_reload=True)
    feeds = get_enabled_feeds(force_reload=True)

    # 凌晨模式+RSS预取
    _night_mode = _now_c().hour < 8
    _rss_cache = []
    if feeds:
        print(f"  [缓存] RSS预取中...")
        try:
            from monitor.collector.rss import search_feeds as _sf
            _rss_cache = _sf(feeds)
            print(f"  [RSS] 预取 {len(_rss_cache)} 条")
        except Exception as _e:
            print(f"  [RSS] 预取失败: {_e}")
    if _night_mode:
        print("  [模式] 凌晨模式: 跳过Bing/Google搜索, 仅RSS源")
    else:
        print("  [模式] 日间模式: 全链路采集")

    health_tracker = HealthTracker()
    throttle = Throttle()
    all_val = []
    hot_candidates = []
    stats: dict[str, int] = {"CRITICAL": 0, "IMPORTANT": 0, "WATCH": 0}
        # 超时策略: 总时限=环境变量或90秒，每节点平均分配
    total_timeout = int(os.environ.get("SCAN_TIMEOUT", "180"))
    deadline = time.monotonic() + total_timeout

    # 重试队列邮件
    _retry_queued_mails()

    # 遍历节点
    for node in nodes:
        if time.monotonic() > deadline:
            print(f"  [{node['name']}] SKIP (timeout)")
            health_tracker.record_node_result(node["name"], 0, "Scan timeout")
            log_scan(node["name"], 0, 0)
            continue

        name = node["name"]
        keywords = node.get("keywords", [])
        if not keywords:
            continue

        print(f"[{name}] ...", end=" ", flush=True)

        # === 采 集 层 ===
        all_items = []
        source_ok = False

        # 主源 1: Bing
        for kw in keywords:
            try:
                items = [] if _night_mode else bing_search(kw)
                all_items.extend(items)
                if items:
                    source_ok = True
            except Exception as e:
                log_health("collector:bing", "DOWN", f"{name}: {str(e)[:100]}")
                print(f"      [bing fail] {e}")

        # 主源 2: Google News（如果 Bing 没出结果）
        if not source_ok:
            for kw in keywords:
                try:
                    items = [] if _night_mode else google_news_search(kw)
                    all_items.extend(items)
                    if items:
                        source_ok = True
                except Exception as e:
                    log_health("collector:google-news", "DOWN", f"{name}: {str(e)[:100]}")
                    print(f"      [google-news fail] {e}")

        # 兜底: RSS feed（如果前两个都挂了）
        if not source_ok and feeds:
            try:
                rss_items = _rss_cache
                # 只取跟当前节点关键词相关的条目
                for it in rss_items:
                    t = (it["t"] + " " + it["s"]).lower()
                    if any(kw.lower() in t for kw in keywords):
                        all_items.append(it)
                if all_items:
                    source_ok = True
                    print("[RSS]", end=" ", flush=True)
            except Exception as e:
                log_health("collector:rss", "DOWN", f"{name}: {str(e)[:100]}")
                print(f"      [rss fail] {e}")

        # URL 去重
        seen_urls = set()
        unique_items = []
        for it in all_items:
            if it["u"] not in seen_urls:
                seen_urls.add(it["u"])
                unique_items.append(it)

        # === 过 滤 层 ===
        new_count = 0
        total_count = len(unique_items)

        for it in unique_items:
            text = it["t"] + " " + it["s"]

            # 短文本过滤
            if len(text) <= 60:
                continue

            # 去重
            h = make_hash(text)
            if is_seen(h):
                continue

            # 质量评分
            pol_score, pol_flags = quality_score(it["t"], it["s"], it.get("u", ""))
            mark_seen(h)  # 先标记，后续过滤不影响去重

            # 多标签分类
            classification = classify_multi(text)
            primary = classification["primary"]
            if primary is None:
                continue  # 没有任何级别命中

            # 污染过滤
            if not is_worth_sending(pol_score, primary):
                print(f"      [filtered] pol={pol_score} {pol_flags}")
                continue

            it["n"] = node["name"]
            it["level"] = primary
            it["levels"] = classification["levels"]
            it["kw"] = classification["keywords"][:3]
            it["pol_score"] = pol_score
            it["pol_flags"] = pol_flags
            all_val.append(it)
            hot_candidates.extend(classification["keywords"])
            stats[primary] = stats.get(primary, 0) + 1
            new_count += 1

        # 记录扫描日志和健康状态
        log_scan(node["name"], total_count, new_count)
        health_tracker.record_node_result(node["name"], total_count)

        print(f"{total_count} items, {new_count} new")
        time.sleep(0.3)

    # === 推 演 层 ===
    # LLM 批量分析（含互斥锁，上一轮未完成则跳过）
    if all_val:
        # 只分析 CRITICAL+IMPORTANT，最多 30 条（省 token 省时间）
        llm_input = [v for v in all_val if v.get("level") in ("CRITICAL", "IMPORTANT")][:20]
        if llm_input and not llm_is_busy():
            analyzed = batch_analyze(llm_input)
            llm_count = sum(1 for v in analyzed if "llm_summary" in v)
            if llm_count:
                print(f"  [LLM] 分析完成: {llm_count}/{len(analyzed)} 条 (仅 CRITICAL+IMPORTANT)")
                # 将 LLM 结果合并回 all_val
                analyzed_map = {}
                for v in analyzed:
                    if "llm_summary" in v:
                        key = (v.get("t",""), v.get("u",""))
                        analyzed_map[key] = v
                for v in all_val:
                    key = (v.get("t",""), v.get("u",""))
                    if key in analyzed_map:
                        av = analyzed_map[key]
                        v["llm_summary"] = av.get("llm_summary", "")
                        v["llm_importance"] = av.get("llm_importance", 3)
                        v["llm_confidence"] = av.get("llm_confidence", 3)
                        v["llm_related"] = av.get("llm_related", [])
            else:
                print(f"  [LLM] 不可用，使用规则分类结果")
        elif not llm_input:
            print(f"  [LLM] 仅 WATCH 级，跳过 LLM 分析")
        else:
            print(f"  [LLM] 上一轮分析未完成，跳过本轮")
    print(f"\n总计: {len(all_val)} 新条目")
    print(f"  CRITICAL={stats.get('CRITICAL',0)}, IMPORTANT={stats.get('IMPORTANT',0)}, WATCH={stats.get('WATCH',0)}")

    # === 米罗鱼推演推送（P0+P2）===
    if all_val:
        try:
            _push_to_miroyu(all_val)
        except Exception as e:
            print(f"  [MiroFish] 推送模块异常: {e}")

    # === 热 词 追 踪 ===
    heated = track_hotwords(hot_candidates)
    if heated:
        print(f"🔥 热词升温: {heated}")

    # === 通 知 层 ===
    if all_val:
        health_summary = health_tracker.get_summary()
        report_html = build_report(all_val, health_summary)
        crit = [v for v in all_val if v.get("level") == "CRITICAL"]
        imp = [v for v in all_val if v.get("level") == "IMPORTANT"]

        # 按级别逐步发送
        sent_any = False
        for node_name in set(v["n"] for v in all_val):
            for v in all_val:
                if v["n"] != node_name:
                    continue
                lv = v["level"]
                should, reason = throttle.should_send(node_name, lv)
                if should:
                    sent_any = True

        if crit or imp:
            subject = f"[Monitor] C={len(crit)} I={len(imp)} | {_now_str_c()}"
            _send_mail(subject, report_html)
        else:
            print("[Mail] WATCH 级仅汇总发送")

    else:
        print("无新条目")

    # === 系 统 心 跳 ===
    health_tracker.increment_scan()
    if health_tracker.should_send_heartbeat():
        hb_html = build_heartbeat_mail(health_tracker)
        _send_mail(f"[Heartbeat] {_now_str_c()}", hb_html)

    # === 24h 统计 ===
    stats_24h = get_stats_24h()
    print(f"[Filter] 24h: {stats_24h['fetched']} fetched, {stats_24h['accepted']} accepted, ~{stats_24h['filtered']} filtered")

    # === KB 同 步 ===
    if all_val:
        try:
            sync_to_kb(all_val)
        except Exception as e:
            print(f"  [KB] sync error: {e}")


    # === 数 据 备 份 ===
    try:
        from monitor.storage.db import backup_db, _backup_chromadb
        backup_db()
        _backup_chromadb()
    except Exception as e:
        print(f"  [Backup] 备份异常: {e}")

# === CLI 入口 ===

def cmd_scan():
    scan()


def cmd_test_config():
    """验证配置"""
    errors = validate_config()
    if errors:
        print("❌ 配置错误:")
        for e in errors:
            print(f"  • {e}")
        sys.exit(1)

    nodes = get_enabled_nodes(force_reload=True)
    feeds = get_enabled_feeds(force_reload=True)
    print(f"✅ 配置验证通过")
    print(f"  • {len(nodes)} 节点")
    for n in nodes:
        print(f"    [{n['mail_level']:>8}] {n['name']} ({len(n['keywords'])} 关键词)")
    print(f"  • {len(feeds)} RSS Feed")
    for f in feeds:
        print(f"    {f['name']}: {f['url']}")
    data_dir = get_data_dir()
    print(f"  • 数据目录: {data_dir} (可写: {os.access(str(data_dir), os.W_OK)})")
    print()
    print("SMTP 配置:")
    smtp_host = os.environ.get("SMTP_HOST", "smtp.qq.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "465"))
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_pass = os.environ.get("SMTP_PASS", "")
    mail_to = os.environ.get("MAIL_TO", "")
    ssl_enabled = os.environ.get("SMTP_SSL", "1") == "1"
    print(f"  Host: {smtp_host}")
    print(f"  Port: {smtp_port}")
    print(f"  SSL:  {ssl_enabled}")
    print(f"  User: {smtp_user or '(未设置)'}")
    print(f"  To:   {mail_to or '(未设置)'}")

    # SMTP 连通性测试
    if mail_to and smtp_user and smtp_pass:
        print()
        print("  🔌 SMTP 连通性测试...", end=" ", flush=True)
        import smtplib, email.utils
        from email.message import EmailMessage
        try:
            m = EmailMessage()
            m["Subject"] = "[Monitor] SMTP 测试"
            m["From"] = smtp_user
            m["To"] = mail_to
            m["Date"] = email.utils.formatdate()
            m.set_content("这是一封来自情报系统的 SMTP 连通性测试邮件。如果收到说明配置正确。")

            if ssl_enabled:
                with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=10) as s:
                    if smtp_user:
                        s.login(smtp_user, smtp_pass)
                    s.send_message(m)
            else:
                with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as s:
                    s.starttls()
                    if smtp_user:
                        s.login(smtp_user, smtp_pass)
                    s.send_message(m)
            print("OK ✅")
        except Exception as e:
            print(f"失败 ❌")
            print(f"  SMTP 错误: {e}")
    elif not mail_to:
        print("  ⚠️ MAIL_TO 未设置，跳过 SMTP 测试")


def cmd_heartbeat():
    """手动触发心跳"""
    from monitor.engine.health import HealthTracker
    init_db()
    ht = HealthTracker()
    html = build_heartbeat_mail(ht)
    _send_mail(f"[Heartbeat] Manual | {_now_str_c()}", html)
    print("Heartbeat sent")


def cmd_clean():
    """清理过期数据
    """
    init_db()
    clean_old_data()
    try:
        from monitor.storage.db import backup_db
        backup_db()
    except Exception as e:
        print(f"  [Backup] 失败: {e}")
    print("✅ 过期数据已清理")


if __name__ == "__main__":
    cmds = {
        "scan": cmd_scan,
        "test-config": cmd_test_config,
        "heartbeat": cmd_heartbeat,
        "clean": cmd_clean,
    }
    if len(sys.argv) < 2 or sys.argv[1] not in cmds:
        print(__doc__.strip())
        sys.exit(1)
    cmds[sys.argv[1]]()

