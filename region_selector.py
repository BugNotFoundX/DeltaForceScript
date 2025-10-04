# -*- coding: utf-8 -*-
# @Author: BugNotFound
# @Date: 2025-10-04
# @Description: 屏幕区域选择器 - 支持多屏幕蒙版框选

import cv2
import numpy as np
from typing import Tuple, Optional, Dict
from PIL import Image, ImageDraw, ImageFont
import dxcam
from dxcam.dxcam import Output, Device
from dxcam.util.io import (
    enum_dxgi_adapters,
)


class RegionSelector:
    """屏幕区域选择器类
    
    支持在指定屏幕上显示蒙版图层，通过鼠标拖动框选区域。
    可以命名选框并获取(left, top, right, bottom)格式的坐标。
    """
    
    def __init__(self):
        """初始化区域选择器
        
        Args:
            output_idx: 输出屏幕索引（多屏幕时指定）
            device_idx: 设备索引
        """
        self.output_idx = 0
        self.device_idx = 0
        self.regions: Dict[str, Tuple[int, int, int, int]] = {}

        p_adapters = enum_dxgi_adapters()
        self.devices, self.outputs = [], []
        for p_adapter in p_adapters:
            device = Device(p_adapter)
            p_outputs = device.enum_outputs()
            if len(p_outputs) != 0:
                self.devices.append(device)
                self.outputs.append([Output(p_output) for p_output in p_outputs])
        
        # 获取屏幕分辨率
        outputs = self.outputs[self.device_idx]
        if self.output_idx >= len(outputs):
            raise ValueError(f"output_idx {self.output_idx} 超出范围，可用屏幕数: {len(outputs)}")

        output_info = outputs[self.output_idx]
        self.screen_width = output_info.resolution[0]
        self.screen_height = output_info.resolution[1]
        print(f"屏幕 {self.output_idx} 分辨率: {self.screen_width}x{self.screen_height}")

        # 鼠标状态
        self.drawing = False
        self.start_point = None
        self.current_point = None
        
        # 尝试加载中文字体
        try:
            # Windows 系统字体路径
            self.font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 24)  # 微软雅黑
            self.font_large = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 32)
        except:
            try:
                # 备选：黑体
                self.font = ImageFont.truetype("C:/Windows/Fonts/simhei.ttf", 24)
                self.font_large = ImageFont.truetype("C:/Windows/Fonts/simhei.ttf", 32)
            except:
                # 如果都失败，使用默认字体（不支持中文）
                self.font = ImageFont.load_default()
                self.font_large = ImageFont.load_default()
                print("警告: 无法加载中文字体，可能无法正确显示中文")
        
    def _mouse_callback(self, event, x, y, flags, param):
        """鼠标回调函数"""
        if event == cv2.EVENT_LBUTTONDOWN:
            self.drawing = True
            self.start_point = (x, y)
            self.current_point = (x, y)
        elif event == cv2.EVENT_MOUSEMOVE:
            if self.drawing:
                self.current_point = (x, y)
        elif event == cv2.EVENT_LBUTTONUP:
            self.drawing = False
            self.current_point = (x, y)
            
    def _normalize_rect(self, pt1: Tuple[int, int], pt2: Tuple[int, int]) -> Tuple[int, int, int, int]:
        """标准化矩形坐标为(left, top, right, bottom)格式"""
        x1, y1 = pt1
        x2, y2 = pt2
        left = min(x1, x2)
        top = min(y1, y2)
        right = max(x1, x2)
        bottom = max(y1, y2)
        return (left, top, right, bottom)

    def _put_chinese_text(self, img: np.ndarray, text: str, position: Tuple[int, int], 
                          font: ImageFont.FreeTypeFont, color: Tuple[int, int, int] = (0, 255, 0),
                          bg_color: Optional[Tuple[int, int, int]] = None) -> np.ndarray:
        """在图像上绘制中文文本
        
        Args:
            img: 输入图像（numpy数组，BGR格式）
            text: 要显示的文本
            position: 文本位置 (x, y)
            font: PIL字体对象
            color: 文本颜色 (B, G, R)
            bg_color: 背景颜色，None表示无背景
            
        Returns:
            绘制后的图像
        """
        # 转换为PIL图像（RGB格式）
        img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(img_pil)
        
        # 转换颜色从BGR到RGB
        text_color = (color[2], color[1], color[0])
        
        # 如果有背景色，先绘制背景
        if bg_color is not None:
            # 获取文本边界框
            bbox = draw.textbbox(position, text, font=font)
            bg_color_rgb = (bg_color[2], bg_color[1], bg_color[0])
            draw.rectangle(bbox, fill=bg_color_rgb)
        
        # 绘制文本
        draw.text(position, text, font=font, fill=text_color)
        
        # 转换回OpenCV格式（BGR）
        img_cv = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
        return img_cv
    
    def select_region(self, name: str = "region") -> Tuple[int, int, int, int]:
        """选择屏幕区域
        
        Args:
            name: 选框名称，用于标识和保存
            
        Returns:
            (left, top, right, bottom) 格式的坐标元组
        """
        # 截取当前屏幕作为背景
        camera = dxcam.create(device_idx=self.device_idx, output_idx=self.output_idx, output_color="BGR")
        screenshot = camera.grab()
        if screenshot is None:
            raise RuntimeError(f"无法截取屏幕 output_idx={self.output_idx}")
        
        # 创建半透明黑色蒙版
        mask = np.zeros_like(screenshot, dtype=np.uint8)
        mask_alpha = 0.3  # 蒙版透明度（0.3表示70%透明）
        
        # 创建窗口
        window_name = f"区域选择器 - {name}"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        cv2.setMouseCallback(window_name, self._mouse_callback)
        
        # 重置状态
        self.drawing = False
        self.start_point = None
        self.current_point = None
        
        region = None
        
        while True:
            # 混合截图和半透明蒙版
            display = cv2.addWeighted(screenshot, 1, mask, mask_alpha, 0)
            
            # 如果正在绘制或已完成绘制，显示矩形框
            if self.start_point and self.current_point:
                # 绘制矩形框
                cv2.rectangle(display, self.start_point, self.current_point, (0, 255, 0), 2)
                
                # 在选框内部绘制半透明填充以突出显示
                rect = self._normalize_rect(self.start_point, self.current_point)
                overlay = display.copy()
                cv2.rectangle(overlay, (rect[0], rect[1]), (rect[2], rect[3]), (0, 255, 0), -1)
                cv2.addWeighted(overlay, 0.1, display, 0.9, 0, display)
                
                # 显示坐标信息（使用中文字体）
                coord_text = f"({rect[0]}, {rect[1]}) -> ({rect[2]}, {rect[3]})"
                text_x = self.current_point[0] + 10
                text_y = self.current_point[1] - 10
                
                # 确保文本不超出屏幕边界
                if text_x + 300 > self.screen_width:
                    text_x = self.current_point[0] - 310
                if text_y < 40:
                    text_y = self.current_point[1] + 40
                
                # 使用PIL绘制文本（支持中文）
                display = self._put_chinese_text(display, coord_text, (text_x, text_y), 
                                                 self.font, color=(0, 255, 0), bg_color=(0, 0, 0))
            
            # 显示提示信息（使用中文字体）
            help_text = f"选择区域: {name} | ENTER-确认 | ESC-取消"
            display = self._put_chinese_text(display, help_text, (20, 20), 
                                            self.font_large, color=(0, 255, 0), bg_color=(0, 0, 0))
            
            cv2.imshow(window_name, display)
            
            key = cv2.waitKey(1) & 0xFF
            
            # ENTER 确认
            if key == 13:
                if self.start_point and self.current_point:
                    region = self._normalize_rect(self.start_point, self.current_point)
                    self.regions[name] = region
                    print(f"✓ 区域 '{name}' 已保存: {region}")
                    break
                else:
                    print("! 请先框选一个区域")
            
            # ESC 取消
            elif key == 27:
                print("✗ 已取消选择")
                break
        
        cv2.destroyWindow(window_name)
        del camera
        
        if region is None:
            raise ValueError("未选择有效区域")
        
        return region
    
    def select_multiple_regions(self, names: list) -> Dict[str, Tuple[int, int, int, int]]:
        """批量选择多个区域
        
        Args:
            names: 区域名称列表
            
        Returns:
            字典，键为区域名称，值为(left, top, right, bottom)坐标
        """
        results = {}
        for name in names:
            try:
                region = self.select_region(name)
                results[name] = region
            except ValueError:
                print(f"跳过区域 '{name}'")
                continue
        
        return results
    
    def get_region(self, name: str) -> Optional[Tuple[int, int, int, int]]:
        """获取已保存的区域坐标
        
        Args:
            name: 区域名称
            
        Returns:
            (left, top, right, bottom) 坐标，如果不存在则返回None
        """
        return self.regions.get(name)
    
    def get_all_regions(self) -> Dict[str, Tuple[int, int, int, int]]:
        """获取所有已保存的区域
        
        Returns:
            字典，键为区域名称，值为坐标
        """
        return self.regions.copy()
    
    def save_regions_to_file(self, filepath: str):
        """保存区域配置到文件
        
        Args:
            filepath: 文件路径
        """
        import json
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.regions, f, indent=2, ensure_ascii=False)
        print(f"✓ 区域配置已保存到: {filepath}")
    
    def load_regions_from_file(self, filepath: str):
        """从文件加载区域配置
        
        Args:
            filepath: 文件路径
        """
        import json
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # 转换为元组格式
            self.regions = {name: tuple(coords) for name, coords in data.items()}
        print(f"✓ 已从文件加载 {len(self.regions)} 个区域配置")

if __name__ == "__main__":
    # 示例：选择单个区域
    selector = RegionSelector()

    regions = selector.select_multiple_regions(["time", "buy", "verify"])
    print(f"所有区域: {regions}")
    
    # 保存配置
    selector.save_regions_to_file("regions_config.json")
