"""
验证 Neo4j 中人物关系与事件/判词是否正确导入。

输出：
- 事件节点数、INVOLVED 边数量
- 判词样例（拥有判词）前 10 条
- 人物样例（王熙凤、林黛玉）参与的事件前 5 条
- 一个人物关系样例（贾宝玉）前 5 条
"""
from py2neo import Graph
from config import get_graph

graph = get_graph()


def q(graph: Graph, cypher: str, **params):
    return list(graph.run(cypher, **params))


def main():
    print("== 基本统计 ==")
    ev_cnt = q(graph, "MATCH (e:Event) RETURN count(e) AS c")[0]["c"]
    inv_cnt = q(graph, "MATCH ()-[r:INVOLVED]->() RETURN count(r) AS c")[0]["c"]
    rel_cnt = q(graph, "MATCH ()-[r:RELATION]->() RETURN count(r) AS c")[0]["c"]
    print(f"Event 节点: {ev_cnt}")
    print(f"INVOLVED 边: {inv_cnt}")
    print(f"RELATION 边: {rel_cnt}")

    print("\n== 判词样例（拥有判词，去重后按人名排序取前10）==")
    rows = q(
        graph,
        """
        MATCH (p:Person)-[r:INVOLVED {type:'拥有判词'}]->(e:Event)
        RETURN coalesce(p.name,p.Name) AS person, e.id AS event_id, e.title AS title
        ORDER BY person
        LIMIT 10
        """,
    )
    for r in rows:
        print(f"{r['person']} -> {r['event_id']} | {r['title']}")

    print("\n== 王熙凤 参与的事件（按事件ID排序取前5）==")
    rows = q(
        graph,
        """
        MATCH (p:Person)-[r:INVOLVED]->(e:Event)
        WHERE coalesce(p.name,p.Name)='王熙凤'
        RETURN r.type AS type, e.id AS event_id, e.title AS title
        ORDER BY event_id
        LIMIT 5
        """,
    )
    for r in rows:
        print(f"[{r['type']}] {r['event_id']} | {r['title']}")

    print("\n== 林黛玉 参与的事件（按事件ID排序取前5）==")
    cnt_rows = q(
        graph,
        """
        MATCH (p:Person)-[r:INVOLVED]->(e:Event)
        WHERE coalesce(p.name,p.Name)='林黛玉'
        RETURN count(r) AS c
        """,
    )
    print(f"林黛玉 INVOLVED 边计数: {cnt_rows[0]['c']}")
    rows = q(
        graph,
        """
        MATCH (p:Person)-[r:INVOLVED]->(e:Event)
        WHERE coalesce(p.name,p.Name)='林黛玉'
        RETURN r.type AS type, e.id AS event_id, e.title AS title
        ORDER BY event_id
        LIMIT 5
        """,
    )
    for r in rows:
        print(f"[{r['type']}] {r['event_id']} | {r['title']}")
    print("\n== 贾宝玉 参与的事件（按事件ID排序取前8）==")
    rows = q(
        graph,
        """
        MATCH (p:Person)-[r:INVOLVED]->(e:Event)
        WHERE coalesce(p.name,p.Name)='贾宝玉'
        RETURN r.type AS type, e.id AS event_id, e.title AS title
        ORDER BY event_id
        LIMIT 8
        """,
    )
    for r in rows:
        print(f"[{r['type']}] {r['event_id']} | {r['title']}")

    print("\n== 薛宝钗 参与的事件（按事件ID排序取前7）==")
    rows = q(
        graph,
        """
        MATCH (p:Person)-[r:INVOLVED]->(e:Event)
        WHERE coalesce(p.name,p.Name)='薛宝钗'
        RETURN r.type AS type, e.id AS event_id, e.title AS title
        ORDER BY event_id
        LIMIT 7
        """,
    )
    for r in rows:
        print(f"[{r['type']}] {r['event_id']} | {r['title']}")

    print("\n== 人物关系样例：贾宝玉（前5）==")
    rows = q(
        graph,
        """
        MATCH (:Person {name:'贾宝玉'})-[r:RELATION]-(p)
        RETURN r.type AS type, coalesce(p.name,p.Name) AS other
        LIMIT 5
        """,
    )
    for r in rows:
        print(f"{r['type']} -> {r['other']}")

    print("\n== 人物-人物关系样例 (前10) ==")
    rels = graph.run(
        """
        MATCH (a:Person)-[r:RELATION]->(b:Person)
        RETURN coalesce(a.name,a.Name) AS src, r.type AS rel, coalesce(b.name,b.Name) AS dst
        LIMIT 10
        """
    ).data()
    for row in rels:
        print(f"{row['src']} -[{row['rel']}]-> {row['dst']}")


if __name__ == "__main__":
    main()
