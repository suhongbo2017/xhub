#!/bin/bash
# 切换到脚本所在目录
cd "$(dirname "$0")"

# 检查虚拟环境（可选，如果你系统默认使用全局环境则注释掉）
# 如果没有虚拟环境，自动创建一个
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# 激活虚拟环境
source venv/bin/activate

# 自动检测并安装缺失的依赖
echo "Checking and installing requirements..."
pip install -r requirements.txt

# 启动 FastAPI 服务，监听 8866 端口
echo "Starting Uvicorn server..."
exec uvicorn server:app --host 0.0.0.0 --port 8866
