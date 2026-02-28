# -*- coding: utf-8 -*-
# @Author: BugNotFound
# @Date: 2025-10-04
# @FilePath: /DeltaForceScript/src/deltaforcescript/script_thread.py
# @Description: 带 PyQt6 GUI 的主程序

import re
import time

from .capture import WindowCapture
from .region_selector import RegionSelector
from .input_helper import click_point, click_region_center, press_esc
from .runtime_utils import extract_and_merge_digits

from PyQt6.QtCore import QThread, pyqtSignal
from colormath.color_objects import sRGBColor, LabColor
from colormath.color_diff import delta_e_cie2000
from colormath.color_conversions import convert_color

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
                        if self.verify_window(): press_esc()
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

