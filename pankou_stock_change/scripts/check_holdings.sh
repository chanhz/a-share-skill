#!/bin/bash
# ======================================================
# 持仓监控启动脚本
# 运行后每3分钟自动检查持仓的卖出信号
# 卖出报警时推送到企业微信群（可选）
# ======================================================
set -e

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PORTFOLIO_FILE="/tmp/a_share_holdings.txt"
DATE=$(date +%Y%m%d)
NOW=$(date +%H:%M)

# Webhook 优先级: 命令行参数 > 环境变量 > 不推送
WEBHOOK="${1:-$WX_WEBHOOK}"

# 创建持仓文件
cat > "$PORTFOLIO_FILE" << EOF
600206 有研新材
600246 万通发展
002463 沪电股份
002484 江海股份
002851 麦格米特
300054 鼎龙股份
EOF

echo "=============================="
echo "  持仓卖出信号监控"
echo "  日期: $DATE"
echo "  启动时间: $NOW"
echo "  检查间隔: 3分钟"
if [ -n "$WEBHOOK" ]; then
  echo "  微信通知: 已开启"
else
  echo "  微信通知: 未设置 (export WX_WEBHOOK=...)"
fi
echo "=============================="
echo ""
echo "【持仓列表】"
cat "$PORTFOLIO_FILE"
echo ""

ARGS="--portfolio $PORTFOLIO_FILE --date $DATE"
if [ -n "$WEBHOOK" ]; then
  ARGS="$ARGS --webhook $WEBHOOK"
fi

# 1. 先做一次当前快照
echo "【初始快照】当前信号状态:"
python3 "$SKILL_DIR/scripts/monitor_portfolio.py" \
  $ARGS \
  --backtest-time "$NOW" 2>/dev/null || true
echo ""

# 2. 启动持续监控（每3分钟）
echo "【实时监控】开始轮询 (Ctrl+C 停止)..."
echo ""
python3 "$SKILL_DIR/scripts/monitor_portfolio.py" \
  $ARGS \
  --interval 180
