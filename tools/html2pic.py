import imgkit

def html_to_image(html_path, output_path, options=None):
    """
    将HTML文件转换为图片
    
    参数:
        html_path: HTML文件路径或HTML字符串
        output_path: 输出图片路径(如'output.png')
        options: 可选配置字典
    """
    default_options = {
        'encoding': "UTF-8",
        'enable-local-file-access': None,
        'custom-header': [
            ('Accept-Language', 'zh-CN,zh;q=0.9')
        ],
        'quiet': None, 
        'quality':100,
        'disable-smart-width': None, 
        'width': 500, 
        'minimum-font-size': 16,  
        'zoom': 100,  
    }
    
    if options:
        default_options.update(options)
    
    try:
        imgkit.from_file(html_path, output_path, options=default_options)
        print(f"图片已成功保存到 {output_path}，已优化中文字体和图像清晰度")
    except Exception as e:
        print(f"转换失败: {str(e)}")

# 使用示例
html_to_image('./1c6ccb00-f117-4cc0-af04-90b008c2744c.html', 'output.png')