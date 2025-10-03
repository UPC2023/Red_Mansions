from __future__ import annotations

from typing import Dict, Tuple, Any
from config import get_graph


def build_query(payload: Dict) -> Tuple[str, Dict[str, Any]]:
    intent = payload.get("intent")
    if intent == "panci":
        return (
            """
            MATCH (p:Person)-[:INVOLVED {type:'拥有判词'}]->(e:Event)
            WHERE coalesce(p.name,p.Name) = $who
            RETURN e.title AS title, e.sentence AS sentence, e.chapter AS chapter
            LIMIT 1
            """,
            {"who": payload.get("who")},
        )
    if intent == "events":
        return (
            """
            MATCH (p:Person)-[r:INVOLVED]->(e:Event)
            WHERE coalesce(p.name,p.Name) = $who AND r.type IN ['参与','涉及']
            RETURN r.type AS rtype, e.title AS title, e.sentence AS sentence, e.chapter AS chapter
            ORDER BY e.id
            LIMIT 10
            """,
            {"who": payload.get("who")},
        )
    if intent == "relation":
        return (
            """
            MATCH (a:Person)-[r:RELATION]-(b:Person)
            WHERE coalesce(a.name,a.Name)=$A AND coalesce(b.name,b.Name)=$B
            RETURN DISTINCT r.type AS rtype LIMIT 5
            """,
            {"A": payload.get("A"), "B": payload.get("B")},
        )
    if intent == "path":
        return (
            """
            MATCH (a:Person) WHERE coalesce(a.name,a.Name)=$A
            MATCH (b:Person) WHERE coalesce(b.name,b.Name)=$B
            MATCH p=shortestPath((a)-[*..4]-(b))
            RETURN p LIMIT 1
            """,
            {"A": payload.get("A"), "B": payload.get("B")},
        )
    if intent == "cooccur":
        return (
            """
            MATCH (p:Person)-[:INVOLVED]->(e:Event)<-[:INVOLVED]-(q:Person)
            WHERE coalesce(p.name,p.Name)=$who AND coalesce(q.name,q.Name)<>$who
            RETURN DISTINCT coalesce(q.name,q.Name) AS other, e.title AS title, e.chapter AS chapter
            LIMIT 10
            """,
            {"who": payload.get("who")},
        )
    if intent == "chapter_events":
        return (
            """
            MATCH (e:Event) WHERE e.chapter CONTAINS $chap
            RETURN e.title AS title, e.sentence AS sentence, e.chapter AS chapter
            LIMIT 10
            """,
            {"chap": payload.get("chap")},
        )
    # search 兜底
    return (
        """
        WITH $kw AS kw
        MATCH (e:Event)
        WHERE e.title CONTAINS kw OR e.sentence CONTAINS kw
        RETURN e.title AS title, e.sentence AS sentence, e.chapter AS chapter
        LIMIT 10
        """,
        {"kw": payload.get("kw")},
    )


def run_query(cypher: str, params: Dict) -> list[dict]:
    graph = get_graph()
    return list(graph.run(cypher, **params))
