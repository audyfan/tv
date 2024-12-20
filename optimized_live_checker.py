import os
import time
from datetime import datetime
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

# 配置文件路径
BASE_DIR = "./live_results"  # 存放检测结果的文件夹
MERGED_OUTPUT_FILE = "./live_white_list.txt"  # 白名单文件
BLACKLIST_FILE = "./live_black_list.txt"  # 黑名单文件
SOURCE_FILE = "./merged_output.txt"  # 根目录的直播源文件
THREAD_POOL_SIZE = 10  # 线程池大小
DETECTION_ROUNDS = 3  # 每个直播源检测次数
DETECTION_TIMEOUT = 5  # 每次检测的超时时间（秒）

def create_folders_and_files():
    """
    自动创建必要的文件夹和文件。
    """
    os.makedirs(BASE_DIR, exist_ok=True)
    for file in [MERGED_OUTPUT_FILE, BLACKLIST_FILE, SOURCE_FILE]:
        if not os.path.exists(file):
            with open(file, "w", encoding="utf-8") as f:
                pass
    print("文件夹和文件已创建或确认存在。")

def parse_sources(file_path):
    """
    按分类解析直播源文件，支持新的格式：
    格式示例：
    🅰世界光影汇,#genre#
    📹直播中国,https://example.com/live1.m3u8
    """
    categories = {}
    current_category = None

    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()  # 去掉多余的空格或换行
            if not line:
                continue  # 跳过空行
            if line.endswith("#genre#"):  # 判断是否是分类标题
                current_category = line.strip()  # 直接保留分类标题完整内容
                categories[current_category] = []
                print(f"发现分类: {current_category}")
            elif current_category:
                # 解析直播源名称和 URL
                parts = line.split(",", 1)
                if len(parts) == 2:  # 确保有名称和 URL 两部分
                    source_name, source_url = parts[0].strip(), parts[1].strip()
                    if source_url:  # 跳过空的 URL
                        categories[current_category].append((source_name, source_url))
                        print(f"添加直播源到分类 {current_category}: {source_name} -> {source_url}")
    return categories

def check_single_source(source_url):
    """
    检测单个直播源是否存活，发送 HTTP 请求检测。
    """
    try:
        response = requests.get(source_url, timeout=DETECTION_TIMEOUT)
        if response.status_code == 200:
            print(f"检测成功: {source_url} -> 存活")
            return True
        else:
            print(f"检测失败: {source_url} -> 状态码 {response.status_code}")
            return False
    except requests.RequestException as e:
        print(f"检测失败: {source_url} -> 异常 {e}")
        return False

def check_live_source(source_url):
    """
    对单个直播源多次检测，提高准确性。
    """
    results = []
    for i in range(DETECTION_ROUNDS):
        result = check_single_source(source_url)
        results.append(result)
        time.sleep(0.2)  # 增加短暂延迟
    # 统计结果：至少 2 次存活判定为存活
    return results.count(True) >= 2

def save_results(category, results):
    """
    保存检测结果到白名单文件和黑名单文件。
    输出格式：
    🅰世界光影汇,#genre#
    📹直播中国,https://example.com/live1.m3u8
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 保存白名单
    with open(MERGED_OUTPUT_FILE, "a", encoding="utf-8") as f:
        f.write(f"{category} (检测时间: {timestamp})\n")
        for source_name, (source_url, status) in results.items():
            if status:  # 存活
                f.write(f"{source_name},{source_url}\n")
    print(f"存活直播源已追加到 {MERGED_OUTPUT_FILE}。")

    # 保存黑名单
    with open(BLACKLIST_FILE, "a", encoding="utf-8") as f:
        f.write(f"{category} (检测时间: {timestamp})\n")
        for source_name, (source_url, status) in results.items():
            if not status:  # 失效
                f.write(f"{source_name},{source_url}\n")
    print(f"失效直播源已追加到 {BLACKLIST_FILE}。")

def check_category(category, sources):
    """
    检测指定分类内的所有直播源，使用多线程加速。
    """
    results = {}
    with ThreadPoolExecutor(max_workers=THREAD_POOL_SIZE) as executor:
        future_to_source = {
            executor.submit(check_live_source, source_url): (source_name, source_url)
            for source_name, source_url in sources
        }
        for future in as_completed(future_to_source):
            source_name, source_url = future_to_source[future]
            try:
                is_alive = future.result()
                results[source_name] = (source_url, is_alive)
            except Exception as e:
                print(f"检测失败：{source_name} -> {e}")
                results[source_name] = (source_url, False)
    save_results(category, results)

def main():
    """
    主程序逻辑，每天检测一个分类。
    """
    create_folders_and_files()
    categories = parse_sources(SOURCE_FILE)
    category_list = list(categories.keys())
    if not category_list:
        print("没有分类可检测。")
        return

    # 每天检测一个分类
    today_index = datetime.now().timetuple().tm_yday % len(category_list)
    today_category = category_list[today_index]
    print(f"今天检测分类：{today_category}")
    check_category(today_category, categories[today_category])

if __name__ == "__main__":
    main()
