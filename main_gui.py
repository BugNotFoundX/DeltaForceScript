# -*- coding: utf-8 -*-
# @Author: BugNotFound
# @Date: 2025-10-04
# @FilePath: /DeltaForceScript/main_gui.py
# @Description: 带 PyQt6 GUI 的主程序

import os
import sys
import ctypes
from window_capture import *
from region_selector import RegionSelector
from paddleocr import PaddleOCR
from gui_monitor import MonitorWindow
import re
import time
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QThread, pyqtSignal
import pydirectinput


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


def click_region_center(region: tuple, clicks=1, interval=0.1):
    """点击区域的中心位置 - 使用多种方法尝试
    
    Args:
        region: (left, top, right, bottom) 格式的区域坐标
    """
    left, top, right, bottom = region
    center_x = (left + right) // 2
    center_y = (top + bottom) // 2
    
    # print(f"准备点击位置: ({center_x}, {center_y})")
    # 在20个像素的范围内随机偏移，防止被检测
    center_x += int((os.urandom(1)[0] / 255 - 0.5) * 10)
    center_y += int((os.urandom(1)[0] / 255 - 0.5) * 10)

    pydirectinput.click(x=center_x, y=center_y, clicks=clicks, interval=interval, button=pydirectinput.LEFT)

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
    
    def __init__(self, selector, win_cap: WindowCapture, ocr, config):
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

    def ocr_region(self, region):
        """OCR 识别"""
        frame = self.win_cap.capture()
        while frame is None or frame.size == 0: frame = self.win_cap.capture()
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
            click_region_center(refresh_region)
            while self.is_running:
                # 暂停时等待
                while self.is_paused: time.sleep(0.2); continue
                # 截图并OCR识别时间
                res = self.ocr_region(time_region)
                match = pattern.search(res)
                if match:
                    minutes = int(match.group(1))
                    seconds = int(match.group(2))
                    # 更新时间显示
                    self.timer_updated.emit(str(minutes), str(seconds))
                    # 剩余时间到 0:03 时点击刷新（如果启用）
                    if minutes == 0 and seconds == 3 and self.config['click_refresh_at_3s']:
                        self.status_updated.emit("🔄 点击刷新...")
                        click_region_center(refresh_region, interval=0.9)
                    # 剩余时间到 0:01 时执行点击
                    if minutes == 0 and seconds == 1:
                        self.status_updated.emit("准备点击...")
                        time.sleep(self.config['buy_click_delay'])
                        # 点击购买按钮
                        self.status_updated.emit("点击购买按钮...")
                        click_region_center(buy_region, interval=self.config['buy_interval'])
                        # 校验点击是否成功
                        verify = self.ocr_region(verify_region)
                        while "确认" not in verify:
                            click_region_center(buy_region, interval=self.config['buy_interval'])
                            verify = self.ocr_region(verify_region)
                        # 购买到确认之间的延迟
                        time.sleep(self.config['buy_to_verify_delay'])
                        # 点击确认按钮
                        self.status_updated.emit("点击确认按钮...")
                        click_region_center(verify_region, interval=self.config['verify_interval'])
                        # 校验点到了确认
                        verify = self.ocr_region(verify_region)
                        while "确认" in verify:
                            click_region_center(verify_region, interval=self.config['verify_interval'])
                            verify = self.ocr_region(verify_region)
                            self.status_updated.emit(f"确认按钮识别结果: {verify}")

                        self.status_updated.emit("等待刷新...")
                        time.sleep(1.5)
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
                            self.status_updated.emit("继续监控中...")
                    else:
                        if minutes > 0 or seconds > 4:
                            time.sleep(self.config['ocr_interval'])
                else:
                    time.sleep(0.95)
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
    
    win_cap = WindowCapture(max_buffer_len=1)
    
    # 初始化 OCR
    ocr = PaddleOCR(
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
        text_detection_model_dir="models/PP-OCRv5_server_det_infer",
        text_recognition_model_dir="models/PP-OCRv5_server_rec_infer",
        device='gpu:0'
    )
    window = MonitorWindow()
    window.show()
    window.add_log("程序已启动")
    window.add_log("点击 [开始] 按钮启动监控")
    script_thread = None
    
    def on_start():
        nonlocal script_thread
        window.add_log("正在启动监控线程...")
        
        # 获取当前配置
        config = window.get_config()
        window.add_log(f"配置: 购买延迟={config['buy_click_delay']}秒, 间隔延迟={config['buy_to_verify_delay']}秒")
        
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
