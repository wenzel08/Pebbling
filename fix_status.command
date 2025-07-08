#!/bin/bash

# 设置窗口标题
echo -ne "\033]0;Pebbling - 状态修复\007"

# 切换到脚本所在目录
cd "$(dirname "$0")"

echo "🔧 Pebbling 状态修复工具"
echo "=========================="
echo ""

echo "⚠️  警告：此工具将修复状态为空的词条"
echo "📊 根据调试信息，可能有943个词条状态为空"
echo ""

read -p "是否继续修复? (y/n): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🚀 开始修复..."
    python3 fix_empty_status.py
else
    echo "❌ 取消修复"
fi

echo ""
echo "按任意键退出..."
read -n 1 