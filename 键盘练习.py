import tkinter as tk
from tkinter import ttk
import time
import random
import winsound  # 添加音效库


class TypingTutor:
    def __init__(self, root):
        self.root = root
        self.root.title("智能打字练习器")
        # 设置窗口默认大小和可调整性
        self.root.geometry("800x600")
        self.root.minsize(600, 400)  # 最小尺寸
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # 练习句子库（可扩展）
        self.sentences = [
            "The quick brown fox jumps over the lazy dog.",
            "Python is a great programming language.",
            "Practice makes perfect in keyboard typing.",
            "Hello world! This is a typing test application.",
            "DeepSeek creates awesome AI solutions."
        ]

        # 英文字母练习
        self.letters = "abcdefghijklmnopqrstuvwxyz"

        # 汉字练习
        self.chinese_chars = "的一是在不了有和人这中大为上个国我以要他时来用们生到作地于出就分对成会可主发年动同工也能下过子说产种面而方后多定行学法所民得经十三之进样理体信息东"

        # 初始化音效
        self.correct_sound = lambda: winsound.Beep(1000, 100)  # 正确音效(高音)
        self.wrong_sound = lambda: winsound.Beep(400, 100)  # 错误音效(低音)

        # 初始化界面
        self.setup_ui()
        self.new_exercise()

    def setup_ui(self):
        # 定义字体样式
        self.large_font = ('Microsoft YaHei', 12, 'bold')  # 大号加粗字体
        self.normal_font = ('Microsoft YaHei', 11)  # 常规字体

        # 配置样式
        style = ttk.Style()
        style.configure('TRadiobutton', font=self.large_font)
        style.configure('TLabel', font=self.large_font)
        style.configure('TButton', font=self.large_font)

        # 主框架，用于支持窗口缩放
        main_frame = ttk.Frame(self.root)
        main_frame.grid(row=0, column=0, sticky="nsew")

        # 练习模式选择
        self.mode_var = tk.StringVar(value="english")
        self.mode_frame = ttk.Frame(main_frame)
        self.mode_frame.grid(row=0, column=0, pady=10, sticky="ew")

        # 修改后的单选按钮，移除font参数
        ttk.Radiobutton(self.mode_frame, text="英语句子", value="english",
                        variable=self.mode_var, command=self.new_exercise).grid(row=0, column=0, padx=5)
        ttk.Radiobutton(self.mode_frame, text="英文字母", value="letters",
                        variable=self.mode_var, command=self.new_exercise).grid(row=0, column=1, padx=5)
        ttk.Radiobutton(self.mode_frame, text="汉字", value="chinese",
                        variable=self.mode_var, command=self.new_exercise).grid(row=0, column=2, padx=5)

        # 目标文本显示
        self.target_label = ttk.Label(main_frame, text="目标文本：", wraplength=600)
        self.target_label.grid(row=1, column=0, pady=10, sticky="ew")

        # 用户输入显示（带高亮） - 修改高度为4行
        self.input_text = tk.Text(main_frame, height=4, width=60, wrap=tk.WORD, font=self.normal_font)
        self.input_text.grid(row=2, column=0, pady=5, sticky="nsew")

        # 控制按钮框架（必须先定义）
        self.control_frame = ttk.Frame(main_frame)
        self.control_frame.grid(row=5, column=0, pady=10, sticky="ew")

        # 定义大按钮样式
        style = ttk.Style()
        style.configure('Large.TButton', font=self.large_font)

        # 然后才能创建按钮
        self.new_btn = ttk.Button(self.control_frame, text="新练习", command=self.new_exercise,
                                  style='Large.TButton')
        self.new_btn.grid(row=0, column=0, padx=5)

        # 统计信息
        self.stats_label = ttk.Label(main_frame, text="正确率: 0% | 速度: 0 CPM", font=self.large_font)
        self.stats_label.grid(row=4, column=0, pady=5, sticky="ew")

        self.input_text.bind("<KeyRelease>", self.check_typing)

        # 添加虚拟键盘
        self.keyboard_frame = ttk.Frame(main_frame)
        self.keyboard_frame.grid(row=3, column=0, pady=10, sticky="ew")
        self.setup_keyboard()

        # 统计信息
        self.stats_label = ttk.Label(main_frame, text="正确率: 0% | 速度: 0 CPM")
        self.stats_label.grid(row=4, column=0, pady=5, sticky="ew")

        # 设置文本框和主框架的缩放权重
        main_frame.rowconfigure(2, weight=1)
        main_frame.columnconfigure(0, weight=1)

    def new_exercise(self):
        """开始新练习"""
        mode = self.mode_var.get()
        if mode == "english":
            self.target_sentence = random.choice(self.sentences)
        elif mode == "letters":
            self.target_sentence = self.letters
        elif mode == "chinese":
            self.target_sentence = ''.join(random.choice(self.chinese_chars) for _ in range(50))

        self.target_label.config(text=f"目标文本：{self.target_sentence}")
        self.input_text.delete(1.0, tk.END)
        self.start_time = time.time()
        self.correct_chars = 0
        self.total_chars = 0
        self.update_stats()

        # 智能调整：根据表现调整难度
        if hasattr(self, 'last_accuracy'):
            if self.last_accuracy > 90:
                self.target_sentence = self.make_harder(self.target_sentence)
            elif self.last_accuracy < 70:
                self.target_sentence = self.make_easier(self.target_sentence)

    def setup_keyboard(self):
        """设置虚拟键盘布局"""
        # 标准QWERTY键盘布局
        rows = [
            "1234567890",
            "QWERTYUIOP",
            "ASDFGHJKL",
            "ZXCVBNM"
        ]

        self.key_buttons = {}
        for i, row in enumerate(rows):
            row_frame = ttk.Frame(self.keyboard_frame)
            row_frame.pack()
            for j, key in enumerate(row):
                # 修改按钮宽度为5，增大字体
                btn = ttk.Label(row_frame, text=key, width=5, relief="ridge", 
                               font=('Microsoft YaHei', 12, 'bold'))
                btn.pack(side="left", padx=1, pady=1)
                self.key_buttons[key] = btn

    def check_typing(self, event):
        """实时检查输入内容"""
        user_input = self.input_text.get(1.0, tk.END).strip()
        self.total_chars = len(user_input)

        # 重置所有键盘按钮样式
        for btn in self.key_buttons.values():
            btn.config(background="SystemButtonFace")

        # 高亮当前需要按的键
        if user_input and len(user_input) < len(self.target_sentence):
            next_char = self.target_sentence[len(user_input)].upper()
            if next_char in self.key_buttons:
                self.key_buttons[next_char].config(background="yellow")

        # 实时高亮显示正确/错误
        self.input_text.tag_remove("correct", "1.0", "end")
        self.input_text.tag_remove("wrong", "1.0", "end")

        self.correct_chars = 0
        for i, (input_char, target_char) in enumerate(zip(user_input, self.target_sentence)):
            if input_char == target_char:
                self.correct_chars += 1
                self.input_text.tag_add("correct", f"1.{i}")
                if i == len(user_input) - 1:  # 只在最新输入时播放音效
                    self.correct_sound()
            else:
                self.input_text.tag_add("wrong", f"1.{i}")
                if i == len(user_input) - 1:  # 只在最新输入时播放音效
                    self.wrong_sound()

        # 设置标签样式
        self.input_text.tag_config("correct", background="lightgreen")
        self.input_text.tag_config("wrong", background="salmon")

        self.update_stats()

    def update_stats(self):
        """更新统计信息"""
        time_elapsed = max(time.time() - self.start_time, 1)
        cpm = int(self.total_chars / time_elapsed * 60)
        accuracy = (self.correct_chars / max(self.total_chars, 1)) * 100
        self.last_accuracy = accuracy

        stats_text = f"正确率: {accuracy:.1f}% | 速度: {cpm} CPM"
        if accuracy < 70:
            stats_text += " (建议降低速度提高准确性)"
        elif accuracy > 95 and cpm > 200:
            stats_text += " (优秀！)"
        self.stats_label.config(text=stats_text)

    def make_harder(self, sentence):
        """智能增强难度"""
        # 示例增强方法：增加标点/数字/大写
        modifiers = [
            lambda s: s.replace(" ", "  "),  # 增加空格
            lambda s: s.upper(),  # 全大写
            lambda s: s + " 12345",  # 添加数字
            lambda s: s + ",.;:!?"  # 添加标点
        ]
        return random.choice(modifiers)(sentence)

    def make_easier(self, sentence):
        """降低难度"""
        # 示例简化方法：缩短句子/移除特殊字符
        return ' '.join(sentence.split()[:5]).replace(",", "").replace("!", "")


if __name__ == "__main__":
    root = tk.Tk()
    app = TypingTutor(root)
    root.mainloop()