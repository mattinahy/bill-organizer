"""待处理页面 - 移动端友好"""
import streamlit as st
from utils import db, logic, sync
from utils.config import get_expense_types, get_quick_buttons, add_expense_type, delete_expense_type, set_quick_buttons
from utils import merchant_memory


def render():
    st.subheader("⚡ 待处理")

    # 费用类型管理（折叠）
    with st.expander("⚙️ 公司费用管理", expanded=False):
        _render_type_manager()

    # Tab
    tab1, tab2 = st.tabs(["📝 待处理支出", "🔄 疑似重复"])

    with tab1:
        _render_pending_expenses()

    with tab2:
        _render_pending_duplicates()

    # 处理备注弹窗状态
    _handle_note_dialog()


def _render_type_manager():
    expense_types = get_expense_types()
    quick_buttons = get_quick_buttons()

    # 新增
    col1, col2 = st.columns([3, 1])
    with col1:
        new_type = st.text_input("新费用类型", key="new_type", placeholder="如：加工费")
    with col2:
        if st.button("➕ 新增", use_container_width=True):
            if new_type.strip():
                if add_expense_type(new_type):
                    st.success(f"已新增: {new_type}")
                    st.rerun()
                else:
                    st.warning("已存在")
            else:
                st.warning("请输入名称")

    # 删除
    if expense_types:
        del_type = st.selectbox("删除类型", expense_types, key="del_type")
        if st.button("🗑️ 删除", key="btn_del"):
            delete_expense_type(del_type)
            st.success(f"已删除: {del_type}")
            st.rerun()

    # 快捷按钮
    st.caption("快捷按钮（最多6个）")
    selected = st.multiselect(
        "选择", expense_types, default=quick_buttons,
        max_selections=6, label_visibility="collapsed"
    )
    if st.button("💾 保存设置"):
        set_quick_buttons(selected)
        st.success("已保存")
        st.rerun()


def _handle_note_dialog():
    """处理备注弹窗"""
    note_state = st.session_state.get("note_dialog")
    if not note_state:
        return

    tx_id = note_state["tx_id"]
    ownership = note_state["ownership"]
    usage_category = note_state["usage_category"]

    tx = db.get_transaction_by_id(tx_id)
    if not tx:
        st.session_state.pop("note_dialog", None)
        return

    st.markdown("---")
    st.markdown(f"#### 📝 添加备注")
    st.caption(f"交易：{tx.get('merchant') or tx.get('original_note') or '-'} ¥{tx['amount']:.2f}")
    st.caption(f"分类：{ownership}" + (f" / {usage_category}" if usage_category else ""))

    note = st.text_area("备注说明", key="note_input", placeholder="例如：7月团建、客户A货款...",
                        value=st.session_state.get("note_default", ""))

    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 保存", key="note_save", type="primary", use_container_width=True):
            _finalize_classify(tx_id, ownership, usage_category, note)
            st.session_state.pop("note_dialog", None)
            st.session_state.pop("note_default", None)
            sync.sync_to_github()
            st.rerun()
    with col2:
        if st.button("取消", key="note_cancel", use_container_width=True):
            st.session_state.pop("note_dialog", None)
            st.session_state.pop("note_default", None)
            st.rerun()


def _finalize_classify(tx_id: int, ownership: str, usage_category: str, note: str):
    """最终保存分类和备注"""
    fields = {"ownership": ownership, "confirmed": 1}
    if usage_category:
        fields["usage_category"] = usage_category
    if note:
        fields["usage_note"] = note

    db.update_transaction(tx_id, fields)

    tx = db.get_transaction_by_id(tx_id)
    if tx and tx.get("merchant") and ownership == "公司" and usage_category:
        # 记住商户分类
        merchant_memory.remember(tx["merchant"], ownership, usage_category, note)
        # 同步同商户
        logic.sync_same_merchant(tx["merchant"], ownership, usage_category)


def _render_pending_expenses():
    pending = logic.get_pending_expenses()

    if not pending:
        st.success("✅ 全部已分类完成！")
        return

    total_amount = sum(t["amount"] for t in pending)
    st.info(f"**{len(pending)}** 笔待处理 · 合计 ¥{total_amount:,.2f}")

    quick_buttons = get_quick_buttons()

    # 自动应用商户记忆
    auto_applied = 0
    for tx in pending:
        merchant = tx.get("merchant")
        if merchant and tx.get("ownership") == "待确认":
            rule = merchant_memory.auto_classify(merchant)
            if rule:
                db.update_transaction(tx["id"], {
                    "ownership": rule["ownership"],
                    "usage_category": rule["usage_category"] or None,
                    "usage_note": rule["usage_note"] or None,
                    "confirmed": 1,
                })
                auto_applied += 1

    if auto_applied > 0:
        sync.sync_to_github()
        st.success(f"🧠 已自动记忆分类 {auto_applied} 笔")
        st.rerun()

    for tx in pending:
        _render_pending_item(tx, quick_buttons)


def _render_pending_item(tx: dict, quick_buttons: list[str]):
    """单条待处理卡片"""
    emoji = {"个人": "👤", "公司": "🏢", "待确认": "❓"}.get(tx.get("ownership"), "❓")
    merchant = tx.get("merchant") or tx.get("original_note") or "-"

    with st.container():
        # 信息行
        st.markdown(
            f"**¥{tx['amount']:.2f}** `{tx['tx_time'][:16]}` {emoji} "
            f"`{tx['source']}`"
        )
        st.caption(f"📌 {merchant[:40]}")
        if tx.get("usage_category"):
            st.caption(f"当前: {tx['usage_category']}")

        # 个人按钮
        if st.button("👤 个人", key=f"p_{tx['id']}", use_container_width=True):
            _open_note_dialog(tx["id"], "个人", None)

        # 快捷公司分类按钮
        for btn in quick_buttons[:6]:
            if st.button(f"🏢 {btn}", key=f"qb_{tx['id']}_{btn}", use_container_width=True):
                _open_note_dialog(tx["id"], "公司", btn)

        # 自定义分类
        if st.button("✏️ 自定义分类", key=f"custom_{tx['id']}", use_container_width=True):
            st.session_state[f"show_custom_{tx['id']}"] = True
            st.rerun()

        if st.session_state.get(f"show_custom_{tx['id']}", False):
            custom_type = st.text_input("分类名称", key=f"custom_type_{tx['id']}", placeholder="如：客户招待")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("确认", key=f"custom_ok_{tx['id']}"):
                    if custom_type.strip():
                        add_expense_type(custom_type)
                        _open_note_dialog(tx["id"], "公司", custom_type.strip())
            with col2:
                if st.button("取消", key=f"custom_cancel_{tx['id']}"):
                    st.session_state[f"show_custom_{tx['id']}"] = False
                    st.rerun()

        # 不计入按钮
        if st.button("🚫 不计入统计", key=f"ex_{tx['id']}", use_container_width=True):
            logic.mark_not_counted(tx["id"])
            sync.sync_to_github()
            st.rerun()

        st.markdown("---")


def _open_note_dialog(tx_id: int, ownership: str, usage_category: str):
    """打开备注输入弹窗"""
    tx = db.get_transaction_by_id(tx_id)
    if not tx:
        return

    # 如果有历史记忆，预填备注
    default_note = ""
    if tx.get("merchant"):
        rule = merchant_memory.get_rule(tx["merchant"])
        if rule and rule.get("ownership") == ownership and rule.get("usage_category") == (usage_category or ""):
            default_note = rule.get("usage_note", "")

    st.session_state["note_dialog"] = {
        "tx_id": tx_id,
        "ownership": ownership,
        "usage_category": usage_category,
    }
    st.session_state["note_default"] = default_note
    st.rerun()


def _render_pending_duplicates():
    duplicates = logic.get_pending_duplicates()

    if not duplicates:
        st.success("✅ 没有疑似重复交易")
        return

    st.warning(f"共 **{len(duplicates)}** 笔疑似重复")

    # 分组显示
    groups = {}
    for tx in duplicates:
        key = f"{tx['amount']:.2f}_{tx['tx_time'][:10]}"
        groups.setdefault(key, []).append(tx)

    for key, txs in groups.items():
        st.markdown(f"**¥{txs[0]['amount']:.2f}** - {txs[0]['tx_time'][:10]}")

        for tx in txs:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(
                    f"- `{tx['source']}` `{tx['tx_time'][:16]}` "
                    f"{(tx.get('merchant') or tx.get('original_note') or '-')[:30]}"
                )
            with col2:
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("保留", key=f"dk_{tx['id']}", use_container_width=True):
                        logic.resolve_duplicate(tx["id"], "keep")
                        sync.sync_to_github()
                        st.rerun()
                with c2:
                    if st.button("不计", key=f"de_{tx['id']}", use_container_width=True):
                        logic.resolve_duplicate(tx["id"], "exclude")
                        sync.sync_to_github()
                        st.rerun()

        st.markdown("---")
