import os
import argparse
from extract_relations import extract_relations

def main(threshold: float, debug: bool):
    output = open('all_relations.csv', 'w', encoding='utf-8')
    output.write('chapter,sentence,entity1,entity2,relation\n')

    chapters_dir = 'reddream_chapters'
    file_list = sorted([f for f in os.listdir(chapters_dir) if f.endswith('.txt')])
    total = len(file_list)
    total_lines = kept_lines = total_triples = 0

    for idx, fname in enumerate(file_list):
        chapter_path = os.path.join(chapters_dir, fname)
        with open(chapter_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                total_lines += 1
                line = line.strip()
                if not line or len(line) < 5:
                    continue
                triples = extract_relations(line, proba_threshold=threshold, debug=False)
                if triples:
                    kept_lines += 1
                for ent1, ent2, rel in triples:
                    total_triples += 1
                    output.write(f'{fname},{line},{ent1},{ent2},{rel}\n')
                if (i+1) % 100 == 0:
                    print(f'{fname}: 已处理 {i+1} 行...')
        print(f'完成章节 {fname} ({idx+1}/{total})')

    output.close()
    print('全书三元组抽取完成，结果保存在 all_relations.csv')
    print(f'统计：总行数={total_lines}，有三元组的行数={kept_lines}，总三元组数={total_triples}，通过率={(kept_lines/max(1,total_lines)):.2%}')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--threshold', type=float, default=0.6)
    parser.add_argument('--debug', action='store_true')
    args = parser.parse_args()
    main(args.threshold, args.debug)
