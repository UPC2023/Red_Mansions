"""
将 Neo4j 中 (Person)-[INVOLVED]->(Event) 的边与本地 CSV (kg_event_edges.csv) 同步：
- 读取 CSV，构建允许存在的三元组集合 (src_name, event_id, type)
- 枚举图中现有 INVOLVED 边，凡不在集合内的，一律删除（清理历史错误边）

用法（在项目根目录执行）:
  python -m scripts.sync_event_edges --edges kg_event_edges.csv
"""
from __future__ import annotations

import csv
import argparse
from typing import Set, Tuple

from config import get_graph


def load_allowed(path: str) -> Set[Tuple[str, str, str]]:
    allowed: Set[Tuple[str, str, str]] = set()
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            src = (row.get("src") or row.get("\ufeffsrc") or "").strip()
            dst = (row.get("dst") or "").strip()
            rtype = (row.get("type") or "参与").strip()
            if not src or not dst:
                continue
            allowed.add((src, dst, rtype))
    return allowed


def build_current(graph) -> Set[Tuple[str, str, str]]:
    data = graph.run(
        """
        MATCH (p:Person)-[r:INVOLVED]->(e:Event)
        RETURN coalesce(p.name,p.Name) AS src, e.id AS dst, r.type AS type
        """
    ).data()
    cur: Set[Tuple[str, str, str]] = set()
    for row in data:
        src = (row["src"] or "").strip()
        dst = (row["dst"] or "").strip()
        rtype = (row["type"] or "参与").strip()
        if src and dst:
            cur.add((src, dst, rtype))
    return cur


def delete_extra(graph, extras: Set[Tuple[str, str, str]]) -> int:
    """删除不在允许集合内的 INVOLVED 边。"""
    deleted = 0
    tx = graph.begin()
    for src, dst, rtype in extras:
        tx.run(
            """
            MATCH (p:Person)-[r:INVOLVED {type:$rtype}]->(e:Event {id:$dst})
            WHERE p.name=$src OR p.Name=$src
            DELETE r
            """,
            src=src,
            dst=dst,
            rtype=rtype,
        )
        deleted += 1
    graph.commit(tx)
    return deleted


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--edges", default="kg_event_edges.csv", help="人物-事件边CSV路径")
    args = ap.parse_args()

    graph = get_graph()

    allowed = load_allowed(args.edges)
    current = build_current(graph)
    extras = current - allowed

    print(f"CSV 边数: {len(allowed)} | 图中边数: {len(current)} | 需删除: {len(extras)}")
    if extras:
        n = delete_extra(graph, extras)
        print(f"已删除多余 INVOLVED 边: {n}")
    else:
        print("无需删除，多余边为 0")


if __name__ == "__main__":
    main()
