
# 基于开源的生成事件卡片测试 （仅作为测试使用）

# 智能卡片工坊 (Smart Card Workshop)

一款基于AI的内容转换工具，可以将文本、网页内容或HTML代码转换为精美的卡片图像。


## 功能特点

- **多种输入方式**：
  - 直接输入需求文本，AI自动生成HTML
  - 粘贴已有HTML代码
  - 智能总结长文本内容
  - 抓取并总结网页内容

- **基于AI的内容生成**：
  - 使用先进的大语言模型处理内容
  - 自动提取关键信息生成结构化卡片
  - 支持多种模型选择

- **精美卡片导出**：
  - 生成适合移动设备的HTML卡片
  - 导出为PNG图片格式
  - 实时预览编辑效果

## 技术栈

- **后端**：FastAPI (Python)
- **前端**：Bootstrap 5, JavaScript
- **AI模型**：通过ARK平台接入大语言模型
- **图像处理**：Selenium WebDriver, OpenCV
- **网页抓取**：Jina API

## 安装指南

### 使用uv包管理器安装

[uv](https://github.com/astral-sh/uv) 是一个快速且现代的Python包管理器，推荐使用它来安装项目依赖。

#### 安装uv

```bash
# 使用pip安装uv
pip install uv

# 或者使用pipx安装(推荐)
pipx install uv
```

#### 克隆项目并安装依赖

```bash
# 克隆项目
git clone https://github.com/datawhalechina/smart-card-workshop.git
cd smart-card-workshop

# 创建虚拟环境并安装依赖
uv venv
uv pip install -r app/requirements.txt
```

### 环境变量配置

在`tools`目录下创建一个`.env`文件，添加以下配置：

ARK指的是火山平台，你需要完成两步可以得到你的可用api_key
1. 创建api_key
https://console.volcengine.com/ark/region:ark+cn-beijing/apiKey?apikey=%7B%7D

2. 创建模型推理接入点，记得选择deepseekv3 0324版本
https://console.volcengine.com/ark/region:ark+cn-beijing/endpoint?config=%7B%7D

Jina api需要再下面的网页获取token，如果不用网页获取功能可以随便填一个key哦
https://jina.ai/zh-CN/

```
# ARK平台API密钥
ARK_API_KEY="your_ark_api_key_here"

# Jina API密钥(用于网页抓取)
JINA_API_KEY="your_jina_api_key_here"
```

## 运行应用

```bash
# 激活虚拟环境
# Windows
.venv\Scripts\activate
# Linux/MacOS
source .venv/bin/activate

# 启动应用
uvicorn app.main:app --reload
```

然后在浏览器中访问 `http://localhost:8000` 即可使用应用。

## 使用指南

1. **需求生成**：输入您需要的卡片内容描述，AI将生成相应的HTML卡片
2. **智能总结**：输入长文本，自动提取关键信息并生成摘要
3. **总结网页**：输入网页URL，抓取并总结网页内容
4. **粘贴HTML**：直接粘贴您已有的HTML代码生成卡片

## 系统要求

- Python 3.8+
- Google Chrome浏览器 (用于Selenium渲染)
- 网络连接 (用于API调用)


## 原始开源项目的人员 联系方式  -本项目仅作为测试使用

- 邮箱：bard0wang@foxmail.com
- GitHub Issues：[提交问题](https://github.com/Bald0Wang/Smart_Card_Workshop/issues)
