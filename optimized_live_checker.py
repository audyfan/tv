import os
import asyncio
import aiohttp
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import subprocess
import sys

# 安装必要的依赖
def install_dependencies():
    try:
        import aiohttp  # 检查是否已安装
    except ImportError:
        print("正在安装依赖库 aiohttp ...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "aiohttp"])

# 配置文件路径
BASE_DIR = "./live_results"
MERGED_OUTPUT_FILE = "./live_white_list.txt"
BLACKLIST_FILE = "./live_black_list.txt"
SOURCE_FILE = "./merged_output.txt"

THREAD_POOL_SIZE = 20  # 并发线程数
DETECTION_TIMEOUT = 3  # 每次检测的超时时间（秒）
RETRY_COUNT = 2  # 每个直播源检测的重试次数


def create_folders_and_files():
    """自动创建必要的文件夹和文件。"""
    os.makedirs(BASE_DIR, exist_ok=True)
    for file in [MERGED_OUTPUT_FILE, BLACKLIST_FILE, SOURCE_FILE]:
        if not os.path.exists(file):
            with open(file, "w", encoding="utf-8") as f:
                pass
    print("文件夹和文件已创建或确认存在。")


def parse_sources(file_path):
    """按分类解析直播源文件。"""
    categories = {}
    current_category = None

    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.endswith("#genre#"):  # 分类标题
                current_category = line.strip()
                categories[current_category] = []
            elif current_category:
                parts = line.split(",", 1)
                if len(parts) == 2:
                    source_name, source_url = parts[0].strip(), parts[1].strip()
                    if source_url:
                        categories[current_category].append((source_name, source_url))
    return categories


async def check_live_source(session, source_url):
    """检测单个直播源是否存活（异步）。"""
    try:
        async with session.get(source_url, timeout=DETECTION_TIMEOUT) as response:
            if response.status == 200:
                return True
    except Exception:
        pass
    return False


async def check_source_with_retries(source_url):
    """对单个直播源进行多次检测。"""
    async with aiohttp.ClientSession() as session:
        for _ in range(RETRY_COUNT):
            if await check_live_source(session, source_url):
                return True
    return False


async def check_category(category, sources):
    """检测指定分类内的所有直播源，使用异步请求加速。"""
    results = {}
    tasks = {
        asyncio.create_task(check_source_with_retries(source_url)): (source_name, source_url)
        for source_name, source_url in sources
    }
    for task in asyncio.as_completed(tasks):
        source_name, source_url = tasks[task]
        try:
            is_alive = await task
            results[source_name] = (source_url, is_alive)
        except Exception as e:
            results[source_name] = (source_url, False)
    save_results(category, results)


def save_results(category, results):
    """保存检测结果到白名单文件和黑名单文件。"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(MERGED_OUTPUT_FILE, "a", encoding="utf-8") as f:
        f.write(f"{category} (检测时间: {timestamp})\n")
        for source_name, (source_url, status) in results.items():
            if status:
                f.write(f"{source_name},{source_url}\n")

    with open(BLACKLIST_FILE, "a", encoding="utf-8") as f:
        f.write(f"{category} (检测时间: {timestamp})\n")
        for source_name, (source_url, status) in results.items():
            if not status:
                f.write(f"{source_name},{source_url}\n")


def select_today_category(categories):
    """根据当天日期选择一个分类。"""
    category_list = list(categories.keys())
    if not category_list:
        return None
    today_index = datetime.now().timetuple().tm_yday % len(category_list)
    return category_list[today_index]


def main():
    """主程序逻辑，每天检测一个分类。"""
    install_dependencies()  # 确保依赖已安装
    create_folders_and_files()
    categories = parse_sources(SOURCE_FILE)

    # 每天检测一个分类
    today_category = select_today_category(categories)
    if not today_category:
        print("没有分类可检测。")
        return

    print(f"今天检测分类：{today_category}")
    sources = categories[today_category]

    # 异步运行检测任务
    asyncio.run(check_category(today_category, sources))


if __name__ == "__main__":
    main()
