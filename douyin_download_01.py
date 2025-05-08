import requests
import re
import os
import time

#修复空文案的命名问题，支持多次重试下载，仍失败则保存失败链接备份

def extract_douyin_link(input_text):
    # 使用正则表达式提取链接
    match = re.search(r'https://v\.douyin\.com/[^/]+/', input_text)
    if match:
        return match.group()
    else:
        print("Failed to extract Douyin link. Please ensure the link is correct.")
        return None

def parse_douyin_video(url, retry_count=3):
    # 新野API的接口地址
    api_url = "https://api.xinyew.cn/api/douyinjx"
    
    # 构造请求参数
    params = {
        "url": url
    }
    
    # 自动重试机制
    for attempt in range(retry_count):
        response = requests.get(api_url, params=params)
        if response.status_code == 200:
            try:
                result = response.json()
                print(f"API Response: {result}")
                if "code" in result and result["code"] == 200:
                    video_url = result["data"]["video_url"]
                    # 提取视频标题，如果为空则使用默认名称 "video"
                    video_title = result["data"].get("additional_data", [{}])[0].get("desc", "").strip()
                    if not video_title:
                        video_title = "video"
                    return video_url, video_title
                else:
                    print(f"Error: {result.get('msg', 'Unknown error')}")
            except ValueError as e:
                print(f"Failed to parse JSON response: {e}")
        else:
            print(f"Failed to get data. Status code: {response.status_code}")
        
        print(f"Retrying... (Attempt {attempt + 1}/{retry_count})")
        time.sleep(2)  # 等待2秒后重试
    
    print(f"Failed to parse video URL or title after {retry_count} attempts.")
    return None, None

def clean_filename(filename):
    # 清理文件名中的非法字符
    invalid_chars = r'<>:"/\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, "_")
    # 截取前120个字符
    if len(filename) > 120:
        filename = filename[:120]
    return filename.strip().replace("\n", "_")  # 移除换行符

def download_video(video_url, video_title, download_folder, max_retries=5):
    video_title = clean_filename(video_title)
    
    # 生成文件名，确保不覆盖已有文件
    base_filename = f"{video_title}.mp4"
    filename = base_filename
    counter = 1
    while os.path.exists(os.path.join(download_folder, filename)):
        filename = f"{video_title}({counter}).mp4"
        counter += 1
    
    file_path = os.path.join(download_folder, filename)
    
    for attempt in range(max_retries):
        try:
            response = requests.get(video_url, stream=True, timeout=10)
            if response.status_code == 200:
                with open(file_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=1024):
                        if chunk:
                            f.write(chunk)
                print(f"Video downloaded successfully as {file_path}")
                return True
            else:
                print(f"Failed to download video. Status code: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"Request failed (attempt {attempt + 1}/{max_retries}): {e}")
        
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"Deleted failed download: {file_path}")
        
        time.sleep(2)
    
    if os.path.exists(file_path):
        os.remove(file_path)
        print(f"Deleted failed download after all retries: {file_path}")
    return False

def read_links_from_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        links = file.readlines()
    return [link.strip() for link in links]

def write_failed_link_to_file(link, file_path="fail.txt"):
    with open(file_path, 'a', encoding='utf-8') as file:
        file.write(link + "\n")
    print(f"Failed link added to {file_path}: {link}")

def save_titles_to_file(titles, file_path="douyin_video_title.txt"):
    with open(file_path, 'w', encoding='utf-8') as file:
        for title in titles:
            file.write(title + "\n")
    print(f"Video titles saved to {file_path}")

def main():
    input_file = "douyin_video_01.txt"
    download_folder = "DouyinDownloadVideo"
    
    if not os.path.exists(download_folder):
        os.makedirs(download_folder)
        print(f"Created download folder: {download_folder}")
    
    links = read_links_from_file(input_file)
    video_titles = []
    
    for link in links:
        print(f"Processing link: {link}")
        douyin_url = extract_douyin_link(link)
        if douyin_url:
            print(f"Extracted Douyin link: {douyin_url}")
            video_url, video_title = parse_douyin_video(douyin_url)
            if video_url and video_title:
                print(f"无水印视频下载链接: {video_url}")
                print(f"视频标题: {video_title}")
                video_titles.append(video_title)
                if not download_video(video_url, video_title, download_folder):
                    write_failed_link_to_file(link)
            else:
                print("Failed to parse video URL or title")
        else:
            print("Failed to extract valid Douyin link from input.")
        print("-" * 50)
    
    # save_titles_to_file(video_titles)

if __name__ == "__main__":
    main()
