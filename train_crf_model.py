import os
import pickle
from typing import List, Tuple, Dict

import pycrfsuite


BIO_FILE_TRAIN = os.path.join(os.path.dirname(__file__), 'train.txt')
BIO_FILE_DEV = os.path.join(os.path.dirname(__file__), 'dev.txt')
BIO_FILE_TEST = os.path.join(os.path.dirname(__file__), 'test.txt')


def load_bio_data(file_path: str) -> List[List[Tuple[str, str]]]:
    """按句加载 BIO 格式数据：每行 `char\tlabel`，空行分句。"""
    sentences: List[List[Tuple[str, str]]] = []
    current: List[Tuple[str, str]] = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for raw in f:
            line = raw.rstrip('\n')
            if not line:
                if current:
                    sentences.append(current)
                    current = []
                continue
            parts = line.split('\t')
            if len(parts) == 2:
                ch, lab = parts
                current.append((ch, lab))
        if current:
            sentences.append(current)
    return sentences


def extract_features(sentence: List[Tuple[str, str]], i: int) -> Dict[str, object]:
    ch, _ = sentence[i]
    feats = {
        'bias': 1.0,
        'ch': ch,
        'is_digit': ch.isdigit(),
        'is_alpha': ch.isalpha(),
        'is_space': ch.isspace(),
        'len': 1,
    }
    if i == 0:
        feats['BOS'] = True
    else:
        pch, _ = sentence[i-1]
        feats.update({
            '-1:ch': pch,
            '-1:is_digit': pch.isdigit(),
        })
    if i == len(sentence) - 1:
        feats['EOS'] = True
    else:
        nch, _ = sentence[i+1]
        feats.update({
            '+1:ch': nch,
            '+1:is_digit': nch.isdigit(),
        })
    return feats


def prepare_crf_data(sents: List[List[Tuple[str, str]]]):
    X, y = [], []
    for sent in sents:
        X.append([extract_features(sent, i) for i in range(len(sent))])
        y.append([lab for _, lab in sent])
    return X, y


def train_and_evaluate():
    print('加载训练数据...')
    train_sents = load_bio_data(BIO_FILE_TRAIN)
    dev_sents = load_bio_data(BIO_FILE_DEV)
    test_sents = load_bio_data(BIO_FILE_TEST)

    print(f'训练集: {len(train_sents)} 句, 验证集: {len(dev_sents)} 句, 测试集: {len(test_sents)} 句')

    print('准备特征...')
    X_train, y_train = prepare_crf_data(train_sents)
    X_dev, y_dev = prepare_crf_data(dev_sents)
    X_test, y_test = prepare_crf_data(test_sents)

    print('训练 CRF (python-crfsuite)...')
    trainer = pycrfsuite.Trainer(verbose=False)
    for xseq, yseq in zip(X_train, y_train):
        trainer.append(xseq, yseq)
    # 可选使用 dev 作为 early stopping 参考，这里仅保存为单模型
    trainer.set_params({
        'c1': 0.1,              # L1 正则
        'c2': 0.1,              # L2 正则
        'max_iterations': 100,
        'feature.possible_transitions': True,
    })
    model_path = os.path.join(os.path.dirname(__file__), 'crf_ner_model.crfsuite')
    trainer.train(model_path)

    tagger = pycrfsuite.Tagger()
    tagger.open(model_path)

    # 评估（token 级别的简易报告）
    def simple_report(y_true, y_pred, labels=(
        'B-PER', 'I-PER', 'O'
    )) -> str:
        from collections import defaultdict
        tp = defaultdict(int); fp = defaultdict(int); fn = defaultdict(int); support = defaultdict(int)
        for yt_sent, yp_sent in zip(y_true, y_pred):
            for yt, yp in zip(yt_sent, yp_sent):
                support[yt] += 1
                if yp == yt:
                    tp[yt] += 1
                else:
                    fp[yp] += 1
                    fn[yt] += 1
        lines = []
        micro_tp = micro_fp = micro_fn = 0
        for lab in labels:
            p = tp[lab] / (tp[lab] + fp[lab]) if (tp[lab] + fp[lab]) else 0.0
            r = tp[lab] / (tp[lab] + fn[lab]) if (tp[lab] + fn[lab]) else 0.0
            f1 = (2*p*r)/(p+r) if (p+r) else 0.0
            lines.append(f"{lab:>6}  P={p:.4f}  R={r:.4f}  F1={f1:.4f}  support={support[lab]}")
            micro_tp += tp[lab]; micro_fp += fp[lab]; micro_fn += fn[lab]
        p = micro_tp / (micro_tp + micro_fp) if (micro_tp + micro_fp) else 0.0
        r = micro_tp / (micro_tp + micro_fn) if (micro_tp + micro_fn) else 0.0
        f1 = (2*p*r)/(p+r) if (p+r) else 0.0
        lines.append('-'*48)
        lines.append(f"micro avg  P={p:.4f}  R={r:.4f}  F1={f1:.4f}")
        return '\n'.join(lines)

    y_pred = []
    for xseq in X_test:
        y_pred.append(tagger.tag(xseq))
    report = simple_report(y_test, y_pred)
    print(report)

    # 另存一个方便加载的 pickle（包含标签集合和模型路径）
    save_obj = {
        'model_path': model_path,
        'labels': sorted({lab for sent in y_train for lab in sent} | {lab for sent in y_dev for lab in sent}),
    }
    with open(os.path.join(os.path.dirname(__file__), 'crf_ner_model.pkl'), 'wb') as f:
        pickle.dump(save_obj, f)
    with open(os.path.join(os.path.dirname(__file__), 'model_evaluation_report.txt'), 'w', encoding='utf-8') as f:
        f.write('CRF 模型评估报告 (python-crfsuite)\n')
        f.write('='*50 + '\n')
        f.write(report)

    print("模型与报告已保存。")


def predict_with_crf(model_obj, text: str):
    # 简单按句切分
    sentences: List[List[Tuple[str, str]]] = []
    cur: List[Tuple[str, str]] = []
    for ch in text:
        if ch in '。！？?!':
            if cur:
                sentences.append(cur)
                cur = []
        else:
            cur.append((ch, 'O'))
    if cur:
        sentences.append(cur)

    X, _ = prepare_crf_data(sentences)
    # 载入 tagger
    tagger = pycrfsuite.Tagger()
    if isinstance(model_obj, pycrfsuite.Tagger):
        tagger = model_obj
    else:
        # model_obj 可能是我们保存的字典
        model_path = None
        if isinstance(model_obj, dict):
            model_path = model_obj.get('model_path')
        if not model_path:
            model_path = os.path.join(os.path.dirname(__file__), 'crf_ner_model.crfsuite')
        tagger.open(model_path)
    preds = [tagger.tag(xseq) for xseq in X]

    entities = []
    for sent, tags in zip(sentences, preds):
        cur_ent = ''
        for (ch, _), tag in zip(sent, tags):
            if tag == 'B-PER':
                if cur_ent:
                    entities.append(cur_ent)
                cur_ent = ch
            elif tag == 'I-PER' and cur_ent:
                cur_ent += ch
            else:
                if cur_ent:
                    entities.append(cur_ent)
                    cur_ent = ''
        if cur_ent:
            entities.append(cur_ent)
    # 去重保持顺序
    seen = set()
    ordered = []
    for e in entities:
        if e not in seen:
            seen.add(e)
            ordered.append(e)
    return ordered


if __name__ == '__main__':
    train_and_evaluate()
    try:
        with open(os.path.join(os.path.dirname(__file__), 'crf_ner_model.pkl'), 'rb') as f:
            saved = pickle.load(f)
        sample = '贾宝玉和林黛玉在园中说话，王夫人与薛宝钗在一旁谈笑。'
        print('示例预测:', predict_with_crf(saved, sample))
    except Exception as e:
        print('示例预测失败:', e)
