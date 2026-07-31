"""支出处理页面 - 移动端友好"""
import streamlit as st
from utils import db, logic
from utils.config import get_expense_types


def render():
    st.subheader("📊 支出处理")

    # 筛选
    months = db.get_all_months()

    col1, col2 = st.columns(2)
    with col1:
        selected_month = st.selectbox("月份", ["全部"] + months, key="exp_m")
    with col2:
        ownership = st.selectbox("归属", ["全部", "个人", "公司", "待确认", "不计入统计"], key="exp_o")

    # 搜索
    search = st.text_input("🔍 搜索商户/备注", key="exp_s", placeholder="输入关键词...")

    # 构建查询
    month = None if selected_month == "全部" else selected_month
    own = None if ownership == "全部" else ownership

    txs = db.get_transactions_by_filter(
        direction="支出", ownership=own, month=month,
        search=search if search else None
    )

    total = sum(t["amount"] for t in txs)
    st.caption(f"共 **{len(txs)}** 条 · 合计 **¥{total:,.2f}**")

    if not txs:
        st.info("无匹配记录")
        return

    expense_types = get_expense_types()

    for tx in txs:
        _render_expense_row(tx, expense_types)


def _render_expense_row(tx: dict, expense_types: list[str]):
    """单条支出编辑行"""
    with st.container():
        # 信息行
        merchant = tx.get("merchant") or tx.get("original_note") or "-"
        st.markdown(
            f"**¥{tx['amount']:.2f}** `{tx['tx_time'][:16]}` "
            f"`{tx['source']}` {merchant[:25]}"
        )

        col1, col2, col3 = st.columns([1, 1, 1])

        with col1:
            own = st.selectbox(
                "归属", ["个人", "公司", "待确认", "不计入统计"],
                index=["个人", "公司", "待确认", "不计入统计"].index(tx.get("ownership") or "待确认"),
                key=f"e_o_{tx['id']}", label_visibility="collapsed"
            )

        with col2:
            cur = tx.get("usage_category") or "其他"
            idx = expense_types.index(cur) if cur in expense_types else 0
            usage = st.selectbox(
                "用途", expense_types,
                index=idx, key=f"e_u_{tx['id']}", label_visibility="collapsed"
            )

        with col3:
            if st.button("💾 保存", key=f"e_s_{tx['id']}", use_container_width=True):
                fields = {"ownership": own, "usage_category": usage, "confirmed": 1}
                if own == "不计入统计":
                    fields["tx_nature"] = "不计入统计"
                elif tx.get("tx_nature") == "不计入统计":
                    fields["tx_nature"] = "消费"

                db.update_transaction(tx["id"], fields)
                if own == "公司" and tx.get("merchant"):
                    logic.sync_same_merchant(tx["merchant"], "公司", usage)
                st.success("已保存")
                st.rerun()

        st.markdown("---")
