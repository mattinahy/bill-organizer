"""待处理页面 - 移动端友好"""
import streamlit as st
from utils import db, logic
from utils.config import get_expense_types, get_quick_buttons, add_expense_type, delete_expense_type, set_quick_buttons


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

    quick_buttons = get_quick_buttons()

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

        # 快捷按钮行
        cols = st.columns(min(len(quick_buttons) + 2, 4))

        with cols[0]:
            if st.button("👤 个人", key=f"p_{tx['id']}", use_container_width=True):
                logic.classify_expense(tx["id"], "个人")
                st.rerun()

        for idx, btn in enumerate(quick_buttons[:6]):
            col_idx = (idx + 1) % 3 + 1
            if col_idx >= len(cols):
                break
            with cols[col_idx]:
                if st.button(btn, key=f"qb_{tx['id']}_{btn}", use_container_width=True):
                    logic.classify_expense(tx["id"], "公司", btn)
                    if tx.get("merchant"):
                        logic.sync_same_merchant(tx["merchant"], "公司", btn)
                    st.rerun()

        # 不计入按钮
        if st.button("🚫 不计入统计", key=f"ex_{tx['id']}", use_container_width=True):
            logic.mark_not_counted(tx["id"])
            st.rerun()

        st.markdown("---")


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
                        st.rerun()
                with c2:
                    if st.button("不计", key=f"de_{tx['id']}", use_container_width=True):
                        logic.resolve_duplicate(tx["id"], "exclude")
                        st.rerun()

        st.markdown("---")
