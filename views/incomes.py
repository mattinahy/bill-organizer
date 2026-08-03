"""收入处理页面 - 移动端友好（顶部待处理快捷区 + 下方已分类列表）"""
import streamlit as st
from utils import db, logic, sync
from utils import merchant_memory


def render():
    st.subheader("💵 收入处理")

    # ── 顶部：待处理快捷区 ──
    _render_pending_quick()

    st.markdown("### 已分类收入")

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


def _render_pending_quick():
    """顶部待处理快捷区：逐条快速分类"""
    pending = logic.get_pending_incomes()
    if not pending:
        return

    with st.container(border=True):
        st.warning(f"⚡ 有 **{len(pending)}** 笔待处理收入")
        tx = pending[0]
        _render_quick_item(tx)


def _render_quick_item(tx: dict):
    """收入待处理快捷卡片"""
    merchant = tx.get("merchant") or tx.get("original_note") or "-"
    tx_id = tx["id"]

    st.markdown(
        f"**¥{tx['amount']:.2f}** `{tx['tx_time'][:16]}` "
        f"`{tx['source']}` {merchant[:30]}"
    )

    edit_state = st.session_state.get("inc_edit")

    if edit_state is not None:
        ownership = edit_state.get("ownership", "")
        st.markdown(f"**分类：** {ownership}收入")

        client = st.text_input(
            "🏢 客户/来源（可留空）",
            value=edit_state.get("default_client", ""),
            key=f"iq_client_{tx_id}",
            placeholder="如：某客户A、XX项目、工资...",
        )
        note = st.text_input(
            "📝 备注（可留空）",
            value=edit_state.get("default_note", ""),
            key=f"iq_note_{tx_id}",
            placeholder="如：7月货款、项目尾款...",
        )

        c1, c2 = st.columns(2)
        with c1:
            if st.button("✅ 确认提交", key=f"iq_ok_{tx_id}", type="primary", use_container_width=True):
                _quick_finalize(tx_id, ownership, client, note)
                st.session_state.pop("inc_edit", None)
                sync.sync_to_github()
                st.rerun()
        with c2:
            if st.button("↩️ 返回重选", key=f"iq_back_{tx_id}", use_container_width=True):
                st.session_state.pop("inc_edit", None)
                st.rerun()

    else:
        if st.button("👤 个人收入", key=f"iq_p_{tx_id}", use_container_width=True):
            _quick_start(tx_id, "个人")
        if st.button("🏢 公司收入", key=f"iq_c_{tx_id}", use_container_width=True):
            _quick_start(tx_id, "公司")
        if st.button("🚫 不计入统计", key=f"iq_ex_{tx_id}", use_container_width=True):
            logic.mark_not_counted(tx_id)
            sync.sync_to_github()
            st.rerun()


def _quick_start(tx_id: int, ownership: str):
    tx = db.get_transaction_by_id(tx_id)
    default_note = ""
    if tx and tx.get("merchant"):
        rule = merchant_memory.get_rule(tx["merchant"])
        if rule and rule.get("ownership") == ownership:
            default_note = rule.get("usage_note", "")
    st.session_state["inc_edit"] = {
        "tx_id": tx_id,
        "ownership": ownership,
        "default_client": "",
        "default_note": default_note,
    }
    st.rerun()


def _quick_finalize(tx_id: int, ownership: str, client: str, note: str):
    fields = {"ownership": ownership, "confirmed": 1}
    fields["project_client"] = client or ""
    fields["usage_note"] = note or ""
    db.update_transaction(tx_id, fields)
    tx = db.get_transaction_by_id(tx_id)
    if tx and tx.get("merchant"):
        merchant_memory.remember(tx["merchant"], ownership, None, note)


def _render_income_row(tx: dict):
    """单条收入编辑行（已分类列表）"""
    with st.container():
        merchant = tx.get("merchant") or tx.get("original_note") or "-"
        note_str = f" 📝{tx['usage_note']}" if tx.get("usage_note") else ""
        client_str = f" 🏢{tx['project_client']}" if tx.get("project_client") else ""
        st.markdown(
            f"**¥{tx['amount']:.2f}** `{tx['tx_time'][:16]}` "
            f"`{tx['source']}` {merchant[:25]}{client_str}{note_str}"
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
