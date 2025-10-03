def extract_entities(relation_file, output_file):
    """
    从关系文件中提取所有不重复的人物实体
    :param relation_file: 输入关系文件路径
    :param output_file: 输出实体列表文件路径
    """
    entities = set()
    with open(relation_file, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split(',')
            if len(parts) >= 2:
                # 提取每行的前两个字段作为实体
                entities.add(parts[0].strip())
                entities.add(parts[1].strip())
    
    # 按字母顺序排序并写入文件
    with open(output_file, 'w', encoding='utf-8') as f_out:
        for entity in sorted(entities):
            f_out.write(entity + '\n')
    
    print(f"从 {relation_file} 中提取了 {len(entities)} 个不重复的实体，保存到 {output_file}")

# 执行提取
if __name__ == '__main__':
    extract_entities('relation.txt', 'entity_list.txt')