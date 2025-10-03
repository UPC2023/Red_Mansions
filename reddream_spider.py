# reddream_spider.py
import requests
import time
import os
import urllib3

# 禁用 SSL 警告（因为使用了 verify=False）
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def crawl_reddream_chapters(start=1, end=5):
    """爬取红楼梦指定回目"""
    # 创建保存目录
    output_dir = "reddream_chapters"
    os.makedirs(output_dir, exist_ok=True)

    # raw 链接格式
    base_url = "https://raw.githubusercontent.com/EaconTang/gitbook-hongloumeng/refs/heads/master/ch_cgb/{:03d}.md"

    print(f"开始爬取《红楼梦》第{start}到{end}回内容...")

    # 循环爬取指定回目
    for i in range(start, end + 1):
        url = base_url.format(i)
        print(f"正在爬取第 {i} 回: {url}")

        try:
            # 发送请求（忽略 SSL 验证）
            response = requests.get(url, verify=False)
            response.raise_for_status()  # 抛出异常如果请求失败

            # 直接使用 response.text 即可，因为 raw.githubusercontent.com 返回的是纯文本（Markdown）
            raw_text = response.text

            # 保存为 txt 文件
            filename = os.path.join(output_dir, f"{i:03d}.txt")
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(raw_text)

            print(f"第 {i} 回已保存为 {filename}")
            time.sleep(2)

        except requests.exceptions.HTTPError as http_err:
            print(f"第 {i} 回 HTTP 错误: {http_err}")
            continue
        except requests.exceptions.ConnectionError as conn_err:
            print(f"第 {i} 回 连接错误: {conn_err}")
            continue
        except requests.exceptions.Timeout as timeout_err:
            print(f"第 {i} 回 请求超时: {timeout_err}")
            continue
        except requests.exceptions.RequestException as req_err:
            print(f"第 {i} 回 其他请求异常: {req_err}")
            continue
        except Exception as e:
            print(f"第 {i} 回 发生未知错误: {e}")
            continue

    print("所有章节爬取完成！")

# 执行爬虫
if __name__ == '__main__':
    crawl_reddream_chapters(6, 120)