#!/usr/bin/env bash
set -euo pipefail

# ============================================
# TCM EClinic - 一键环境安装脚本
# 支持: macOS / Linux
# 模式: 本地 PostgreSQL | Docker PostgreSQL | SQLite
# ============================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo -e "${CYAN}============================================"
echo "  中医 EClinic - 环境安装向导"
echo -e "============================================${NC}"
echo ""

# ---- 检测系统 ----
OS="$(uname -s)"
case "$OS" in
    Darwin)  OS_NAME="macOS" ;;
    Linux)   OS_NAME="Linux" ;;
    *)
        echo -e "${RED}不支持的操作系统: $OS${NC}"
        exit 1
        ;;
esac
echo -e "${GREEN}[+] 检测到系统: $OS_NAME${NC}"

# ---- Python 检查 ----
PYTHON=""
for py in python3 python; do
    if command -v $py &>/dev/null && $py -c "import sys; exit(0 if sys.version_info >= (3, 10) else 1)" 2>/dev/null; then
        PYTHON=$py
        break
    fi
done
if [ -z "$PYTHON" ]; then
    echo -e "${RED}[!] 需要 Python 3.10+，未找到${NC}"
    echo "请先安装 Python: https://www.python.org/downloads/"
    exit 1
fi
echo -e "${GREEN}[+] Python: $($PYTHON --version)${NC}"

# ---- 选择数据库后端 ----
echo ""
echo "请选择数据库后端:"
echo "  1) PostgreSQL（Docker 提供，推荐 — 全平台通用）"
echo "  2) PostgreSQL（本地安装，仅 macOS/Linux）"
echo "  3) SQLite（零外部依赖，开发/演示用）"
echo ""
read -rp "请输入选项 [1-3] (默认: 1): " DB_CHOICE
DB_CHOICE="${DB_CHOICE:-1}"

case "$DB_CHOICE" in
    1) DB_MODE="docker" ;;
    2) DB_MODE="local" ;;
    3) DB_MODE="sqlite" ;;
    *) echo -e "${RED}无效选项${NC}"; exit 1 ;;
esac

# ---- 创建虚拟环境 ----
VENV_DIR="$SCRIPT_DIR/venv"
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${GREEN}[+] 创建 Python 虚拟环境...${NC}"
    $PYTHON -m venv "$VENV_DIR"
fi
source "$VENV_DIR/bin/activate"
echo -e "${GREEN}[+] 虚拟环境已激活${NC}"

# ---- 安装 Python 依赖 ----
echo -e "${GREEN}[+] 安装 Python 依赖...${NC}"
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo -e "${GREEN}[+] 依赖安装完成${NC}"

# ---- 生成 .env ----
if [ ! -f "$SCRIPT_DIR/.env" ]; then
    cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
    if [ "$DB_MODE" = "sqlite" ]; then
        $PYTHON -c "
import sys
with open('$SCRIPT_DIR/.env', 'r') as f:
    content = f.read()
content = content.replace('DB_TYPE=postgres', 'DB_TYPE=sqlite')
with open('$SCRIPT_DIR/.env', 'w') as f:
    f.write(content)
"
        echo -e "${GREEN}[+] .env 已生成 (SQLite 模式)${NC}"
    else
        echo -e "${GREEN}[+] .env 已生成 (PostgreSQL 模式)${NC}"
    fi
else
    echo -e "${YELLOW}[i] .env 已存在，跳过${NC}"
fi

# ---- 初始化数据库 ----
case "$DB_MODE" in
    docker)
        echo -e "${GREEN}[+] 启动 PostgreSQL Docker 容器...${NC}"
        if ! command -v docker &>/dev/null; then
            echo -e "${RED}[!] Docker 未安装，请先安装 Docker Desktop${NC}"
            echo "  macOS: https://docs.docker.com/desktop/install/mac-install/"
            echo "  Linux: https://docs.docker.com/engine/install/"
            exit 1
        fi
        if ! docker info &>/dev/null; then
            echo -e "${RED}[!] Docker 守护进程未运行，请启动 Docker Desktop${NC}"
            exit 1
        fi
        docker compose up -d
        echo -e "${GREEN}[+] PostgreSQL 容器已启动 (localhost:5432)${NC}"
        echo -e "${YELLOW}[i] 等待 PostgreSQL 就绪...${NC}"
        sleep 3
        ;;

    local)
        echo -e "${GREEN}[+] 检查本地 PostgreSQL...${NC}"
        if ! command -v psql &>/dev/null; then
            if [ "$OS_NAME" = "macOS" ] && command -v brew &>/dev/null; then
                echo "正在通过 Homebrew 安装 PostgreSQL..."
                brew install postgresql@16
                brew services start postgresql@16
            else
                echo -e "${RED}[!] 未找到 PostgreSQL，请手动安装${NC}"
                exit 1
            fi
        fi
        # 创建数据库和用户
        if pg_isready &>/dev/null; then
            source "$SCRIPT_DIR/.env"
            createuser -s "$PG_USER" 2>/dev/null || true
            createdb "$PG_DATABASE" -O "$PG_USER" 2>/dev/null || true
            psql -U "$PG_USER" -d "$PG_DATABASE" -f "$SCRIPT_DIR/data/schema_postgres.sql" 2>/dev/null || true
            echo -e "${GREEN}[+] PostgreSQL 本地数据库已就绪${NC}"
        else
            echo -e "${RED}[!] PostgreSQL 服务未运行，请手动启动${NC}"
            exit 1
        fi
        ;;

    sqlite)
        echo -e "${GREEN}[+] SQLite 模式 — 无需额外配置${NC}"
        ;;
esac

# ---- 验证 ----
echo ""
echo -e "${GREEN}[+] 验证安装...${NC}"
$PYTHON -c "
import sys; sys.path.insert(0, '.')
from config import *
print(f'  DB_TYPE: {APP_DB_TYPE}')
print(f'  PG_HOST: {PG_HOST}:{PG_PORT}/{PG_DATABASE}')
print(f'  App: {APP_CONFIG[\"app_name\"]} v{APP_CONFIG[\"version\"]}')
" && echo -e "${GREEN}[+] 配置验证通过${NC}"

echo ""
echo -e "${CYAN}============================================"
echo "  安装完成！"
echo "  启动程序:"
echo "    source venv/bin/activate"
echo "    python main.py"
echo -e "============================================${NC}"
echo ""

if [ "$DB_MODE" = "docker" ]; then
    echo -e "${YELLOW}提示: 停止 PostgreSQL 容器:  docker compose down${NC}"
fi
