#!/bin/bash
# macOS 双击启动文件
# 双击此文件即可启动账单整理工具

cd "$(dirname "$0")"

echo "========================================="
echo "  账单整理工具 启动中..."
echo "========================================="
echo ""

# 检查 Python3
if ! command -v python3 &> /dev/null; then
    echo "❌ 未检测到 Python3，请先安装 Python 3"
    echo "   下载地址: https://www.python.org/downloads/"
    echo ""
    echo "按回车键退出..."
    read
    exit 1
fi

echo "✅ 检测到 Python3: $(python3 --version)"
echo ""

# 安装依赖
echo "📦 正在检查/安装依赖..."
pip3 install -r requirements.txt -q

echo ""
echo "🌐 正在启动网页服务..."
echo "   请在浏览器中打开: http://localhost:8501"
echo ""
echo "   关闭此窗口将停止服务"
echo "========================================="
echo ""

streamlit run app.py
