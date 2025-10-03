// 将 kg_nodes.csv / kg_edges.csv 放入 Neo4j 的 import 目录后执行
// 适用于 Neo4j Desktop 或本地服务器，注意启用 apoc 或者使用纯 LOAD CSV

// 建立唯一约束
CREATE CONSTRAINT person_name_unique IF NOT EXISTS
FOR (p:Person)
REQUIRE p.name IS UNIQUE;

CREATE CONSTRAINT event_id_unique IF NOT EXISTS
FOR (e:Event)
REQUIRE e.id IS UNIQUE;

// 导入节点
LOAD CSV WITH HEADERS FROM 'file:///kg_nodes.csv' AS row
MERGE (p:Person {name: row.name});

// 导入关系（统一用 RELATION 类型，并将中文关系作为属性）
LOAD CSV WITH HEADERS FROM 'file:///kg_edges.csv' AS row
MATCH (h:Person {name: row.head})
MATCH (t:Person {name: row.tail})
MERGE (h)-[r:RELATION {type: row.relation}]->(t)
ON CREATE SET r.chapter = row.chapter, r.sentence = row.sentence;

// ===== 事件/判词 导入 =====
// 导入事件节点（人物剧情、判词等，统一用标签 Event）
LOAD CSV WITH HEADERS FROM 'file:///kg_events.csv' AS row
MERGE (e:Event {id: row.id})
ON CREATE SET e.title=row.title, e.sentence=row.sentence, e.chapter=row.chapter, e.person=row.person
ON MATCH  SET e.title=row.title, e.sentence=row.sentence, e.chapter=row.chapter, e.person=row.person;

// 导入人物->事件 边（统一类型 INVOLVED，中文边型写入属性 type，例如 参与/涉及/拥有判词）
LOAD CSV WITH HEADERS FROM 'file:///kg_event_edges.csv' AS row
MERGE (p:Person {name: row.src})
MERGE (e:Event {id: row.dst})
MERGE (p)-[r:INVOLVED {type: row.type}]->(e);

// 常用查询示例：
// 1) 查询人物的所有关系
// MATCH (:Person {name:'贾宝玉'})-[r:RELATION]-(p) RETURN r,p LIMIT 50;
// 2) 查询两人之间的路径
// MATCH p=shortestPath((a:Person {name:'贾宝玉'})-[*..4]-(b:Person {name:'林黛玉'})) RETURN p;
// 3) 指定关系类型
// MATCH (:Person {name:'贾政'})-[r:RELATION {type:'父亲'}]->(p) RETURN p;

// 4) 查询人物参与的事件/判词
// MATCH (p:Person {name:'林黛玉'})-[r:INVOLVED]->(e:Event) RETURN r,e LIMIT 20;
// 5) 仅查看拥有判词的边
// MATCH (p:Person)-[r:INVOLVED {type:'拥有判词'}]->(e:Event) RETURN p,e LIMIT 20;
