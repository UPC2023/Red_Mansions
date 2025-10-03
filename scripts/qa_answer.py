from __future__ import annotations

from typing import List, Dict


def format_answer(intent: str, payload: Dict, rows: List[Dict]) -> str:
    if not rows:
        if intent == "search":
            return "没有直接命中，建议换个说法或提供更多关键词。"
        return "暂无查询结果。"

    if intent == "panci":
        r = rows[0]
        return f"判词：{r['title']}。正文：{_preview(r['sentence'])}（章节：{r['chapter']}）"

    if intent == "events":
        items = [f"[{r['rtype']}] {r['title']}（{_preview(r['sentence'])}，章：{r['chapter']}）" for r in rows[:5]]
        return "相关剧情：\n- " + "\n- ".join(items)

    if intent == "relation":
        kinds = ", ".join(sorted({r['rtype'] for r in rows if r.get('rtype')}))
        return f"两者关系：{kinds or '未明确'}。"

    if intent == "path":
        return "已找到两者之间的连接路径（请在图视图中查看细节）。"

    if intent == "cooccur":
        items = [f"{r['other']}（事件：{r['title']}，章：{r['chapter']}）" for r in rows[:5]]
        return "同一事件出现的人物：\n- " + "\n- ".join(items)

    if intent == "chapter_events":
        items = [f"{r['title']}（{_preview(r['sentence'])}）" for r in rows[:5]]
        return "该章节相关事件：\n- " + "\n- ".join(items)

    # search
    items = [f"{r['title']}（{_preview(r['sentence'])}）" for r in rows[:5]]
    return "相关事件：\n- " + "\n- ".join(items)


def _preview(text: str, n: int = 40) -> str:
    if not text:
        return ""
    t = text.replace("\n", " ").strip()
    return t if len(t) <= n else t[:n] + "…"
