# 统计 relation.txt 中所有关系类型
relation_types = set()
with open('c:/red dream/red_dream/relation.txt', 'r', encoding='utf-8') as f:
    for line in f:
        parts = line.strip().split(',')
        if len(parts) >= 3:
            relation_types.add(parts[2])

print('《红楼梦》关系类型体系:')
for i, rel in enumerate(sorted(relation_types)):
    print(f'{i+1}. {rel}')

print(f'\n共提取出 {len(relation_types)} 种关系类型。')

# 保存标签映射
with open('c:/red dream/red_dream/relation_types.txt', 'w', encoding='utf-8') as f:
    for rel in sorted(relation_types):
        f.write(rel + '\n')
