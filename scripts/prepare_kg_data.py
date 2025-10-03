import os
import csv
import json
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(__file__))
ALL_REL = os.path.join(ROOT, 'all_relations.csv')
NODES_CSV = os.path.join(ROOT, 'kg_nodes.csv')
EDGES_CSV = os.path.join(ROOT, 'kg_edges.csv')
ECHARTS_JSON = os.path.join(ROOT, 'kg_echarts.json')

nodes = {}
links = []

# 读取 all_relations.csv: chapter,sentence,entity1,entity2,relation
with open(ALL_REL, 'r', encoding='utf-8') as f:
    header = f.readline()
    for line in f:
        line = line.rstrip('\n')
        if not line:
            continue
        chapter, sentence, e1, e2, rel = line.split(',', 4)
        for name in (e1, e2):
            if name not in nodes:
                nodes[name] = {
                    'id': name,
                    'name': name,
                    'category': '人物',
                    'value': 1
                }
        links.append({
            'source': e1,
            'target': e2,
            'relation': rel,
            'chapter': chapter,
            'sentence': sentence
        })

# 写出 Neo4j CSV
with open(NODES_CSV, 'w', encoding='utf-8', newline='') as f:
    w = csv.writer(f)
    w.writerow(['name','label'])
    for n in nodes.values():
        w.writerow([n['name'], 'Person'])

with open(EDGES_CSV, 'w', encoding='utf-8', newline='') as f:
    w = csv.writer(f)
    w.writerow(['head','tail','relation','chapter','sentence'])
    for l in links:
        w.writerow([l['source'], l['target'], l['relation'], l['chapter'], l['sentence']])

# 写出 ECharts JSON
out = {
    'nodes': [{'id': n['id'], 'name': n['name'], 'category': n['category'], 'value': n['value']} for n in nodes.values()],
    'links': [{'source': l['source'], 'target': l['target'], 'name': l['relation']} for l in links]
}
with open(ECHARTS_JSON, 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

print('导出完成:')
print(' -', NODES_CSV)
print(' -', EDGES_CSV)
print(' -', ECHARTS_JSON)
