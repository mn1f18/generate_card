#!/usr/bin/env python
"""
智能卡片工坊环境配置脚本
此脚本可在不同平台上支持快速设置uv环境并安装依赖
"""

import os
import subprocess
import sys
import platform

# 检测操作系统
IS_WINDOWS = platform.system() == "Windows"
VENV_DIR = ".venv"
VENV_BIN = os.path.join(VENV_DIR, "Scripts" if IS_WINDOWS else "bin")
VENV_PYTHON = os.path.join(VENV_BIN, "python")
VENV_UV = os.path.join(VENV_BIN, "uv")

def run_command(cmd, desc=None, check=True):
    """执行命令并输出状态"""
    if desc:
        print(f">>> {desc}...")
    print(f"$ {' '.join(cmd)}")
    result = subprocess.run(cmd, check=check)
    return result.returncode == 0

def check_uv():
    """检查uv是否已安装"""
    try:
        subprocess.run(["uv", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        return True
    except FileNotFoundError:
        return False

def install_deps_with_uv():
    """使用uv安装项目依赖"""
    # 创建虚拟环境
    run_command(["uv", "venv", VENV_DIR], "创建虚拟环境")
    
    # 安装依赖
    uv_pip = [VENV_UV, "pip"]
    run_command(uv_pip + ["install", "-r", "app/requirements.txt"], "安装项目依赖")
    
    # 安装开发依赖（如果存在）
    dev_reqs = "app/requirements-dev.txt"
    if os.path.exists(dev_reqs):
        run_command(uv_pip + ["install", "-r", dev_reqs], "安装开发依赖")
    
    print("\n✅ 环境设置完成!")
    print(f"使用以下命令激活环境:\n"
          f"{'> ' if IS_WINDOWS else '$ '}"
          f"{os.path.join(VENV_DIR, 'Scripts', 'activate') if IS_WINDOWS else f'source {os.path.join(VENV_DIR, 'bin', 'activate')}'}")
    print("然后启动应用:\n"
          f"$ cd app && uvicorn main:app --reload")

def install_with_pip():
    """使用标准pip设置虚拟环境并安装依赖"""
    # 创建虚拟环境
    run_command([sys.executable, "-m", "venv", VENV_DIR], "创建虚拟环境")
    
    # 安装依赖
    pip_cmd = [VENV_PYTHON, "-m", "pip"]
    run_command(pip_cmd + ["install", "--upgrade", "pip"], "升级pip")
    run_command(pip_cmd + ["install", "-r", "app/requirements.txt"], "安装项目依赖")
    
    # 安装开发依赖（如果存在）
    dev_reqs = "app/requirements-dev.txt"
    if os.path.exists(dev_reqs):
        run_command(pip_cmd + ["install", "-r", dev_reqs], "安装开发依赖") 
    
    print("\n✅ 环境设置完成!")
    print(f"使用以下命令激活环境:\n"
          f"{'> ' if IS_WINDOWS else '$ '}"
          f"{os.path.join(VENV_DIR, 'Scripts', 'activate') if IS_WINDOWS else f'source {os.path.join(VENV_DIR, 'bin', 'activate')}'}")
    print("然后启动应用:\n"
          f"$ cd app && uvicorn main:app --reload")

def main():
    """主函数"""
    print("=== 智能卡片工坊环境设置 ===")
    print(f"操作系统: {platform.system()} {platform.release()}")
    print(f"Python版本: {platform.python_version()}")
    
    if check_uv():
        print("检测到uv，将使用uv安装依赖")
        install_deps_with_uv()
    else:
        print("未检测到uv，将使用pip安装依赖")
        print("推荐使用uv以获得更快的依赖安装体验，运行: pip install uv")
        install_with_pip()

if __name__ == "__main__":
    main()
