import pickle
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.multiclass import OneVsRestClassifier
from sklearn.pipeline import Pipeline


# 读取训练数据
X_train, y_train = [], []
with open('relation_train_samples_formatted.txt', 'r', encoding='utf-8') as f:
    for line in f:
        parts = line.strip().split('\t')
        if len(parts) == 4:
            sentence, ent1, ent2, relation = parts
            sentence_marked = sentence.replace(ent1, '[E1]').replace(ent2, '[E2]')
            X_train.append(sentence_marked)
            y_train.append(relation)

# 建立管道
model = Pipeline([
    ('tfidf', TfidfVectorizer()),
    ('clf', OneVsRestClassifier(LogisticRegression(max_iter=200)))
])

print(f'训练样本数: {len(X_train)}')
if len(X_train) == 0:
    print('训练数据为空，请检查 relation_train_samples_formatted.txt 文件！')
else:
    model.fit(X_train, y_train)
    with open('relation_classifier.pkl', 'wb') as f:
        pickle.dump(model, f)
    print("模型已保存到 relation_classifier.pkl")
