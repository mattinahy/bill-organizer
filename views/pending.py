"""待处理页面 - 移动端友好，逐条处理模式"""
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


def _render_pending_expenses():
    pending = logic.get_pending_expenses()

    if not pending:
        st.success("✅ 全部已分类完成！")
        return

    total_amount = sum(t["amount"] for t in pending)
    st.info(f"**{len(pending)}** 笔待处理 · 合计 ¥{total_amount:,.2f}")

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
        st.success(f"🧠 已自动套用记忆分类 {auto_applied} 笔")
        st.rerun()

    # 只显示第一条待处理交易，逐条处理
    tx = pending[0]
    _render_pending_item(tx, get_quick_buttons())

    # 如果还有剩下的，显示提示
    if len(pending) > 1:
        st.caption(f"处理完这笔后，还剩 {len(pending) - 1} 笔")


def _render_pending_item(tx: dict, quick_buttons: list[str]):
    """单条待处理卡片"""
    emoji = {"个人": "👤", "公司": "🏢", "待确认": "❓"}.get(tx.get("ownership"), "❓")
    merchant = tx.get("merchant") or tx.get("original_note") or "-"
    tx_id = tx["id"]

    with st.container():
        # 信息行
        st.markdown(
            f"**¥{tx['amount']:.2f}** `{tx['tx_time'][:16]}` {emoji} "
            f"`{tx['source']}`"
        )
        st.caption(f"📌 {merchant[:40]}")
        if tx.get("usage_category"):
            st.caption(f"当前: {tx['usage_category']}")

        # 获取编辑状态
        edit_state = st.session_state.get("pending_edit")
        # 检查是否在自定义分类输入模式
        show_custom = st.session_state.get("show_custom_input", False)

        # 确保 edit_state 和 show_custom 不会同时为"激活"状态
        # 优先级：自定义输入模式 > 备注编辑模式 > 分类选择模式
        if show_custom:
            _render_custom_input(tx_id, quick_buttons)
        elif edit_state is not None:
            _render_note_input(tx_id, edit_state)
        else:
            _render_category_buttons(tx_id, quick_buttons)

        st.markdown("---")


def _render_category_buttons(tx_id: int, quick_buttons: list[str]):
    """显示分类选择按钮"""
    # 个人按钮
    if st.button("👤 个人", key=f"p_{tx_id}", use_container_width=True):
        _start_editing(tx_id, "个人", None)

    # 快捷公司分类按钮
    for btn in quick_buttons[:6]:
        if st.button(f"🏢 {btn}", key=f"qb_{tx_id}_{btn}", use_container_width=True):
            _start_editing(tx_id, "公司", btn)

    # 自定义分类
    if st.button("✏️ 自定义分类", key=f"custom_{tx_id}", use_container_width=True):
        st.session_state["show_custom_input"] = True
        st.session_state.pop("pending_edit", None)  # 清除编辑状态
        st.rerun()

    # 不计入按钮
    if st.button("🚫 不计入统计", key=f"ex_{tx_id}", use_container_width=True):
        logic.mark_not_counted(tx_id)
        sync.sync_to_github()
        st.rerun()


def _render_note_input(tx_id: int, edit_state: dict):
    """编辑状态：显示备注输入框 + 确认/取消"""
    ownership = edit_state.get("ownership", "")
    usage_category = edit_state.get("usage_category", "")

    # 显示当前选择的分类
    category_display = f"{ownership}" + (f" / {usage_category}" if usage_category else "")
    st.markdown(f"**分类：** {category_display}")

    # 备注输入框（预填记忆的备注）
    default_note = edit_state.get("default_note", "")
    note = st.text_input(
        "📝 备注（可留空）",
        value=default_note,
        key=f"note_input_{tx_id}",
        placeholder="例如：电费、买螺丝、7月团建...",
    )

    # 确认和取消按钮
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ 确认提交", key=f"note_confirm_{tx_id}", type="primary", use_container_width=True):
            _finalize_classify(tx_id, ownership, usage_category, note)
            # 清除编辑状态
            st.session_state.pop("pending_edit", None)
            sync.sync_to_github()
            st.rerun()
    with col2:
        if st.button("↩️ 返回重选", key=f"note_back_{tx_id}", use_container_width=True):
            st.session_state.pop("pending_edit", None)
            st.rerun()


def _render_custom_input(tx_id: int, quick_buttons: list[str]):
    """自定义分类输入"""
    custom_type = st.text_input("分类名称", key="custom_type_input", placeholder="如：客户招待")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("确认", key=f"custom_ok_{tx_id}", use_container_width=True):
            if custom_type.strip():
                add_expense_type(custom_type)
                st.session_state["show_custom_input"] = False
                _start_editing(tx_id, "公司", custom_type.strip())
    with col2:
        if st.button("取消", key=f"custom_cancel_{tx_id}", use_container_width=True):
            st.session_state["show_custom_input"] = False
            st.rerun()


def _start_editing(tx_id: int, ownership: str, usage_category: str):
    """开始编辑备注：记住选的分类，切到备注输入模式"""
    tx = db.get_transaction_by_id(tx_id)
    default_note = ""

    # 如果有商户记忆，预填备注
    if tx and tx.get("merchant"):
        rule = merchant_memory.get_rule(tx["merchant"])
        if rule and rule.get("ownership") == ownership:
            if rule.get("usage_category") == (usage_category or ""):
                default_note = rule.get("usage_note", "")

    st.session_state["pending_edit"] = {
        "tx_id": tx_id,
        "ownership": ownership,
        "usage_category": usage_category,
        "default_note": default_note,
    }
    st.rerun()


def _finalize_classify(tx_id: int, ownership: str, usage_category: str, note: str):
    """最终保存分类和备注，并记住商户"""
    fields = {"ownership": ownership, "confirmed": 1}
    if usage_category:
        fields["usage_category"] = usage_category
    if note:
        fields["usage_note"] = note
    else:
        fields["usage_note"] = ""

    db.update_transaction(tx_id, fields)

    # 记住商户分类（个人和公司都记）
    tx = db.get_transaction_by_id(tx_id)
    if tx and tx.get("merchant"):
        merchant_memory.remember(tx["merchant"], ownership, usage_category, note)
        # 同步同商户待确认
        if ownership == "公司" and usage_category:
            logic.sync_same_merchant(tx["merchant"], ownership, usage_category)


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
