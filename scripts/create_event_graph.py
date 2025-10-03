"""
将人物事件与判词写入 Neo4j

数据来源：
- kg_events.csv: id,title,sentence,chapter,person
- kg_event_edges.csv: src,dst,type  （src=人物名，dst=事件ID，type=参与/涉及/拥有判词 等）

用法（在项目根目录执行）：
  python -m scripts.create_event_graph --events kg_events.csv --edges kg_event_edges.csv

注意：连接配置复用 config.py 中的 Graph 实例。
"""
from __future__ import annotations

import csv
import argparse
from typing import Iterable, Dict

from py2neo import Node, Relationship
from config import get_graph

# 惰性获取 Graph 实例，避免模块导入期出错
graph = get_graph()


def ensure_constraints() -> None:
    # 为 Event.id 创建唯一约束
    graph.run(
        """
        CREATE CONSTRAINT event_id_unique IF NOT EXISTS
        FOR (e:Event)
        REQUIRE e.id IS UNIQUE
        """
    )


def load_events(path: str) -> int:
    count = 0
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        tx = graph.begin()
        for row in reader:
            # 兼容带 BOM 的列名
            rid = row.get("id") or row.get("\ufeffid")
            if not rid:
                continue
            title = row.get("title", "")
            sentence = row.get("sentence", "")
            chapter = row.get("chapter", "")
            person = row.get("person", "")

            # MERGE 事件节点
            tx.run(
                """
                MERGE (e:Event {id: $id})
                ON CREATE SET e.title=$title, e.sentence=$sentence, e.chapter=$chapter, e.person=$person
                ON MATCH  SET e.title=$title, e.sentence=$sentence, e.chapter=$chapter, e.person=$person
                """,
                id=rid,
                title=title,
                sentence=sentence,
                chapter=chapter,
                person=person,
            )
            count += 1
        graph.commit(tx)
    return count


def _get_or_create_person(tx, name: str) -> None:
    """确保存在一个 Person 节点（兼容 name/Name），若无则创建，并补全两个属性。"""
    # 先尝试匹配任何已有的 Person（name 或 Name 命中）
    rec = tx.run(
        """
        MATCH (p:Person)
        WHERE p.name = $name OR p.Name = $name
        RETURN id(p) AS pid
        LIMIT 1
        """,
        name=name,
    ).evaluate()
    if rec is None:
        # 不存在则创建，并同时写入两个属性，便于后续统一使用 name
        tx.run(
            "MERGE (p:Person {name:$name}) ON CREATE SET p.Name=$name",
            name=name,
        )
    else:
        # 若存在但缺少规范属性 name，则补齐（尽量不破坏原有 Name）
        tx.run(
            """
            MATCH (p:Person)
            WHERE id(p) = $pid
            SET p.name = coalesce(p.name, $name), p.Name = coalesce(p.Name, $name)
            """,
            pid=rec,
            name=name,
        )


def load_event_edges(path: str) -> int:
    count = 0
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        tx = graph.begin()
        for row in reader:
            src = row.get("src") or row.get("\ufeffsrc")
            dst = row.get("dst")
            rtype = row.get("type", "参与")
            if not src or not dst:
                continue

            # 人物：兼容既有 Name/name，必要时创建并补齐双属性
            _get_or_create_person(tx, src)

            # 事件存在性由 load_events 保障；此处也做一次惰性创建以健壮
            tx.run("MERGE (e:Event {id:$id})", id=dst)

            # 统一用 INVOLVED 类型，中文关系放在属性 type
            tx.run(
                """
                MATCH (p:Person)
                WHERE p.name=$src OR p.Name=$src
                MATCH (e:Event {id:$dst})
                MERGE (p)-[r:INVOLVED {type:$rtype}]->(e)
                """,
                src=src,
                dst=dst,
                rtype=rtype,
            )
            count += 1
        graph.commit(tx)
    return count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", default="kg_events.csv", help="事件CSV路径")
    parser.add_argument("--edges", default="kg_event_edges.csv", help="人物-事件边CSV路径")
    args = parser.parse_args()

    ensure_constraints()
    n_event = load_events(args.events)
    n_edges = load_event_edges(args.edges)
    print(f"[Neo4j] 已导入事件节点: {n_event}，人物-事件边: {n_edges}")


if __name__ == "__main__":
    main()
