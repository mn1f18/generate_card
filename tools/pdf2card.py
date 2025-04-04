import cv2
import numpy as np
from pdf2image import convert_from_path
import os
from PIL import Image
from card_extractor import extract_card_from_image  # 导入从单独文件中拆分出的函数

def pdf_to_images(pdf_path, output_folder, dpi=1000):
    """
    将PDF所有页面转换为一张垂直拼接的长图片，并去除页面交界处的白色边框。
    
    参数:
        pdf_path: PDF文件路径
        output_folder: 输出图片文件夹
        dpi: 图片分辨率(默认300)
    
    返回:
        str: 合并后的长图片的文件路径，如果转换失败则返回None。
    """
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    try:
        # 转换PDF为图片列表 (PIL Image objects)
        images = convert_from_path(pdf_path, dpi=dpi)
        
        if not images:
            print("No images were generated from the PDF.")
            return None

        # 处理图像以去除白边
        processed_images = []
        
        # 定义一个函数来检测一行或一列是否为白色（或接近白色）
        def is_white_row(row, threshold=245):
            # 如果行的平均颜色值高于阈值，认为它是白色的
            return np.mean(row) > threshold
        
        for i, img in enumerate(images):
            # 转换为NumPy数组以进行处理
            img_np = np.array(img)
            
            # --- 3x Scaling using Linear Interpolation ---
            scale_factor = 2
            try:
                print(f"Applying {scale_factor}x linear interpolation scaling to page {i+1}...")
                h, w = img_np.shape[:2]
                new_h, new_w = int(h * scale_factor), int(w * scale_factor)
                # Use cv2.resize with linear interpolation
                img_np = cv2.resize(img_np, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
                print(f"Scaling complete for page {i+1}.")
            except Exception as scale_error:
                print(f"\nWarning: Scaling failed for page {i+1} ({scale_error}). Using original resolution.")
            # --- End Scaling ---

            # 找到图像内容的顶部边界（去除顶部白边）
            top_crop = 0
            for y in range(img_np.shape[0]):
                if not is_white_row(img_np[y]):
                    top_crop = y
                    break
            
            # 找到图像内容的底部边界（去除底部白边）
            bottom_crop = img_np.shape[0] - 1
            for y in range(img_np.shape[0] - 1, -1, -1):
                if not is_white_row(img_np[y]):
                    bottom_crop = y
                    break
            
            # 如果是第一个图像，保留顶部的一些空白（通常需要）
            if i == 0:
                top_crop = 0  # 第一页保留顶部边距
            
            # 如果是最后一个图像，保留底部的一些空白
            if i == len(images) - 1:
                cropped_img = img_np[:bottom_crop+1]
            
            # 裁剪图像，保留内容区域
            # 对于中间的页面，如果不是第一页，去除顶部白边；如果不是最后一页，去除底部白边
            if i != 0 and i != len(images) - 1:
                # 中间页裁剪顶部和底部
                cropped_img = img_np[top_crop:bottom_crop+1]
            elif i == 0 and i != len(images) - 1:
                # 第一页只裁剪底部
                cropped_img = img_np[:bottom_crop+1]
            elif i != 0 and i == len(images) - 1:
                # 最后一页只裁剪顶部
                cropped_img = img_np[top_crop:]
            else:
                # 只有一页的情况，不裁剪
                cropped_img = img_np
            
            # 转回PIL图像
            processed_img = Image.fromarray(cropped_img)
            processed_images.append(processed_img)
        
        # 计算处理后图像的总高度和最大宽度
        widths = [img.width for img in processed_images]
        heights = [img.height for img in processed_images]
        max_width = max(widths)
        total_height = sum(heights)
        
        # 创建一个新的空白长图
        combined_image = Image.new('RGB', (max_width, total_height), color='white')
        
        # 拼接图片，无缝连接
        current_y = 0
        for img in processed_images:
            # 确保图片是RGB模式
            if img.mode != 'RGB':
                img = img.convert('RGB')
            combined_image.paste(img, (0, current_y))
            current_y += img.height
        
        # 保存合并后的图片
        pdf_filename = os.path.splitext(os.path.basename(pdf_path))[0]
        combined_image_path = os.path.join(output_folder, f'{pdf_filename}_combined.png')
        combined_image.save(combined_image_path, 'PNG')
        print(f"Combined image with removed borders saved to: {combined_image_path}")
        
        return combined_image_path
        
    except Exception as e:
        print(f"Error converting PDF to combined image: {e}")
        return None

# 使用示例
if __name__ == "__main__":
    # 1. 将PDF转换为图片
    pdf_path = "./output_weasyprint.pdf"
    output_folder = "output_images"
    image_path = pdf_to_images(pdf_path, output_folder, dpi=300)
    
    # 2. 从图片中提取卡片
    if image_path:
        extract_card_from_image(
            image_path, 
            os.path.join(output_folder, 'card.png'),
            min_area=500,  # 根据实际情况调整
            debug=True
        )