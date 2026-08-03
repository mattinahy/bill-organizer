"""支出处理页面 - 移动端友好（顶部待处理快捷区 + 下方已分类列表）"""
import streamlit as st
from utils import db, logic, sync
from utils.config import get_expense_types, get_quick_buttons
from utils import merchant_memory


def render():
    st.subheader("📊 支出处理")

    # ── 顶部：待处理快捷区 ──
    _render_pending_quick()

    st.markdown("### 已分类支出")

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


def _render_pending_quick():
    """顶部待处理快捷区：逐条快速分类"""
    pending = logic.get_pending_expenses()
    if not pending:
        return

    with st.container(border=True):
        st.warning(f"⚡ 有 **{len(pending)}** 笔待处理支出")
        # 只显示第一条
        tx = pending[0]
        _render_quick_item(tx, get_quick_buttons())


def _render_quick_item(tx: dict, quick_buttons: list[str]):
    """待处理快捷卡片"""
    merchant = tx.get("merchant") or tx.get("original_note") or "-"
    tx_id = tx["id"]

    st.markdown(
        f"**¥{tx['amount']:.2f}** `{tx['tx_time'][:16]}` "
        f"`{tx['source']}` {merchant[:30]}"
    )

    # 编辑状态（key 带 eq 前缀，和 pending 页面独立）
    edit_state = st.session_state.get("exp_edit")
    show_custom = st.session_state.get("exp_show_custom", False)

    if show_custom:
        custom_type = st.text_input("分类名称", key="exp_custom_input", placeholder="如：客户招待")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("确认", key=f"eq_cok_{tx_id}", use_container_width=True):
                if custom_type.strip():
                    from utils.config import add_expense_type
                    add_expense_type(custom_type)
                    st.session_state["exp_show_custom"] = False
                    _quick_start(tx_id, "公司", custom_type.strip())
        with c2:
            if st.button("取消", key=f"eq_ccancel_{tx_id}", use_container_width=True):
                st.session_state["exp_show_custom"] = False
                st.rerun()

    elif edit_state is not None:
        ownership = edit_state.get("ownership", "")
        usage_category = edit_state.get("usage_category", "")
        category_display = f"{ownership}" + (f" / {usage_category}" if usage_category else "")
        st.markdown(f"**分类：** {category_display}")

        note = st.text_input(
            "📝 备注（可留空）",
            value=edit_state.get("default_note", ""),
            key=f"eq_note_{tx_id}",
            placeholder="例如：电费、买螺丝...",
        )

        c1, c2 = st.columns(2)
        with c1:
            if st.button("✅ 确认提交", key=f"eq_ok_{tx_id}", type="primary", use_container_width=True):
                _quick_finalize(tx_id, ownership, usage_category, note)
                st.session_state.pop("exp_edit", None)
                sync.sync_to_github()
                st.rerun()
        with c2:
            if st.button("↩️ 返回重选", key=f"eq_back_{tx_id}", use_container_width=True):
                st.session_state.pop("exp_edit", None)
                st.rerun()

    else:
        # 快捷按钮
        if st.button("👤 个人", key=f"eq_p_{tx_id}", use_container_width=True):
            _quick_start(tx_id, "个人", None)
        for btn in quick_buttons[:6]:
            if st.button(f"🏢 {btn}", key=f"eq_qb_{tx_id}_{btn}", use_container_width=True):
                _quick_start(tx_id, "公司", btn)
        cc1, cc2 = st.columns(2)
        with cc1:
            if st.button("✏️ 自定义", key=f"eq_custom_{tx_id}", use_container_width=True):
                st.session_state["exp_show_custom"] = True
                st.session_state.pop("exp_edit", None)
                st.rerun()
        with cc2:
            if st.button("🚫 不计入", key=f"eq_ex_{tx_id}", use_container_width=True):
                logic.mark_not_counted(tx_id)
                sync.sync_to_github()
                st.rerun()


def _quick_start(tx_id: int, ownership: str, usage_category: str):
    tx = db.get_transaction_by_id(tx_id)
    default_note = ""
    if tx and tx.get("merchant"):
        rule = merchant_memory.get_rule(tx["merchant"])
        if rule and rule.get("ownership") == ownership:
            if rule.get("usage_category") == (usage_category or ""):
                default_note = rule.get("usage_note", "")
    st.session_state["exp_edit"] = {
        "tx_id": tx_id,
        "ownership": ownership,
        "usage_category": usage_category,
        "default_note": default_note,
    }
    st.rerun()


def _quick_finalize(tx_id: int, ownership: str, usage_category: str, note: str):
    fields = {"ownership": ownership, "confirmed": 1}
    if usage_category:
        fields["usage_category"] = usage_category
    fields["usage_note"] = note or ""
    db.update_transaction(tx_id, fields)
    tx = db.get_transaction_by_id(tx_id)
    if tx and tx.get("merchant"):
        merchant_memory.remember(tx["merchant"], ownership, usage_category, note)
        if ownership == "公司" and usage_category:
            logic.sync_same_merchant(tx["merchant"], ownership, usage_category)


def _render_expense_row(tx: dict, expense_types: list[str]):
    """单条支出编辑行（已分类列表）"""
    with st.container():
        # 信息行
        merchant = tx.get("merchant") or tx.get("original_note") or "-"
        note_str = f" 📝{tx['usage_note']}" if tx.get("usage_note") else ""
        st.markdown(
            f"**¥{tx['amount']:.2f}** `{tx['tx_time'][:16]}` "
            f"`{tx['source']}` {merchant[:25]}{note_str}"
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
                sync.sync_to_github()
                st.success("已保存")
                st.rerun()

        st.markdown("---")
