# convert_relation_samples.py
# 将 relation_train_samples.txt 转换为每行一个三元组的标准格式

input_file = 'relation_train_samples.txt'
output_file = 'relation_train_samples_formatted.txt'

with open(input_file, 'r', encoding='utf-8') as fin, open(output_file, 'w', encoding='utf-8') as fout:
    for line in fin:
        line = line.strip()
        if not line:
            continue
        if '\t' not in line:
            continue
        sentence, triples = line.split('\t', 1)
        for triple in triples.split(';'):
            triple = triple.strip()
            if not triple:
                continue
            parts = triple.split(',')
            if len(parts) == 3:
                ent1, ent2, relation = parts
                fout.write(f"{sentence}\t{ent1}\t{ent2}\t{relation}\n")

print(f"转换完成，已保存为 {output_file}")
