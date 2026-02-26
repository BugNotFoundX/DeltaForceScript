# -*- coding: utf-8 -*-
"""Package entrypoint for the GUI app."""

from .main_gui import main
from .system_utils import is_admin, run_as_admin


def run():
    """Run the GUI app with admin check."""
    if not is_admin():
        print("检测到程序未以管理员权限运行")
        run_as_admin()
    else:
        print("Delta Force 自动购买脚本 - PyQt6 GUI版本 (管理员模式)")
        main()


if __name__ == "__main__":
    run()
