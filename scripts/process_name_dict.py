
import csv
import os

ROOT = os.path.dirname(os.path.dirname(__file__))
DICT_TXT = os.path.join(ROOT, 'name_dict.txt')
ENHANCED_CSV = os.path.join(ROOT, 'name_dict_enhanced.csv')
CLEAN_TXT = os.path.join(ROOT, 'name_dict_clean.txt')


def enhance_name_dict():
    if not os.path.exists(DICT_TXT):
        raise FileNotFoundError(DICT_TXT)
    with open(DICT_TXT, 'r', encoding='utf-8') as f:
        names = [ln.strip() for ln in f if ln.strip()]

    # 写出增强 CSV（无需 pandas）
    with open(ENHANCED_CSV, 'w', encoding='utf-8', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['name', 'length', 'first_char', 'source'])
        for n in names:
            writer.writerow([n, len(n), n[0] if n else '', 'name_dict.txt'])

    # 也整理一个按长度、字典序排序的 clean 版本
    with open(CLEAN_TXT, 'w', encoding='utf-8') as f:
        for n in sorted(names, key=lambda x: (len(x), x)):
            f.write(n + '\n')

    print(f'已处理 {len(names)} 个名称')
    print('生成文件:')
    print(' -', ENHANCED_CSV)
    print(' -', CLEAN_TXT)


if __name__ == '__main__':
    enhance_name_dict()
