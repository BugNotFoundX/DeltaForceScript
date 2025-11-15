# DeltaForceScript

## ISSUE的统一回复

- 关于OCR识别的问题
  我屏幕是2k的，可能需要改一下region_2k.json的数值，按照比例换算一下，您可以问问AI：“文件中提供了2k屏幕下的坐标，1k/4k下的对应坐标如何换算”
- 关于requirement.txt安装paddlepaddle-gpu的问题，参考官方链接：https://www.paddlepaddle.org.cn/install/quick?docurl=/documentation/docs/zh/develop/install

## 项目简介

DeltaForceScript 是一个基于 PyQt6 的 Windows 自动购买（抢购）辅助脚本，使用 PaddleOCR 从游戏/应用窗口读取倒计时文本并在指定时间自动点击购买和确认按钮。项目以简单的 GUI 暴露常用配置，让用户无需修改代码即可微调行为。

主要功能：
- 在指定的屏幕区域读取倒计时文本（格式如 `0分1秒`）
- 在倒计时达到触发条件时自动点击购买与确认区域
- 提供 GUI 配置项：购买点击延迟、购买到确认的延迟、点击次数、确认点击间隔、OCR 识别间隔，以及任务完成后是否继续运行
- 支持多屏/Windows Graphics Capture（dxcam）捕获


## 目录结构（主要文件）

- `main_gui.py` - 程序入口，负责初始化 OCR、窗口捕获和启动 GUI
- `gui_monitor.py` - PyQt6 GUI 界面，包含脚本配置与日志
- `region_selector.py` - 交互式屏幕区域选择工具（使用 dxcam + OpenCV）
- `window_capture.py` - 屏幕捕获封装（基于 dxcam）
- `regions_2k.json` - 示例/保存的区域配置
- `models/` - PaddleOCR 模型目录（det & rec 推理文件）
- `requirement.txt` - 依赖列表


## 依赖

请使用 Python 3.10/3.11 及对应的 CUDA 驱动（如需 GPU 版本的 paddlepaddle）。依赖项见 `requirement.txt`：

- dxcam
- numpy
- pywin32
- pillow
- PyQt6
- PyDirectInput
- paddleocr
- paddlepaddle-gpu (如使用 GPU)

在虚拟环境中安装依赖：

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirement.txt
```

如果使用 GPU 的 `paddlepaddle-gpu`，请确保与本机 CUDA 驱动版本匹配（参见 PaddlePaddle 官方安装说明）。


## 快速开始（运行步骤）

1. 准备模型：将 `models/PP-OCRv5_server_det_infer` 和 `models/PP-OCRv5_server_rec_infer` 放在 `models/` 目录下。模型地址：
   https://modelscope.cn/models/PaddlePaddle/PP-OCRv5_server_det
   https://modelscope.cn/models/PaddlePaddle/PP-OCRv5_server_rec

3. 运行程序（管理员权限）：

```powershell
python main_gui.py
```

脚本会尝试以管理员权限重新启动以获取更稳定的鼠标/键盘控制（仅 Windows）。

3. 在 GUI 中：
- 使用 `RegionSelector` 工具（脚本已提供）选择 `time`（倒计时）、`buy`（购买按钮）和 `verify`（确认按钮）区域并保存到 `regions_2k.json`。
- 在 GUI 的“脚本配置”区域调整：
  - 购买点击延迟（购买前等待多少秒）
  - 购买确认间延迟（购买和确认之间的额外等待）
  - 购买点击次数、确认点击次数、确认点击间隔
  - OCR识别间隔（调整识别频率）
  - 任务完成后继续运行（复选框，勾选后脚本完成一次购买后会继续监控）
- 点击“开始”启动脚本，脚本会在日志区域打印运行信息


## 配置说明（关键项）

- buy_click_delay：倒计时到触发点时，等待多少秒再点击购买（GUI 中为“购买点击延迟”）
- buy_to_verify_delay：购买后到点击确认之间的等待
- buy_clicks：购买按钮点击次数
- verify_clicks：确认按钮点击次数
- verify_interval：确认按钮多次点击之间的间隔
- ocr_interval：两次 OCR 识别之间的间隔
- continue_after_complete：任务完成后是否继续监控（复选框）

这些设置可在 GUI 中实时调整，且修改后会记录到日志。


## 区域选择（RegionSelector）

运行 `region_selector.py`（或在 GUI 中触发）以交互方式选择屏幕区域。
选择完成后请保存为 `regions_2k.json`（项目示例文件已包含），示例保存格式为：

```json
{
  "time": [100, 50, 400, 120],
  "buy": [500, 300, 620, 360],
  "verify": [520, 380, 660, 420]
}
```

确保 `time` 区域能完整包含倒计时文本。

## TODO

- [ ] 这段时间有点忙，等12月底看看能不能优化一下性能，试试能不能靠网络抓包来搞（可能不太好搞，就怕他加密）

## 常见问题与故障排查

1. OCR 识别不准确或无识别结果：
   - 检查 `time` 区域是否正确截取（不要包含过多背景）
   - 提高 OCR 识别对比度（可在 `region_selector` 保存截图后手动检查）
   - 增大 `ocr_interval` 或调整识别模型

2. 点击不准确或失败：
   - 确认 `buy` 和 `verify` 区域坐标是否正确
   - 尝试以管理员权限运行（脚本会自动尝试请求管理员权限）
   - 调整 `buy_click_delay` 与 `buy_to_verify_delay`，应对界面响应延迟

3. GPU/模型问题：
   - 若使用 GPU，确保 `paddlepaddle-gpu` 与 CUDA 驱动匹配
   - 若无法加载模型，可尝试使用 CPU 版本 `paddlepaddle`（速度较慢）


## 安全与免责声明

- 本工具仅为自动化辅助工具。请确保在合法和符合相关服务条款的前提下使用。
- 使用脚本可能违反部分平台的使用协议，请自行承担风险。


## 开发与贡献

欢迎提交 issue 或 PR：
- 改进 OCR 容错、区域选择体验
- 增加更多点击策略（随机偏移、重试逻辑等）


# 运行主程序
python main_gui.py
```
