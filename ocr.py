# -*- coding: utf-8 -*-
# @Author: BugNotFound
# @Date: 2025-10-02 15:20:05
# @LastEditTime: 2025-10-02 15:21:55
# @FilePath: /DeltaForceScript/ocr.py
# @Description: 

from paddleocr import PaddleOCR
# 初始化 PaddleOCR 实例
ocr = PaddleOCR(
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    use_textline_orientation=False)

# 对示例图像执行 OCR 推理
def ocr_image(image_path):
    result = ocr.predict(input=image_path)
    return result

if __name__ == "__main__":
    image_path = "screenshot.png"  # 替换为你的图像路径
    ocr_result = ocr_image(image_path)
    for line in ocr_result:
        print(line)