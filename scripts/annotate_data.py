# -*- coding: utf-8 -*-
"""
实体抽取数据标注脚本（BIO，字符级）：
- 优先使用项目根目录下的 name_dict.txt 作为实体列表；若不存在则回退到 entity_list.txt。
- 自动合并 reddream_chapters_clean/*.txt 生成全文（无须 hongloumeng.txt）。
- 生成 annotated_data.txt、train.txt、dev.txt、test.txt。
"""
import re
import random
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME_DICT = ROOT / 'name_dict.txt'
ENTITY_LIST = ROOT / 'entity_list.txt'
CLEAN_DIR = ROOT / 'reddream_chapters_clean'
OUT_ALL = ROOT / 'annotated_data.txt'
OUT_TRAIN = ROOT / 'train.txt'
OUT_DEV = ROOT / 'dev.txt'
OUT_TEST = ROOT / 'test.txt'


def load_entity_list():
    """优先加载 name_dict.txt；否则加载 entity_list.txt。每行一个实体名。"""
    src = None
    if NAME_DICT.exists():
        src = NAME_DICT
    elif ENTITY_LIST.exists():
        src = ENTITY_LIST
    else:
        raise FileNotFoundError('未找到 name_dict.txt 或 entity_list.txt，请在项目根目录提供其中之一')

    entities = []
    with open(src, 'r', encoding='utf-8') as f:
        for line in f:
            # 支持 "name\tscore" 或 "name" 两种格式
            parts = line.strip().split('\t')
            name = parts[0].strip()
            if name:
                entities.append(name)
    print(f"已加载实体 {len(entities)} 个，来源：{src.name}")
    return entities


def load_full_text():
    """合并 reddream_chapters_clean 下所有 txt，作为全文。"""
    if not CLEAN_DIR.exists():
        raise FileNotFoundError('未找到 reddream_chapters_clean 目录')
    files = sorted(CLEAN_DIR.glob('*.txt'))
    if not files:
        raise FileNotFoundError('reddream_chapters_clean 下没有 txt 文件')
    parts = []
    for p in files:
        try:
            parts.append(p.read_text(encoding='utf-8'))
        except Exception:
            continue
    text = '\n'.join(parts)
    print(f"合并章节完成，共 {len(files)} 个文件，全文长度 {len(text)} 字")
    return text


def annotate_sentence(sentence, entity_list):
    """对单个句子进行 BIO 标注（字符级），长实体优先并避免重叠。"""
    sorted_entities = sorted(entity_list, key=len, reverse=True)
    tokens = list(sentence)
    labels = ['O'] * len(tokens)

    for entity in sorted_entities:
        if not entity:
            continue
        start_idx = sentence.find(entity)
        while start_idx != -1:
            end_idx = start_idx + len(entity)
            # 检查位置是否未被标注
            if all(labels[i] == 'O' for i in range(start_idx, end_idx)):
                labels[start_idx] = 'B-PER'
                for i in range(start_idx + 1, end_idx):
                    labels[i] = 'I-PER'
            start_idx = sentence.find(entity, start_idx + 1)

    return list(zip(tokens, labels))


def process_full_text(text, entity_list, output_file, sample_ratio=0.3):
    """对全文分句、采样并标注，输出 annotated_data.txt。"""
    # 分句（保留常见中文标点）
    sentences = re.split(r'[。！？!?]', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 5]

    print(f"原文共有 {len(sentences)} 个句子")
    if len(sentences) == 0:
        return []

    # 随机采样一部分句子（避免数据过大）
    k = max(1, int(len(sentences) * sample_ratio))
    sampled_sentences = random.sample(sentences, k)
    print(f"采样 {len(sampled_sentences)} 个句子进行标注")

    annotated_data = []
    entity_count = Counter()

    for i, sentence in enumerate(sampled_sentences):
        annotated = annotate_sentence(sentence, entity_list)
        # 只保留包含实体的句子
        if any(label != 'O' for _, label in annotated):
            annotated_data.append(annotated)
            # 统计实体出现次数（使用实体首字作近似计数）
            for token, label in annotated:
                if label.startswith('B-'):
                    entity_count[token] += 1
        if (i + 1) % 1000 == 0:
            print(f"已处理 {i+1} 个句子")

    print(f"标注完成，共得到 {len(annotated_data)} 个包含实体的句子")
    print("最常见实体首字:", entity_count.most_common(10))

    # 保存 annotated_data.txt
    with open(output_file, 'w', encoding='utf-8') as f:
        for sentence_data in annotated_data:
            for token, label in sentence_data:
                f.write(f"{token}\t{label}\n")
            f.write("\n")

    return annotated_data


def split_dataset(annotated_data, train_ratio=0.7, val_ratio=0.15, test_ratio=0.15):
    random.shuffle(annotated_data)
    total = len(annotated_data)
    train_end = int(total * train_ratio)
    val_end = train_end + int(total * val_ratio)
    return annotated_data[:train_end], annotated_data[train_end:val_end], annotated_data[val_end:]


def save_dataset(data, filename):
    with open(filename, 'w', encoding='utf-8') as f:
        for sentence_data in data:
            for token, label in sentence_data:
                f.write(f"{token}\t{label}\n")
            f.write("\n")


if __name__ == '__main__':
    random.seed(42)
    entities = load_entity_list()
    text = load_full_text()

    annotated_data = process_full_text(text, entities, OUT_ALL, sample_ratio=0.3)

    train_data, val_data, test_data = split_dataset(annotated_data)
    save_dataset(train_data, OUT_TRAIN)
    save_dataset(val_data, OUT_DEV)
    save_dataset(test_data, OUT_TEST)

    print('数据标注和划分完成！')
