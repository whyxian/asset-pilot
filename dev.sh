#!/usr/bin/env bash
# dev.sh — 一键启动前后端开发服务器
#
# 用法：
#   ./dev.sh              # 启动前端 + 后端
#   ./dev.sh --backend    # 只启动后端
#   ./dev.sh --frontend   # 只启动前端
#
# 后端：uvicorn (http://localhost:8000)
# 前端：Vite dev server (http://localhost:5173，自动代理 /api → :8000)

set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND_CMD=".venv/bin/uvicorn app.main:app --reload --app-dir backend/app"
FRONTEND_CMD="npm --prefix frontend run dev"

# 颜色输出
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[0;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[dev]${NC} $*"; }
info() { echo -e "${CYAN}[dev]${NC} $*"; }

# 清理子进程
BACKEND_PID=""
FRONTEND_PID=""
cleanup() {
    info "正在停止服务..."
    [ -n "$BACKEND_PID" ]  && kill "$BACKEND_PID"  2>/dev/null && log "后端已停止"
    [ -n "$FRONTEND_PID" ] && kill "$FRONTEND_PID" 2>/dev/null && log "前端已停止"
    wait 2>/dev/null
    exit 0
}
trap cleanup SIGINT SIGTERM

MODE="all"
if [ "${1:-}" = "--backend" ];  then MODE="backend";  fi
if [ "${1:-}" = "--frontend" ]; then MODE="frontend"; fi

# ── 后端 ──
start_backend() {
    if ! [ -f .venv/bin/uvicorn ]; then
        echo -e "${YELLOW}错误: 找不到 .venv/bin/uvicorn，请先运行:${NC}"
        echo "  uv venv && source .venv/bin/activate && uv pip install -e backend"
        exit 1
    fi
    log "启动后端 → http://localhost:8000"
    $BACKEND_CMD &
    BACKEND_PID=$!
}

# ── 前端 ──
start_frontend() {
    if ! [ -d frontend/node_modules ]; then
        echo -e "${YELLOW}提示: 前端依赖未安装，正在安装...${NC}"
        npm --prefix frontend install
    fi
    log "启动前端 → http://localhost:5173"
    $FRONTEND_CMD &
    FRONTEND_PID=$!
}

# ── 启动 ──
case "$MODE" in
    backend)  start_backend  ;;
    frontend) start_frontend ;;
    all)
        start_backend
        start_frontend
        echo ""
        log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        log "  后端  http://localhost:8000"
        log "  前端  http://localhost:5173"
        log "  按 Ctrl+C 停止全部服务"
        log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""
        ;;
esac

wait
