# DeltaForceScript

## 项目简介

DeltaForceScript 是一个基于 PyQt6 的 Windows 抽选参与辅助脚本。S9 购买资格改为随机抽选后，脚本不再围绕极限连点抢购，而是按状态机完成当前已筛选/已选中砖皮的参与流程：读取倒计时、按时刷新、点击参与、确认参与、识别弹窗结果，并用余额变化判断是否真正购买完成。

脚本不负责自动筛选、翻页或按皮肤名挑选；请先在游戏内手动筛选目标砖皮。

主要功能：
- OCR 读取倒计时文本（如 `0分1秒`）
- 剩余 3 秒按配置刷新一次
- 剩余 1 秒后按 `buy_click_delay` 点击参与/购买按钮
- 仅在未检测到确认窗口时有限重试参与按钮
- 点击确认后识别结果弹窗文本
- 余额变化优先判定为购买完成
- 根据弹窗文本区分已参与抽选、未中签、售罄、余额不足、未知结果
- 支持多屏/Windows Graphics Capture（dxcam）捕获

## 依赖

项目使用 `uv` 管理依赖，Python 版本要求见 `pyproject.toml`。如使用 GPU 版本 PaddlePaddle，请确保 CUDA 驱动与 `paddlepaddle-gpu` 版本匹配。

```powershell
uv sync
```

如果 PaddlePaddle GPU 安装失败，请参考官方安装说明：

https://www.paddlepaddle.org.cn/install/quick?docurl=/documentation/docs/zh/develop/install

模型下载地址：

https://modelscope.cn/models/PaddlePaddle/PP-OCRv5_server_det

https://modelscope.cn/models/PaddlePaddle/PP-OCRv5_server_rec

也可以使用网盘版本：

```text
通过网盘分享的文件：PP-OCRv5_for_DeltaForceScript
链接: https://pan.baidu.com/s/1xUiHcZrw-AS85GxltRCC6g?pwd=dn3q 提取码: dn3q
```

## 快速开始

1. 将 OCR 模型放到项目根目录的 `models/` 下：

```text
models/PP-OCRv5_server_det_infer
models/PP-OCRv5_server_rec_infer
```

2. 确认区域配置文件存在。默认入口加载 `regions_2k.json`。

3. 用包入口运行。推荐使用下面任一方式，不要切到 `src/deltaforcescript` 后手动运行内部文件：

```powershell
uv run deltaforce-gui
```

或：

```powershell
uv run python -m deltaforcescript
```

本地开发兼容入口：

```powershell
uv run python scripts/run_gui.py
```

资源路径会自动从项目根目录解析。若需要从其它目录启动，可设置：

```powershell
$env:DELTAFORCESCRIPT_ROOT="D:\proj\DeltaForceScript"
uv run deltaforce-gui
```

4. 在游戏内手动筛选目标砖皮，保持当前目标处于可参与购买流程的位置。

5. 在 GUI 中调整配置并点击“开始”。

## GUI 配置

- `buy_click_delay`：倒计时到 1 秒后，等待多少秒再点击参与/购买按钮
- `buy_to_verify_delay`：参与按钮点击后，到确认参与按钮点击前的额外等待
- `buy_interval`：未检测到确认窗口时，重试参与按钮的间隔
- `verify_interval`：确认参与按钮的点击间隔
- `ocr_interval`：两次 OCR 识别之间的间隔
- `click_refresh_at_3s`：倒计时 3 秒时是否刷新一次
- `continue_after_complete`：遇到已参与抽选、未中签、售罄、余额不足或未知结果后是否继续监控

余额发生变化时会优先判定为 `SUCCESS`，并停止本轮任务。

## 区域配置

区域配置文件是 JSON，坐标格式为 `[left, top, right, bottom]`。

必需字段：
- `time`：倒计时 OCR 区域
- `buy`：参与/购买按钮区域
- `verify`：确认参与按钮区域
- `refresh`：刷新按钮区域
- `money`：余额 OCR 区域
- `verify_check`：确认弹窗颜色校验点附近区域

可选字段：
- `result_text`：弹窗正文 OCR 区域，建议覆盖确认弹窗正文，但不要包含过多背景

示例：

```json
{
  "time": [2095, 1150, 2290, 1176],
  "buy": [1974, 1184, 2372, 1271],
  "verify": [1422, 894, 1820, 970],
  "refresh": [1803, 204, 1860, 260],
  "money": [2304, 52, 2500, 86],
  "verify_check": [740, 493, 783, 536],
  "result_text": [1422, 514, 1820, 894]
}
```

如果旧配置没有 `result_text`，脚本会临时回退到确认按钮上方区域，不会直接崩溃。建议后续用区域选择器重新框选弹窗正文以提高识别准确率。

## 抽选结果判定

内部结果类型：
- `SUCCESS`：购买成功，或余额发生变化
- `JOINED_DRAW`：已参与抽选，余额未变
- `NOT_SELECTED`：未中签/未获得购买资格
- `SOLD_OUT`：售罄/下架/库存不足
- `INSUFFICIENT_FUNDS`：余额不足
- `UNKNOWN`：无法识别或文本未命中关键词

关键词集中维护在 `src/deltaforcescript/runtime_utils.py`，后续小版本只需要调整这里。

## 测试

```powershell
uv run pytest
```

当前测试覆盖倒计时解析、余额数字提取和弹窗文本分类。

## 常见问题

1. OCR 识别不准确：
   - 检查 `time`、`money`、`result_text` 是否只覆盖必要文字
   - 避免 GUI 遮挡游戏内 OCR 区域
   - 根据分辨率调整 `regions_2k.json`、`regions_1k.json` 或 `regions_4k.json`

2. 点击不准确或失败：
   - 确认 `buy`、`verify`、`refresh` 坐标正确
   - 尝试管理员权限运行
   - 调整 `buy_click_delay`、`buy_to_verify_delay`、`buy_interval`

3. 已参与抽选但没有购买完成：
   - 这是随机抽选机制下的正常结果
   - 弹窗识别为 `JOINED_DRAW` 且余额未变时，脚本不会误报购买成功

## 安全与免责声明

本工具仅为自动化辅助工具。请确保在合法并符合相关服务条款的前提下使用；使用脚本可能违反部分平台规则，风险自行承担。
