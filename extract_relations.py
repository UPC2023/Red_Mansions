import os
import csv
import pickle
import argparse
from typing import List, Tuple, Optional
from train_crf_model import predict_with_crf


print('加载 NER 模型...')
with open('crf_ner_model.pkl', 'rb') as f:
    ner_model = pickle.load(f)
print('NER 模型加载完成')

print('加载关系分类模型...')
with open('relation_classifier.pkl', 'rb') as f:
    rel_model = pickle.load(f)
print('关系分类模型加载完成')


# 高精度关键词规则（优先）
RULE_KEYWORDS = {
    '父亲': '父亲', '母亲': '母亲', '儿子': '儿子', '女儿': '女儿',
    '爷爷': '爷爷', '奶奶': '奶奶', '祖母': '奶奶', '孙子': '孙子',
    '哥哥': '哥哥', '弟弟': '弟弟', '姐姐': '姐姐', '妹妹': '妹妹', '兄弟': '兄弟', '姐妹': '姐妹',
    '妻': '妻', '丈夫': '丈夫', '夫妻': '夫妻', '妾': '妾', '二房': '二房', '嫂子': '嫂子',
    '丫环': '丫环', '丫鬟': '丫环', '丫头': '丫头', '小厮': '小厮', '乳母': '乳母',
    # 朋友/交往类同义词
    '朋友': '朋友', '好友': '朋友', '好兄弟': '兄弟', '相好': '相好',
    '交接': '朋友', '相识': '朋友', '相交': '朋友', '结交': '朋友', '故交': '朋友', '旧交': '朋友',
    '相知': '朋友', '相与': '朋友', '会友': '朋友', '相逢': '朋友', '相会': '朋友',
    # 师生类补充
    '老师': '老师', '西席': '老师', '弟子': '学生', '学生': '学生',
    # 其他亲属/外亲
    '伯父': '伯父', '姑母': '姑母', '姑妈': '姑母', '侄女': '侄女', '侄儿': '侄儿',
    '外祖母': '外祖母', '外孙女': '外孙女'
}


def _load_name_dict() -> List[str]:
    """加载人物词典，按长度降序返回，用于最长匹配纠正（例如 贾雨 -> 贾雨村）。"""
    candidates: List[str] = []
    root = os.path.dirname(__file__) or '.'
    path_csv = os.path.join(root, 'name_dict_enhanced.csv')
    path_txt = os.path.join(root, 'name_dict.txt')
    try:
        if os.path.exists(path_csv):
            with open(path_csv, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    n = (row.get('name') or '').strip()
                    if n:
                        candidates.append(n)
        elif os.path.exists(path_txt):
            with open(path_txt, 'r', encoding='utf-8') as f:
                for line in f:
                    n = line.strip()
                    if n:
                        candidates.append(n)
    except Exception:
        # 词典缺失不致命，直接返回空列表
        candidates = []
    # 去重并按长度降序，优先匹配更长的标准名
    seen = set()
    uniq = []
    for n in candidates:
        if n not in seen:
            seen.add(n)
            uniq.append(n)
    uniq.sort(key=lambda s: len(s), reverse=True)
    return uniq


_NAME_DICT = _load_name_dict()


def _normalize_entities(text: str, entities: List[str]) -> List[str]:
    """将 CRF 抽取的人名纠正为出现在文本中的词典“最长匹配”。

    规则：
    - 若实体本身在词典且出现在文本中，保留原样。
    - 否则，在词典中寻找“包含该实体且出现在文本中”的候选，取长度最长者作为替换。
    - 若无候选，保留原样。
    - 保持顺序去重。
    """
    if not entities or not _NAME_DICT:
        # 无词典或无实体，原样返回
        seen = set()
        ordered = []
        for e in entities:
            if e not in seen:
                seen.add(e)
                ordered.append(e)
        return ordered

    normed: List[str] = []
    for e in entities:
        cand = e
        if e in _NAME_DICT and e in text:
            cand = e
        else:
            # 在词典中找“包含 e 的名字”。不强制要求全文出现全名，
            # 以便将“士隐/雨村”等截断规范到“甄士隐/贾雨村”。
            best = None
            best_len = -1
            for name in _NAME_DICT:
                if e and (e in name):
                    if len(name) > best_len:
                        best = name
                        best_len = len(name)
            cand = best or e
        normed.append(cand)

    # 去重保持顺序
    seen = set()
    ordered = []
    for e in normed:
        if e not in seen:
            seen.add(e)
            ordered.append(e)
    return ordered


def rule_predict(sentence: str, ent1: str, ent2: str) -> Optional[str]:
    """基于关键词的高精度规则：
    - 仅在“同时包含两实体的同一句子片段”内生效，避免跨句误判。
    - 先在两实体之间的文本片段查找关键词；若未命中，再在该句子片段内查找。
    """
    try:
        i1 = sentence.index(ent1)
        i2 = sentence.index(ent2)
    except ValueError:
        return None

    lo, hi = (i1, i2) if i1 < i2 else (i2, i1)

    # 定位同句片段边界
    PUNCS = '。！？!?;；\n'
    # 若两实体之间存在句读符号，视为不在同一句，避免跨句误判
    between_raw = sentence[lo:hi]
    if any(p in between_raw for p in PUNCS):
        return None
    start = lo
    while start > 0 and sentence[start - 1] not in PUNCS:
        start -= 1
    end = hi
    n = len(sentence)
    while end < n and sentence[end] not in PUNCS:
        end += 1
    segment = sentence[start:end]

    # 确保两实体都在该片段内（通常恒为真，但防御性判断）
    if ent1 not in segment or ent2 not in segment:
        return None

    # 先查“实体之间”的片段
    between = between_raw
    for kw, rel in RULE_KEYWORDS.items():
        if kw in between:
            return rel

    # 再查该“句子片段”整体（避免跨句污染）
    for kw, rel in RULE_KEYWORDS.items():
        if kw in segment:
            return rel
    return None


def extract_relations(text: str, proba_threshold: float = 0.6, debug: bool = False) -> List[Tuple[str, str, str]]:
    # 1) NER
    entities = predict_with_crf(ner_model, text)
    # 1.1) 词典最长匹配纠正（修复 贾雨 -> 贾雨村 等截断问题）
    entities = _normalize_entities(text, entities)
    results: List[Tuple[str, str, str]] = []
    if len(entities) < 2:
        return results
    print('实体（规范化后）：', entities)
    # 2) 枚举实体对
    classes = rel_model.named_steps['clf'].classes_
    for i, ent1 in enumerate(entities):
        for j, ent2 in enumerate(entities):
            if i >= j:
                continue
            # 跳过跨句的实体对（两实体之间若有句读符，则不判定关系）
            try:
                p1 = text.index(ent1)
                p2 = text.index(ent2)
                lo, hi = (p1, p2) if p1 < p2 else (p2, p1)
                if any(ch in text[lo:hi] for ch in '。！？!?;；\n'):
                    continue
            except ValueError:
                # 任一实体未在文本中找到，保守跳过
                continue
            # 规则优先
            rel_by_rule = rule_predict(text, ent1, ent2)
            if rel_by_rule:
                if debug:
                    print(f'[RULE] {ent1}-{ent2} -> {rel_by_rule}')
                results.append((ent1, ent2, rel_by_rule))
                continue
            sentence_marked = text.replace(ent1, '[E1]').replace(ent2, '[E2]')
            # 概率阈值过滤
            try:
                probas = rel_model.predict_proba([sentence_marked])[0]
                idx = int(probas.argmax())
                pred = classes[idx]
                if debug:
                    print(f'[ML] {ent1}-{ent2} -> {pred} ({float(probas[idx]):.3f})')
                if pred != '无关系' and float(probas[idx]) >= proba_threshold:
                    results.append((ent1, ent2, pred))
            except Exception:
                pred = rel_model.predict([sentence_marked])[0]
                if debug:
                    print(f'[ML:NO_PROBA] {ent1}-{ent2} -> {pred}')
                if pred != '无关系':
                    results.append((ent1, ent2, pred))
    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--text', type=str, default='贾政是贾宝玉的父亲。王熙凤是贾琏的妻。')
    parser.add_argument('--threshold', type=float, default=0.6)
    parser.add_argument('--debug', action='store_true')
    args = parser.parse_args()

    print('开始抽取实体和关系...')
    triples = extract_relations(args.text, proba_threshold=args.threshold, debug=args.debug)
    print('抽取三元组:')
    for t in triples:
        print(t)
