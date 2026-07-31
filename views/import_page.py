"""导入账单页面 - 移动端友好"""
import streamlit as st
import os
import time
from utils import db, parser, logic

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

SOURCE_OPTIONS = {
    "alipay": "支付宝",
    "wechat": "微信支付",
    "bank": "银行卡",
    "credit": "信用卡",
}


def render():
    st.subheader("📥 导入账单")

    # 来源选择 - 大按钮卡片
    st.markdown("**选择账单来源**")
    source = _source_selector()

    # 文件上传
    uploaded_file = st.file_uploader(
        "选择文件上传",
        type=["csv", "xlsx", "xls"],
        help=f"支持 {SOURCE_OPTIONS.get(source, '')} 的 CSV / Excel 文件",
        label_visibility="visible",
    )

    if uploaded_file is not None:
        # 保存文件
        file_path = os.path.join(UPLOAD_DIR, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        # 解析
        with st.spinner("🔍 正在解析账单..."):
            transactions, message = parser.parse_bill(file_path, source)

        if not transactions:
            st.error(f"❌ {message}")
            return

        st.success(f"✅ {message}")

        # 统计
        expense_count = len([t for t in transactions if t["direction"] == "支出"])
        income_count = len([t for t in transactions if t["direction"] == "收入"])
        neutral_count = len([t for t in transactions if t["direction"] == "中性"])

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("支出", f"{expense_count}笔")
        with col2:
            st.metric("收入", f"{income_count}笔")
        with col3:
            st.metric("其他", f"{neutral_count}笔")

        # 预览
        st.markdown("**📋 解析预览（前20条）**")
        preview_data = []
        for tx in transactions[:20]:
            preview_data.append({
                "时间": tx["tx_time"][:16] if tx["tx_time"] else "-",
                "金额": tx["amount"],
                "方向": tx["direction"],
                "商户": (tx.get("merchant") or tx.get("original_note") or "-")[:15],
                "性质": tx["tx_nature"],
            })
        st.dataframe(preview_data, use_container_width=True, hide_index=True)

        if len(transactions) > 20:
            st.caption(f"仅显示前20条，共{len(transactions)}条")

        # 确认导入
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ 确认导入", type="primary", use_container_width=True):
                batch_id = time.strftime("%Y%m%d%H%M%S")
                for tx in transactions:
                    tx["import_batch"] = batch_id

                count = db.batch_insert(transactions)

                # 导入后检测重复
                with st.spinner("🔍 正在检测重复交易..."):
                    dup_count = logic.detect_duplicates()

                st.success(f"✅ 成功导入 {count} 条！")
                if dup_count > 0:
                    st.warning(f"⚠️ 检测到 {dup_count} 条疑似重复")
                st.balloons()
                st.rerun()

        with col2:
            if st.button("❌ 取消", use_container_width=True):
                st.rerun()

    # 数据库信息
    st.markdown("---")
    all_txs = db.get_all_transactions()
    st.caption(f"📊 当前共 {len(all_txs)} 条交易记录")


def _source_selector() -> str:
    """大按钮来源选择器"""
    if "selected_source" not in st.session_state:
        st.session_state.selected_source = "alipay"

    cols = st.columns(4)
    sources = [("alipay", "💙", "支付宝"), ("wechat", "💚", "微信"),
               ("bank", "🏦", "银行卡"), ("credit", "💳", "信用卡")]

    for i, (key, icon, label) in enumerate(sources):
        with cols[i]:
            is_active = st.session_state.selected_source == key
            btn_type = "primary" if is_active else "secondary"
            if st.button(f"{icon}\n{label}", key=f"src_{key}",
                         type=btn_type, use_container_width=True):
                st.session_state.selected_source = key
                st.rerun()

    return st.session_state.selected_source
