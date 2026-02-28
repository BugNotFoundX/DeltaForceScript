# -*- coding: utf-8 -*-
"""鼠标输入控制工具（win32api）。"""

import os
import time

import win32api
import win32con


def click_point(x: int, y: int, clicks=1, interval=0.1):
    """使用 win32api 在屏幕坐标点击。"""
    total_clicks = max(1, int(clicks))
    win32api.SetCursorPos((x, y))
    for i in range(total_clicks):
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        if i < total_clicks - 1 and interval > 0:
            time.sleep(interval)


def click_region_center(region: tuple, clicks=1, interval=0.1):
    """点击区域中心位置（带轻微随机偏移）。"""
    left, top, right, bottom = region
    center_x = (left + right) // 2
    center_y = (top + bottom) // 2

    center_x += int((os.urandom(1)[0] / 255 - 0.5) * 10)
    center_y += int((os.urandom(1)[0] / 255 - 0.5) * 10)

    click_point(center_x, center_y, clicks=clicks, interval=interval)


def press_esc(interval=0.02):
    """使用 win32api 发送 ESC 按键。"""
    win32api.keybd_event(win32con.VK_ESCAPE, 0, 0, 0)
    if interval and interval > 0:
        time.sleep(interval)
    win32api.keybd_event(win32con.VK_ESCAPE, 0, win32con.KEYEVENTF_KEYUP, 0)
