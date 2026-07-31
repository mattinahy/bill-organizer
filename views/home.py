"""首页 - 移动端友好"""
import streamlit as st
from utils import db


def render():
    summary = db.get_summary()
    month = summary["current_month"]

    # 当前月份标签
    st.markdown(f"### 📅 {month}")

    # 2x2 指标卡片
    col1, col2 = st.columns(2)
    with col1:
        st.metric("本月总支出", f"¥{summary['total_expense']:,.2f}")
    with col2:
        st.metric("公司支出", f"¥{summary['company_expense']:,.2f}")

    col3, col4 = st.columns(2)
    with col3:
        st.metric("个人支出", f"¥{summary['personal_expense']:,.2f}")
    with col4:
        st.metric("待确认", f"¥{summary['pending_amount']:,.2f}")

    # 待办提醒
    st.markdown("---")
    pending_todo = summary["pending_todo"]
    pending_dup = summary["pending_dup_count"]

    if pending_todo > 0 or pending_dup > 0:
        st.warning(f"⚡ 待处理 **{pending_todo}** 笔 · 疑似重复 **{pending_dup}** 笔")
        st.caption("💡 前往「待处理」快速分类")
    else:
        st.success("✅ 所有交易已处理完成")

    # 最近交易
    st.markdown("---")
    tab1, tab2 = st.tabs(["💸 最近支出", "💵 最近收入"])

    with tab1:
        expenses = summary.get("recent_expenses", [])[:5]
        if expenses:
            for tx in expenses:
                emoji = {"个人": "👤", "公司": "🏢", "待确认": "❓", "不计入统计": "🚫"}.get(tx.get("ownership"), "❓")
                merchant = tx.get("merchant") or tx.get("original_note") or "-"
                st.markdown(
                    f"`{tx['tx_time'][:10]}` **¥{tx['amount']:.2f}** {emoji} {merchant[:20]}"
                )
        else:
            st.info("暂无支出")

    with tab2:
        incomes = summary.get("recent_incomes", [])[:5]
        if incomes:
            for tx in incomes:
                emoji = {"个人": "👤", "公司": "🏢", "待确认": "❓"}.get(tx.get("ownership"), "❓")
                merchant = tx.get("merchant") or tx.get("original_note") or "-"
                st.markdown(
                    f"`{tx['tx_time'][:10]}` **¥{tx['amount']:.2f}** {emoji} {merchant[:20]}"
                )
        else:
            st.info("暂无收入")
