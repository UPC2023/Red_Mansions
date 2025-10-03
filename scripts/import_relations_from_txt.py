"""
从 relation.txt 导入人物关系到 Neo4j。

relation.txt 每行：主语,客体,关系,主语家族,客体家族
示例：王熙凤,贾琏,妻,王家,贾家荣国府

建模：
- (:Person {name, Name, cate}) 统一人物节点，name/Name 双属性兼容
- (:Person)-[:RELATION {type, chapter?, sentence?}]->(:Person)

注意：人物关系的中文关系作为属性 `type`，而不是关系类型，避免中文作为类型带来的限制。
"""
from __future__ import annotations

import csv
from typing import Optional
from py2neo import Graph
from config import get_graph, similar_words


def ensure_constraints(graph: Graph):
    graph.run(
        """
        CREATE CONSTRAINT person_name_unique IF NOT EXISTS
        FOR (p:Person)
        REQUIRE p.name IS UNIQUE
        """
    )


def _get_or_create_person(tx, name: str, cate: Optional[str] = None):
    rec = tx.run(
        """
        MATCH (p:Person)
        WHERE p.name=$name OR p.Name=$name
        RETURN id(p) AS pid
        LIMIT 1
        """,
        name=name,
    ).evaluate()
    if rec is None:
        tx.run(
            "MERGE (p:Person {name:$name}) ON CREATE SET p.Name=$name, p.cate=$cate",
            name=name,
            cate=cate,
        )
    else:
        tx.run(
            """
            MATCH (p:Person) WHERE id(p)=$pid
            SET p.name = coalesce(p.name, $name), p.Name = coalesce(p.Name, $name)
            SET p.cate = coalesce(p.cate, $cate)
            """,
            pid=rec,
            name=name,
            cate=cate,
        )


def import_relations(graph: Graph, path: str = "relation.txt") -> int:
    count = 0
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        tx = graph.begin()
        for row in reader:
            if not row or len(row) < 5:
                # 兼容可能存在的空行
                continue
            a, b, rel, a_cate, b_cate = [cell.strip() for cell in row[:5]]
            if not a or not b or not rel:
                continue

            # 关系同义词归一
            rel_norm = similar_words.get(rel, rel)

            _get_or_create_person(tx, a, a_cate)
            _get_or_create_person(tx, b, b_cate)

            tx.run(
                """
                MATCH (x:Person) WHERE x.name=$a OR x.Name=$a
                MATCH (y:Person) WHERE y.name=$b OR y.Name=$b
                MERGE (x)-[r:RELATION {type:$rel}]->(y)
                """,
                a=a,
                b=b,
                rel=rel_norm,
            )
            count += 1
        # 提交事务（避免使用已废弃的 tx.commit()）
        graph.commit(tx)
    return count


def main():
    graph = get_graph()
    ensure_constraints(graph)
    n = import_relations(graph)
    print(f"[Neo4j] 已导入人物-人物关系条数: {n}")


if __name__ == "__main__":
    main()
