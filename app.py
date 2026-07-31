"""账单整理工具 - 主应用（移动端适配版，link_button底部导航）"""
import streamlit as st
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import db

# ─── 全局 CSS（移动端优先） ───
MOBILE_CSS = """
<style>
/* 基础：移动端优先，大按钮大字体 */
.stApp { margin: 0; padding: 0; }
.main .block-container { padding: 0.5rem 0.75rem 5rem 0.75rem !important; max-width: 100% !important; }

/* 顶部标题栏 */
.app-header {
    position: sticky; top: 0; z-index: 100;
    background: linear-gradient(135deg, #2563eb, #1d4ed8);
    color: white; padding: 0.75rem 1rem;
    display: flex; align-items: center; justify-content: space-between;
    border-radius: 0 0 16px 16px; margin: -0.5rem -0.75rem 0.75rem -0.75rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
}
.app-header .title { font-size: 1.15rem; font-weight: 700; }
.app-header .subtitle { font-size: 0.75rem; opacity: 0.85; }

/* 底部导航栏容器 */
.bottom-nav {
    position: fixed; bottom: 0; left: 0; right: 0; z-index: 1000;
    background: #fff; border-top: 1px solid #e5e7eb;
    box-shadow: 0 -2px 10px rgba(0,0,0,0.08);
    padding: 0.3rem 0.5rem 0.6rem 0.5rem;
}
.bottom-nav .nav-row { display: flex; justify-content: space-around; }
.bottom-nav a, .bottom-nav button {
    display: flex; flex-direction: column; align-items: center;
    text-decoration: none; color: #9ca3af; font-size: 0.65rem;
    padding: 0.2rem 0.4rem; border-radius: 8px; min-width: 48px;
    background: none; border: none; cursor: pointer;
}
.bottom-nav .icon { font-size: 1.3rem; margin-bottom: 1px; }
.bottom-nav .active { color: #2563eb; font-weight: 600; background: #eff6ff; }

/* 隐藏 Streamlit 默认元素 */
#MainMenu { display: none !important; }
footer { display: none !important; }
header[data-testid="stHeader"] { display: none !important; }
.stDeployButton { display: none !important; }
[data-testid="stSidebar"] { display: none !important; }
[data-testid="stSidebarCollapsedControl"] { display: none !important; }
.stApp > header { display: none !important; }
section[data-testid="stSidebar"] { width: 0px !important; min-width: 0px !important; }
div[data-testid="stSidebarContent"] { display: none !important; }

/* 表格优化 */
[data-testid="stDataFrame"] { font-size: 0.8rem !important; }
[data-testid="stDataFrame"] th { font-size: 0.75rem !important; padding: 0.4rem !important; }
[data-testid="stDataFrame"] td { padding: 0.35rem !important; }

/* 上传区域 */
[data-testid="stFileUploader"] section { padding: 1rem !important; }
[data-testid="stFileUploader"] button { font-size: 0.95rem !important; padding: 0.5rem 1rem !important; }

/* 表单元素更大 */
.stSelectbox [data-baseweb="select"], .stTextInput input {
    font-size: 0.95rem !important; padding: 0.5rem !important;
}

/* 修复 link_button 在底部导航的样式 */
[data-testid="stPageLink-NavLink"] p { font-size: 0.65rem !important; }
</style>
"""


def inject_css():
    st.markdown(MOBILE_CSS, unsafe_allow_html=True)


# ─── 页面函数 ───
def show_home():
    from views import home as home_view
    home_view.render()


def show_import():
    from views import import_page as imp
    imp.render()


def show_pending():
    from views import pending as pending_view
    pending_view.render()


def show_expenses():
    from views import expenses as exp
    exp.render()


def show_incomes():
    from views import incomes as inc
    inc.render()


def show_reports():
    from views import reports as rep
    rep.render()


PAGES = {
    "home": ("🏠 首页", "🏠", show_home),
    "import": ("📥 导入", "📥", show_import),
    "pending": ("⚡ 待处理", "⚡", show_pending),
    "expenses": ("📊 支出", "📊", show_expenses),
    "incomes": ("💵 收入", "💵", show_incomes),
    "reports": ("📈 报告", "📈", show_reports),
}


def get_current_page() -> str:
    """从 URL 参数获取当前页面"""
    params = st.query_params
    p = params.get("p", ["home"])
    if isinstance(p, list):
        p = p[0]
    return p if p in PAGES else "home"


def render_page(page_key: str):
    """渲染当前页面"""
    _, _, render_func = PAGES.get(page_key, PAGES["home"])
    render_func()


def render_bottom_nav(current_key: str):
    """渲染底部标签栏 - 使用 st.link_button 实现可靠跳转"""
    st.markdown('<div class="bottom-nav"><div class="nav-row">', unsafe_allow_html=True)

    cols = st.columns(len(PAGES))
    for i, (key, (label, icon, _)) in enumerate(PAGES.items()):
        with cols[i]:
            short_label = label.split(" ")[1] if " " in label else label
            is_active = current_key == key
            btn_label = f"{icon}\n{short_label}"
            # 构造完整 URL（保留其他参数）
            params = st.query_params.to_dict()
            params["p"] = key
            url = "?" + "&".join([f"{k}={v}" for k, v in params.items()])
            st.link_button(
                btn_label,
                url=url,
                type="primary" if is_active else "secondary",
                use_container_width=True,
            )

    st.markdown('</div></div>', unsafe_allow_html=True)


def main():
    # 初始化数据库
    db.init_db()

    st.set_page_config(
        page_title="账单整理",
        page_icon="💰",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    inject_css()

    current_key = get_current_page()

    # 顶部标题栏
    st.markdown("""
    <div class="app-header">
        <div>
            <div class="title">💰 账单整理</div>
            <div class="subtitle">个人 · 公司 收支一目了然</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 页面内容
    render_page(current_key)

    # 底部导航
    render_bottom_nav(current_key)


main()
