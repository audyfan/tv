import os
import time
from datetime import datetime

# 配置文件路径
BASE_DIR = "./live_results"  # 存放检测结果的文件夹
MERGED_OUTPUT_FILE = "./live_white_list.txt"  # 白名单文件
BLACKLIST_FILE = "./live_black_list.txt"  # 黑名单文件
SOURCE_FILE = "./merged_output.txt"  # 根目录的直播源文件

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
                current_category = line[:-8].strip()  # 移除末尾的 "#genre#"
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

def check_live_source(source_url):
    """
    检测单个直播源是否存活，模拟逻辑。
    """
    print(f"检测直播源：{source_url}")
    time.sleep(0.1)  # 模拟检测延迟
    if hash(source_url) % 7 == 0:  # 模拟随机失效
        return False
    return hash(source_url) % 2 == 0

def save_results(category, results):
    """
    保存检测结果到日志文件、白名单文件和黑名单文件。
    """
    date_str = datetime.now().strftime("%Y-%m-%d")
    category_file = os.path.join(BASE_DIR, f"{date_str}_{category}.txt")

    with open(category_file, "w", encoding="utf-8") as f:
        for source_name, status in results.items():
            f.write(f"{source_name} -> {'存活' if status else '失效'}\n")
    print(f"分类 {category} 检测结果已保存到 {category_file}。")

    alive_sources = [source_name for source_name, status in results.items() if status]
    dead_sources = [source_name for source_name, status in results.items() if not status]

    # 保存白名单
    with open(MERGED_OUTPUT_FILE, "a", encoding="utf-8") as f:
        for source in alive_sources:
            f.write(source + "\n")
    print(f"存活直播源已追加到 {MERGED_OUTPUT_FILE}。")

    # 保存黑名单
    with open(BLACKLIST_FILE, "a", encoding="utf-8") as f:
        for source in dead_sources:
            f.write(source + "\n")
    print(f"失效直播源已追加到 {BLACKLIST_FILE}。")

def check_category(category, sources):
    """
    检测指定分类内的所有直播源。
    """
    results = {}
    for source_name, source_url in sources:
        try:
            is_alive = check_live_source(source_url)
            results[source_name] = is_alive
        except Exception as e:
            print(f"检测失败：{source_name} -> {e}")
            results[source_name] = False
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
