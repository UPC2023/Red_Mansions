import re

# 加载全文（假设用清洗后的合并文本）
with open('reddream_chapters_clean/001.txt', 'r', encoding='utf-8') as f:
    full_text = f.read()
for i in range(2, 121):
    fname = f'reddream_chapters_clean/{i:03d}.txt'
    try:
        with open(fname, 'r', encoding='utf-8') as f:
            full_text += f.read()
    except FileNotFoundError:
        continue

# 加载已知关系
known_relations = []
with open('relation.txt', 'r', encoding='utf-8') as f:
    for line in f:
        parts = line.strip().split(',')
        if len(parts) >= 3:
            known_relations.append((parts[0], parts[1], parts[2]))

# 在全文中有已知关系的句子
training_sentences = []
relation_labels = []

for sentence in re.split(r'[。！？!?]', full_text):
    sentence = sentence.strip()
    if len(sentence) < 10:
        continue
    found_relations = []
    for head, tail, relation in known_relations:
        if head in sentence and tail in sentence:
            found_relations.append((head, tail, relation))
    if found_relations:
        training_sentences.append(sentence)
        relation_labels.append(found_relations)

print(f"生成了 {len(training_sentences)} 个关系抽取训练样本")
# 可选：保存训练样本
with open('relation_train_samples.txt', 'w', encoding='utf-8') as f:
    for sent, rels in zip(training_sentences, relation_labels):
        rel_str = ';'.join([f"{h},{t},{r}" for h,t,r in rels])
        f.write(f"{sent}\t{rel_str}\n")
