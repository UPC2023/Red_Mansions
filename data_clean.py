# data_clean.py
import os
from bs4 import BeautifulSoup

def clean_reddream_chapter(input_path, output_path):
    """清洗单个章节的 TXT 文件，去除 HTML 标签，只保留纯文本"""
    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 使用 BeautifulSoup 清除 HTML 标签，保留换行
    soup = BeautifulSoup(content, 'html.parser')
    clean_text = soup.get_text(separator='\n')  # 用换行分隔

    # 逐行处理：
    # - 去掉行首的 '###' 前缀但保留其后的文字
    # - 将只由 '-' 组成的分隔线替换为单个空格
    # - 保留其他文本的内容
    processed_lines = []
    for line in clean_text.splitlines():
        raw = line
        line = line.rstrip()
        if line.lstrip().startswith('###'):
            # 移除开头的三个井号及可能的空格
            # 找到第一个非#后的内容
            stripped = line.lstrip()
            # remove only one group of leading ###
            if stripped.startswith('###'):
                new = stripped[3:]
                # 如果后面跟着空格，去掉一个空格
                if new.startswith(' '):
                    new = new[1:]
                processed_lines.append(new)
                continue
        # 如果这一行只由 '-' 和空白组成，则替换为单个空格
        if line.strip() and set(line.strip()) == {'-'}:
            processed_lines.append(' ')
            continue
        # 普通文本行，保留（去除首尾空白）
        if line.strip():
            processed_lines.append(line.strip())
        else:
            # 记录空行为 ''，稍后合并连续空行为单个空行
            processed_lines.append('')

    # 合并多余空行：相邻多个空行只保留一个
    cleaned = []
    prev_blank = False
    for ln in processed_lines:
        if ln == '':
            if not prev_blank:
                cleaned.append('')
            prev_blank = True
        else:
            cleaned.append(ln)
            prev_blank = False

    clean_text = '\n'.join(cleaned)

    # 保存清洗后的内容
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(clean_text)

    print(f"已清洗并保存：{output_path}")


def clean_all_chapters(input_dir="reddream_chapters", output_dir="reddream_chapters_clean"):
    """批量清洗所有章节"""
    os.makedirs(output_dir, exist_ok=True)

    for filename in os.listdir(input_dir):
        if filename.endswith(".txt"):
            input_path = os.path.join(input_dir, filename)
            output_path = os.path.join(output_dir, filename)
            clean_reddream_chapter(input_path, output_path)

    print("所有章节清洗完成！")

if __name__ == '__main__':
    clean_all_chapters()