import aiohttp
import asyncio
import os
import logging
import re  # 用于正则匹配直播源链接
from bs4 import BeautifulSoup
import subprocess
import sys

# 设置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 目标URL列表
URLS = [
    "http://tonkiang.us",
    "https://tv.cctv.com/live/"
]

TIMEOUT = 5  # 请求超时时间（秒）
VALID_THRESHOLD = 2  # 响应时间阈值，2秒以内视为有效

# 自动生成 requirements.txt 文件并写入依赖
def ensure_requirements_file():
    dependencies = [
        "aiohttp",
        "beautifulsoup4"
    ]
    
    if not os.path.exists("requirements.txt"):
        try:
            with open("requirements.txt", "w") as f:
                for dep in dependencies:
                    f.write(f"{dep}\n")
            logging.info("requirements.txt 文件已创建并写入依赖。")
        except Exception as e:
            logging.error(f"创建 requirements.txt 文件时出错：{e}")
            sys.exit(1)
    else:
        logging.info("requirements.txt 文件已存在，跳过创建。")

# 自动安装依赖
def install_requirements():
    ensure_requirements_file()  # 确保 requirements.txt 文件存在
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        logging.info("依赖已成功安装。")
    except subprocess.CalledProcessError as e:
        logging.error(f"安装依赖失败：{e}")
        sys.exit(1)

# 获取网页内容
async def fetch_page_content(url):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    html = await response.text()
                    logging.info(f"获取网页内容成功，来自 {url}，内容如下：\n{html[:1000]}")  # 打印网页内容的前1000个字符
                    return html
                else:
                    logging.error(f"获取网页内容失败，来自 {url}，状态码：{response.status}")
                    return None
    except Exception as e:
        logging.error(f"获取网页内容时出错，来自 {url}：{e}")
        return None

# 分类节目名称
def classify_channel(name):
    name = name.lower()
    if '新闻' in name:
        return '新闻频道'
    elif '体育' in name:
        return '体育频道'
    elif '地方' in name:
        return '地方频道'
    elif '娱乐' in name:
        return '娱乐频道'
    else:
        return '其他频道'

# 测试直播源响应时间
async def test_speed(url):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=TIMEOUT) as response:
                return response.status, response.url, response.elapsed.total_seconds()
    except Exception as e:
        logging.error(f"测试直播源 {url} 时出错：{e}")
        return None, url, None

# 正则表达式用于匹配直播源格式（http, rtmp, p3p, rtp 等）
def match_live_source(url):
    patterns = [
        r'http://',  # http
        r'rtmp://',  # rtmp
        r'p3p://',   # p3p
        r'rtsp://',  # rtsp
        r'rtp://',   # rtp
        r'p2p://'    # p2p
    ]
    
    for pattern in patterns:
        if re.match(pattern, url):
            return True
    return False

# 解析网页内容并提取直播源
def parse_live_sources(html_content, url):
    soup = BeautifulSoup(html_content, 'html.parser')
    live_sources = []
    
    if url == "http://tonkiang.us":
        # 假设所有 <a> 标签中的链接是直播源（可以根据实际网页结构调整）
        channels = soup.find_all('a', href=True)
        for channel in channels:
            link = channel['href']
            if match_live_source(link):
                name = channel.text.strip()
                live_sources.append((name, link))
                logging.info(f"发现直播源：{name}, 链接：{link} - 来自 {url}")
    
    elif url == "https://tv.cctv.com/live/":
        # 假设每个频道信息在 <div class="playItem"> 中（可以根据实际网页结构调整）
        channels = soup.find_all('div', class_='playItem')
        for channel in channels:
            name = channel.find('span').text.strip() if channel.find('span') else '未知频道'
            link = channel.find('a')['href'] if channel.find('a') else None
            if link and match_live_source(link):
                live_sources.append((name, link))
                logging.info(f"发现直播源：{name}, 链接：{link} - 来自 {url}")
    
    if not live_sources:
        logging.warning(f"未找到任何符合条件的直播源，来自 {url}。")
    
    return live_sources

# 根据响应时间分类
async def test_and_categorize(live_sources):
    white_list = []
    black_list = []
    tasks = [test_speed(url) for _, url in live_sources]
    results = await asyncio.gather(*tasks)
    
    for (name, url), (status, _, elapsed) in zip(live_sources, results):
        if status == 200 and elapsed is not None:
            if elapsed <= VALID_THRESHOLD:
                white_list.append(f"{name}, {url}, {elapsed}s")
                logging.info(f"有效：{name} ({url}) 响应时间：{elapsed}s")
            else:
                black_list.append(f"{name}, {url}, {elapsed}s")
                logging.warning(f"无效（响应过慢）：{name} ({url}) 响应时间：{elapsed}s")
        else:
            black_list.append(f"{name}, {url}, 无法访问")
            logging.warning(f"无效（无法访问）：{name} ({url})")
    
    return white_list, black_list

# 保存白名单和黑名单到文件
def save_to_files(white_list, black_list, base_path="live_streams"):
    if not os.path.exists(base_path):
        os.makedirs(base_path)
    
    white_file = os.path.join(base_path, "white_list.txt")
    black_file = os.path.join(base_path, "black_list.txt")
    
    with open(white_file, 'w', encoding='utf-8') as f:
        for line in white_list:
            f.write(line + "\n")
    
    with open(black_file, 'w', encoding='utf-8') as f:
        for line in black_list:
            f.write(line + "\n")
    
    logging.info(f"白名单保存至 {white_file}")
    logging.info(f"黑名单保存至 {black_file}")

# 主程序
async def main():
    install_requirements()  # 确保安装依赖

    for url in URLS:
        html_content = await fetch_page_content(url)
        
        if html_content:
            live_sources = parse_live_sources(html_content, url)
            if live_sources:
                white_list, black_list = await test_and_categorize(live_sources)
                save_to_files(white_list, black_list)
            else:
                logging.warning(f"未找到任何直播源，来自 {url}。")
        else:
            logging.error(f"无法获取网页内容，来自 {url}，程序终止。")

# 启动爬虫程序
if __name__ == "__main__":
    asyncio.run(main())
