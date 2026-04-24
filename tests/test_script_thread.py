import importlib
import sys
import types

import pytest

from deltaforcescript.runtime_utils import PurchaseOutcome


class _Signal:
    def __init__(self, *_args, **_kwargs):
        self.values = []

    def emit(self, *args):
        self.values.append(args)


class _QThread:
    def __init__(self, *_args, **_kwargs):
        pass


class _Selector:
    def __init__(self):
        self.regions = {
            "time": (0, 0, 10, 10),
            "buy": (10, 0, 20, 10),
            "verify": (20, 0, 30, 10),
            "refresh": (30, 0, 40, 10),
            "money": (40, 0, 50, 10),
            "verify_check": (50, 0, 60, 10),
        }

    def get_region(self, name):
        return self.regions[name]

    def get_all_regions(self):
        return self.regions.copy()


class _Capture:
    pass


@pytest.fixture
def script_module(monkeypatch):
    qtcore = types.ModuleType("PyQt6.QtCore")
    qtcore.QThread = _QThread
    qtcore.pyqtSignal = _Signal
    pyqt6 = types.ModuleType("PyQt6")
    pyqt6.QtCore = qtcore

    capture = types.ModuleType("deltaforcescript.capture")
    capture.WindowCapture = _Capture

    region_selector = types.ModuleType("deltaforcescript.region_selector")
    region_selector.RegionSelector = _Selector

    input_helper = types.ModuleType("deltaforcescript.input_helper")
    input_helper.click_point = lambda *_args, **_kwargs: None
    input_helper.click_region_center = lambda *_args, **_kwargs: None
    input_helper.press_esc = lambda *_args, **_kwargs: None

    color_objects = types.ModuleType("colormath.color_objects")
    color_objects.LabColor = object
    color_objects.sRGBColor = object
    color_diff = types.ModuleType("colormath.color_diff")
    color_diff.delta_e_cie2000 = lambda *_args, **_kwargs: 100
    color_conversions = types.ModuleType("colormath.color_conversions")
    color_conversions.convert_color = lambda color, _target: color

    monkeypatch.setitem(sys.modules, "PyQt6", pyqt6)
    monkeypatch.setitem(sys.modules, "PyQt6.QtCore", qtcore)
    monkeypatch.setitem(sys.modules, "deltaforcescript.capture", capture)
    monkeypatch.setitem(sys.modules, "deltaforcescript.region_selector", region_selector)
    monkeypatch.setitem(sys.modules, "deltaforcescript.input_helper", input_helper)
    monkeypatch.setitem(sys.modules, "colormath.color_objects", color_objects)
    monkeypatch.setitem(sys.modules, "colormath.color_diff", color_diff)
    monkeypatch.setitem(sys.modules, "colormath.color_conversions", color_conversions)
    monkeypatch.delitem(sys.modules, "deltaforcescript.script_thread", raising=False)

    return importlib.import_module("deltaforcescript.script_thread")


@pytest.fixture
def thread(script_module):
    config = {
        "buy_click_delay": 0,
        "buy_to_verify_delay": 0,
        "buy_interval": 0,
        "verify_interval": 0,
        "ocr_interval": 0,
        "continue_after_complete": True,
        "click_refresh_at_3s": True,
    }
    thread = script_module.ScriptThread(_Selector(), _Capture(), object(), config)
    thread._sleep = lambda _seconds: None
    return thread


def test_countdown_refreshes_once_at_3s(script_module, thread, monkeypatch):
    clicks = []
    monkeypatch.setattr(script_module, "click_region_center", lambda region, **_kwargs: clicks.append(region))

    regions = thread.selector.get_all_regions()
    assert thread._handle_countdown(0, 3, regions, refreshed=False) is True
    assert clicks == [regions["refresh"]]

    assert thread._handle_countdown(0, 3, regions, refreshed=True) is True
    assert clicks == [regions["refresh"]]


def test_countdown_enters_purchase_and_confirms_at_1s(thread):
    calls = []
    regions = thread.selector.get_all_regions()
    thread._enter_purchase = lambda region: calls.append(("enter", region)) or True
    thread._confirm_draw = lambda region: calls.append(("confirm", region)) or True
    thread._read_result = lambda region: (PurchaseOutcome.JOINED_DRAW, "已参与抽选", thread.initial_money)
    thread._finish_or_continue = lambda outcome, region: calls.append(("finish", outcome, region)) or True

    assert thread._handle_countdown(0, 1, regions, refreshed=True) is False
    assert calls == [
        ("enter", regions["buy"]),
        ("confirm", regions["verify"]),
        ("finish", PurchaseOutcome.JOINED_DRAW, regions["refresh"]),
    ]


def test_joined_draw_without_money_change_does_not_report_success(thread):
    thread.initial_money = "1000"
    thread.ocr_region = lambda _region: "已参与抽选"
    thread._read_money = lambda _region: "1000"

    outcome, _text, _money = thread._read_result(thread.selector.get_region("money"))
    assert outcome == PurchaseOutcome.JOINED_DRAW


def test_money_change_overrides_popup_text_as_success(thread):
    thread.initial_money = "1000"
    thread.ocr_region = lambda _region: "已参与抽选"
    thread._read_money = lambda _region: "900"

    outcome, _text, _money = thread._read_result(thread.selector.get_region("money"))
    assert outcome == PurchaseOutcome.SUCCESS


def test_failure_outcomes_follow_continue_config(thread):
    thread.config["continue_after_complete"] = True
    assert thread._should_continue_after_outcome(PurchaseOutcome.NOT_SELECTED) is True
    assert thread._should_continue_after_outcome(PurchaseOutcome.SOLD_OUT) is True

    thread.config["continue_after_complete"] = False
    assert thread._should_continue_after_outcome(PurchaseOutcome.NOT_SELECTED) is False
    assert thread._should_continue_after_outcome(PurchaseOutcome.SOLD_OUT) is False
