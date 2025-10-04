# -*- coding: utf-8 -*-
# @Author: BugNotFound
# @Date: 2025-10-04
# @Description: PyQt6 GUI 监控窗口

from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QGroupBox, QTextEdit, QProgressBar)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt6.QtGui import QFont, QPalette, QColor
import sys


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
        
        self.init_ui()
        
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("Delta Force 脚本监控")
        self.setGeometry(100, 100, 500, 650)
        
        # 设置窗口始终置顶
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)
        
        # 中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        # ========== 标题区域 ==========
        title_label = QLabel("🎮 Delta Force 自动购买脚本")
        title_font = QFont("微软雅黑", 16, QFont.Weight.Bold)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("color: #4CAF50; padding: 10px;")
        main_layout.addWidget(title_label)
        
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
        
        # ========== 倒计时显示组 ==========
        timer_group = QGroupBox("倒计时")
        timer_group.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                border: 2px solid #9C27B0;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
        """)
        timer_layout = QVBoxLayout()
        timer_group.setLayout(timer_layout)
        
        # 大字体倒计时
        self.timer_label = QLabel("--分--秒")
        timer_font = QFont("微软雅黑", 32, QFont.Weight.Bold)
        self.timer_label.setFont(timer_font)
        self.timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.timer_label.setStyleSheet("color: #00BCD4; padding: 20px;")
        timer_layout.addWidget(self.timer_label)
        
        main_layout.addWidget(timer_group)
        
        # ========== OCR信息组 ==========
        ocr_group = QGroupBox("OCR 识别信息")
        ocr_group.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                border: 2px solid #FF5722;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
        """)
        ocr_layout = QVBoxLayout()
        ocr_group.setLayout(ocr_layout)
        
        # 置信度标签
        self.confidence_label = QLabel("置信度: 0.00")
        self.confidence_label.setFont(QFont("微软雅黑", 11))
        self.confidence_label.setStyleSheet("padding: 5px;")
        ocr_layout.addWidget(self.confidence_label)
        
        # 置信度进度条
        self.confidence_bar = QProgressBar()
        self.confidence_bar.setMaximum(100)
        self.confidence_bar.setValue(0)
        self.confidence_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid grey;
                border-radius: 5px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
            }
        """)
        ocr_layout.addWidget(self.confidence_bar)
        
        # OCR文本
        self.ocr_label = QLabel("识别文本: ")
        self.ocr_label.setFont(QFont("微软雅黑", 10))
        self.ocr_label.setWordWrap(True)
        self.ocr_label.setStyleSheet("color: #757575; padding: 5px;")
        ocr_layout.addWidget(self.ocr_label)
        
        main_layout.addWidget(ocr_group)
        
        # ========== 统计信息组 ==========
        stats_group = QGroupBox("统计信息")
        stats_group.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                border: 2px solid #607D8B;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
        """)
        stats_layout = QVBoxLayout()
        stats_group.setLayout(stats_layout)
        
        self.clicks_label = QLabel("总点击次数: 0")
        self.clicks_label.setFont(QFont("微软雅黑", 11))
        self.clicks_label.setStyleSheet("padding: 5px;")
        stats_layout.addWidget(self.clicks_label)
        
        main_layout.addWidget(stats_group)
        
        # ========== 日志区域 ==========
        log_group = QGroupBox("运行日志")
        log_group.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                border: 2px solid #795548;
                border-radius: 5px;
                margin-top: 10px;
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
        
        self.ocr_label.setText(f"识别文本: {text}")
        self.confidence_label.setText(f"置信度: {confidence:.2f}")
        self.confidence_bar.setValue(int(confidence * 100))
        
        # 根据置信度改变颜色
        if confidence > 0.9:
            self.confidence_label.setStyleSheet("color: #4CAF50; padding: 5px;")
        elif confidence > 0.7:
            self.confidence_label.setStyleSheet("color: #FF9800; padding: 5px;")
        else:
            self.confidence_label.setStyleSheet("color: #F44336; padding: 5px;")
    
    def increment_clicks(self):
        """增加点击次数"""
        self.click_count += 1
        self.clicks_label.setText(f"总点击次数: {self.click_count}")
    
    def add_log(self, message):
        """添加日志"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        # 自动滚动到底部
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )
    
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
