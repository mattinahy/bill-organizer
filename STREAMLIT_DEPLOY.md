# 📱 账单整理工具 - Streamlit Cloud 部署指南（手机操作）

## 一、把代码上传到 GitHub

### 1. 在 GitHub 创建仓库
用手机浏览器打开 https://github.com/new
- Repository name: `bill-organizer`（或你喜欢的名字）
- 选 **Public**
- **不要**勾选 "Add a README file"
- 点 "Create repository"

### 2. 上传文件
创建后会看到上传页面，点 **"uploading an existing file"** 链接。

把以下文件**全部上传**（保持目录结构，可以拖拽整个文件夹）：

```
app.py
requirements.txt
.streamlit/config.toml
utils/ (整个文件夹，共6个.py文件)
views/ (整个文件夹，共6个.py文件)
sample_data/ (可选，测试用的)
```

或者直接用电脑上的代码目录打包上传。

### 3. 确认上传
拖拽所有文件到 GitHub 页面，点 "Commit changes"。

---

## 二、部署到 Streamlit Cloud

### 1. 打开 Streamlit Cloud
手机浏览器打开 https://share.streamlit.io

### 2. 登录
点 "Sign in with GitHub"，授权登录。

### 3. 部署
- 点 "New app"
- Repository 选你刚创建的 `bill-organizer`
- Branch: `main`
- Main file path: `app.py`
- 点 "Deploy!"

等 1-2 分钟，部署完成后会得到一个网址，比如：
```
https://你的用户名-bill-organizer.streamlit.app
```

### 4. 添加到手机桌面
- iPhone: Safari 打开 → 分享按钮 → "添加到主屏幕"
- Android: Chrome 打开 → 菜单 → "添加到主屏幕"

---

## 三、数据说明

- 数据存在 Streamlit 服务器上，其他人无法访问
- 重新部署时数据会丢失（因为从 GitHub 重新拉取代码）
- 建议定期在"报告"页面下载 Excel 备份到手机

