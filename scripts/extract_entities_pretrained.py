#scripts\extract_entities_pretrained.py
# -*- coding: utf-8 -*-
"""
基于预训练模型的实体抽取（无需训练）：
- 首选 HuggingFace NER pipeline（中文已微调模型），抽取 PER 实体；
- 若本机未安装 transformers 或模型下载失败，则回退到词典匹配（name_dict.txt 或 entity_list.txt）。
- 输入：reddream_chapters_clean/*.txt
- 输出：ner_entities.csv（明细）、persons_unique.txt（去重人物名单）

可配置：
- 默认模型：'uer/roberta-base-finetuned-cluener2020-chinese'（中文NER，含 PER/ORG/LOC 等）
- aggregation_strategy='simple' 聚合子词
"""
import os
import re
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLEAN_DIR = ROOT / 'reddream_chapters_clean'
NAME_DICT = ROOT / 'name_dict.txt'
ENTITY_LIST = ROOT / 'entity_list.txt'
OUT_CSV = ROOT / 'ner_entities.csv'
OUT_TXT = ROOT / 'persons_unique.txt'

DEFAULT_MODEL = 'uer/roberta-base-finetuned-cluener2020-chinese'


def load_known_names():
    """加载本地人物词典（name_dict.txt 优先，其次 entity_list.txt）。支持`name\tscore`或单列。"""
    names = set()
    src = None
    if NAME_DICT.exists():
        src = NAME_DICT
    elif ENTITY_LIST.exists():
        src = ENTITY_LIST
    if src is None:
        return names, None
    with open(src, 'r', encoding='utf-8') as f:
        for ln in f:
            ln = ln.strip()
            if not ln:
                continue
            nm = ln.split('\t')[0].strip()
            if nm:
                names.add(nm)
    return names, src.name


def iter_sentences_from_files(limit_sent_per_file=None):
    """遍历清洗文本并按句子分割；yield (file, sent_index, sentence)。"""
    if not CLEAN_DIR.exists():
        raise FileNotFoundError('未找到目录 reddream_chapters_clean')
    files = sorted(CLEAN_DIR.glob('*.txt'))
    sent_split = re.compile(r'[。！？!?]')
    for p in files:
        try:
            text = p.read_text(encoding='utf-8')
        except Exception:
            continue
        sentences = [s.strip() for s in sent_split.split(text) if s and len(s.strip()) > 1]
        if limit_sent_per_file:
            sentences = sentences[:limit_sent_per_file]
        for idx, s in enumerate(sentences):
            yield p.name, idx, s


def run_with_hf(model_name=DEFAULT_MODEL, max_files=None, limit_sent_per_file=200):
    """使用 HuggingFace NER pipeline 进行抽取。返回 rows(list[dict])。"""
    try:
        from transformers import pipeline
    except Exception as e:
        print('[WARN] 未安装 transformers 或导入失败，将使用规则回退。错误：', e)
        return None

    print('[INFO] 加载模型：', model_name)
    nlp = pipeline('ner', model=model_name, aggregation_strategy='simple')

    rows = []
    file_count = 0
    for fname, idx, sent in iter_sentences_from_files(limit_sent_per_file=limit_sent_per_file):
        # 可选：限制处理文件数以便快速试跑
        if max_files is not None and file_count > max_files:
            break
        if idx == 0:
            file_count += 1
        try:
            results = nlp(sent)
        except Exception as e:
            # 某些超长句或异常，跳过
            continue
        for r in results:
            ent = r.get('word') or r.get('entity')
            etype = r.get('entity_group') or r.get('entity')
            score = r.get('score', None)
            # 仅保留人物
            if (etype or '').upper() in ('PER', 'PERSON', 'NR', 'Nh'):
                rows.append({
                    'file': fname,
                    'sent_index': idx,
                    'entity': ent,
                    'type': 'PER',
                    'score': f"{score:.4f}" if isinstance(score, float) else (score or ''),
                })
    return rows


def run_with_dict(names, max_files=None, limit_sent_per_file=200):
    """词典回退：基于已知名单匹配句子（长词优先）。返回 rows(list[dict])。"""
    if not names:
        print('[WARN] 本地未找到 name_dict.txt 或 entity_list.txt，无法规则回退。')
        return []
    sorted_names = sorted(names, key=len, reverse=True)
    rows = []
    file_count = 0
    for fname, idx, sent in iter_sentences_from_files(limit_sent_per_file=limit_sent_per_file):
        if max_files is not None and file_count > max_files:
            break
        if idx == 0:
            file_count += 1
        found = set()
        for nm in sorted_names:
            if nm in sent:
                found.add(nm)
        for ent in sorted(found):
            rows.append({
                'file': fname,
                'sent_index': idx,
                'entity': ent,
                'type': 'PER',
                'score': '',
            })
    return rows


def save_outputs(rows):
    # 明细 CSV
    with open(OUT_CSV, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['file','sent_index','entity','type','score'])
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
    # 去重人物
    uniq = sorted({r['entity'] for r in rows if r.get('entity')})
    with open(OUT_TXT, 'w', encoding='utf-8') as f:
        for name in uniq:
            f.write(name + '\n')
    print('[OK] 写出：', OUT_CSV)
    print('[OK] 写出：', OUT_TXT, '（共', len(uniq), '人）')


def main():
    names, src = load_known_names()
    if src:
        print('[INFO] 本地人物名单：', src, '（', len(names), '条 ）')

    rows = run_with_hf(model_name=DEFAULT_MODEL, max_files=None, limit_sent_per_file=200)
    if rows is None:
        print('[INFO] 使用规则回退（词典匹配）')
        rows = run_with_dict(names, max_files=None, limit_sent_per_file=200)

    # 合并：模型结果 + 词典补充（若需要）
    if names and rows:
        # 用词典补充未覆盖的人名（从已处理句子中再次匹配）
        covered_entities = {r['entity'] for r in rows}
        add_rows = []
        if len(covered_entities) < len(names):
            # 简单补充到明细中（不带上下文），可选
            for nm in (names - covered_entities):
                add_rows.append({'file':'', 'sent_index':'', 'entity': nm, 'type':'PER', 'score':''})
        rows.extend(add_rows)

    save_outputs(rows or [])


if __name__ == '__main__':
    main()
