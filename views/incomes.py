"""收入处理页面 - 移动端友好"""
import streamlit as st
from utils import db, logic, sync


def render():
    st.subheader("💵 收入处理")

    # 筛选
    months = db.get_all_months()
    col1, col2 = st.columns(2)
    with col1:
        selected_month = st.selectbox("月份", ["全部"] + months, key="inc_m")
    with col2:
        ownership = st.selectbox("归属", ["全部", "个人", "公司", "待确认"], key="inc_o")

    search = st.text_input("🔍 搜索付款方/备注", key="inc_s", placeholder="输入关键词...")

    month = None if selected_month == "全部" else selected_month
    own = None if ownership == "全部" else ownership

    txs = db.get_transactions_by_filter(
        direction="收入", ownership=own, month=month,
        search=search if search else None
    )

    total = sum(t["amount"] for t in txs)
    personal = sum(t["amount"] for t in txs if t.get("ownership") == "个人")
    company = sum(t["amount"] for t in txs if t.get("ownership") == "公司")
    pending = sum(t["amount"] for t in txs if t.get("ownership") == "待确认")

    # 统计卡片
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("合计", f"¥{total:,.0f}")
    with c2:
        st.metric("个人", f"¥{personal:,.0f}")
    with c3:
        st.metric("公司", f"¥{company:,.0f}")
    with c4:
        st.metric("待确认", f"¥{pending:,.0f}")

    if not txs:
        st.info("无匹配记录")
        return

    st.caption(f"共 **{len(txs)}** 条")

    # 逐条编辑
    for tx in txs:
        _render_income_row(tx)


def _render_income_row(tx: dict):
    """单条收入编辑行"""
    with st.container():
        merchant = tx.get("merchant") or tx.get("original_note") or "-"
        st.markdown(
            f"**¥{tx['amount']:.2f}** `{tx['tx_time'][:16]}` "
            f"`{tx['source']}` {merchant[:25]}"
        )

        col1, col2, col3 = st.columns([1, 1, 1])

        with col1:
            own = st.selectbox(
                "归属", ["个人", "公司", "待确认"],
                index=["个人", "公司", "待确认"].index(tx.get("ownership") or "待确认"),
                key=f"i_o_{tx['id']}", label_visibility="collapsed"
            )

        with col2:
            client = st.text_input(
                "客户", value=tx.get("project_client") or "",
                key=f"i_c_{tx['id']}", label_visibility="collapsed",
                placeholder="客户/来源"
            )

        with col3:
            if st.button("💾 保存", key=f"i_s_{tx['id']}", use_container_width=True):
                db.update_transaction(tx["id"], {
                    "ownership": own,
                    "project_client": client,
                    "confirmed": 1,
                })
                sync.sync_to_github()
                st.success("已保存")
                st.rerun()

        st.markdown("---")
