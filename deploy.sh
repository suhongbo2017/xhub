# ===================================================================
# X HUB - 一键部署脚本
#
# 使用方法：
#   Linux/Mac:  chmod +x deploy.sh && ./deploy.sh
#   Windows:     deploy.bat
#
# 支持三种模式：
#   1. Docker    (推荐，隔离干净)
#   2. Systemd   (Linux 服务器长期运行)
#   3. Python    (开发调试)
# ===================================================================

#!/usr/bin/env bash
set -euo pipefail

# ── 颜色与图标 ──
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'
CHECK="✅"
INFO="ℹ️ "
WARN="⚠️ "
ERROR_PREFIX="❌"

# ── 配置 ──
APP_NAME="xhub"
CONTAINER_PORT=8866
HOST_PORT=${PORT:-$CONTAINER_PORT}
VERSION=$(grep version server.py | grep -oP 'version="\K[^"]+' || echo "latest")

# ── 工具检测 ──
check_docker() {
    if command -v docker &>/dev/null; then
        echo true
    else
        echo false
    fi
}

python_version() {
    python3 --version 2>&1 | grep -oP '\d+\.\d+' | head -1
}

# ── 帮助信息 ──
show_help() {
    cat <<EOF
╔══════════════════════════════════════════════╗
║          X HUB - 一键部署工具 v${VERSION}         ║
╚══════════════════════════════════════════════╝

用法: $0 [选项]

选项:
  mode     部署模式: docker(默认) / systemd / local
  port     宿主机端口: 8866(默认)
  cookie   Cookie 文件路径
  help     显示此帮助信息

示例:
  $0              # Docker 部署（自动）
  $0 mode=docker  # 明确指定 Docker
  $0 mode=local   # 本地 Python 直接运行
  $0 mode=systemd # 安装为系统服务
  $0 port=9000    # 使用自定义端口

EOF
}

# ── 参数解析 ──
DEPLOY_MODE="docker"
COOKIE_FILE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        mode=*) DEPLOY_MODE="${1#*=}"; shift ;;
        port=*) HOST_PORT="${1#*=}"; shift ;;
        cookie=*) COOKIE_FILE="${1#*=}"; shift ;;
        help|-h|--help) show_help; exit 0 ;;
        *) echo "未知参数: $1"; exit 1 ;;
    esac
done

echo ""
echo -e "${CYAN}┌──────────────────────────────────────────────┐${NC}"
echo -e "${CYAN}│   ${GREEN}X HUB Deploy Tool${NC}   v${VERSION}${NC}"
echo -e "${CYAN}│   Mode: ${DEPLOY_MODE}   |   Port: ${HOST_PORT}${NC}"
echo -e "${CYAN}└──────────────────────────────────────────────┘${NC}"
echo ""

# ── Cookie 处理 ──
setup_cookie() {
    local src="$1"
    local dest="./xcookies.txt"

    if [[ -n "$COOKIE_FILE" ]]; then
        cp "$COOKIE_FILE" "$dest"
        echo -e "${GREEN}✓ Cookie from: $COOKIE_FILE → xcookies.txt${NC}"
    elif [[ -f "./xcookies.txt" ]] && [[ -s "./xcookies.txt" ]]; then
        echo -e "${GREEN}✓ Using existing cookie file${NC}"
    else
        echo -e "${YELLOW}⚠ No cookie file found! Downloading from X.com is needed.${NC}"
        echo -e "${YELLOW}   Please add your Twitter cookie to xcookies.txt${NC}"
        read -rp "   Continue anyway? (y/N): " answer
        if [[ ! "$answer" =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

# ── Docker 模式 ──
deploy_docker() {
    if ! $(check_docker); then
        echo -e "${RED}❌ Docker not installed. Install first:${NC}"
        echo -e "${CYAN}   curl -fsSL https://get.docker.com | sh${NC}"
        exit 1
    fi

    setup_cookie "./xcookies.txt"

    echo -e "${INFO} Building Docker image..."
    docker build -t "$APP_NAME:$VERSION" .

    # 清理旧容器
    docker rm -f "$APP_NAME" >/dev/null 2>&1 || true

    echo -e "${INFO} Starting container on port $HOST_PORT..."
    docker run -d \
        --name "$APP_NAME" \
        --restart unless-stopped \
        -p "${HOST_PORT}:${CONTAINER_PORT}" \
        -v "$(pwd)/cookies:/app/cookies:ro" \
        -v "$(pwd)/logs:/app/logs" \
        --memory=1g \
        --cpus=2.0 \
        "$APP_NAME:$VERSION"

    sleep 2

    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}   ${CHECK} X HUB is running!"
    echo -e "${GREEN}   URL: http://localhost:${HOST_PORT}${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${INFO} Logs:    docker logs -f $APP_NAME"
    echo -e "${INFO} Status:  docker ps --filter name=$APP_NAME"
    echo -e "${INFO} Remove:  docker rm -f $APP_NAME && docker rmi $APP_NAME:$VERSION"
}

# ── Local Python 模式 ──
deploy_local() {
    setup_cookie "./xcookies.txt"

    # 创建虚拟环境
    if [[ ! -d "venv" ]]; then
        echo -e "${INFO} Creating virtual environment..."
        python3 -m venv venv
    fi

    source venv/bin/activate 2>/dev/null || source venv/Scripts/activate

    # 预装依赖并缓存
    echo -e "${INFO} Installing dependencies..."
    pip install --upgrade pip >/dev/null 2>&1
    pip install -r requirements.txt --quiet

    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}   ${CHECK} Start with:${NC}"
    echo -e "${GREEN}   uvicorn server:app --host 0.0.0.0 --port $HOST_PORT${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${INFO} Activated: venv"
    echo -e "${INFO} Run:       source venv/bin/activate && uvicorn server:app --host 0.0.0.0 --port $HOST_PORT"
}

# ── Systemd 服务模式 ──
deploy_systemd() {
    sudo apt-get update
    sudo apt-get install -y python3-pip python3-venv ffmpeg

    setup_cookie "./xcookies.txt"

    # 生成 systemd unit 文件
    cat > /tmp/xhub.service <<EOF
[Unit]
Description=X Hub Video Downloader
After=network.target

[Service]
Type=simple
WorkingDirectory=$(pwd)
ExecStart=$(which python3) server.py
Restart=always
RestartSec=5
Environment="PATH=/usr/bin:/usr/local/bin"
Environment="PYTHONDONTWRITEBYTECODE=1"
User=$USER

[Install]
WantedBy=multi-user.target
EOF

    sudo cp /tmp/xhub.service /etc/systemd/system/xhub.service
    sudo systemctl daemon-reload
    sudo systemctl enable xhub.service
    sudo systemctl start xhub.service

    echo ""
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}   ${CHECK} Service installed & started!"
    echo -e "${GREEN}   SystemD will auto-restart on crash${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${INFO} Status:  sudo systemctl status xhub"
    echo -e "${INFO} Logs:    journalctl -u xhub -f"
    echo -e "${INFO} Stop:    sudo systemctl stop xhub"
}

# ── 主入口 ──
case "$DEPLOY_MODE" in
    docker)   deploy_docker   ;;
    local|dev) deploy_local   ;;
    systemd)  deploy_systemd  ;;
    *)
        echo -e "${RED}Unknown mode: $DEPLOY_MODE${NC}"
        show_help
        exit 1
        ;;
esac
