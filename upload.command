#!/bin/bash

# 切换到脚本所在目录
cd "$(dirname "$0")"

# 快速上传到GitHub
echo "🚀 快速上传到 GitHub..."
git add .
git commit -m "更新Pebbling应用 - $(date '+%Y-%m-%d %H:%M:%S')"
git push origin main
echo "✅ 上传完成！" 