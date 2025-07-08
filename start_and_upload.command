#!/bin/bash

# 设置窗口标题
echo -ne "\033]0;Pebbling - 启动与上传\007"

# 切换到脚本所在目录
cd "$(dirname "$0")"

echo "🪨 Pebbling 应用启动与上传工具"
echo "================================"
echo ""

# 显示菜单
echo "请选择操作："
echo "1️⃣ 启动 Pebbling 应用"
echo "2️⃣ 上传到 GitHub"
echo "3️⃣ 启动应用并上传到 GitHub"
echo "4️⃣ 退出"
echo ""

read -p "请输入选择 (1-4): " choice

case $choice in
    1)
        echo "🚀 启动 Pebbling 应用..."
        echo "应用将在浏览器中打开..."
        streamlit run Pebbling.py
        ;;
    2)
        echo "📤 开始上传流程..."
        
        # 检查Git状态
        echo "📊 检查Git状态..."
        git status --porcelain
        
        # 询问用户是否要上传
        echo ""
        read -p "是否要上传到GitHub? (y/n): " -n 1 -r
        echo ""
        
        if [[ $REPLY =~ ^[Yy]$ ]]; then
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
        ;;
    3)
        echo "🚀 启动应用并准备上传..."
        echo "应用将在后台启动..."
        
        # 在后台启动应用
        streamlit run Pebbling.py &
        STREAMLIT_PID=$!
        
        echo "应用已启动 (PID: $STREAMLIT_PID)"
        echo "等待5秒后开始上传流程..."
        sleep 5
        
        # 检查Git状态
        echo "📊 检查Git状态..."
        git status --porcelain
        
        # 询问用户是否要上传
        echo ""
        read -p "是否要上传到GitHub? (y/n): " -n 1 -r
        echo ""
        
        if [[ $REPLY =~ ^[Yy]$ ]]; then
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
        echo "应用仍在运行中..."
        echo "按任意键退出此脚本 (应用将继续运行)..."
        read -n 1
        ;;
    4)
        echo "👋 再见！"
        exit 0
        ;;
    *)
        echo "❌ 无效选择，请重新运行脚本"
        exit 1
        ;;
esac

echo ""
echo "按任意键退出..."
read -n 1 