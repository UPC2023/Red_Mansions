"""
从 reddream_chapters 中为关键事件抽取原著片段，更新 kg_events.csv 的 sentence 字段。

策略：
- 针对新增的宝玉/宝钗权威事件，准备关键词列表。
- 在对应章节（chapter 列，如 002.txt）搜索关键短语，命中后裁剪出附近 120~200 字的窗口，并尽量对齐到句读（。！？；）边界。
- 多个关键词命中时取首个；未命中则退化为：优先取包含主人人名的首段，否则取章节开头 120 字。
- 写回 CSV（就地覆盖）。

用法：在项目根目录执行
  python -m scripts.extract_event_snippets --events kg_events.csv --chapters reddream_chapters --minlen 120 --maxlen 220
"""
from __future__ import annotations

import csv
import argparse
import os
import re
from typing import Dict, List, Tuple

DEFAULT_MINLEN = 120
DEFAULT_MAXLEN = 220

# 事件 ID 到关键词与主人人名的映射（可按需扩充）
EVENT_HINTS: Dict[str, Dict[str, List[str]]] = {
    # 贾宝玉
    "EV_贾宝玉_002_txt_贾宝玉衔玉而诞": {
        "keywords": [r"衔.*玉", r"通灵宝玉", r"降生", r"口衔"],
        "names": ["贾宝玉", "贾母"],
    },
    "EV_贾宝玉_003_txt_初见黛玉与摔玉": {
        "keywords": [r"摔.*玉", r"你也配得", r"林黛玉"],
        "names": ["贾宝玉", "林黛玉"],
    },
    "EV_贾宝玉_005_txt_梦游太虚幻境": {
        "keywords": [r"太虚幻境", r"警幻", r"金陵十二钗", r"薄命司"],
        "names": ["贾宝玉", "警幻"],
    },
    "EV_贾宝玉_033_txt_贾宝玉挨打": {
        "keywords": [r"贾政.*打", r"板子", r"棍责", r"笞挞"],
        "names": ["贾宝玉", "贾政", "贾母"],
    },
    "EV_贾宝玉_057_txt_紫鹃试玉": {
        "keywords": [r"紫鹃", r"试", r"回苏州", r"要回去"],
        "names": ["贾宝玉", "紫鹃", "林黛玉"],
    },
    "EV_贾宝玉_077-078_txt_晴雯被逐与芙蓉诔": {
        "keywords": [r"芙蓉女儿诔", r"诔", r"晴雯"],
        "names": ["贾宝玉", "晴雯"],
    },
    "EV_贾宝玉_094_txt_失玉成亲与出家": {
        "keywords": [r"失.*玉", r"通灵宝玉不见", r"出家", r"僧"],
        "names": ["贾宝玉", "薛宝钗", "黛玉"],
    },
    # 薛宝钗
    "EV_薛宝钗_004_txt_薛宝钗入都": {
        "keywords": [r"薛氏", r"薛姨妈", r"入都", r"荣国府"],
        "names": ["薛宝钗", "薛姨妈"],
    },
    "EV_薛宝钗_008_txt_微恙互看金玉": {
        "keywords": [r"金玉", r"冷香丸", r"病", r"微恙"],
        "names": ["薛宝钗", "贾宝玉"],
    },
    "EV_薛宝钗_027_txt_薛宝钗扑蝶": {
        "keywords": [r"扑蝶", r"蝴蝶"],
        "names": ["薛宝钗"],
    },
    "EV_薛宝钗_030_txt_机带双敲": {
        "keywords": [r"金麒麟", r"机带双敲"],
        "names": ["薛宝钗", "贾宝玉"],
    },
    "EV_薛宝钗_042_txt_兰言解疑癖": {
        "keywords": [r"解疑癖", r"宽言", r"勸", r"劝"],
        "names": ["薛宝钗", "贾宝玉"],
    },
    "EV_薛宝钗_056_txt_小惠全大体": {
        "keywords": [r"小惠全大体"],
        "names": ["薛宝钗"],
    },
    "EV_薛宝钗_097_txt_出闺成大礼": {
        "keywords": [r"大礼", r"成婚", r"成亲", r"出闺"],
        "names": ["薛宝钗", "贾宝玉"],
    },
}

SENTENCE_SPLIT = re.compile(r"(?<=[。！？；])")


def trim_to_window(text: str, start: int, minlen: int, maxlen: int) -> str:
    begin = max(0, start - maxlen // 4)
    end = min(len(text), start + maxlen)
    window = text[begin:end]
    # 优先对齐到句子边界
    parts = SENTENCE_SPLIT.split(window)
    out = ""
    for p in parts:
        if len(out) < minlen:
            out += p
        else:
            break
    # 如果还太短，直接用窗口裁剪
    if len(out) < minlen:
        out = window[:maxlen]
    return out.strip()


def find_snippet(chapter_text: str, hints: Dict[str, List[str]], minlen: int, maxlen: int) -> str:
    # 关键词优先
    for pat in hints.get("keywords", []):
        m = re.search(pat, chapter_text)
        if m:
            return trim_to_window(chapter_text, m.start(), minlen, maxlen)
    # 含主人人名的首段
    for name in hints.get("names", []):
        m = re.search(re.escape(name), chapter_text)
        if m:
            return trim_to_window(chapter_text, m.start(), minlen, maxlen)
    # 退化：章节开头
    return chapter_text[:maxlen].strip()


def load_chapter(base_dir: str, chapter_file: str) -> str:
    path = os.path.join(base_dir, chapter_file)
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        txt = f.read()
    # 简单清洗：合并多余空白
    txt = re.sub(r"\s+", "", txt)
    return txt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--events", default="kg_events.csv", help="事件CSV路径")
    ap.add_argument("--chapters", default="reddream_chapters", help="章节文本目录")
    ap.add_argument("--minlen", type=int, default=DEFAULT_MINLEN)
    ap.add_argument("--maxlen", type=int, default=DEFAULT_MAXLEN)
    args = ap.parse_args()

    rows: List[Dict[str, str]] = []
    with open(args.events, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    updated = 0
    for row in rows:
        eid = row.get("id") or row.get("\ufeffid")
        if not eid:
            continue
        if eid not in EVENT_HINTS:
            continue  # 仅处理新增权威事件
        chapter = (row.get("chapter") or "").strip()
        if not chapter:
            continue
        chap_text = load_chapter(args.chapters, chapter)
        if not chap_text:
            continue
        snippet = find_snippet(chap_text, EVENT_HINTS[eid], args.minlen, args.maxlen)
        if snippet and snippet != (row.get("sentence") or "").strip():
            row["sentence"] = snippet
            updated += 1

    # 写回（保持列头次序）
    fieldnames = ["id", "title", "sentence", "chapter", "person"]
    with open(args.events, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            # 兼容 BOM 列名
            if "\ufeffid" in row and "id" not in row:
                row["id"] = row.pop("\ufeffid")
            writer.writerow({k: row.get(k, "") for k in fieldnames})

    print(f"已更新 {updated} 条事件的原文片段。")


if __name__ == "__main__":
    main()
