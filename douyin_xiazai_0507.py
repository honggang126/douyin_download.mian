import sys
import os
import requests
import re
import time
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QTextEdit, QFileDialog, QProgressBar
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QIcon

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
        try:
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
        except requests.exceptions.RequestException as e:
            print(f"Request error: {e}")

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


def download_video(video_url, video_title, download_folder, max_retries=5, progress_signal=None, thread=None):
    video_title = clean_filename(video_title)

    # 生成文件名（原有逻辑保留）
    base_filename = f"{video_title}.mp4"
    filename = base_filename
    counter = 1
    while os.path.exists(os.path.join(download_folder, filename)):
        filename = f"{video_title}({counter}).mp4"
        counter += 1
    file_path = os.path.join(download_folder, filename)

    for attempt in range(max_retries):
        # 停止状态检查
        if thread and thread.is_stopped:
            thread.log_signal.emit("下载已停止")
            return False

        # 暂停状态检查
        if thread and thread.is_paused:
            thread.log_signal.emit("下载暂停中...")
            time.sleep(1)
            continue

        try:
            # 增大超时时间至30秒（原10秒）
            response = requests.get(video_url, stream=True, timeout=30)
            total_size = int(response.headers.get('content-length', 0))
            bytes_downloaded = 0
            if response.status_code == 200:
                with open(file_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=1024):
                        # 实时检查停止状态
                        if thread and thread.is_stopped:
                            # 添加异常处理：尝试删除未完成文件
                            try:
                                os.remove(file_path)  # 清理未完成文件
                            except PermissionError:
                                thread.log_signal.emit(f"警告：无法删除被占用的文件 {file_path}，请手动清理")
                            thread.log_signal.emit("下载已停止（中断）")
                            return False

                        # 实时检查暂停状态
                        if thread and thread.is_paused:
                            thread.log_signal.emit("下载暂停中...")
                            time.sleep(1)
                            continue

                        if chunk:
                            f.write(chunk)
                            bytes_downloaded += len(chunk)
                            if progress_signal:
                                progress = int((bytes_downloaded / total_size) * 100)
                                progress_signal.emit(progress)
                thread.log_signal.emit(f"视频下载成功：{file_path}")
                return True
            else:
                thread.log_signal.emit(f"下载失败（状态码：{response.status_code}）")
        except requests.exceptions.RequestException as e:
            thread.log_signal.emit(f"请求失败（尝试{attempt + 1}/{max_retries}）: {e}")

        # 清理失败的临时文件（添加异常处理）
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except PermissionError:
                thread.log_signal.emit(f"警告：无法删除被占用的临时文件 {file_path}，请手动清理")
        time.sleep(2)

    # 所有重试失败后的清理（添加异常处理）
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except PermissionError:
            thread.log_signal.emit(f"警告：无法删除被占用的失败文件 {file_path}，请手动清理")
    thread.log_signal.emit("所有重试次数已用尽，下载失败")
    return False


def write_failed_link_to_file(link, file_path="fail.txt"):
    with open(file_path, 'a', encoding='utf-8') as file:
        file.write(link + "\n")
    print(f"Failed link added to {file_path}: {link}")


class DownloadThread(QThread):
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)

    def __init__(self, url, download_folder):
        super().__init__()
        self.url = url
        self.download_folder = download_folder
        self.is_paused = False  # 暂停状态
        self.is_stopped = False  # 停止状态

    def run(self):
        douyin_url = extract_douyin_link(self.url)
        if douyin_url:
            self.log_signal.emit(f"Extracted Douyin link: {douyin_url}")
            video_url, video_title = parse_douyin_video(douyin_url)
            if video_url and video_title:
                self.log_signal.emit(f"无水印视频下载链接: {video_url}")
                self.log_signal.emit(f"视频标题: {video_title}")

                # 增加状态检查的下载循环
                while not self.is_stopped:  # 未停止时持续尝试
                    if self.is_paused:
                        time.sleep(1)  # 暂停时等待
                        continue

                    # 调用下载函数并传递线程状态
                    download_result = download_video(
                        video_url,
                        video_title,
                        self.download_folder,
                        progress_signal=self.progress_signal,
                        thread=self  # 传递当前线程对象用于状态检查
                    )

                    if download_result or self.is_stopped:
                        break  # 下载成功或手动停止时退出循环
        else:
            self.log_signal.emit("Failed to extract valid Douyin link from input.")


class DouyinDownloader(QWidget):
    def __init__(self):
        super().__init__()
        self.download_folder = "DouyinDownloadVideo"
        if not os.path.exists(self.download_folder):
            os.makedirs(self.download_folder)
        
        # 获取打包后的图标路径
        if getattr(sys, 'frozen', False):
            icon_path = os.path.join(sys._MEIPASS, "icon.ico")
        else:
            icon_path = "icon.ico"
            
        self.initUI()
        self.setWindowIcon(QIcon(icon_path))  # 使用正确的图标路径
        self.download_thread = None

    def initUI(self):
        self.setWindowTitle('抖抖下载器')
        self.setGeometry(100, 100, 650, 500)

        # 第一行：输入框和按钮
        input_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("复制分享链接到这里！")  # 添加提示文字
        paste_button = QPushButton('粘贴网址')
        paste_button.clicked.connect(self.paste_url)
        delete_button = QPushButton('删除网址')
        delete_button.clicked.connect(self.delete_url)
        input_layout.addWidget(self.url_input)
        input_layout.addWidget(paste_button)
        input_layout.addWidget(delete_button)

        # 第二行：下载控制按钮、保存路径选择和刷新按钮
        control_layout = QHBoxLayout()
        start_button = QPushButton('开始下载')
        start_button.clicked.connect(self.start_download)
        pause_button = QPushButton('暂停下载')
        pause_button.clicked.connect(self.pause_download)
        stop_button = QPushButton('停止下载')
        stop_button.clicked.connect(self.stop_download)
        refresh_button = QPushButton('刷新')
        refresh_button.clicked.connect(self.refresh)
        self.path_label = QLineEdit(self.download_folder)
        self.path_label.setReadOnly(True)
        path_button = QPushButton('选择')
        path_button.clicked.connect(self.select_download_folder)
        control_layout.addWidget(start_button)
        control_layout.addWidget(pause_button)
        control_layout.addWidget(stop_button)
        control_layout.addWidget(refresh_button)
        control_layout.addWidget(self.path_label)
        control_layout.addWidget(path_button)

        # 日志显示框
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        # 添加提示信息
        self.log_text.setPlainText('世界是你们的，也是我们的，但是归根结底是你们的。你们青年人朝气蓬勃，正在兴旺时期，好像早晨八九点钟的太阳。希望寄托在你们身上。” 这句话表达了毛泽东先生对年轻一代的殷切期望。年轻人应该勇挑重担，为国家和民族的繁荣发展贡献自己的力量。。。。毛泽东')

        # 下载进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)

        # 底部说明
        bottom_layout = QHBoxLayout()
        bottom_label = QPushButton('本软件仅供个人使用，QQ交流群：1035396790 不得用于商用')
        bottom_label.setFlat(True)
        bottom_layout.addWidget(bottom_label)

        # 设置所有按钮和文本框字体增大3号（原+2改为+3），按钮背景为浅蓝色
        font_size = self.font().pointSize() + 3
        style = f"font-size: {font_size}pt; background-color: lightblue;"
        for button in [paste_button, delete_button, start_button, pause_button, stop_button, path_button, bottom_label, refresh_button]:
            button.setStyleSheet(style)
        for textbox in [self.url_input, self.path_label, self.log_text]:
            textbox.setStyleSheet(f"font-size: {font_size}pt;")

        # 主布局
        main_layout = QVBoxLayout()
        main_layout.addLayout(input_layout)
        main_layout.addLayout(control_layout)
        main_layout.addWidget(self.log_text)
        main_layout.addWidget(self.progress_bar)
        main_layout.addLayout(bottom_layout)

        self.setLayout(main_layout)

    def paste_url(self):
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        douyin_url = extract_douyin_link(text)
        if douyin_url:
            self.url_input.setText(douyin_url)
        else:
            self.url_input.clear()

    def delete_url(self):
        self.url_input.clear()

    def start_download(self):
        url = self.url_input.text()
        if url:
            # 下载开始时清除初始提示文字
            self.log_text.clear()
            self.download_thread = DownloadThread(url, self.download_folder)
            self.download_thread.log_signal.connect(self.update_log)
            self.download_thread.progress_signal.connect(self.update_progress)
            self.download_thread.start()

    def pause_download(self):
        if self.download_thread:
            self.download_thread.is_paused = not self.download_thread.is_paused
            status = "暂停" if self.download_thread.is_paused else "恢复"
            self.log_text.append(f"下载已{status}")

    def stop_download(self):
        if self.download_thread:
            self.download_thread.is_stopped = True  # 设置停止标志
            self.log_text.append("正在终止下载...")
            # 等待线程安全退出（最多等待5秒）
            self.download_thread.wait(5000)
            self.download_thread = None  # 清空线程引用
            self.log_text.append("下载已停止")

    def select_download_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择下载文件夹")
        if folder:
            self.download_folder = folder
            self.path_label.setText(folder)

    def update_log(self, log):
        self.log_text.append(log)

    def update_progress(self, progress):
        self.progress_bar.setValue(progress)

    def refresh(self):
        self.log_text.clear()
        # 重新添加提示信息
        self.log_text.setPlainText('世界是你们的，也是我们的，但是归根结底是你们的。你们青年人朝气蓬勃，正在兴旺时期，好像早晨八九点钟的太阳。希望寄托在你们身上。” 这句话表达了毛泽东先生对年轻一代的殷切期望。年轻人应该勇挑重担，为国家和民族的繁荣发展贡献自己的力量。。。。毛泽东')


if __name__ == '__main__':
    app = QApplication(sys.argv)
    downloader = DouyinDownloader()
    downloader.show()
    sys.exit(app.exec_())
    