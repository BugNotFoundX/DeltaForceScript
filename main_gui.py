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

ocr = PaddleOCR(
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    use_textline_orientation=False,
    text_detection_model_dir="models/PP-OCRv5_server_det_infer",
    text_recognition_model_dir="models/PP-OCRv5_server_rec_infer",
    device='gpu:0'
)


def click_region_center(region: tuple, clicks=2, interval=0.1):
    """点击区域的中心位置 - 使用多种方法尝试
    
    Args:
        region: (left, top, right, bottom) 格式的区域坐标
    """
    left, top, right, bottom = region
    center_x = (left + right) // 2
    center_y = (top + bottom) // 2
    
    print(f"准备点击位置: ({center_x}, {center_y})")

    pydirectinput.moveTo(center_x, center_y)
    time.sleep(0.05)
    pydirectinput.click(x=center_x, y=center_y, clicks=clicks, interval=interval, button=pydirectinput.LEFT)


class ScriptThread(QThread):
    """脚本运行线程"""
    
    status_updated = pyqtSignal(str)
    timer_updated = pyqtSignal(str, str)
    ocr_updated = pyqtSignal(str, float)
    click_performed = pyqtSignal()
    task_completed = pyqtSignal()
    
    def __init__(self, selector, win_cap):
        super().__init__()
        self.selector = selector
        self.win_cap = win_cap
        self.is_running = True
        self.is_paused = False
        
    def run(self):
        """运行脚本"""
        try:
            self.status_updated.emit("初始化中...")
            
            time_region = self.selector.get_region("time")
            if not time_region:
                self.status_updated.emit("❌ 错误: 未找到time区域")
                return
                
            left, top, right, bottom = time_region
            pattern = re.compile(r'(\d+)\s*分\s*(\d+)\s*秒')
            
            self.status_updated.emit("监控中...")
            buy_region = self.selector.get_region("buy")
            verify_region = self.selector.get_region("verify")
            while self.is_running:
                while self.is_paused and self.is_running:
                    time.sleep(0.1)
                
                if not self.is_running:
                    break
                
                frame = self.win_cap.capture()
                    
                time_roi = frame[top:bottom, left:right]
                # cv2.imwrite("time_roi.png", time_roi)
                
                ocr_result = ocr.predict(time_roi)
                
                if not ocr_result or not ocr_result[0]['rec_texts'][0]:
                    continue
                
                res = ocr_result[0]['rec_texts'][0]
                confidence = ocr_result[0]['rec_scores'][0]
                
                self.ocr_updated.emit(res, confidence)
                
                match = pattern.search(res)
                minutes = "59"
                seconds = "59"
                
                if match:
                    minutes = match.group(1)
                    seconds = match.group(2)
                    
                    self.timer_updated.emit(minutes, seconds)
                    
                    if minutes == '0' and seconds == '1':
                        self.status_updated.emit("⚠️ 准备点击...")
                        time.sleep(0.9)
                        
                        if buy_region:
                            self.status_updated.emit("🖱️ 点击购买按钮...")
                            click_region_center(buy_region, clicks=1)
                            self.click_performed.emit()
                            time.sleep(0.18)
                        
                        if verify_region:
                            self.status_updated.emit("🖱️ 点击确认按钮...")
                            click_region_center(verify_region, clicks=1)
                            self.click_performed.emit()
                        
                        self.status_updated.emit("✅ 任务完成！")
                        self.task_completed.emit()
                        break
                    else:
                        time.sleep(0.05)
                    
        except Exception as e:
            self.status_updated.emit(f"❌ 错误: {str(e)}")
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
    
    window = MonitorWindow()
    window.show()
    window.add_log("程序已启动")
    window.add_log("点击 [开始] 按钮启动监控")
    script_thread = None
    
    def on_start():
        nonlocal script_thread
        window.add_log("正在启动监控线程...")
        
        script_thread = ScriptThread(selector, win_cap)
        
        script_thread.status_updated.connect(lambda s: window.update_status(s))
        script_thread.status_updated.connect(lambda s: window.add_log(s))
        script_thread.timer_updated.connect(lambda m, s: window.update_timer(m, s))
        script_thread.ocr_updated.connect(lambda t, c: window.update_ocr(t, c))
        script_thread.click_performed.connect(lambda: window.increment_clicks())
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
