from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Set


_NAMES: Optional[Set[str]] = None


def _load_names() -> Set[str]:
    global _NAMES
    if _NAMES is not None:
        return _NAMES
    names: Set[str] = set()
    # 优先从 name_dict.txt 读取
    for fname in ["name_dict.txt", "persons_unique.txt"]:
        p = Path(__file__).resolve().parent.parent / fname
        if p.exists():
            with p.open("r", encoding="utf-8") as f:
                for line in f:
                    s = line.strip().split()[0]
                    if s:
                        names.add(s)
    _NAMES = names
    return names


def _extract_persons(q: str) -> List[str]:
    names = _load_names()
    hits = [n for n in names if n and n in q]
    # 按长度降序，去重
    hits = sorted(set(hits), key=len, reverse=True)
    return hits[:3]


def _extract_chapter(q: str) -> Optional[str]:
    # 匹配“第23回/第二十三回/第023回/第23章”等，返回数字字符串
    m = re.search(r"第\s*(\d{1,3})\s*[回章节]", q)
    if m:
        return m.group(1)
    # 备选：直接匹配 1-3 位数字
    m2 = re.search(r"\b(\d{1,3})\b", q)
    return m2.group(1) if m2 else None


def detect_intent_and_entities(q: str) -> Dict:
    qs = q.strip()
    persons = _extract_persons(qs)
    chap = _extract_chapter(qs)

    def has(*kws: str) -> bool:
        return any(k in qs for k in kws)

    if has("判词", "判语"):
        return {"intent": "panci", "who": persons[0] if persons else None}
    if has("关系", "是什么关系") and len(persons) >= 2:
        return {"intent": "relation", "A": persons[0], "B": persons[1]}
    if has("联系", "路径", "怎么连") and len(persons) >= 2:
        return {"intent": "path", "A": persons[0], "B": persons[1]}
    if has("一起", "同场", "同一事件", "同一剧情") and persons:
        return {"intent": "cooccur", "who": persons[0]}
    if chap and has("回", "章节"):
        return {"intent": "chapter_events", "chap": chap}
    if has("参与", "涉及", "发生", "做了什么", "经历") and persons:
        return {"intent": "events", "who": persons[0]}
    # 兜底：关键词搜索事件
    return {"intent": "search", "kw": qs}


# 与服务端保持名称一致的别名
def detect_intent(q: str) -> Dict:
    return detect_intent_and_entities(q)
