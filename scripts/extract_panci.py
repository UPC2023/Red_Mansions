import argparse
import csv
import json
import os
import re
from typing import List, Dict, Tuple


ROOT = os.path.dirname(os.path.dirname(__file__))
CH5 = os.path.join(ROOT, 'reddream_chapters_clean', '005.txt')
PANCI_SUMMARY = os.path.join(ROOT, 'reddream_chapters_clean', 'panci.txt')


def read_text(path: str) -> str:
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def extract_poem_blocks(text: str) -> List[Dict[str, str]]:
    """
    从第五回文本中顺序抽取册页“判词/判语/其词曰”等诗段，并尽量保留前置画面提示。
    返回列表，元素含 {group, hint, poem}
    """
    # 维护当前所在册：正册/副册/又副册
    group = ''
    blocks: List[Dict[str, str]] = []

    # 按行扫描，收集画面提示与判词
    lines = text.splitlines()

    # 正则：判词起始标记
    start_pat = re.compile(
        r'('
        r'也有四句诗道：|'
        r'也有几句言词写道是：|'
        r'也有一首歌词云：|'
        r'其词曰：|'
        r'其断语云：|'
        r'其下书云：|'
        r'其判云：|'
        r'其判曰：|'
        r'书云：|'
        r'写道是：'
        r')'
    )

    i = 0
    last_hint = ''
    while i < len(lines):
        line = lines[i].strip()
        if '金陵十二钗正册' in line:
            group = '正册'
        elif '金陵十二钗副册' in line:
            group = '副册'
        elif '金陵十二钗又副册' in line:
            group = '又副册'

        # 画面提示行（简单启发：包含“画着”或明显意象的句子）
        if ('画着' in line) or ('乌云浊雾' in line) or ('鲜花' in line and '床' in line) or ('桂花' in line and '池' in line):
            last_hint = line

        m = start_pat.search(line)
        if m:
            # 收集后续若干行，直到遇到下一条“后面”/“宝玉还欲看时”/空行分段
            poem_lines = []
            # 如果同一行 start 标记后有内容，截取其后的部分
            after = line.split(m.group(1), 1)[1].strip()
            if after:
                poem_lines.append(after)
            i += 1
            while i < len(lines):
                l2 = lines[i].rstrip()
                l2s = l2.strip()
                if not l2s:
                    break
                if l2s.startswith('后面') or l2s.startswith('宝玉还欲看时'):
                    break
                poem_lines.append(l2s)
                i += 1
            poem = '\n'.join([p for p in poem_lines if p])
            blocks.append({'group': group or '', 'hint': last_hint, 'poem': poem})
            continue  # 已经前进i
        i += 1

    return blocks


def map_blocks_to_names(blocks: List[Dict[str, str]]) -> Dict[str, Dict[str, str]]:
    """
    依据文本出现的经典顺序，映射到十二钗正/副/又副册人物。
    - 正册顺序（本回文本片段）：
      0:（四句合一幅）=> 林黛玉 + 薛宝钗（共用）
      1: 贾元春
      2: 贾探春
      3: 史湘云
      4: 妙玉
      5: 贾迎春
      6: 贾惜春
      7: 王熙凤
      8: 巧姐
      9: 李纨
      10: 秦可卿
    - 副册：香菱（甄英莲）
    - 又副册：晴雯、袭人
    返回一个 name -> {group, poem, hint}
    """
    name_map: Dict[str, Dict[str, str]] = {}

    # 提取分组下的索引序列
    idx_by_group: Dict[str, List[Tuple[int, Dict[str, str]]]] = {'正册': [], '副册': [], '又副册': []}
    for idx, b in enumerate(blocks):
        g = b.get('group', '')
        if g in idx_by_group:
            idx_by_group[g].append((idx, b))

    # 简化：按 blocks 顺序筛选出属于各组的 block 列表
    blocks_zheng = [b for (_, b) in idx_by_group['正册']]
    blocks_fu = [b for (_, b) in idx_by_group['副册']]
    blocks_youfu = [b for (_, b) in idx_by_group['又副册']]

    # 正册映射
    if len(blocks_zheng) >= 11:
        first = blocks_zheng[0]
        # 林黛玉、薛宝钗共用首幅四句判词
        name_map['林黛玉'] = {'group': '正册', 'poem': first['poem'], 'hint': first['hint']}
        name_map['薛宝钗'] = {'group': '正册', 'poem': first['poem'], 'hint': first['hint']}
        mapping_seq = [
            ('贾元春', 1),
            ('贾探春', 2),
            ('史湘云', 3),
            ('妙玉', 4),
            ('贾迎春', 5),
            ('贾惜春', 6),
            ('王熙凤', 7),
            ('巧姐', 8),
            ('李纨', 9),
            ('秦可卿', 10),
        ]
        for name, idx in mapping_seq:
            b = blocks_zheng[idx]
            name_map[name] = {'group': '正册', 'poem': b['poem'], 'hint': b['hint']}

    # 副册映射：香菱（甄英莲）在副册第一条
    if blocks_fu:
        b = blocks_fu[0]
        name_map['香菱'] = {'group': '副册', 'poem': b['poem'], 'hint': b['hint']}
        name_map['甄英莲'] = {'group': '副册', 'poem': b['poem'], 'hint': b['hint']}

    # 又副册：按出现顺序 晴雯、袭人
    if len(blocks_youfu) >= 2:
        name_map['晴雯'] = {'group': '又副册', 'poem': blocks_youfu[0]['poem'], 'hint': blocks_youfu[0]['hint']}
        name_map['袭人'] = {'group': '又副册', 'poem': blocks_youfu[1]['poem'], 'hint': blocks_youfu[1]['hint']}

    return name_map


def parse_summary_panci(text: str) -> Dict[str, Dict[str, str]]:
    """
    解析结构化的 panci.txt：
    - 正册部分：编号+名字行，下一行包含“判词：<内容>”。
    - 副册/又副册部分：形如 “- **姓名**：“诗句……””。
    返回 name -> {group, poem, hint}
    """
    name_map: Dict[str, Dict[str, str]] = {}
    lines = text.splitlines()
    group = ''

    # 辅助函数：将“林黛玉和薛宝钗”拆成人名列表
    def split_names(s: str) -> List[str]:
        s = s.strip()
        # 去掉粗体符号中的 **
        s = re.sub(r'^\*\*|\*\*$', '', s)
        parts = re.split(r'[、，,和\s]+', s)
        return [p for p in (x.strip() for x in parts) if p]

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if '正册判词' in line:
            group = '正册'
        elif '副册判词' in line and '又副册' not in line:
            group = '副册'
        elif '又副册判词' in line:
            group = '又副册'

        # 模式A：编号 + **名字** 行
        m_name = re.match(r'^\s*\d+\.\s*\*\*(.+?)\*\*', line)
        if m_name:
            names = split_names(m_name.group(1))
            poem = ''
            hint = ''
            # 向后查找 “判词：” 行
            j = i + 1
            while j < len(lines):
                l2 = lines[j].strip()
                if not l2:
                    j += 1
                    continue
                if re.match(r'^\s*[-•]\s*\*\*判词\*\*\s*[:：]', l2):
                    poem = re.split(r'[:：]', l2, maxsplit=1)[1].strip()
                    poem = poem.strip('“”"')
                    break
                # 到了下一个编号，提前结束
                if re.match(r'^\s*\d+\.', l2):
                    break
                j += 1
            for nm in names:
                name_map[nm] = {'group': group or '', 'poem': poem, 'hint': hint}
            i = j
            continue

        # 模式B：- **姓名**：“诗句……”
        m_simple = re.match(r'^\s*[-•]\s*\*\*(.+?)\*\*\s*[:：]\s*[“\"](.+?)[”\"]', line)
        if m_simple and group in ('副册', '又副册'):
            nm = m_simple.group(1).strip()
            poem = m_simple.group(2).strip()
            name_map[nm] = {'group': group, 'poem': poem, 'hint': ''}
        i += 1

    # 别名：香菱=甄英莲（若出现其一，另一个也映射同判词）
    if '香菱' in name_map and '甄英莲' not in name_map:
        name_map['甄英莲'] = {**name_map['香菱']}
    if '甄英莲' in name_map and '香菱' not in name_map:
        name_map['香菱'] = {**name_map['甄英莲']}

    return name_map


def main():
    parser = argparse.ArgumentParser(description='提取“判词”并按人物映射导出（优先使用 panci.txt）')
    parser.add_argument('--names', default='', help='以逗号分隔的人名过滤列表；留空则导出映射中全部')
    parser.add_argument('--outdir', default='.', help='输出目录')
    parser.add_argument('--source', choices=['auto', 'summary', 'chapter'], default='auto', help='数据来源：summary=读取 panci.txt；chapter=从第五回正文抽取；auto=存在panci.txt则用summary，否则chapter')
    parser.add_argument('--export-kg', action='store_true', help='将判词写入事件KG（kg_events.csv / kg_event_edges.csv）')
    parser.add_argument('--kg-mode', choices=['append', 'overwrite'], default='append', help='导出KG时写入模式：append=追加，overwrite=覆盖写入')
    args = parser.parse_args()

    # 选择数据来源
    name_map: Dict[str, Dict[str, str]] = {}
    if args.source == 'summary' or (args.source == 'auto' and os.path.exists(PANCI_SUMMARY)):
        text = read_text(PANCI_SUMMARY)
        name_map = parse_summary_panci(text)
        if not name_map:
            # 回退到章节解析
            text = read_text(CH5)
            blocks = extract_poem_blocks(text)
            name_map = map_blocks_to_names(blocks)
    else:
        text = read_text(CH5)
        blocks = extract_poem_blocks(text)
        name_map = map_blocks_to_names(blocks)

    targets: List[str]
    if args.names.strip():
        targets = [x.strip() for x in args.names.split(',') if x.strip()]
    else:
        targets = list(name_map.keys())

    rows = []
    for nm in targets:
        info = name_map.get(nm)
        if not info:
            continue
        rows.append({'name': nm, 'group': info['group'], 'poem': info['poem'], 'hint': info.get('hint', '')})

    os.makedirs(args.outdir, exist_ok=True)
    csv_path = os.path.join(args.outdir, 'panci_selected.csv')
    json_path = os.path.join(args.outdir, 'panci_selected.json')

    with open(csv_path, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['name', 'group', 'poem', 'hint'])
        w.writeheader()
        for r in rows:
            w.writerow(r)
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)

    print(f'[DONE] 导出 {len(rows)} 条判词 -> {csv_path}, {json_path}')

    # 可选：写入事件KG
    if args.export_kg and rows:
        kg_events = os.path.join(args.outdir, 'kg_events.csv')
        kg_edges = os.path.join(args.outdir, 'kg_event_edges.csv')

        # 事件ID：PANCI_{name}
        def eid_for(name: str) -> str:
            base = f'PANCI_{name}'
            base = re.sub(r'[^\w\u4e00-\u9fa5]+', '_', base)
            return base

        # 写事件节点
        write_header_nodes = True
        write_header_edges = True
        if args.kg_mode == 'append' and os.path.exists(kg_events):
            write_header_nodes = False
        if args.kg_mode == 'append' and os.path.exists(kg_edges):
            write_header_edges = False

        mode = 'w' if args.kg_mode == 'overwrite' else 'a'

        with open(kg_events, mode, encoding='utf-8', newline='') as f:
            w = csv.writer(f)
            if write_header_nodes:
                w.writerow(['id', 'title', 'sentence', 'chapter', 'person'])
            for r in rows:
                eid = eid_for(r['name'])
                title = f"{r['name']}判词"
                sentence = r['poem']
                chapter = '第五回/判词汇总'
                person = r['name']
                w.writerow([eid, title, sentence, chapter, person])

        with open(kg_edges, mode, encoding='utf-8', newline='') as f:
            w = csv.writer(f)
            if write_header_edges:
                w.writerow(['src', 'dst', 'type'])
            for r in rows:
                eid = eid_for(r['name'])
                # 人物 -> 判词事件
                w.writerow([r['name'], eid, '拥有判词'])

        print(f"[KG] 已写入事件节点/边 -> {kg_events}, {kg_edges} （模式：{args.kg_mode}）")


if __name__ == '__main__':
    main()
