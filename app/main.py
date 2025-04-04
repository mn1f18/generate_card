from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from typing import Optional, List
import os
import uuid
import logging
import cv2
import numpy as np
from enum import Enum
# from tools.pdf2card import pdf_to_images, extract_card_from_image
# from tools.html2pdf import html_to_pdf
from tools.selenium2img import html_to_image
from tools.card_extractor import extract_card_from_image
import asyncio
from dotenv import load_dotenv
import requests
# Import functions from llm_prompt.py
from tools.llm_prompt import call_ark_llm, extract_html_from_response
from tools.prompt_config import SYSTEM_PROMPT_WEB_DESIGNER, USER_PROMPT_WEB_DESIGNER, SYSTEM_PROMPT_SUMMARIZE_2MD
from tools.llm_caller import generate_content_with_llm
import os

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file with correct path
env_path = os.path.join(os.path.dirname(__file__), "..", "tools", ".env")
load_dotenv(env_path)

# Jina API Key for web content extraction
JINA_API_URL = "https://r.jina.ai/"
JINA_API_KEY = os.getenv("JINA_API_KEY")

# Log environment variable loading
logger.info(f"Loading environment variables from: {env_path}")
logger.info(f"JINA_API_KEY loaded: {'Yes' if JINA_API_KEY else 'No'}")

app = FastAPI()


# Constants
OUTPUT_DIR = "output"
STATIC_DIR = "static"
TEMPLATES_DIR = "templates"

# Ensure output and static directories exist
os.makedirs(OUTPUT_DIR, exist_ok=True)
app_static_dir = os.path.join(os.path.dirname(__file__), STATIC_DIR)
os.makedirs(app_static_dir, exist_ok=True)
app.mount(f"/{STATIC_DIR}", StaticFiles(directory=app_static_dir), name=STATIC_DIR)

# Setup templates
# Adjust the path to point to the root templates directory, relative to main.py
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "..", TEMPLATES_DIR))

class MarkdownRequest(BaseModel):
    markdown: str
    style: Optional[str] = Field(default="default")
    file_id: Optional[str] = None

class GenerationMode(str, Enum):
    DIRECT = "direct"
    PROMPT = "prompt"
    PASTE = "paste"

class GenerationRequest(BaseModel):
    mode: GenerationMode
    prompt: Optional[str] = None
    template: Optional[str] = None
    html_input: Optional[str] = None
    style: Optional[str] = Field(default="default")
    model: Optional[str] = None
    temperature: Optional[float] = 0.7

class GenerationResponseData(BaseModel):
    """API的数据响应结构，用于返回生成内容的状态和信息"""
    file_id: str
    success: bool
    html_path: Optional[str] = None
    image_path: Optional[str] = None
    card_path: Optional[str] = None
    raw_llm_response: Optional[str] = None
    message: Optional[str] = None

class SummarizeRequest(BaseModel):
    content: str
    model: Optional[str] = None

class SummarizeResponse(BaseModel):
    summary: str
    success: bool
    message: Optional[str] = None

class WebFetchRequest(BaseModel):
    url: str

class WebFetchResponse(BaseModel):
    content: str
    success: bool
    message: Optional[str] = None

class GenerationResponse(BaseModel):
    file_id: str
    html_url: str
    pdf_url: str
    image_url: Optional[str] = None

def generate_html_from_markdown(markdown_content: str, style: str, file_id: str, request: Request):
    """Generates HTML from Markdown content and saves it."""
    # Render Markdown to basic HTML
    basic_html_content = markdown_content
    # Use Jinja2 template to wrap HTML content, include CSS based on style
    full_html = templates.get_template("card_template.html").render(
        {"request": request, "content": basic_html_content, "style": style}
    )
    html_path = os.path.join(OUTPUT_DIR, f"{file_id}.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(full_html)
    logger.info(f"HTML file generated: {html_path}")
    return html_path

async def generate_card(payload: GenerationRequest) -> GenerationResponseData:
    """根据提供的请求负载生成卡片。"""
    # 生成唯一的文件ID
    file_id = str(uuid.uuid4())
    llm_raw_response = ""
    html_path = ""
    
    # 根据生成模式处理
    if payload.mode == GenerationMode.PROMPT:
        # PROMPT模式：首先调用LLM转换Markdown到HTML
        if not payload.prompt:
            raise HTTPException(status_code=400, detail="PROMPT模式需要提供prompt")
        
        logger.info(f"处理PROMPT模式 - file_id: {file_id}")
        
        # 合并用户提示和设计师提示
        combined_prompt = USER_PROMPT_WEB_DESIGNER + payload.prompt
        
        # 保存原始提示到文件
        prompt_path = os.path.join(OUTPUT_DIR, f"{file_id}_prompt.txt")
        with open(prompt_path, "w", encoding="utf-8") as f:
            f.write(payload.prompt)
        
        try:
            # 调用LLM生成内容
            logger.info(f"使用模型 '{payload.model or 'default'}' 调用LLM")
            
            # 使用直接从llm_prompt.py导入的call_ark_llm函数
            model_to_use = payload.model or "deepseek-v3-250324"  # 默认模型
            temperature_to_use = payload.temperature or 0.7       # 默认温度
            
            # 使用同步调用，放到异步线程中执行
            llm_raw_response = await asyncio.to_thread(
                call_ark_llm,
                prompt=combined_prompt,
                model_id=model_to_use,
                temperature=temperature_to_use
            )
            
            # 从LLM响应中提取HTML
            html_content = extract_html_from_response(llm_raw_response)
            
            # 保存提取的HTML到文件
            html_path = os.path.join(OUTPUT_DIR, f"{file_id}.html")
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            logger.info(f"HTML内容已保存到: {html_path}")
            
        except Exception as e:
            logger.error(f"通过LLM生成内容时发生错误: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"LLM调用期间发生内部服务器错误: {str(e)}")

    elif payload.mode == GenerationMode.PASTE:
        # PASTE模式：直接使用请求中提供的HTML内容
        if not payload.html_input:
            raise HTTPException(status_code=400, detail="PASTE模式需要提供HTML输入")
        logger.info(f"处理PASTE模式 - file_id: {file_id}")
        html_path = os.path.join(OUTPUT_DIR, f"{file_id}.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(payload.html_input)
        logger.info(f"HTML文件已直接保存: {html_path}")
    else:
        # 无效的生成模式
        raise HTTPException(status_code=400, detail="无效的生成模式")

    # 直接从HTML生成图像
    image_path = os.path.join(OUTPUT_DIR, f"{file_id}.png")
    card_image_path = os.path.join(OUTPUT_DIR, f"{file_id}_card.png")
    
    # 使用Selenium从HTML生成图像
    logger.info(f"使用Selenium从HTML生成图像: {html_path} -> {image_path}")
    image_success = html_to_image(html_path, image_path, width=1200)
    
    if not image_success:
        logger.error(f"从HTML生成图像失败: {html_path}")
        raise HTTPException(status_code=500, detail="生成图像失败")
    
    # 从生成的图像提取卡片
    logger.info(f"从图像提取卡片: {image_path} -> {card_image_path}")
    card_success = extract_card_from_image(image_path, card_image_path, min_area=500, debug=True)
    
    if not card_success:
        logger.warning(f"卡片提取失败，使用原始图像作为备选: {image_path} -> {card_image_path}")
        # 如果提取失败，使用原始图像作为备用
        import shutil
        shutil.copy(image_path, card_image_path)
    
    # 构造API URL
    html_url = f"/api/download-html/{file_id}"
    image_url = f"/api/download-image/{file_id}"
    
    # 构造响应数据
    response_data = GenerationResponseData(
        file_id=file_id,
        success=True,
        html_path=html_url,
        image_path=image_url,
        card_path=image_url,
        raw_llm_response=llm_raw_response if payload.mode == GenerationMode.PROMPT else None,
        message="卡片生成成功"
    )
    
    return response_data

@app.post("/api/generate")
async def generate_files(payload: GenerationRequest):
    """接收生成请求，根据模式处理，并返回文件URL。"""
    response_data = await generate_card(payload)
    return response_data

@app.get("/")
async def read_root(request: Request):
    """Serves the main HTML page."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/download-html/{file_id}")
async def download_html(file_id: str):
    """Serves the generated HTML file."""
    file_path = os.path.join(OUTPUT_DIR, f"{file_id}.html")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="HTML file not found")
    return FileResponse(file_path, media_type='text/html', filename=f"{file_id}.html")

@app.get("/api/download-image/{file_id}")
async def download_image(file_id: str):
    """Serves the generated card image file."""
    image_path = os.path.join(OUTPUT_DIR, f"{file_id}.png")
    card_image_path = os.path.join(OUTPUT_DIR, f"{file_id}_card.png")
    
    if not os.path.exists(card_image_path):
        logger.warning(f"Card image file {card_image_path} not found. Attempting to regenerate.")
        html_path = os.path.join(OUTPUT_DIR, f"{file_id}.html")
        
        if not os.path.exists(html_path):
            raise HTTPException(status_code=404, detail="HTML file not found, cannot regenerate image")
        
        # Generate image directly from HTML using Selenium
        logger.info(f"Generating image from HTML {html_path} using Selenium")
        if not html_to_image(html_path, image_path, width=1200):
            raise HTTPException(status_code=500, detail="Failed to generate image from HTML")
        
        # Extract card from the generated image
        logger.info(f"Extracting card from {image_path} to {card_image_path}")
        if not extract_card_from_image(image_path, card_image_path, min_area=500, debug=True):
            logger.warning("Card extraction failed, using the full image instead")
            # If extraction fails, use the original image as fallback
            if os.path.exists(image_path):
                import shutil
                shutil.copy(image_path, card_image_path)
            else:
                raise HTTPException(status_code=500, detail="Failed to generate card image")
    
    if not os.path.exists(card_image_path):
        raise HTTPException(status_code=404, detail="Card image file not found")
    
    return FileResponse(card_image_path, media_type='image/png', filename=f"{file_id}_card.png")

@app.post("/api/summarize", response_model=SummarizeResponse)
async def summarize_content(summarize_req: SummarizeRequest):
    """
    接收用户内容并生成智能总结
    """
    try:
        content = summarize_req.content

        if not content:
            return SummarizeResponse(
                summary="",
                success=False,
                message="请提供需要总结的内容"
            )

        # 构造总结提示词
        summarize_prompt = f"""请对以下内容进行简洁明了的总结，突出关键信息，保持语言简练：

{content}

总结：
"""

        # 调用LLM生成总结
        summary = await generate_content_with_llm(
            prompt=summarize_prompt,
            sys_prompt=SYSTEM_PROMPT_SUMMARIZE_2MD,
            model=summarize_req.model,
            temperature=0.5  # 使用较低的温度以获得更一致的总结
        )

        return SummarizeResponse(
            summary=summary.strip(),
            success=True
        )
    except Exception as e:
        logger.error(f"内容总结失败: {str(e)}")
        return SummarizeResponse(
            summary="",
            success=False,
            message=f"总结生成失败: {str(e)}"
        )


@app.post("/api/fetch-web", response_model=WebFetchResponse)
async def fetch_web_content(fetch_req: WebFetchRequest):
    """
    使用Jina服务获取网页内容
    """
    try:
        url = fetch_req.url.strip()

        if not url:
            return WebFetchResponse(
                content="",
                success=False,
                message="请提供有效的URL"
            )

        # 构建Jina API请求
        jina_url = f"{JINA_API_URL}{url}"
        
        # 检查是否成功获取API密钥
        if not JINA_API_KEY:
            logger.error("JINA_API_KEY environment variable not found")
            return WebFetchResponse(
                content="",
                success=False,
                message="Jina API密钥未配置，请检查环境变量"
            )
        
        headers = {'Authorization': f'Bearer {JINA_API_KEY}'}

        logger.info(f"Fetching web content from: {url}")
        
        # 使用requests获取内容
        response = requests.get(jina_url, headers=headers)
        response.raise_for_status()  # 会抛出异常如果请求失败
        
        # 提取网页内容
        content = response.text
        
        return WebFetchResponse(
            content=content,
            success=True
        )
    except Exception as e:
        logger.error(f"获取网页内容失败: {str(e)}")
        return WebFetchResponse(
            content="",
            success=False,
            message=f"获取网页内容失败: {str(e)}"
        )


# --- Main Execution ---
if __name__ == "__main__":
    import uvicorn
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    # Startup warnings moved to llm_caller or can be checked here if needed
    # Check API keys availability using os.getenv again if critical for startup
    if not os.getenv("ARK_API_KEY") and not os.getenv("DEEPSEEK_API_KEY"):
        logger.warning("CRITICAL: Neither ARK_API_KEY nor DEEPSEEK_API_KEY environment variables are set. PROMPT mode WILL fail.")

    uvicorn.run(app, host="0.0.0.0", port=8000)