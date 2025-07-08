#!/bin/bash

# 设置窗口标题
echo -ne "\033]0;Pebbling - 一键上传\007"

# 切换到脚本所在目录
cd "$(dirname "$0")"

echo "🚀 Pebbling 一键上传到 GitHub"
echo "================================"

# 检查Git状态
echo "📊 检查Git状态..."
git status --porcelain

# 询问用户是否要上传
echo ""
read -p "是否要上传到GitHub? (y/n): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "📤 开始上传流程..."
    
    # 添加所有更改
    echo "1️⃣ 添加文件到暂存区..."
    git add .
    
    # 获取提交信息
    echo ""
    read -p "请输入提交信息 (直接回车使用默认信息): " commit_message
    
    if [ -z "$commit_message" ]; then
        commit_message="更新Pebbling应用 - $(date '+%Y-%m-%d %H:%M:%S')"
    fi
    
    # 提交更改
    echo "2️⃣ 提交更改..."
    git commit -m "$commit_message"
    
    # 推送到GitHub
    echo "3️⃣ 推送到GitHub..."
    git push origin main
    
    echo ""
    echo "✅ 上传完成！"
    echo "🔗 GitHub仓库: https://github.com/wenzel08/Pebbling.git"
else
    echo "❌ 取消上传"
fi

echo ""
echo "按任意键退出..."
read -n 1 