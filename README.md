# 红楼梦知识图谱与问答系统

一个基于 Neo4j 的《红楼梦》人物—事件知识图谱，并提供 FastAPI 问答服务与简洁前端（/ui）。支持查询判词、人物剧情、人物关系、章节事件与关键词检索等。

- 数据层：Neo4j（节点 Person、Event；关系 RELATION、INVOLVED）
- 服务层：FastAPI + py2neo（/qa 接口，/docs Swagger，/ui 前端）
- 前端层：静态页面（可选：粒子/星宿水墨背景、首屏图片轮播），/photos 人物图

## 目录结构（摘）
- kg_events.csv                事件/判词列表
- kg_event_edges.csv           人物—事件边（参与/涉及/拥有判词）
- relation.txt                 人物—人物关系（父亲/儿子/夫妻/朋友…）
- persons_unique.txt           人物名清单（去重）
- name_dict.txt                问答人名词典（抽取匹配用）
- reddream_chapters/           原文章节（用于事件节选抽取）
- photos/                      前端轮播图片（已在后端静态挂载）
- scripts/
  - qa_service.py              后端服务入口（/qa、/ui、/photos）
  - qa_intent.py               轻量规则意图识别与实体抽取
  - qa_cypher.py               模板化 Cypher 生成与执行
  - qa_answer.py               答案格式化
  - create_event_graph.py      导入 Event/INVOLVED
  - import_relations_from_txt.py 导入 RELATION
  - sync_event_edges.py        按 CSV 清理多余 INVOLVED 边
  - verify_graph.py            图谱校验与样例输出
  - extract_event_snippets.py  从章节抽取事件节选（可选）
  - extract_character_events.py 人物剧情抽取（可选）
- frontend/                    前端静态资源（index.html、styles.css 等）

## 环境与依赖（Windows）
推荐使用 Conda（你之前可运行的环境即可）。也可用 venv。

- Neo4j：本机或远程已启动（默认 bolt://localhost:7687）
- Python 3.9+：已在 Conda 环境中安装 fastapi、uvicorn、py2neo

Conda（推荐）
```powershell
# 替换为你可用的环境名（例如 py39_numpy）
conda activate <你的conda环境名>
# 安装依赖（若已安装可跳过）
python -m pip install --upgrade pip
python -m pip install fastapi uvicorn py2neo
```

venv（备选）
```powershell
cd "c:\red dream\red_dream"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install fastapi uvicorn py2neo
```

## 配置 Neo4j
- 在 config.py 中设置 NEO4J_URL、NEO4J_AUTH（bolt 地址、用户名、密码）
- 保证数据库已启动并可连接

## 导入数据（首次或数据更新后执行）
在仓库根目录执行：
```powershell
# 1) 人物—人物关系（relation.txt → RELATION）
python -m scripts.import_relations_from_txt

# 2) 事件与人物—事件边（CSV → Event/INVOLVED）
python -m scripts.create_event_graph --events kg_events.csv --edges kg_event_edges.csv

# 3) 同步清理：删掉图中不在 CSV 里的多余 INVOLVED 边（可选，推荐）
python -m scripts.sync_event_edges --edges kg_event_edges.csv

# 4) 校验：计数、样例、判词唯一性等
python -m scripts.verify_graph
```

说明
- 关系查询为“无向匹配”（MATCH (a)-[r:RELATION]-(b)），即使导入时只写了一侧方向，也能查到（如“贾宝玉—史湘云→朋友”）。
- 若要为对称关系（朋友/夫妻等）写双向边，可在导入脚本启用补反向（可选）。

## 启动问答服务（后端托管前端）
```powershell
# Conda 环境下
conda activate <你的conda环境名>
cd "c:\red dream\red_dream"
python -m scripts.qa_service
```
访问：
- 前端：http://127.0.0.1:8000/ui
- API 文档：http://127.0.0.1:8000/docs

局域网访问（可选）
```powershell
uvicorn scripts.qa_service:app --host 0.0.0.0 --port 8000
```

## 使用示例
前端示例问题：
- 王熙凤的判词是什么？
- 林黛玉参与了什么？
- 贾政和贾宝玉是什么关系？
- 第23回讲了什么？

接口示例（PowerShell）
```powershell
$body = @{ question = "贾宝玉和史湘云是什么关系？" } | ConvertTo-Json
Invoke-RestMethod -Method POST -Uri http://127.0.0.1:8000/qa -Body $body -ContentType 'application/json'
```

## 数据文件说明
- relation.txt：人物—人物关系。导入为 [:RELATION {type}]。查询采用无向匹配，方向不敏感。
- kg_events.csv：事件/判词。判词也作为 Event 节点统一管理。
- kg_event_edges.csv：人物—事件边 [:INVOLVED {type}]，type ∈ 参与/涉及/拥有判词。
- name_dict.txt：问答系统的“人名抽取词典”，由 qa_intent.py 用于命中问句中的主语/宾语人物。
  - 如需加入别名（如“甄英莲/英莲”），直接在此文件补充，以提升命中率。
  - 若要将别名归一到同一人物，可在 qa_intent.py 中加入 alias 映射，或在 Person 节点增加 aliases 属性并在 Cypher 中匹配。
- persons_unique.txt：人物去重清单，导入前校验与统计可用。
- reddream_chapters/：章节文本（可用于 extract_event_snippets.py 抽取事件节选）。

## 截图建议（成果展示）
- 数据目录结构（kg_events.csv、kg_event_edges.csv、relation.txt、name_dict.txt、reddream_chapters/）
- create_event_graph/import_relations_from_txt 的导入终端输出
- verify_graph 的计数与样例（判词唯一、关键人物剧情）
- /docs Swagger 与 /ui 前端问答实拍

## 常见问题
- No module named 'fastapi'：使用安装依赖的同一解释器启动服务（Conda 环境内）；必要时用绝对路径启动。
- 无法连接 Neo4j：检查 config.py 的 bolt 地址与账号密码，确认 Neo4j 已启动。
- 关系查不到：确认已导入 relation.txt；查询已改为无向匹配，方向不敏感。

## 设计要点
- 轻量规则意图识别（qa_intent.py）+ 模板化 Cypher（qa_cypher.py），避免复杂 NLP 依赖，便于复现与调试。
- 判词统一为 Event 节点，人物通过 INVOLVED(type='拥有判词') 关联，查询与展示一致化。
- 章节节选可自动抽取（extract_event_snippets.py），QA 答案可带原文片段。

---
如需进一步优化（别名归一、前端视觉、更多问答意图），可在 issues 中记录并逐步增强。