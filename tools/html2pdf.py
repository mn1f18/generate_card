import pdfkit

def html_to_pdf(html_path, output_path, options=None):
    """
    将HTML转换为PDF
    
    参数:
        html_path: HTML文件路径或HTML字符串
        output_path: 输出PDF路径(如'output.pdf')
        options: 可选配置字典
    """
    default_options = {
        'encoding': "UTF-8",
        'quiet': '',
        'enable-local-file-access': None  # 允许访问本地文件
    }
    
    if options:
        default_options.update(options)
    
    try:
        # 判断输入是文件还是HTML字符串
        if html_path.endswith('.html'):
            pdfkit.from_file(html_path, output_path, options=default_options)
        else:
            pdfkit.from_string(html_path, output_path, options=default_options)
            
        print(f"PDF已成功保存到 {output_path}")
    except Exception as e:
        print(f"转换失败: {str(e)}")

# 使用示例
html_to_pdf('./1c6ccb00-f117-4cc0-af04-90b008c2744c.html', 'output_weasyprint.pdf')# 或直接使用HTML字符串
# html_to_pdf('<h1>Hello World</h1>', 'output.pdf')

