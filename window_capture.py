# -*- coding: utf-8 -*-
# @Author: BugNotFound
# @Date: 2025-10-02 14:45:20
# @LastEditTime: 2025-10-04 18:29:29
# @FilePath: /DeltaForceScript/window_capture.py
# @Description: 窗口截图工具 - 包含Windows Graphics Capture API支持

import dxcam
import win32gui
import win32api
import cv2
import numpy as np

def enum_windows_with_title():
    """枚举所有窗口并显示标题"""
    def enum_callback(hwnd, results):
        if win32gui.IsWindowVisible(hwnd):
            window_title = win32gui.GetWindowText(hwnd)
            if window_title:
                results.append((hwnd, window_title))
        return True
    
    windows = []
    win32gui.EnumWindows(enum_callback, windows)
    return windows

class WindowCapture():
    def __init__(self, device_idx: int = 0, output_idx: int = 0, target_fps: int = 200, max_buffer_len: int = 8):
        """初始化窗口捕获
        
        Args:
            device_idx: 设备索引
            output_idx: 输出屏幕索引（多屏幕时指定）
            target_fps: 目标帧率
        """
        print(dxcam.device_info())
        print(dxcam.output_info())
        self.device_idx = device_idx
        self.output_idx = output_idx
        self.camera = dxcam.create(device_idx=device_idx, output_idx=output_idx, output_color="BGR", max_buffer_len=max_buffer_len)
        self.camera.start(target_fps=target_fps, video_mode=True)

    def capture(self) -> np.ndarray:
        img = self.camera.get_latest_frame()
        return img

    def stop(self):
        self.camera.stop()
    
# if __name__ == "__main__":
#     windows = enum_windows_with_title()
#     wc = WindowCapture()
#     frame = wc.capture()
#     cv2.imwrite("screenshot.png", frame)
#     wc.stop()
