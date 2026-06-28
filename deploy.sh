#!/bin/bash
# =============================================================================
# AI-Trader Pro — 一键部署脚本
# 在阿里云/Ubuntu服务器上执行: bash deploy.sh
# =============================================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
REPO_URL="https://github.com/1171746190-gif/ai-trader-pro.git"
INSTALL_DIR="/opt/ai-trader-pro"
API_PORT=8000

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                🤖 AI-Trader Pro 一键部署                     ║"
echo "║                                                              ║"
echo "║  支持: Ubuntu 20.04+ / Debian 11+ / CentOS 8+               ║"
echo "║  作者: 1171746190-gif                                        ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# ========== 检查 root 权限 ==========
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}❌ 请使用 root 权限运行: sudo bash deploy.sh${NC}"
    exit 1
fi

# ========== 步骤1: 系统依赖 ==========
echo -e "\n${YELLOW}📦 步骤1/7: 安装系统依赖...${NC}"
apt-get update -qq

if command -v apt-get &> /dev/null; then
    apt-get install -y -qq python3 python3-pip python3-venv git curl nginx sqlite3
elif command -v yum &> /dev/null; then
    yum install -y python3 python3-pip git curl nginx sqlite
fi

# 安装 Node.js 20
curl -fsSL https://deb.nodesource.com/setup_20.x | bash - 2>/dev/null || true
apt-get install -y nodejs 2>/dev/null || true

echo -e "${GREEN}✅ 系统依赖安装完成${NC}"

# ========== 步骤2: 拉取代码 ==========
echo -e "\n${YELLOW}📥 步骤2/7: 拉取项目代码...${NC}"

if [ -d "$INSTALL_DIR" ]; then
    echo -e "${YELLOW}⚠️  目录已存在，正在更新...${NC}"
    cd "$INSTALL_DIR"
    git pull origin main 2>/dev/null || true
else
    git clone "$REPO_URL" "$INSTALL_DIR"
fi

cd "$INSTALL_DIR/service/server"
echo -e "${GREEN}✅ 代码拉取完成: $INSTALL_DIR${NC}"

# ========== 步骤3: Python 环境 ==========
echo -e "\n${YELLOW}🐍 步骤3/7: 配置 Python 环境...${NC}"

python3 -m venv "$INSTALL_DIR/service/venv"
source "$INSTALL_DIR/service/venv/bin/activate"

# 修复 openrouter 版本约束（官方版本号有误）
sed -i 's/openrouter>=1.0.0/openrouter>=0.10.7/' "$INSTALL_DIR/service/requirements.txt" 2>/dev/null || true

pip install -q -r "$INSTALL_DIR/service/requirements.txt"

echo -e "${GREEN}✅ Python 环境配置完成${NC}"

# ========== 步骤4: 环境变量 ==========
echo -e "\n${YELLOW}⚙️  步骤4/7: 配置环境变量...${NC}"

cat > "$INSTALL_DIR/.env" << 'EOF'
# AI-Trader Pro 环境配置
# ======================

# 环境: development | production
ENVIRONMENT=production

# 数据库: 生产环境推荐 PostgreSQL，测试用 SQLite
# DATABASE_URL=postgresql://user:pass@localhost:5432/ai_trader
DATABASE_URL=
DB_PATH=service/server/data/clawtrader.db

# Alpha Vantage API Key（免费获取: https://www.alphavantage.co/support/#api-key）
ALPHA_VANTAGE_API_KEY=demo

# CORS 配置: 你的前端域名（多个用逗号分隔）
CLAWTRADER_CORS_ORIGINS=http://localhost:3000

# Redis 缓存（可选，提升性能）
REDIS_ENABLED=false
REDIS_URL=

# Adanos 情绪分析 API（可选）
ADANOS_API_KEY=

# 后台任务间隔（默认即可）
POSITION_REFRESH_INTERVAL=300
MARKET_NEWS_REFRESH_INTERVAL=900

# 管理员 Agent ID/名称（逗号分隔）
AI_TRADER_ADMIN_AGENTS=

# 启用后台任务
AI_TRADER_BACKGROUND_TASKS=prices,profit_history,settlements,market_intel

# Worker 优先级
AI_TRADER_WORKER_NICE=10
EOF

echo -e "${GREEN}✅ 环境变量配置完成${NC}"
echo -e "${YELLOW}⚠️  请编辑 $INSTALL_DIR/.env 设置你的 ALPHA_VANTAGE_API_KEY${NC}"

# ========== 步骤5: 初始化数据库 ==========
echo -e "\n${YELLOW}🗄️  步骤5/7: 初始化数据库...${NC}"

mkdir -p "$INSTALL_DIR/service/server/data"
cd "$INSTALL_DIR/service/server"

python3 -c "
import sys
sys.path.insert(0, '.')
from database import init_database
init_database()
print('✅ 数据库初始化完成')
" 2>/dev/null || echo -e "${YELLOW}⚠️  数据库将在首次启动时自动初始化${NC}"

# ========== 步骤6: Systemd 服务 ==========
echo -e "\n${YELLOW}🔧 步骤6/7: 创建系统服务...${NC}"

# API 服务
cat > /etc/systemd/system/ai-trader-api.service << EOF
[Unit]
Description=AI-Trader Pro API Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$INSTALL_DIR/service/server
EnvironmentFile=$INSTALL_DIR/.env
ExecStart=$INSTALL_DIR/service/venv/bin/python main.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Worker 服务
cat > /etc/systemd/system/ai-trader-worker.service << EOF
[Unit]
Description=AI-Trader Pro Background Worker
After=ai-trader-api.service

[Service]
Type=simple
User=root
WorkingDirectory=$INSTALL_DIR/service/server
EnvironmentFile=$INSTALL_DIR/.env
ExecStart=$INSTALL_DIR/service/venv/bin/python worker.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable ai-trader-api ai-trader-worker

echo -e "${GREEN}✅ 系统服务创建完成${NC}"

# ========== 步骤7: Nginx 配置 ==========
echo -e "\n${YELLOW}🌐 步骤7/7: 配置 Nginx...${NC}"

# 获取服务器 IP
SERVER_IP=$(curl -s -4 ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')

cat > /etc/nginx/sites-available/ai-trader-pro << EOF
server {
    listen 80;
    server_name $SERVER_IP;

    # API 代理
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 30s;
    }

    # WebSocket 代理
    location /ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
EOF

ln -sf /etc/nginx/sites-available/ai-trader-pro /etc/nginx/sites-enabled/default 2>/dev/null || true
nginx -t && systemctl restart nginx

echo -e "${GREEN}✅ Nginx 配置完成${NC}"

# ========== 启动服务 ==========
echo -e "\n${YELLOW}▶️ 启动服务...${NC}"
systemctl start ai-trader-api
sleep 2
systemctl start ai-trader-worker

# ========== 验证 ==========
sleep 3
HEALTH=$(curl -sf http://localhost:8000/health 2>/dev/null && echo "OK" || echo "FAIL")

echo -e "\n${BLUE}══════════════════════════════════════════════════════════════${NC}"
if [ "$HEALTH" = "OK" ]; then
    echo -e "${GREEN}🎉 AI-Trader Pro 部署成功！${NC}"
    echo -e "${BLUE}══════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "  🌐 访问地址: http://$SERVER_IP"
    echo -e "  📡 API 地址: http://$SERVER_IP:8000"
    echo -e "  📖 API 文档: http://$SERVER_IP:8000/docs"
    echo ""
    echo -e "  📋 常用命令:"
    echo -e "     查看日志: ${YELLOW}journalctl -u ai-trader-api -f${NC}"
    echo -e "     重启API:  ${YELLOW}systemctl restart ai-trader-api${NC}"
    echo -e "     重启Worker: ${YELLOW}systemctl restart ai-trader-worker${NC}"
    echo -e "     查看状态: ${YELLOW}systemctl status ai-trader-api${NC}"
    echo ""
    echo -e "  ⚠️  下一步: 编辑 ${YELLOW}$INSTALL_DIR/.env${NC} 设置 ALPHA_VANTAGE_API_KEY"
    echo -e "     免费获取: https://www.alphavantage.co/support/#api-key"
else
    echo -e "${RED}⚠️  服务启动可能需要几秒，请手动检查:${NC}"
    echo -e "     ${YELLOW}journalctl -u ai-trader-api -n 50${NC}"
fi
echo -e "${BLUE}══════════════════════════════════════════════════════════════${NC}"
