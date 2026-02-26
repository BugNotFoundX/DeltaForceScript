# -*- coding: utf-8 -*-
# @Author: BugNotFound
# @Date: 2025-10-04
# @FilePath: /DeltaForceScript/main_gui.py
# @Description: 带 PyQt6 GUI 的主程序

import os
import sys
import re
import time
import ctypes

from window_capture import *
from region_selector import RegionSelector
from gui_monitor import MonitorWindow

import numpy
from paddleocr import PaddleOCR
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QThread, pyqtSignal
import pydirectinput
import win32api
import win32con
from colormath.color_objects import sRGBColor, LabColor
from colormath.color_diff import delta_e_cie2000
from colormath.color_conversions import convert_color

def patch_asscalar(a):
    return a.item()

setattr(numpy, "asscalar", patch_asscalar)

def is_admin():
    """检查是否以管理员权限运行"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def run_as_admin():
    """以管理员权限重新启动程序"""
    if not is_admin():
        print("正在请求管理员权限...")
        # 获取当前脚本路径
        script = os.path.abspath(sys.argv[0])
        params = ' '.join([script] + sys.argv[1:])
        
        # 使用 ShellExecute 以管理员权限运行
        ret = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, params, None, 1
        )
        
        if ret > 32:  # 成功
            sys.exit(0)
        else:
            print("未获得管理员权限，继续以普通权限运行")
            return False
    return True


def click_point(x: int, y: int, clicks=1, interval=0.1):
    """使用 win32api 在屏幕坐标点击"""
    win32api.SetCursorPos((x, y))
    for i in range(max(1, int(clicks))):
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        if i < max(1, int(clicks)) - 1 and interval > 0:
            time.sleep(interval)


def click_region_center(region: tuple, clicks=1, interval=0.1):
    """点击区域中心位置（win32api 鼠标事件）"""
    left, top, right, bottom = region
    center_x = (left + right) // 2
    center_y = (top + bottom) // 2

    # 在 10 像素范围内随机偏移，防止被检测
    center_x += int((os.urandom(1)[0] / 255 - 0.5) * 10)
    center_y += int((os.urandom(1)[0] / 255 - 0.5) * 10)

    click_point(center_x, center_y, clicks=clicks, interval=interval)

def extract_and_merge_digits(s: str) -> str:
    """识别字符串中的所有数字并合并为一个新字符串"""
    return ''.join(re.findall(r'\d', s))
    

class ScriptThread(QThread):
    """脚本运行线程"""
    
    status_updated = pyqtSignal(str)
    timer_updated = pyqtSignal(str, str)
    ocr_updated = pyqtSignal(str, float)
    click_performed = pyqtSignal()
    task_completed = pyqtSignal()
    
    def __init__(self, selector: RegionSelector, win_cap: WindowCapture, ocr, config):
        super().__init__()
        self.selector = selector
        self.win_cap = win_cap
        self.ocr = ocr
        self.config = config
        self.is_running = True
        self.is_paused = False
    
    def frame_cut(self, frame, region):
        """裁剪图像区域"""
        left, top, right, bottom = region
        return frame[top:bottom, left:right]

    def verify_window(self) -> bool:
        """检查确认按钮区域的颜色是否变化"""
        frame = self.win_cap.capture()
        while frame is None or frame.size == 0: frame = self.win_cap.capture()
        region = self.selector.get_region("verify_check")
        # 获取区域中心颜色
        color_tmp = frame[((region[1] + region[3]) // 2), ((region[0] + region[2]) // 2)]
        center_color = convert_color(
            sRGBColor(color_tmp[2], color_tmp[1], color_tmp[0]),  # BGR to sRGB
            LabColor
        )
        # 预设的确认按钮中心颜色 (BGR)
        target_color = convert_color(
            sRGBColor(175, 109, 65),  # BGR：适用于金色砖皮
            LabColor
        )
        # 计算颜色差异
        delta_e = delta_e_cie2000(center_color, target_color)
        # 色差小说明显示了确认窗口
        self.status_updated.emit(f"颜色：{color_tmp[2], color_tmp[1], color_tmp[0]}")
        self.status_updated.emit(f"色差: {delta_e}")
        if delta_e < 80:
            return True
        return False

    def ocr_region(self, region):
        """OCR 识别"""
        frame = self.win_cap.capture()
        # while frame is None or frame.size == 0: frame = self.win_cap.capture()
        if frame is None or frame.size == 0: return ""
        roi = self.frame_cut(frame, region)
        res = self.ocr.ocr(roi)
        if not res or not res[0]['rec_texts']:
            return ""
        return res[0]['rec_texts'][0]

    def run(self):
        """运行脚本"""
        try:
            self.status_updated.emit("初始化中...")
            
            time_region = self.selector.get_region("time")
            buy_region = self.selector.get_region("buy")
            verify_region = self.selector.get_region("verify")
            refresh_region = self.selector.get_region("refresh")
            money_region = self.selector.get_region("money")

            money = self.ocr_region(money_region)
            money = extract_and_merge_digits(money)
            self.status_updated.emit(f"初始三角币: {money}")
            pattern = re.compile(r'(\d+)\s*分\s*(\d+)\s*秒')
            
            self.status_updated.emit("监控中...")
            refreshed = False  # 标记是否刚刚点击过刷新
            click_region_center(refresh_region)
            while self.is_running:
                # 暂停时等待
                while self.is_paused: time.sleep(0.2); continue
                # 截图并OCR识别时间
                res = self.ocr_region(time_region)
                if "天" in res or "小时" in res: click_region_center(refresh_region); continue
                match = pattern.search(res)
                if match:
                    minutes = int(match.group(1))
                    seconds = int(match.group(2))
                    # 更新时间显示
                    self.timer_updated.emit(str(minutes), str(seconds))
                    # 剩余时间到 0:03 时点击刷新（如果启用）
                    if minutes == 0 and seconds == 3 and self.config['click_refresh_at_3s'] and not refreshed:
                        self.status_updated.emit("🔄 点击刷新...")
                        click_region_center(refresh_region)
                        refreshed = True
                    # 剩余时间到 0:01 时执行点击
                    if minutes == 0 and seconds == 1:
                        self.status_updated.emit("准备点击...")
                        time.sleep(self.config['buy_click_delay'])
                        # 点击购买按钮
                        click_region_center(buy_region, interval=0)
                        # 校验点击是否成功（可能造成延迟）
                        buy_count = 0
                        while not self.verify_window() and buy_count < 5:
                            buy_count += 1
                            if buy_count <= 2:
                                time.sleep(self.config['buy_interval'])
                                click_region_center(buy_region, interval=0)
                        time.sleep(self.config['buy_to_verify_delay'])
                        # 点击确认按钮
                        click_region_center(verify_region, interval=self.config['verify_interval'])
                        self.status_updated.emit("点击确认按钮...")
                        # 校验点到了确认
                        verify_counter = 0
                        while self.verify_window():
                            verify_counter += 1
                            if verify_counter > 2:
                                click_point(1, 1, interval=0.1)
                            click_region_center(verify_region, interval=self.config['verify_interval'])
                        
                        self.status_updated.emit("等待刷新...")
                        time.sleep(1.5)
                        if self.verify_window(): pydirectinput.press('esc')
                        click_region_center(refresh_region)
                        # 检查三角币是否变化
                        now_money = self.ocr_region(money_region)
                        now_money = extract_and_merge_digits(now_money)
                        self.status_updated.emit(f"当前三角币: {now_money}")
                        self.config['continue_after_complete'] &= (now_money == money)
                        # 根据配置决定是否继续
                        if not self.config['continue_after_complete']:
                            self.status_updated.emit("任务完成！")
                            self.task_completed.emit()
                            break
                        else:
                            refreshed = False
                            self.status_updated.emit("继续监控中...")
                    else:
                        if minutes > 0 or seconds > 5:
                            time.sleep(self.config['ocr_interval'])
                else:
                    time.sleep(self.config['ocr_interval'])
        except Exception as e:
            self.status_updated.emit(f"错误: {str(e)}")
            print(f"脚本运行错误: {e}")
    
    def pause(self):
        self.is_paused = True
    
    def resume(self):
        self.is_paused = False
    
    def stop(self):
        self.is_running = False


def main():
    """主函数"""
    app = QApplication(sys.argv)
    selector = RegionSelector()
    selector.load_regions_from_file("regions_2k.json")
    win_cap = WindowCapture(max_buffer_len=2)
    
    # 初始化 OCR
    ocr = PaddleOCR(
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
        text_detection_model_dir="models/PP-OCRv5_server_det_infer",
        text_recognition_model_dir="models/PP-OCRv5_server_rec_infer",
        # use_tensorrt=True,
        device='gpu:0'
    )
    window = MonitorWindow()
    window.show()
    # 移动到屏幕右下角
    screen = app.primaryScreen().geometry()
    win_h = window.height()
    x = screen.x() + 10
    y = screen.y() + screen.height() - win_h - 30
    window.move(x, y)
    window.add_log("程序已启动")
    window.add_log("点击 [开始] 按钮启动监控")
    script_thread = None
    
    def on_start():
        nonlocal script_thread
        window.add_log("正在启动监控线程...")
        
        # 获取当前配置
        config = window.get_config()
        window.add_log(f"配置: 购买延迟={config['buy_click_delay']}秒")
        
        script_thread = ScriptThread(selector, win_cap, ocr, config)
        
        script_thread.status_updated.connect(lambda s: window.update_status(s))
        script_thread.status_updated.connect(lambda s: window.add_log(s))
        script_thread.timer_updated.connect(lambda m, s: window.update_timer(m, s))
        script_thread.task_completed.connect(lambda: window.on_complete())
        
        script_thread.start()
    
    def on_pause():
        if script_thread:
            script_thread.pause()
    
    def on_resume():
        if script_thread:
            script_thread.resume()
    
    def on_stop():
        if script_thread:
            script_thread.stop()
            script_thread.wait()
    
    window.controller.start_requested.connect(on_start)
    window.controller.pause_requested.connect(on_pause)
    window.controller.resume_requested.connect(on_resume)
    window.controller.stop_requested.connect(on_stop)
    
    def cleanup():
        if script_thread and script_thread.isRunning():
            script_thread.stop()
            script_thread.wait()
        win_cap.stop()
    
    app.aboutToQuit.connect(cleanup)
    
    sys.exit(app.exec())


if __name__ == "__main__":
    # 检查并请求管理员权限
    if not is_admin():
        print("检测到程序未以管理员权限运行")
        run_as_admin()
    else:
        print("Delta Force 自动购买脚本 - PyQt6 GUI版本 (管理员模式)")
        main()
