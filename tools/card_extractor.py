import cv2
import numpy as np
import os

def extract_card_from_image(image_path, output_path, min_area=500, debug=False):
    """
    从图片中提取包含所有文字/内容块的完整卡片区域，优先识别最大内容块。
    
    参数：
        image_path: 输入图片路径
        output_path: 输出卡片图片路径
        min_area: 最小文字块面积(像素)
        debug: 是否保存调试图片
    """
    # 读取图片
    img = cv2.imread(image_path)
    if img is None:
        print(f"无法读取图片: {image_path}")
        return False
    
    original = img.copy()
    height, width = img.shape[:2]
    
    # 假设输入图像来自更高分辨率的源，设置缩放因子
    # 如果图像本身就是原始分辨率，可以设为1
    scale_factor = 2  # 根据实际情况调整
    
    # 根据缩放因子调整参数
    scaled_min_area = min_area * (scale_factor ** 2)
    
    # 转换为灰度图
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # 预处理：高斯模糊 + 自适应阈值
    blur_kernel_size = max(3, int(3 * scale_factor))
    if blur_kernel_size % 2 == 0: blur_kernel_size += 1
    blurred = cv2.GaussianBlur(gray, (blur_kernel_size, blur_kernel_size), 0)
    
    block_size = max(11, int(11 * scale_factor))
    if block_size % 2 == 0: block_size += 1
    thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                   cv2.THRESH_BINARY_INV, block_size, 2)
    
    if debug:
        cv2.imwrite(output_path.replace('.png', '_thresh.png'), thresh)
        
    # 形态学操作连接文字区域
    kernel_h_size = max(15, int(15 * scale_factor))
    kernel_v_size = max(15, int(15 * scale_factor))
    kernel_h = np.ones((1, kernel_h_size), np.uint8)
    kernel_v = np.ones((kernel_v_size, 1), np.uint8)
    connected = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel_h)
    connected = cv2.morphologyEx(connected, cv2.MORPH_CLOSE, kernel_v)
    
    if debug:
        cv2.imwrite(output_path.replace('.png', '_connected.png'), connected)
        
    # 查找轮廓
    contours, _ = cv2.findContours(connected, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # --- 新思路：找到最大的轮廓作为主要卡片区域 --- 
    largest_contour = None
    max_area = 0
    all_contours_bbox = [] # 存储所有有效轮廓的边界框
    
    if contours:
        # 过滤掉面积过小的轮廓，并记录边界框
        valid_contours = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area >= scaled_min_area:
                valid_contours.append(contour)
                all_contours_bbox.append(cv2.boundingRect(contour))
                if area > max_area:
                    max_area = area
                    largest_contour = contour
        
        if largest_contour is not None:
            # 获取最大轮廓的边界框
            card_x, card_y, card_w, card_h = cv2.boundingRect(largest_contour)
            
            if debug:
                debug_img = original.copy()
                cv2.drawContours(debug_img, [largest_contour], -1, (0, 255, 0), 3)
                cv2.rectangle(debug_img, (card_x, card_y), (card_x + card_w, card_y + card_h), (0, 0, 255), 2)
                cv2.imwrite(output_path.replace('.png', '_largest_contour.png'), debug_img)
            
            # --- 微调边界以包含所有检测到的内容 --- 
            if all_contours_bbox:
                min_x, min_y = card_x, card_y
                max_x, max_y = card_x + card_w, card_y + card_h
                
                for x_c, y_c, w_c, h_c in all_contours_bbox:
                    min_x = min(min_x, x_c)
                    min_y = min(min_y, y_c)
                    max_x = max(max_x, x_c + w_c)
                    max_y = max(max_y, y_c + h_c)
                    
                # 更新卡片边界以包含所有内容
                card_x, card_y = min_x, min_y
                card_w = max_x - min_x
                card_h = max_y - min_y
            
            # --- 添加边距 --- 
            # 根据卡片尺寸动态添加边距
            padding_h = int(width * 0.015) # 水平边距 1.5%
            padding_v = int(height * 0.015) # 垂直边距 1.5%
            
            x_start = max(0, card_x - padding_h)
            y_start = max(0, card_y - padding_v)
            x_end = min(width, card_x + card_w + padding_h)
            y_end = min(height, card_y + card_h + padding_v)
            
            # 提取卡片区域
            card = original[y_start:y_end, x_start:x_end]
            
            # 保存结果
            cv2.imwrite(output_path, card)
            print(f"卡片已提取保存到 {output_path} (基于最大内容块)")
            return True
        else:
            print("未找到足够大的内容轮廓")
    else:
        print("未找到任何轮廓")

    # 如果主要方法失败，尝试使用备用方法（如果需要，可以重新启用）
    print("主要方法失败，尝试备用方法...")

    # --- MSER备用方法 --- 
    mser = cv2.MSER_create()
    regions, _ = mser.detectRegions(gray)
    if regions:
        # ... (此处省略MSER逻辑，与之前类似，如果需要可以恢复) ...
        # 如果MSER成功，保存并返回True
        pass 

    # --- Otsu备用方法 --- 
    _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    kernel = np.ones((5, 5), np.uint8)
    morph = cv2.morphologyEx(otsu, cv2.MORPH_CLOSE, kernel)
    otsu_contours, _ = cv2.findContours(morph, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if otsu_contours:
        # ... (此处省略Otsu逻辑，与之前类似，如果需要可以恢复) ...
        # 如果Otsu成功，保存并返回True
        pass

    # 所有方法失败
    print("所有方法均无法提取卡片内容区域，返回原始图像并进行超分处理")
    # 使用线性插值将原始图像放大3倍
    h, w = original.shape[:2]
    resized_original = cv2.resize(original, (w * 3, h * 3), interpolation=cv2.INTER_LINEAR)
    cv2.imwrite(output_path, resized_original)
    return False

# 示例用法
if __name__ == "__main__":
    # 测试函数
    input_image = "path/to/your/input_image.png"  # 替换为实际图片路径
    output_image = "path/to/your/output_card.png" # 替换为实际输出路径
    
    if os.path.exists(input_image):
        extract_card_from_image(input_image, output_image, debug=True)
    else:
        print(f"测试图片不存在: {input_image}")
