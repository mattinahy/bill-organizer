# 📱 账单整理工具（手机版 + Streamlit Cloud 部署）

一个可在手机上使用的本地/云端账单整理网页工具，用于统一整理支付宝、微信、银行卡、信用卡账单，快速区分个人/公司收支。

## ✨ 功能特点

- **手机优化**：大按钮、底部导航、触屏友好、响应式布局
- **多平台导入**：支持支付宝 CSV、微信 Excel、银行卡/信用卡 Excel/CSV
- **个人/公司区分**：每笔交易可标记为个人、公司或待确认
- **公司费用细分**：差旅、原材料、办公、软件订阅等，支持自定义
- **收入分类**：区分个人收款和公司收款，按客户汇总
- **重复识别**：跨平台同一笔消费自动识别疑似重复
- **同商户同步**：标记一笔，同商户待确认交易自动同步
- **报告下载**：月度/年度/公司收款总结，支持 Excel 下载

## 🚀 使用方式

### 方式一：本地运行

```bash
pip install -r requirements.txt
streamlit run app.py
```

浏览器打开：http://localhost:8501

### 方式二：Streamlit Cloud 免费部署（手机随时随地访问）

#### 1. 创建 GitHub 仓库

1. 在 GitHub 创建一个新仓库（例如 `bill-organizer`）
2. 将本项目代码推送到仓库：

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/你的用户名/bill-organizer.git
git push -u origin main
```

#### 2. 部署到 Streamlit Cloud

1. 访问 https://streamlit.io/cloud
2. 用 GitHub 账号登录
3. 点击 "New app"
4. 选择你的仓库、分支 `main`、主文件 `app.py`
5. 点击 "Deploy"

#### 3. 手机访问

部署成功后，你会获得一个网址，例如：

```
https://bill-organizer-你的用户名.streamlit.app
```

手机浏览器打开即可使用，也可以添加到手机桌面（像 App 一样打开）。

## 📱 添加到手机桌面

### iPhone
1. 用 Safari 打开部署后的网址
2. 点击底部分享按钮
3. 选择「添加到主屏幕」

### Android
1. 用 Chrome 打开部署后的网址
2. 点击右上角菜单
3. 选择「添加到主屏幕」

## ⚠️ 数据存储说明

### 本地运行
- 数据保存在本机 `database.db`
- 上传的文件在 `uploads/`
- 报告文件在 `reports/`
- 不上传服务器

### Streamlit Cloud 运行
- 数据保存在 Streamlit Cloud 服务器的应用目录中
- 应用运行期间数据会保留
- **重新部署应用时，数据会丢失**（因为会从 GitHub 重新拉取代码）
- 建议定期在「报告」页面下载 Excel 备份

## 📖 使用流程

1. **导入账单**：手机上传支付宝/微信/银行账单文件
2. **待处理**：快速分类每笔支出（个人/公司/不计入）
3. **支出处理**：更细地编辑支出归属、用途、项目
4. **收入处理**：标记收入为个人/公司，填写客户和说明
5. **报告**：生成月度/年度/公司收款总结，下载 Excel

## 🏗️ 技术栈

- Python + Streamlit（网页界面）
- SQLite（数据库）
- pandas + openpyxl（数据处理和 Excel 导出）

## 📁 主要文件

```
bill-organizer/
├── app.py                  # 主程序
├── requirements.txt        # Python 依赖
├── .streamlit/config.toml  # Streamlit 配置
├── run.command             # macOS 本地启动
├── run_windows.bat         # Windows 本地启动
├── utils/                  # 业务模块
├── views/                  # 页面模块
└── sample_data/            # 测试样本
```

## 💡 提示

- 首次使用建议用 `sample_data/` 里的测试文件熟悉流程
- 公司费用类型可以在「待处理」页面的「公司费用管理」中自定义
- 快捷按钮最多显示 6 个，避免页面太乱
