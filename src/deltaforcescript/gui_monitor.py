# -*- coding: utf-8 -*-
# @Author: BugNotFound
# @Date: 2025-10-04
# @Description: PyQt6 GUI 监控窗口

from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QGroupBox, QTextEdit,
                             QSpinBox, QDoubleSpinBox, QCheckBox)
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtGui import QFont


class ScriptController(QObject):
    """脚本控制信号"""
    start_requested = pyqtSignal()
    stop_requested = pyqtSignal()
    pause_requested = pyqtSignal()
    resume_requested = pyqtSignal()


class MonitorWindow(QMainWindow):
    """PyQt6 监控窗口"""
    
    def __init__(self):
        super().__init__()
        self.controller = ScriptController()
        
        # 状态变量
        self.is_running = False
        self.is_paused = False
        self.minutes = "--"
        self.seconds = "--"
        self.ocr_text = ""
        self.confidence = 0.0
        self.click_count = 0
        self.status = "就绪"
        
        # 配置变量
        self.buy_click_delay = 0.50  # 参与点击延迟（秒）
        self.buy_to_verify_delay = 0.0  # 参与到确认的延迟（秒）
        self.buy_interval = 0.05  # 参与按钮点击间隔（秒）
        self.verify_interval = 0.05  # 确认参与按钮点击间隔（秒）
        self.ocr_interval = 0.95  # OCR识别间隔（time >= 5）（秒）
        self.continue_after_complete = True  # 任务完成后继续运行
        self.click_refresh_at_3s = True  # 3秒时点击刷新按钮
        
        self.init_ui()
        
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("Delta Force 脚本监控")
        self.setGeometry(100, 100, 350, 650)
        
        # 设置窗口始终置顶
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)
        
        # 中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        # ========== 标题区域 ===========
        title_label = QLabel("🎮 Delta Force 抽选参与脚本")
        title_font = QFont("微软雅黑", 16, QFont.Weight.Bold)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("color: #4CAF50; padding: 10px;")
        main_layout.addWidget(title_label)

        # 小字提示
        tip_label = QLabel("请将脚本放置在屏幕左下角，避免影响OCR结果")
        tip_font = QFont("微软雅黑", 9)
        tip_label.setFont(tip_font)
        tip_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tip_label.setStyleSheet("color: #888888; padding-bottom: 6px;")
        main_layout.addWidget(tip_label)
        
        # ========== 状态信息组 ==========
        status_group = QGroupBox("运行状态")
        status_group.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                border: 2px solid #2196F3;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        status_layout = QVBoxLayout()
        status_group.setLayout(status_layout)
        
        # 状态标签
        self.status_label = QLabel("状态: 就绪")
        self.status_label.setFont(QFont("微软雅黑", 12))
        self.status_label.setStyleSheet("color: #FF9800; padding: 5px;")
        status_layout.addWidget(self.status_label)
        
        main_layout.addWidget(status_group)
        
        # ========== 倒计时显示组 ===========
        timer_group = QGroupBox("倒计时")
        timer_group.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                border: 2px solid #9C27B0;
                border-radius: 5px;
                margin-top: 0px;
                padding-top: 10px;
            }
        """)
        timer_layout = QVBoxLayout()
        timer_group.setLayout(timer_layout)

        # 缩小字体和间距的倒计时
        self.timer_label = QLabel("--分--秒")
        timer_font = QFont("微软雅黑", 24, QFont.Weight.Bold)
        self.timer_label.setFont(timer_font)
        self.timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.timer_label.setStyleSheet("color: #00BCD4; padding: 10px;")
        timer_layout.addWidget(self.timer_label)

        main_layout.addWidget(timer_group)
        
        # ========== 脚本配置组 ==========
        config_group = QGroupBox("脚本配置")
        config_group.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                border: 2px solid #FF5722;
                border-radius: 5px;
                margin-top: 0px;
                padding-top: 10px;
            }
        """)
        config_layout = QVBoxLayout()
        config_group.setLayout(config_layout)
        
        # 参与点击延迟设置
        delay_layout = QHBoxLayout()
        delay_label = QLabel("参与点击延迟:")
        delay_label.setFont(QFont("微软雅黑", 10))
        delay_label.setFixedWidth(120)
        self.delay_spin = QDoubleSpinBox()
        self.delay_spin.setRange(0.0, 5.0)
        self.delay_spin.setValue(self.buy_click_delay)
        self.delay_spin.setSingleStep(0.1)
        self.delay_spin.setDecimals(2)
        self.delay_spin.setSuffix(" 秒")
        self.delay_spin.setFont(QFont("微软雅黑", 10))
        self.delay_spin.valueChanged.connect(self.on_delay_changed)
        delay_layout.addWidget(delay_label)
        delay_layout.addWidget(self.delay_spin)
        delay_layout.addStretch()
        config_layout.addLayout(delay_layout)
        
        # 参与到确认延迟设置
        buy_to_verify_layout = QHBoxLayout()
        buy_to_verify_label = QLabel("确认参与延迟:")
        buy_to_verify_label.setFont(QFont("微软雅黑", 10))
        buy_to_verify_label.setFixedWidth(120)
        self.buy_to_verify_spin = QDoubleSpinBox()
        self.buy_to_verify_spin.setRange(0.0, 5.0)
        self.buy_to_verify_spin.setValue(self.buy_to_verify_delay)
        self.buy_to_verify_spin.setSingleStep(0.1)
        self.buy_to_verify_spin.setDecimals(2)
        self.buy_to_verify_spin.setSuffix(" 秒")
        self.buy_to_verify_spin.setFont(QFont("微软雅黑", 10))
        self.buy_to_verify_spin.valueChanged.connect(self.on_buy_to_verify_delay_changed)
        buy_to_verify_layout.addWidget(buy_to_verify_label)
        buy_to_verify_layout.addWidget(self.buy_to_verify_spin)
        buy_to_verify_layout.addStretch()
        config_layout.addLayout(buy_to_verify_layout)
        
        # 参与按钮点击间隔
        buy_interval_layout = QHBoxLayout()
        buy_interval_label = QLabel("参与重试间隔:")
        buy_interval_label.setFont(QFont("微软雅黑", 10))
        buy_interval_label.setFixedWidth(120)
        self.buy_interval_spin = QDoubleSpinBox()
        self.buy_interval_spin.setRange(0.00, 1.0)
        self.buy_interval_spin.setValue(self.buy_interval)
        self.buy_interval_spin.setSingleStep(0.01)
        self.buy_interval_spin.setDecimals(2)
        self.buy_interval_spin.setSuffix(" 秒")
        self.buy_interval_spin.setFont(QFont("微软雅黑", 10))
        self.buy_interval_spin.valueChanged.connect(self.on_buy_interval_changed)
        buy_interval_layout.addWidget(buy_interval_label)
        buy_interval_layout.addWidget(self.buy_interval_spin)
        buy_interval_layout.addStretch()
        config_layout.addLayout(buy_interval_layout)
        
        # 确认参与按钮点击间隔
        verify_interval_layout = QHBoxLayout()
        verify_interval_label = QLabel("确认参与间隔:")
        verify_interval_label.setFont(QFont("微软雅黑", 10))
        verify_interval_label.setFixedWidth(120)
        self.verify_interval_spin = QDoubleSpinBox()
        self.verify_interval_spin.setRange(0.00, 1.0)
        self.verify_interval_spin.setValue(self.verify_interval)
        self.verify_interval_spin.setSingleStep(0.01)
        self.verify_interval_spin.setDecimals(2)
        self.verify_interval_spin.setSuffix(" 秒")
        self.verify_interval_spin.setFont(QFont("微软雅黑", 10))
        self.verify_interval_spin.valueChanged.connect(self.on_verify_interval_changed)
        verify_interval_layout.addWidget(verify_interval_label)
        verify_interval_layout.addWidget(self.verify_interval_spin)
        verify_interval_layout.addStretch()
        config_layout.addLayout(verify_interval_layout)
        
        # OCR识别间隔
        ocr_interval_layout = QHBoxLayout()
        ocr_interval_label = QLabel("OCR间隔(t>5s):")
        ocr_interval_label.setFont(QFont("微软雅黑", 10))
        ocr_interval_label.setFixedWidth(120)
        self.ocr_interval_spin = QDoubleSpinBox()
        self.ocr_interval_spin.setRange(0.01, 1.0)
        self.ocr_interval_spin.setValue(self.ocr_interval)
        self.ocr_interval_spin.setSingleStep(0.01)
        self.ocr_interval_spin.setDecimals(2)
        self.ocr_interval_spin.setSuffix(" 秒")
        self.ocr_interval_spin.setFont(QFont("微软雅黑", 10))
        self.ocr_interval_spin.valueChanged.connect(self.on_ocr_interval_changed)
        ocr_interval_layout.addWidget(ocr_interval_label)
        ocr_interval_layout.addWidget(self.ocr_interval_spin)
        ocr_interval_layout.addStretch()
        config_layout.addLayout(ocr_interval_layout)
        
        # 任务完成后继续运行选项
        continue_layout = QHBoxLayout()
        self.continue_checkbox = QCheckBox("任务完成后继续运行")
        self.continue_checkbox.setFont(QFont("微软雅黑", 10))
        self.continue_checkbox.setChecked(self.continue_after_complete)
        self.continue_checkbox.stateChanged.connect(self.on_continue_changed)
        self.continue_checkbox.setStyleSheet("""
            QCheckBox {
                padding: 5px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
        """)
        continue_layout.addWidget(self.continue_checkbox)
        continue_layout.addStretch()
        config_layout.addLayout(continue_layout)
        
        # 3秒时点击刷新选项
        refresh_layout = QHBoxLayout()
        self.refresh_checkbox = QCheckBox("剩余3秒时点击刷新")
        self.refresh_checkbox.setFont(QFont("微软雅黑", 10))
        self.refresh_checkbox.setChecked(self.click_refresh_at_3s)
        self.refresh_checkbox.stateChanged.connect(self.on_refresh_changed)
        self.refresh_checkbox.setStyleSheet("""
            QCheckBox {
                padding: 5px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
        """)
        refresh_layout.addWidget(self.refresh_checkbox)
        refresh_layout.addStretch()
        config_layout.addLayout(refresh_layout)
        
        main_layout.addWidget(config_group)
        
        # ========== 日志区域 ==========
        log_group = QGroupBox("运行日志")
        log_group.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                border: 2px solid #795548;
                border-radius: 5px;
                margin-top: 0px;
                padding-top: 10px;
            }
        """)
        log_layout = QVBoxLayout()
        log_group.setLayout(log_layout)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(100)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #263238;
                color: #B0BEC5;
                font-family: Consolas, monospace;
                font-size: 10px;
                border: 1px solid #37474F;
            }
        """)
        log_layout.addWidget(self.log_text)
        
        main_layout.addWidget(log_group)
        
        # ========== 控制按钮区域 ==========
        button_layout = QHBoxLayout()
        
        # 开始按钮
        self.start_btn = QPushButton("▶ 开始")
        self.start_btn.setFont(QFont("微软雅黑", 11, QFont.Weight.Bold))
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
            }
        """)
        self.start_btn.clicked.connect(self.on_start_clicked)
        button_layout.addWidget(self.start_btn)
        
        # 暂停/继续按钮
        self.pause_btn = QPushButton("⏸ 暂停")
        self.pause_btn.setFont(QFont("微软雅黑", 11, QFont.Weight.Bold))
        self.pause_btn.setEnabled(False)
        self.pause_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
            }
        """)
        self.pause_btn.clicked.connect(self.on_pause_clicked)
        button_layout.addWidget(self.pause_btn)
        
        # 停止按钮
        self.stop_btn = QPushButton("⏹ 停止")
        self.stop_btn.setFont(QFont("微软雅黑", 11, QFont.Weight.Bold))
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #F44336;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #D32F2F;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
            }
        """)
        self.stop_btn.clicked.connect(self.on_stop_clicked)
        button_layout.addWidget(self.stop_btn)
        
        main_layout.addLayout(button_layout)
        
        # 添加弹性空间
        main_layout.addStretch()
        
        # 设置窗口样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #FAFAFA;
            }
            QWidget {
                font-family: "微软雅黑";
            }
        """)
        
    def update_status(self, status):
        """更新状态"""
        self.status = status
        self.status_label.setText(f"状态: {status}")
        
        # 根据状态改变颜色
        if "运行" in status or "监控" in status:
            self.status_label.setStyleSheet("color: #4CAF50; padding: 5px;")
        elif "暂停" in status:
            self.status_label.setStyleSheet("color: #FF9800; padding: 5px;")
        elif "完成" in status or "成功" in status:
            self.status_label.setStyleSheet("color: #2196F3; padding: 5px;")
        elif "错误" in status or "失败" in status:
            self.status_label.setStyleSheet("color: #F44336; padding: 5px;")
        else:
            self.status_label.setStyleSheet("color: #757575; padding: 5px;")
    
    def update_timer(self, minutes, seconds):
        """更新倒计时"""
        self.minutes = str(minutes)
        self.seconds = str(seconds)
        self.timer_label.setText(f"{self.minutes}分{self.seconds}秒")
        
        # 如果时间快到了，变红色
        try:
            if int(minutes) == 0 and int(seconds) <= 5:
                self.timer_label.setStyleSheet("color: #F44336; padding: 20px;")
            else:
                self.timer_label.setStyleSheet("color: #00BCD4; padding: 20px;")
        except:
            pass
    
    def update_ocr(self, text, confidence):
        """更新OCR信息"""
        self.ocr_text = text
        self.confidence = confidence
    
    def on_delay_changed(self, value):
        """参与点击延迟变更"""
        self.buy_click_delay = value
        self.add_log(f"⚙️ 参与点击延迟已设置为: {value}秒")
    
    def on_buy_to_verify_delay_changed(self, value):
        """参与到确认延迟变更"""
        self.buy_to_verify_delay = value
        self.add_log(f"⚙️ 确认参与延迟已设置为: {value}秒")
    
    def on_buy_interval_changed(self, value):
        """参与重试间隔变更"""
        self.buy_interval = value
        self.add_log(f"⚙️ 参与重试间隔已设置为: {value}秒")
    
    def on_verify_interval_changed(self, value):
        """确认参与间隔变更"""
        self.verify_interval = value
        self.add_log(f"⚙️ 确认参与间隔已设置为: {value}秒")
    
    def on_ocr_interval_changed(self, value):
        """OCR识别间隔变更"""
        self.ocr_interval = value
        self.add_log(f"⚙️ OCR识别间隔已设置为: {value}秒")
    
    def on_continue_changed(self, state):
        """任务完成后继续运行选项变更"""
        self.continue_after_complete = (state == 2)  # Qt.CheckState.Checked = 2
        status = "继续运行" if self.continue_after_complete else "停止"
        self.add_log(f"⚙️ 任务完成后将: {status}")
    
    def on_refresh_changed(self, state):
        """3秒时点击刷新选项变更"""
        self.click_refresh_at_3s = (state == 2)  # Qt.CheckState.Checked = 2
        status = "启用" if self.click_refresh_at_3s else "禁用"
        self.add_log(f"⚙️ 3秒时点击刷新: {status}")
    
    def get_config(self):
        """获取当前配置"""
        return {
            'buy_click_delay': self.buy_click_delay,
            'buy_to_verify_delay': self.buy_to_verify_delay,
            'buy_interval': self.buy_interval,
            'verify_interval': self.verify_interval,
            'ocr_interval': self.ocr_interval,
            'continue_after_complete': self.continue_after_complete,
            'click_refresh_at_3s': self.click_refresh_at_3s
        }
    
    def increment_clicks(self):
        """增加点击次数（保留用于兼容性）"""
        self.click_count += 1
    
    def add_log(self, message):
        """添加日志"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        # 自动滚动到底部
        scrollbar = self.log_text.verticalScrollBar()
        if scrollbar is not None:
            scrollbar.setValue(scrollbar.maximum())
    
    def on_start_clicked(self):
        """开始按钮点击"""
        self.is_running = True
        self.is_paused = False
        self.start_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)
        self.update_status("运行中...")
        self.add_log("▶ 脚本已启动")
        self.controller.start_requested.emit()
    
    def on_pause_clicked(self):
        """暂停/继续按钮点击"""
        if self.is_paused:
            # 继续
            self.is_paused = False
            self.pause_btn.setText("⏸ 暂停")
            self.update_status("运行中...")
            self.add_log("▶ 脚本已继续")
            self.controller.resume_requested.emit()
        else:
            # 暂停
            self.is_paused = True
            self.pause_btn.setText("▶ 继续")
            self.update_status("已暂停")
            self.add_log("⏸ 脚本已暂停")
            self.controller.pause_requested.emit()
    
    def on_stop_clicked(self):
        """停止按钮点击"""
        self.is_running = False
        self.is_paused = False
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.pause_btn.setText("⏸ 暂停")
        self.stop_btn.setEnabled(False)
        self.update_status("已停止")
        self.add_log("⏹ 脚本已停止")
        self.controller.stop_requested.emit()
    
    def on_complete(self):
        """任务完成"""
        self.is_running = False
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.update_status("✅ 任务完成！")
        self.add_log("✅ 任务已完成")
