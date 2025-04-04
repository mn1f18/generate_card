from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import os

def html_to_image_selenium(html_path, output_path):
    """
    使用selenium将HTML转换为图片，并根据内容自动调整尺寸
    
    参数:
        html_path: HTML文件路径或URL
        output_path: 输出图片路径
    """
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(f'file://{os.path.abspath(html_path)}' if html_path.endswith('.html') else html_path)
        
        # 获取内容尺寸，而不是整个body
        width = driver.execute_script("return Math.max(document.documentElement.scrollWidth, document.documentElement.clientWidth);")
        height = driver.execute_script("return Math.max(document.documentElement.scrollHeight, document.documentElement.clientHeight);")
        
        # 分析内容是否需要额外边距
        has_card = driver.execute_script("return document.querySelector('.card') !== null;")
        if has_card:
            # 如果有卡片元素，添加一些额外边距
            width += 40
            height += 40
            
        driver.set_window_size(width, height)
        driver.save_screenshot(output_path)
        print(f"图片已成功保存到 {output_path}，尺寸: {width}x{height}")
    except Exception as e:
        print(f"转换失败: {str(e)}")
    finally:
        if 'driver' in locals():
            driver.quit()

# 使用示例
html_to_image_selenium('./1c6ccb00-f117-4cc0-af04-90b008c2744c.html', 'output_selenium.png')