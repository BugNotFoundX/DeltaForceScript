# -*- coding: utf-8 -*-
"""Windows 系统权限相关工具。"""

import ctypes
import os
import sys


def is_admin() -> bool:
    """检查是否以管理员权限运行。"""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def run_as_admin() -> bool:
    """以管理员权限重新启动当前程序。"""
    if is_admin():
        return True

    print("正在请求管理员权限...")
    script = os.path.abspath(sys.argv[0])
    params = " ".join([script] + sys.argv[1:])

    ret = ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, params, None, 1
    )
    if ret > 32:
        sys.exit(0)

    print("未获得管理员权限，继续以普通权限运行")
    return False
