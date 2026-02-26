# -*- coding: utf-8 -*-
# @Author: BugNotFound
# @Date: 2025-10-02 14:45:20
# @LastEditTime: 2025-12-19 21:21:37
# @FilePath: /DeltaForceScript/window_capture.py
# @Description: 窗口截图工具 - 包含Windows Graphics Capture API支持

import dxcam
import win32gui
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
    def __init__(self, device_idx: int = 0, output_idx: int = 0, target_fps: int = 500, max_buffer_len: int = 8):
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
    
if __name__ == "__main__":
    wc = WindowCapture()
    from .region_selector import RegionSelector
    selector = RegionSelector()
    selector.load_regions_from_file("regions_2k.json")
    frame = wc.capture()
    if frame is not None:
        region = selector.get_region("verify_check")
        if region is not None:
            frame = frame[region[1]:region[3], region[0]:region[2]]
        else:
            raise ValueError("Region 'verify_check' not found")
        # 打印中心色块颜色
        center_color = frame[frame.shape[0] // 2, frame.shape[1] // 2]
        print("Center color (BGR):", center_color)
        cv2.imwrite("screenshot.png", frame)
    else:
        print("Failed to capture frame")
    wc.stop()
