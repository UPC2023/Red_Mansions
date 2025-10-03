import os
import csv
import pickle
from collections import defaultdict
from typing import List, Tuple, Dict, Set
from train_crf_model import predict_with_crf

ROOT = os.path.dirname(os.path.dirname(__file__))
POS_FILE = os.path.join(ROOT, 'relation_train_samples_formatted.txt')
NER_MODEL_FILE = os.path.join(ROOT, 'crf_ner_model.pkl')
DATASET_TSV = os.path.join(ROOT, 'relation_train_dataset.tsv')
MODEL_FILE = os.path.join(ROOT, 'relation_classifier.pkl')

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.multiclass import OneVsRestClassifier
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from collections import Counter

# 1) 收集正样本，按句聚合
sent2positives: Dict[str, Set[Tuple[str,str,str]]] = defaultdict(set)
with open(POS_FILE, 'r', encoding='utf-8') as f:
    for line in f:
        parts = line.rstrip('\n').split('\t')
        if len(parts) != 4:
            continue
        sent, e1, e2, rel = parts
        sent2positives[sent].add((e1, e2, rel))

# 2) 加载 NER 模型，挖掘同句中的负样本（无关系）
with open(NER_MODEL_FILE, 'rb') as f:
    ner_model = pickle.load(f)

rows: List[Tuple[str,str,str,str]] = []  # sentence, e1, e2, label
for sent, pos_set in sent2positives.items():
    # 正样本
    for (e1, e2, rel) in pos_set:
        rows.append((sent, e1, e2, rel))
    # 负样本：同句实体对但不在正样本中的，采样最多与正样本等量
    ents = predict_with_crf(ner_model, sent)
    pairs = set()
    for i in range(len(ents)):
        for j in range(i+1, len(ents)):
            pairs.add((ents[i], ents[j]))
    # 生成候选负样本
    negs = []
    pos_pairs = {(e1, e2) for (e1, e2, _) in pos_set}
    for (a, b) in pairs:
        if (a, b) not in pos_pairs and (b, a) not in pos_pairs:
            negs.append((a, b))
    # 采样
    max_neg = max(1, len(pos_set))
    for (a, b) in negs[:max_neg]:
        rows.append((sent, a, b, '无关系'))

# 3) 保存数据集（便于复现）并构造训练输入
marked_rows = []  # (marked_sentence, label)
with open(DATASET_TSV, 'w', encoding='utf-8') as fout:
    for sent, e1, e2, lab in rows:
        marked = sent.replace(e1, '[E1]').replace(e2, '[E2]')
        marked_rows.append((marked, lab))
        fout.write(f"{marked}\t{lab}\n")

# 4) 训练更稳健的分类器（字符TF-IDF，更适合中文）
X = [m for (m, _) in marked_rows]
y = [lab for (_, lab) in marked_rows]

label_counts = Counter(y)
print('标签分布（前10个）：', list(label_counts.items())[:10])
min_count = min(label_counts.values()) if label_counts else 0
stratify_labels = y if (min_count >= 2 and len(label_counts) > 1) else None
if stratify_labels is None:
    print('警告：存在仅出现1次的类别或仅单一类别，train_test_split 将不进行分层抽样。')

X_train, X_val, y_train, y_val = train_test_split(
    X, y, test_size=0.15, random_state=42, stratify=stratify_labels
)

model = Pipeline([
    ('tfidf', TfidfVectorizer(analyzer='char', ngram_range=(2, 4), min_df=2, sublinear_tf=True)),
    ('clf', OneVsRestClassifier(LogisticRegression(max_iter=500, class_weight='balanced', n_jobs=None)))
])

print(f"样本总数: {len(rows)} | 训练: {len(X_train)} | 验证: {len(X_val)}")
model.fit(X_train, y_train)

# 验证报告
try:
    if len(set(y_val)) > 1:
        y_pred = model.predict(X_val)
        print(classification_report(y_val, y_pred))
    else:
        print('验证集仅包含单一类别，跳过分类报告。')
except Exception as e:
    print('验证失败: ', e)

with open(MODEL_FILE, 'wb') as f:
    pickle.dump(model, f)
print('已训练并保存改进版关系分类模型 ->', MODEL_FILE)
