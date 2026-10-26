"""抓取 intervals.icu / TrainerRoad 论坛每周热门帖，供教练知识库吸收。

只抓取、不分析（项目规则：脚本不调用任何 LLM 接口）。每次运行把原始 JSON
和纯文本存到 <warehouse>/9_Coach_Raw/forum/<日期>/，并在 index.md 里标出
相对上次扫描的 NEW / UPDATED；已读过且无新回复的帖子不再抓取。

用法（从 icu/ 目录运行）：
    .venv/bin/python scripts/fetch_forum_weekly_top.py                    # 每周例行
    .venv/bin/python scripts/fetch_forum_weekly_top.py --period monthly   # 首次回补
"""
import argparse
import html
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone

import requests

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.utils.common import setup_encoding, get_warehouse_dir, save_json

setup_encoding()

# 只取训练知识相关分类；软件、Bug、功能请求类不抓
FORUMS = {
    "intervals_icu": {
        "base": "https://forum.intervals.icu",
        "categories": {8: "training", 11: "guide"},
    },
    "trainerroad": {
        "base": "https://www.trainerroad.com/forum",
        "categories": {
            12: "training", 14: "racing", 15: "nutrition", 9: "podcast",
            19: "successful-athletes-podcast", 21: "science-of-getting-faster-podcast",
        },
    },
}
TOPICS_PER_CATEGORY = 15
PERIOD_DAYS = {"weekly": 7, "monthly": 31}
REQUEST_GAP_S = 1.2
MAX_REQUESTS = 150
MAX_POST_CHARS = 2500
HEADERS = {"User-Agent": "icu-coach-forum-digest/1.0 (personal training research)"}

FORUM_ROOT = os.path.join(get_warehouse_dir(), "9_Coach_Raw", "forum")
SEEN_PATH = os.path.join(FORUM_ROOT, "seen.json")


class RequestBudget:
    """限速＋总请求数上限，避免给论坛添负担。"""

    def __init__(self, limit):
        self.limit = limit
        self.used = 0

    def get_json(self, url):
        if self.used >= self.limit:
            raise RuntimeError(f"请求数已达上限 {self.limit}")
        if self.used:
            time.sleep(REQUEST_GAP_S)
        self.used += 1
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        return resp.json()


def html_to_text(cooked):
    """Discourse 的 cooked HTML → 纯文本；引用块压成一行提示，避免重复正文。"""
    text = re.sub(r'<aside class="quote".*?</aside>', "[引用上文]\n", cooked or "", flags=re.S)
    text = re.sub(r"<br\s*/?>|</p>|</li>|</h\d>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def like_count(post):
    return next((a.get("count", 0) for a in post.get("actions_summary", []) if a.get("id") == 2), 0)


def author_label(post):
    tags = [t for t, flag in (("staff", post.get("staff")), ("moderator", post.get("moderator")),
                              ("admin", post.get("admin"))) if flag]
    title = post.get("user_title") or ""
    extra = ", ".join(x for x in [title, *tags] if x)
    name = post.get("name") or post.get("username")
    return f"{name} (@{post.get('username')}){f' [{extra}]' if extra else ''}"


def fetch_topic_posts(budget, base, topic):
    """首页 20 帖；帖子更长时再取末尾一页（每周热门的新讨论多在后面）。"""
    first = budget.get_json(f"{base}/t/{topic['id']}.json")
    posts = {p["post_number"]: p for p in first["post_stream"]["posts"]}
    highest = first.get("highest_post_number", 0)
    if highest > max(posts, default=0):
        tail = budget.get_json(f"{base}/t/{topic['id']}/{highest}.json")
        posts.update({p["post_number"]: p for p in tail["post_stream"]["posts"]})
    return first, [posts[k] for k in sorted(posts)]


def render_topic(forum, base, topic_json, posts):
    url = f"{base}/t/{topic_json['slug']}/{topic_json['id']}"
    lines = [f"# {topic_json['title']}", "",
             f"- forum: {forum} | created: {topic_json['created_at'][:10]} | "
             f"posts: {topic_json.get('posts_count')} | views: {topic_json.get('views')}",
             f"- url: {url}", ""]
    for p in posts:
        body = html_to_text(p.get("cooked"))
        if len(body) > MAX_POST_CHARS:
            body = body[:MAX_POST_CHARS] + " …[截断]"
        lines += [f"## #{p['post_number']} {author_label(p)} | {p['created_at'][:10]} | "
                  f"likes {like_count(p)}", "", body, ""]
    return "\n".join(lines)


def load_seen():
    if os.path.exists(SEEN_PATH):
        with open(SEEN_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


def candidate_topics(budget, base, cat_id, slug, period):
    """热门（Discourse 只算该时段内新开的帖）＋ 该时段内有新回复的老帖，去重。"""
    top = budget.get_json(f"{base}/c/{slug}/{cat_id}/l/top.json?period={period}")
    latest = budget.get_json(f"{base}/c/{slug}/{cat_id}/l/latest.json")
    cutoff = datetime.now(timezone.utc) - timedelta(days=PERIOD_DAYS[period])
    active = [t for t in latest.get("topic_list", {}).get("topics", [])
              if not t.get("pinned") and t.get("bumped_at")
              and datetime.fromisoformat(t["bumped_at"].replace("Z", "+00:00")) >= cutoff]
    picked, ids = [], set()
    for t in top.get("topic_list", {}).get("topics", [])[:TOPICS_PER_CATEGORY] + active[:TOPICS_PER_CATEGORY]:
        if t["id"] not in ids:
            ids.add(t["id"])
            picked.append(t)
    return picked


def scan_forum(budget, forum, cfg, seen, run_dir, period):
    rows = []
    forum_seen = seen.setdefault(forum, {})
    for cat_id, slug in cfg["categories"].items():
        try:
            topics = candidate_topics(budget, cfg["base"], cat_id, slug, period)
        except Exception as e:
            rows.append(f"| {forum} | {slug} | ⚠️ 列表抓取失败: {e} | | | |")
            continue
        for t in topics:
            prev = forum_seen.get(str(t["id"]), 0)
            highest = t.get("highest_post_number", 0)
            if prev and highest <= prev:
                rows.append(f"| {forum} | {slug} | {t['title']} | SEEN | {t.get('posts_count')} | |")
                continue
            status = "NEW" if not prev else f"UPDATED (+{highest - prev})"
            try:
                topic_json, posts = fetch_topic_posts(budget, cfg["base"], t)
            except Exception as e:
                rows.append(f"| {forum} | {slug} | {t['title']} | ⚠️ {e} | | |")
                continue
            out_dir = os.path.join(run_dir, forum)
            save_json({"topic": {k: v for k, v in topic_json.items() if k != "post_stream"},
                       "posts": posts}, out_dir, f"{t['id']}.json")
            md_path = os.path.join(out_dir, f"{t['id']}.md")
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(render_topic(forum, cfg["base"], topic_json, posts))
            forum_seen[str(t["id"])] = topic_json.get("highest_post_number", highest)
            rows.append(f"| {forum} | {slug} | {t['title']} | {status} | {t.get('posts_count')} | "
                        f"{forum}/{t['id']}.md |")
    return rows


def main():
    parser = argparse.ArgumentParser(description="抓取论坛热门与活跃帖")
    parser.add_argument("--period", choices=sorted(PERIOD_DAYS), default="weekly",
                        help="weekly=每周例行；monthly=首次回补")
    parser.add_argument("--max-requests", type=int, default=MAX_REQUESTS)
    args = parser.parse_args()

    run_dir = os.path.join(FORUM_ROOT, datetime.now().strftime("%Y-%m-%d"))
    os.makedirs(run_dir, exist_ok=True)
    seen = load_seen()
    budget = RequestBudget(args.max_requests)
    rows = []
    for forum, cfg in FORUMS.items():
        try:
            rows += scan_forum(budget, forum, cfg, seen, run_dir, args.period)
        except RuntimeError as e:  # 请求预算用完：保留已抓内容，停止
            rows.append(f"| {forum} | | ⚠️ {e} | | | |")
            break
    header = ["# 论坛每周热门抓取", "", f"- 运行: {datetime.now():%Y-%m-%d %H:%M} | 请求数: {budget.used}", "",
              "| 论坛 | 分类 | 标题 | 状态 | 帖数 | 文本 |", "|---|---|---|---|---|---|"]
    with open(os.path.join(run_dir, "index.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(header + rows) + "\n")
    save_json(seen, FORUM_ROOT, "seen.json")
    fetched = sum(1 for r in rows if "| NEW |" in r or "UPDATED" in r)
    print(f"✅ 论坛抓取完成：{fetched} 个新/更新主题，请求 {budget.used} 次 → {run_dir}/index.md")


if __name__ == "__main__":
    main()
