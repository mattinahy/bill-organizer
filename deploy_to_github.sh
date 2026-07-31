#!/bin/bash
# 推送到 GitHub 并部署到 Streamlit Cloud 的辅助脚本

set -e

echo "🚀 账单整理工具 - GitHub 部署助手"
echo ""

# 检查 git
if ! command -v git &> /dev/null; then
    echo "❌ 请先安装 git"
    exit 1
fi

# 读取 GitHub 用户名和仓库名
read -p "请输入你的 GitHub 用户名: " GH_USER
read -p "请输入仓库名（例如 bill-organizer）: " REPO_NAME

REMOTE_URL="https://github.com/${GH_USER}/${REPO_NAME}.git"

echo ""
echo "1. 请先在 GitHub 创建空仓库: ${REMOTE_URL}"
echo "   （不要初始化 README、.gitignore 或 license）"
echo ""
read -p "按回车键继续..."

# 重命名分支为 main
git branch -M main

# 添加远程仓库
git remote remove origin 2>/dev/null || true
git remote add origin "${REMOTE_URL}"

# 推送
echo ""
echo "2. 正在推送到 GitHub..."
git push -u origin main

echo ""
echo "✅ 推送完成！"
echo ""
echo "3. 接下来部署到 Streamlit Cloud:"
echo "   1) 访问 https://streamlit.io/cloud"
echo "   2) 用 GitHub 登录"
echo "   3) 点击 'New app'"
echo "   4) 选择仓库: ${GH_USER}/${REPO_NAME}"
echo "   5) 主文件选择: app.py"
echo "   6) 点击 'Deploy'"
echo ""
echo "📱 部署成功后，用手机浏览器打开生成的网址即可使用"
