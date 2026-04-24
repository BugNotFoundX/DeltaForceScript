# -*- coding: utf-8 -*-
# @Author: BugNotFound
# @Date: 2025-10-04
# @FilePath: /DeltaForceScript/src/deltaforcescript/script_thread.py
# @Description: 带 PyQt6 GUI 的主程序

import time
import warnings
from enum import Enum

from PyQt6.QtCore import QThread, pyqtSignal

warnings.filterwarnings("ignore", category=SyntaxWarning, module=r"colormath\..*")

from colormath.color_conversions import convert_color
from colormath.color_diff import delta_e_cie2000
from colormath.color_objects import LabColor, sRGBColor

from .capture import WindowCapture
from .input_helper import click_point, click_region_center, press_esc
from .region_selector import RegionSelector
from .runtime_utils import (
    PurchaseOutcome,
    classify_purchase_outcome,
    extract_and_merge_digits,
    parse_countdown_text,
)


class PurchaseState(Enum):
    """参与抽选流程状态。"""

    MONITORING = "monitoring"
    PRE_REFRESH = "pre_refresh"
    ENTER_PURCHASE = "enter_purchase"
    CONFIRM_DRAW = "confirm_draw"
    WAIT_RESULT = "wait_result"
    COMPLETED = "completed"
    RETRY_OR_CONTINUE = "retry_or_continue"


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
        self.state = PurchaseState.MONITORING
        self.initial_money = ""
        self.last_outcome = PurchaseOutcome.UNKNOWN

    def frame_cut(self, frame, region):
        """裁剪图像区域"""
        left, top, right, bottom = region
        return frame[top:bottom, left:right]

    def _sleep(self, seconds: float):
        """可被停止打断的 sleep。"""
        end_time = time.monotonic() + max(0, seconds)
        while self.is_running and time.monotonic() < end_time:
            time.sleep(min(0.05, end_time - time.monotonic()))

    def _wait_if_paused(self):
        while self.is_running and self.is_paused:
            time.sleep(0.2)

    def _set_state(self, state: PurchaseState, message: str | None = None):
        self.state = state
        if message:
            self.status_updated.emit(message)

    def _region_or_none(self, name: str):
        regions = self.selector.get_all_regions()
        return regions.get(name)

    def _result_region(self):
        """优先使用 result_text；旧配置缺失时回退到确认按钮上方。"""
        result_region = self._region_or_none("result_text")
        if result_region is not None:
            return result_region

        verify_region = self.selector.get_region("verify")
        left, top, right, bottom = verify_region
        height = bottom - top
        fallback_top = max(0, top - height * 5)
        fallback_bottom = max(fallback_top + 1, top)
        return (left, fallback_top, right, fallback_bottom)

    def verify_window(self) -> bool:
        """检查确认按钮区域的颜色是否变化。"""
        frame = self.win_cap.capture()
        while self.is_running and (frame is None or frame.size == 0):
            frame = self.win_cap.capture()
        if frame is None or frame.size == 0:
            return False

        region = self.selector.get_region("verify_check")
        color_tmp = frame[((region[1] + region[3]) // 2), ((region[0] + region[2]) // 2)]
        center_color = convert_color(
            sRGBColor(color_tmp[2], color_tmp[1], color_tmp[0]),
            LabColor,
        )
        target_color = convert_color(
            sRGBColor(175, 109, 65),
            LabColor,
        )
        return delta_e_cie2000(center_color, target_color) < 80

    def ocr_region(self, region):
        """OCR 识别。"""
        frame = self.win_cap.capture()
        if frame is None or frame.size == 0:
            return ""
        roi = self.frame_cut(frame, region)
        res = self.ocr.ocr(roi)
        if not res or not res[0]["rec_texts"]:
            return ""
        return "".join(res[0]["rec_texts"])

    def _read_money(self, money_region) -> str:
        money_text = self.ocr_region(money_region)
        return extract_and_merge_digits(money_text)

    def _refresh_once(self, refresh_region):
        self._set_state(PurchaseState.PRE_REFRESH, "剩余3秒，刷新一次...")
        click_region_center(refresh_region)
        self.click_performed.emit()

    def _enter_purchase(self, buy_region) -> bool:
        self._set_state(PurchaseState.ENTER_PURCHASE, "进入参与抽选流程...")
        self._sleep(self.config["buy_click_delay"])
        click_region_center(buy_region, interval=0)
        self.click_performed.emit()

        retry_count = 0
        while self.is_running and not self.verify_window() and retry_count < 2:
            retry_count += 1
            self.status_updated.emit(f"未检测到确认窗口，重试购买按钮 {retry_count}/2")
            self._sleep(self.config["buy_interval"])
            click_region_center(buy_region, interval=0)
            self.click_performed.emit()

        return self.verify_window()

    def _confirm_draw(self, verify_region) -> bool:
        self._set_state(PurchaseState.CONFIRM_DRAW, "点击确认参与...")
        self._sleep(self.config["buy_to_verify_delay"])
        click_region_center(verify_region, interval=self.config["verify_interval"])
        self.click_performed.emit()

        verify_counter = 0
        while self.is_running and self.verify_window() and verify_counter < 3:
            verify_counter += 1
            self._sleep(self.config["verify_interval"])
            click_region_center(verify_region, interval=self.config["verify_interval"])
            self.click_performed.emit()

        if self.verify_window():
            click_point(1, 1, interval=0.1)
            return False
        return True

    def _read_result(self, money_region) -> tuple[PurchaseOutcome, str, str]:
        self._set_state(PurchaseState.WAIT_RESULT, "等待并识别弹窗结果...")
        self._sleep(1.5)

        result_text = self.ocr_region(self._result_region())
        outcome = classify_purchase_outcome(result_text)
        now_money = self._read_money(money_region)

        if now_money and self.initial_money and now_money != self.initial_money:
            outcome = PurchaseOutcome.SUCCESS

        self.status_updated.emit(f"弹窗文本: {result_text or '<未识别>'}")
        self.status_updated.emit(f"弹窗分类: {outcome.value}")
        self.status_updated.emit(f"当前三角币: {now_money or '<未识别>'}")
        return outcome, result_text, now_money

    def _should_continue_after_outcome(self, outcome: PurchaseOutcome) -> bool:
        if outcome == PurchaseOutcome.SUCCESS:
            return False
        if outcome in {
            PurchaseOutcome.JOINED_DRAW,
            PurchaseOutcome.NOT_SELECTED,
            PurchaseOutcome.SOLD_OUT,
            PurchaseOutcome.INSUFFICIENT_FUNDS,
        }:
            return bool(self.config["continue_after_complete"])
        return bool(self.config["continue_after_complete"])

    def _finish_or_continue(self, outcome: PurchaseOutcome, refresh_region) -> bool:
        self.last_outcome = outcome
        self._set_state(PurchaseState.RETRY_OR_CONTINUE)

        if self.verify_window():
            press_esc()

        click_region_center(refresh_region)
        self.click_performed.emit()

        if self._should_continue_after_outcome(outcome):
            self._set_state(PurchaseState.MONITORING, "继续监控中...")
            return True

        self._set_state(PurchaseState.COMPLETED, "任务完成！")
        self.task_completed.emit()
        self.is_running = False
        return False

    def _handle_countdown(self, minutes, seconds, regions, refreshed) -> bool:
        self.timer_updated.emit(str(minutes), str(seconds))

        if (
            minutes == 0
            and seconds == 3
            and self.config["click_refresh_at_3s"]
            and not refreshed
        ):
            self._refresh_once(regions["refresh"])
            return True

        if minutes == 0 and seconds == 1:
            if not self._enter_purchase(regions["buy"]):
                self.status_updated.emit("未打开确认窗口，继续监控...")
                self._set_state(PurchaseState.MONITORING)
                return False

            self._confirm_draw(regions["verify"])
            outcome, _result_text, _now_money = self._read_result(regions["money"])
            if not self._finish_or_continue(outcome, regions["refresh"]):
                return False
            return False

        if minutes > 0 or seconds > 5:
            self._sleep(self.config["ocr_interval"])
        return refreshed

    def run(self):
        """运行脚本。"""
        try:
            self.status_updated.emit("初始化中...")

            regions = {
                "time": self.selector.get_region("time"),
                "buy": self.selector.get_region("buy"),
                "verify": self.selector.get_region("verify"),
                "refresh": self.selector.get_region("refresh"),
                "money": self.selector.get_region("money"),
            }

            self.initial_money = self._read_money(regions["money"])
            self.status_updated.emit(f"初始三角币: {self.initial_money or '<未识别>'}")

            self._set_state(PurchaseState.MONITORING, "监控中...")
            refreshed = False
            click_region_center(regions["refresh"])
            self.click_performed.emit()

            while self.is_running:
                self._wait_if_paused()
                if not self.is_running:
                    break

                time_text = self.ocr_region(regions["time"])
                if "天" in time_text or "小时" in time_text:
                    click_region_center(regions["refresh"])
                    self.click_performed.emit()
                    self._sleep(self.config["ocr_interval"])
                    continue

                countdown = parse_countdown_text(time_text)
                if countdown is None:
                    self._sleep(self.config["ocr_interval"])
                    continue

                minutes, seconds = countdown
                refreshed = self._handle_countdown(minutes, seconds, regions, refreshed)
        except Exception as e:
            self.status_updated.emit(f"错误: {str(e)}")
            print(f"脚本运行错误: {e}")

    def pause(self):
        self.is_paused = True

    def resume(self):
        self.is_paused = False

    def stop(self):
        self.is_running = False
