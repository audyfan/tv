import time
import urllib.request
import re
from urllib.error import URLError, HTTPError
import cv2
import requests
import random

# 读取txt文件到数组
def read_txt_to_array(file_name):
    try:
        with open(file_name, 'r', encoding='utf-8') as file:
            lines = file.readlines()
            lines = [line.strip() for line in lines]
            return lines
    except FileNotFoundError:
        print(f"File '{file_name}' not found.")
        return []
    except Exception as e:
        print(f"An error occurred: {e}")
        return []

# 随机获取User-Agent
def get_random_user_agent():
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36",
    ]
    return random.choice(USER_AGENTS)

# 检测URL是否可访问并记录响应时间
def check_url(url, timeout=6):
    headers = {
        'User-Agent': get_random_user_agent(),  # 随机选择一个User-Agent
    }

    elapsed_time = None
    status_ok = False
    width, height, span_time = 0, 0, 0

    try:
        if "://" in url:
            start_time = time.time()
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as response:
                elapsed_time = (time.time() - start_time) * 1000  # 转换为毫秒
                if response.status == 200:
                    status_ok = True
                    # 尝试获取视频分辨率
                    width, height, span_time = get_video_dimensions(url, timeout)
    except HTTPError as e:
        print(f"HTTP Error: {e.code} - {e.reason},{url}")
    except URLError as e:
        print(f"URL Error: {e.reason},{url}")
    except Exception as e:
        print(f"Error checking url: {e},{url}")

    return elapsed_time, status_ok, width, height, span_time

def get_video_dimensions(url, timeout):
    try:
        start_time = time.time()
        print(f"checking url dimensions:{url}")

        response = requests.head(url, timeout=timeout)
        response.raise_for_status()

        cap = cv2.VideoCapture(url)
        if not cap.isOpened():
            return 0, 0, 0

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        cap.release()

        span_time = round(time.time() - start_time, 3)
        return width, height, span_time

    except (requests.RequestException, cv2.error, Exception):
        return 0, 0, 0

# 处理单行文本并检测URL
def process_line(line):
    if "#genre#" in line or "://" not in line:
        return None, None, None  # 确保返回三个值
    parts = line.split(',')
    if len(parts) == 2:
        name, url = parts
        width, height, span_time = get_video_dimensions(url.strip(), 6)
        return width, height, span_time
    return 0, 0, 0  # 确保返回三个值

#########################分割线########################

# 获取上次处理的条目索引
def get_processed_index(file_name):
    try:
        with open(file_name, 'r', encoding='utf-8') as file:
            lines = file.readlines()
            return int(lines[-1].strip()) if lines else 0
    except Exception as e:
        print(f"Error reading processed index: {e}")
        return 0

# 保存已处理的条目索引
def save_processed_index(file_name, index):
    try:
        with open(file_name, 'a', encoding='utf-8') as file:
            file.write(f"{index}\n")
    except Exception as e:
        print(f"Error saving processed index: {e}")

# 主程序
def main():
    merged_output_lines = read_txt_to_array('merged_output.txt')
    total_lines = len(merged_output_lines)
    
    # 获取已处理的条目索引
    processed_index = get_processed_index('processed_index.txt')
    
    # 每次处理100条
    batch_size = 100
    start_index = processed_index
    end_index = min(start_index + batch_size, total_lines)
    
    new_merged_output_lines = []
    for i in range(start_index, end_index):
        line = merged_output_lines[i]
        if "#genre#" in line:
            new_merged_output_lines.append(line)
        elif "://" not in line:
            new_merged_output_lines.append(line)
        elif "#genre#" not in line and "," in line and "://" in line:
            width, height, span_time = process_line(line)
            if width is not None and height is not None and span_time is not None:
                newline = f"{line},{width}x{height},{span_time}"
                new_merged_output_lines.append(newline)

    # 将合并后的文本写入文件
    output_file = "test_merged_output.txt"
    try:
        with open(output_file, 'a', encoding='utf-8') as f:
            for line in new_merged_output_lines:
                f.write(line + '\n')
        print(f"合并后的文本已保存到文件: {output_file}")

        # 更新已处理的条目索引
        save_processed_index('processed_index.txt', end_index)

    except Exception as e:
        print(f"保存文件时发生错误：{e}")

# 执行主程序
if __name__ == "__main__":
    main()
