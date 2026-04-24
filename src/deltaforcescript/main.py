# -*- coding: utf-8 -*-
"""Package entrypoint for the GUI app."""

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    __package__ = "deltaforcescript"

from .system_utils import is_admin, run_as_admin
from .paths import get_app_paths
from .runtime_utils import patch_numpy_asscalar


def create_ocr(paths):
    """Create the OCR engine with project-root-relative model paths."""
    from paddleocr import PaddleOCR

    return PaddleOCR(
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
        text_detection_model_dir=str(paths.detection_model_dir),
        text_recognition_model_dir=str(paths.recognition_model_dir),
        # use_tensorrt=True,
        device="gpu:0",
    )


def main():
    """主函数"""
    patch_numpy_asscalar()

    from PyQt6.QtWidgets import QApplication

    from .capture import WindowCapture
    from .gui_monitor import MonitorWindow
    from .region_selector import RegionSelector
    from .script_thread import ScriptThread

    paths = get_app_paths()
    app = QApplication(sys.argv)
    selector = RegionSelector()
    selector.load_regions_from_file(str(paths.regions_file))
    win_cap = WindowCapture(max_buffer_len=2)

    ocr = create_ocr(paths)
    window = MonitorWindow()
    window.show()
    # 移动到屏幕右下角
    screen_obj = app.primaryScreen() or window.screen()
    if screen_obj is not None:
        screen = screen_obj.geometry()
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
        window.add_log(f"配置: 参与延迟={config['buy_click_delay']}秒")

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


def run():
    """Console script entrypoint."""
    # if not is_admin():
    #     print("检测到程序未以管理员权限运行")
    #     run_as_admin()
    # else:
    print("Delta Force 抽选参与脚本 - PyQt6 GUI版本 (管理员模式)")
    main()


if __name__ == "__main__":
    """Run the GUI app with admin check."""
    run()
