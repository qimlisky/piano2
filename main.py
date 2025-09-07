import tkinter as tk
from tkinter import ttk, messagebox
import pyautogui
import cv2
import numpy as np
import threading
import time
from datetime import datetime
import queue
import mss
import mss.tools

class PianoTiles2Helper:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("🎹 钢琴块2游戏辅助器")
        self.root.geometry("700x800")
        self.root.resizable(True, True)
        
        # 游戏相关变量
        self.selecting = False
        self.game_area = None
        self.screen_window = None
        
        # 运行状态
        self.running = False
        self.helper_thread = None
        self.log_queue = queue.Queue()
        
        # 游戏设置
        self.columns = 4  # 4个轨道
        self.sensitivity = 0.8  # 检测灵敏度
        self.click_delay = 0.01  # 点击延迟10ms
        self.scan_interval = 0.005  # 扫描间隔5ms
        
        # 性能优化
        self.use_mss = True  # 使用mss截图提高速度
        self.last_click_positions = set()
        
        self.setup_ui()
        
    def setup_ui(self):
        # 主框架
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 标题
        title_label = ttk.Label(main_frame, text="🎹 钢琴块2游戏辅助器", 
                               font=('Arial', 16, 'bold'), foreground='blue')
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # 游戏区域设置
        area_frame = ttk.LabelFrame(main_frame, text="🎯 游戏区域设置", padding="15")
        area_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 15))
        
        self.area_label = ttk.Label(area_frame, text="未选择游戏区域", foreground="red", font=('Arial', 10))
        self.area_label.grid(row=0, column=0, columnspan=2, pady=(0, 15))
        
        button_frame1 = ttk.Frame(area_frame)
        button_frame1.grid(row=1, column=0, columnspan=2)
        
        ttk.Button(button_frame1, text="选择游戏区域", command=self.select_game_area).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame1, text="重置区域", command=self.reset_area).pack(side=tk.LEFT)
        
        # 轨道设置
        track_frame = ttk.LabelFrame(main_frame, text="🎵 轨道设置", padding="15")
        track_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 15))
        
        ttk.Label(track_frame, text="轨道数量:").grid(row=0, column=0, sticky=tk.W)
        self.columns_var = tk.StringVar(value="4")
        columns_spin = ttk.Spinbox(track_frame, from_=3, to=6, textvariable=self.columns_var, width=10)
        columns_spin.grid(row=0, column=1, padx=(10, 0))
        
        # 性能设置
        settings_frame = ttk.LabelFrame(main_frame, text="⚙️ 性能设置", padding="15")
        settings_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 15))
        
        # 扫描间隔
        ttk.Label(settings_frame, text="扫描间隔 (ms):").grid(row=0, column=0, sticky=tk.W)
        self.scan_interval_var = tk.StringVar(value="5")
        scan_spin = ttk.Spinbox(settings_frame, from_=1, to=50, textvariable=self.scan_interval_var, width=10)
        scan_spin.grid(row=0, column=1, padx=(10, 0))
        
        # 点击延迟
        ttk.Label(settings_frame, text="点击延迟 (ms):").grid(row=1, column=0, sticky=tk.W, pady=(10, 0))
        self.click_delay_var = tk.StringVar(value="10")
        click_spin = ttk.Spinbox(settings_frame, from_=1, to=100, textvariable=self.click_delay_var, width=10)
        click_spin.grid(row=1, column=1, padx=(10, 0), pady=(10, 0))
        
        # 灵敏度
        ttk.Label(settings_frame, text="检测灵敏度:").grid(row=2, column=0, sticky=tk.W, pady=(10, 0))
        self.sensitivity_var = tk.StringVar(value="高")
        sensitivity_combo = ttk.Combobox(settings_frame, textvariable=self.sensitivity_var, 
                                       values=["低", "中", "高"], state="readonly", width=10)
        sensitivity_combo.grid(row=2, column=1, padx=(10, 0), pady=(10, 0))
        
        # 控制按钮
        control_frame = ttk.LabelFrame(main_frame, text="🎮 控制", padding="15")
        control_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 15))
        
        button_frame2 = ttk.Frame(control_frame)
        button_frame2.grid(row=0, column=0, columnspan=2)
        
        self.start_button = ttk.Button(button_frame2, text="▶️ 开始辅助", command=self.start_helper)
        self.start_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.stop_button = ttk.Button(button_frame2, text="⏹️ 停止辅助", command=self.stop_helper, state="disabled")
        self.stop_button.pack(side=tk.LEFT)
        
        # 状态显示
        self.status_label = ttk.Label(control_frame, text="状态: ⏹️ 已停止", foreground="red", font=('Arial', 11))
        self.status_label.grid(row=1, column=0, columnspan=2, pady=(15, 0))
        
        # 日志显示
        log_frame = ttk.LabelFrame(main_frame, text="📋 运行日志", padding="15")
        log_frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 15))
        
        # 日志文本框
        self.log_text = tk.Text(log_frame, height=15, width=75, font=('Consolas', 9))
        log_scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # 按钮区域
        button_frame3 = ttk.Frame(main_frame)
        button_frame3.grid(row=6, column=0, columnspan=2, pady=(10, 0))
        
        ttk.Button(button_frame3, text="清空日志", command=self.clear_log).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame3, text="使用说明", command=self.show_help).pack(side=tk.LEFT)
        
        # 配置权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(5, weight=1)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        # 启动日志更新定时器
        self.update_log_display()
        
    def select_game_area(self):
        """选择游戏区域"""
        try:
            # 隐藏主窗口
            self.root.withdraw()
            time.sleep(0.3)
            
            # 创建全屏选择窗口
            self.screen_window = tk.Toplevel()
            self.screen_window.attributes('-fullscreen', True)
            self.screen_window.attributes('-alpha', 0.3)
            self.screen_window.configure(bg='purple')
            self.screen_window.title("选择游戏区域")
            self.screen_window.configure(cursor="crosshair")
            
            # 绑定事件
            self.screen_window.bind('<Button-1>', self.on_mouse_down)
            self.screen_window.bind('<B1-Motion>', self.on_mouse_drag)
            self.screen_window.bind('<ButtonRelease-1>', self.on_mouse_up)
            self.screen_window.bind('<Escape>', self.cancel_selection)
            self.screen_window.bind('<Return>', self.confirm_selection)
            
            # 提示文本
            help_text = tk.Label(self.screen_window, 
                               text="拖拽选择钢琴块2游戏区域\n按ESC取消 | 按Enter确认", 
                               font=('Arial', 18, 'bold'), bg='purple', fg='white')
            help_text.pack(expand=True)
            
        except Exception as e:
            self.log_message(f"❌ 选择区域时出错: {str(e)}")
            self.root.deiconify()
    
    def on_mouse_down(self, event):
        """鼠标按下事件"""
        self.selecting = True
        self.start_x, self.start_y = event.x, event.y
        self.end_x, self.end_y = event.x, event.y
        
    def on_mouse_drag(self, event):
        """鼠标拖拽事件"""
        if self.selecting:
            self.end_x, self.end_y = event.x, event.y
            
    def on_mouse_up(self, event):
        """鼠标释放事件"""
        if self.selecting:
            self.selecting = False
            self.end_x, self.end_y = event.x, event.y
            self.confirm_selection(None)
    
    def confirm_selection(self, event):
        """确认选择"""
        if self.selecting or (hasattr(self, 'start_x') and hasattr(self, 'end_x')):
            self.selecting = False
            
            # 确保坐标顺序正确
            x1, x2 = min(self.start_x, self.end_x), max(self.start_x, self.end_x)
            y1, y2 = min(self.start_y, self.end_y), max(self.start_y, self.end_y)
            
            # 检查区域是否有效
            if abs(x2 - x1) > 50 and abs(y2 - y1) > 100:
                self.game_area = (x1, y1, x2, y2)
                self.area_label.config(text=f"游戏区域: ({x1}, {y1}) 到 ({x2}, {y2})", foreground="green")
                self.log_message(f"✅ 已选择游戏区域: ({x1}, {y1}) 到 ({x2}, {y2})")
                self.log_message("💡 建议区域高度包含完整的下落轨道")
            else:
                self.log_message("⚠️ 选择的区域太小，请确保包含完整的4个轨道")
                self.game_area = None
                self.area_label.config(text="未选择游戏区域", foreground="red")
            
            # 关闭选择窗口并显示主窗口
            if self.screen_window:
                self.screen_window.destroy()
                self.screen_window = None
            self.root.deiconify()
    
    def cancel_selection(self, event):
        """取消选择"""
        self.selecting = False
        if self.screen_window:
            self.screen_window.destroy()
            self.screen_window = None
        self.root.deiconify()
        self.log_message("❌ 已取消区域选择")
    
    def reset_area(self):
        """重置区域选择"""
        self.game_area = None
        self.area_label.config(text="未选择游戏区域", foreground="red")
        self.log_message("🔄 已重置游戏区域")
    
    def get_settings(self):
        """获取当前设置"""
        try:
            self.columns = int(self.columns_var.get())
            self.scan_interval = float(self.scan_interval_var.get()) / 1000.0
            self.click_delay = float(self.click_delay_var.get()) / 1000.0
            
            # 根据灵敏度设置阈值
            sensitivity_map = {"低": 0.9, "中": 0.8, "高": 0.7}
            self.sensitivity = sensitivity_map.get(self.sensitivity_var.get(), 0.8)
            
        except ValueError:
            self.columns = 4
            self.scan_interval = 0.005
            self.click_delay = 0.01
            self.sensitivity = 0.8
    
    def detect_black_tiles(self, screenshot_array):
        """检测黑色方块"""
        try:
            # 转换为灰度图像
            gray = cv2.cvtColor(screenshot_array, cv2.COLOR_RGB2GRAY)
            height, width = gray.shape
            
            # 计算每个轨道的宽度
            column_width = width // self.columns
            row_height = height // 10  # 检测底部1/10区域
            
            # 在底部区域检测黑色方块
            detection_area = gray[height - row_height:height, :]
            
            black_positions = []
            
            # 对每个轨道进行检测
            for i in range(self.columns):
                col_start = i * column_width
                col_end = (i + 1) * column_width
                
                # 提取当前轨道的底部区域
                column_area = detection_area[:, col_start:col_end]
                
                # 计算平均亮度
                avg_brightness = np.mean(column_area)
                
                # 如果亮度低于阈值，认为有黑色方块
                if avg_brightness < 50:  # 黑色方块通常亮度很低
                    # 计算点击位置（轨道中心，靠近底部）
                    click_x = col_start + column_width // 2
                    click_y = height - 20  # 距离底部20像素
                    black_positions.append((click_x, click_y, i))
            
            return black_positions
            
        except Exception as e:
            self.log_message(f"❌ 检测出错: {str(e)}")
            return []
    
    def detect_black_tiles_advanced(self, screenshot_array):
        """高级黑色方块检测"""
        try:
            # 转换为HSV颜色空间进行更好的颜色检测
            hsv = cv2.cvtColor(screenshot_array, cv2.COLOR_RGB2HSV)
            height, width = hsv.shape[:2]
            
            # 黑色的HSV范围
            lower_black = np.array([0, 0, 0])
            upper_black = np.array([180, 255, 50])
            
            # 创建黑色掩码
            mask = cv2.inRange(hsv, lower_black, upper_black)
            
            # 计算每个轨道的宽度
            column_width = width // self.columns
            row_height = height // 8  # 检测底部区域
            
            black_positions = []
            
            # 对每个轨道进行检测
            for i in range(self.columns):
                col_start = i * column_width
                col_end = (i + 1) * column_width
                
                # 提取当前轨道的底部区域
                column_mask = mask[height - row_height:height, col_start:col_end]
                
                # 计算黑色像素比例
                black_pixels = np.sum(column_mask > 0)
                total_pixels = column_mask.size
                black_ratio = black_pixels / total_pixels if total_pixels > 0 else 0
                
                # 如果黑色比例超过阈值，认为有黑色方块
                if black_ratio > 0.3:  # 30%以上为黑色
                    # 计算点击位置
                    click_x = self.game_area[0] + col_start + column_width // 2
                    click_y = self.game_area[1] + height - 20
                    black_positions.append((click_x, click_y, i))
            
            return black_positions
            
        except Exception as e:
            self.log_message(f"❌ 高级检测出错: {str(e)}")
            return []
    
    def start_helper(self):
        """开始辅助"""
        if not self.game_area:
            messagebox.showwarning("警告", "请先选择游戏区域")
            return
        
        # 更新设置
        self.get_settings()
        
        self.running = True
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.status_label.config(text="状态: ▶️ 运行中", foreground="green")
        
        # 启动辅助线程
        self.helper_thread = threading.Thread(target=self.helper_loop, daemon=True)
        self.helper_thread.start()
        
        self.log_message(f"🚀 开始辅助... (轨道数: {self.columns}, 扫描间隔: {int(self.scan_interval*1000)}ms)")
    
    def stop_helper(self):
        """停止辅助"""
        self.running = False
        if self.helper_thread and self.helper_thread.is_alive():
            self.helper_thread.join(timeout=1)
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")
        self.status_label.config(text="状态: ⏹️ 已停止", foreground="red")
        self.log_message("⏹️ 已停止辅助")
    
    def helper_loop(self):
        """辅助主循环"""
        try:
            last_click_time = 0
            click_count = 0
            start_time = time.time()
            
            with mss.mss() as sct:
                monitor = {
                    "top": self.game_area[1],
                    "left": self.game_area[0],
                    "width": self.game_area[2] - self.game_area[0],
                    "height": self.game_area[3] - self.game_area[1]
                }
                
                while self.running:
                    # 截取游戏区域
                    screenshot = sct.grab(monitor)
                    screenshot_array = np.array(screenshot)
                    
                    # 检测黑色方块
                    black_positions = self.detect_black_tiles_advanced(screenshot_array)
                    
                    current_time = time.time()
                    
                    # 点击检测到的黑色方块
                    for x, y, column in black_positions:
                        # 检查点击间隔
                        if current_time - last_click_time >= self.click_delay:
                            # 执行点击
                            pyautogui.click(x, y)
                            click_count += 1
                            last_click_time = current_time
                            
                            # 记录点击日志（每100次记录一次以避免日志过多）
                            if click_count % 100 == 0:
                                elapsed_time = time.time() - start_time
                                cps = click_count / elapsed_time if elapsed_time > 0 else 0
                                self.log_queue.put(f"🖱️ 点击位置: ({int(x)}, {int(y)}), 轨道: {column+1}, CPS: {cps:.1f}")
                            
                            # 短暂延迟避免过度频繁
                            time.sleep(0.001)
                    
                    # 短暂休眠
                    time.sleep(self.scan_interval)
                    
        except Exception as e:
            self.log_queue.put(f"❌ 辅助运行出错: {str(e)}")
            self.stop_helper()
    
    def log_message(self, message):
        """添加日志消息到队列"""
        self.log_queue.put(message)
    
    def update_log_display(self):
        """更新日志显示"""
        try:
            while True:
                message = self.log_queue.get_nowait()
                timestamp = datetime.now().strftime("%H:%M:%S")
                self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
                self.log_text.see(tk.END)
                self.log_text.update_idletasks()
        except queue.Empty:
            pass
        
        # 继续定时更新
        self.root.after(100, self.update_log_display)
    
    def clear_log(self):
        """清空日志"""
        self.log_text.delete(1.0, tk.END)
        self.log_message("📋 日志已清空")
    
    def show_help(self):
        """显示使用说明"""
        help_text = """
🎹 钢琴块2辅助器使用说明：

1. 游戏准备：
   - 打开钢琴块2游戏
   - 进入游戏主界面
   - 调整游戏窗口大小适中

2. 设置区域：
   - 点击"选择游戏区域"
   - 拖拽选择包含4个轨道的游戏区域
   - 确保区域包含完整的下落轨道

3. 调整设置：
   - 轨道数量：通常为4个
   - 扫描间隔：5ms（越小越快但占用资源）
   - 点击延迟：10ms（避免点击过快）
   - 检测灵敏度：根据游戏难度调整

4. 开始辅助：
   - 点击"开始辅助"
   - 切换到游戏开始游戏
   - 辅助器会自动点击黑色方块

5. 注意事项：
   - 确保游戏窗口在前台
   - 不要遮挡游戏区域
   - 可根据游戏速度调整参数
   - 使用时请遵守游戏规则

⚠️ 免责声明：此工具仅供学习研究使用，请合理使用！
        """
        
        help_window = tk.Toplevel(self.root)
        help_window.title("使用说明")
        help_window.geometry("600x500")
        
        text_widget = tk.Text(help_window, wrap=tk.WORD, padx=15, pady=15, font=('Arial', 10))
        text_widget.insert(tk.END, help_text)
        text_widget.config(state=tk.DISABLED)
        
        scrollbar = ttk.Scrollbar(help_window, orient="vertical", command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def run(self):
        """运行主程序"""
        # 设置窗口图标（如果有的话）
        try:
            self.root.iconbitmap('piano.ico')
        except:
            pass
        
        self.root.mainloop()

if __name__ == "__main__":
    # 检查依赖
    required_packages = ['pyautogui', 'opencv-python', 'numpy', 'mss']
    missing_packages = []
    
    for package in required_packages:
        try:
            if package == 'opencv-python':
                import cv2
            elif package == 'mss':
                import mss
            elif package == 'numpy':
                import numpy
            elif package == 'pyautogui':
                import pyautogui
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"缺少依赖库: {', '.join(missing_packages)}")
        print("请安装所需库: pip install pyautogui opencv-python numpy mss")
        exit(1)
    
    # 优化PyAutoGUI设置
    pyautogui.FAILSAFE = False  # 禁用安全限制
    pyautogui.PAUSE = 0  # 移除默认延迟
    
    app = PianoTiles2Helper()
    app.run()
