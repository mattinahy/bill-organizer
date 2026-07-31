"""报告页面 - 移动端友好"""
import streamlit as st
import os
from utils import db, report


def render():
    st.subheader("📈 报告")

    tab1, tab2, tab3 = st.tabs(["📊 月度", "📅 年度", "🏢 收款"])

    with tab1:
        _render_monthly()
    with tab2:
        _render_yearly()
    with tab3:
        _render_company_income()


def _render_monthly():
    months = db.get_all_months()
    if not months:
        st.info("暂无数据")
        return

    col1, col2 = st.columns([2, 1])
    with col1:
        selected = st.selectbox("月份", months, key="rpt_m")
    with col2:
        gen = st.button("生成", key="gen_m", use_container_width=True, type="primary")

    if gen:
        st.session_state["monthly_report"] = report.generate_monthly_report(selected)

    rpt = st.session_state.get("monthly_report")
    if not rpt:
        return

    st.markdown(f"### {rpt['period']} 月度报告")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("实际支出", f"¥{rpt['actual_expense_total']:,.0f}")
    with c2:
        st.metric("公司支出", f"¥{rpt['company_expense']:,.0f}")
    with c3:
        st.metric("公司收款", f"¥{rpt['company_income']:,.0f}")

    # 分类统计
    st.markdown("**分类统计**")
    if rpt["category_stats"]:
        for cat, amt in sorted(rpt["category_stats"].items(), key=lambda x: -x[1])[:10]:
            st.markdown(f"- {cat}: **¥{amt:,.2f}**")

    # 公司用途
    if rpt["company_usage_stats"]:
        st.markdown("**公司用途**")
        for cat, amt in sorted(rpt["company_usage_stats"].items(), key=lambda x: -x[1]):
            st.markdown(f"- {cat}: **¥{amt:,.2f}**")

    # 客户收款
    if rpt["client_stats"]:
        st.markdown("**客户收款**")
        for client, amt in sorted(rpt["client_stats"].items(), key=lambda x: -x[1]):
            st.markdown(f"- {client}: **¥{amt:,.2f}**")

    # 下载 Excel
    if st.button("📥 下载 Excel", key="dl_m"):
        filepath = report.export_to_excel(rpt)
        with open(filepath, "rb") as f:
            st.download_button("📥 点击下载", f.read(), os.path.basename(filepath),
                               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


def _render_yearly():
    months = db.get_all_months()
    if not months:
        st.info("暂无数据")
        return

    years = sorted(set(m[:4] for m in months), reverse=True)
    col1, col2 = st.columns([2, 1])
    with col1:
        selected = st.selectbox("年份", years, key="rpt_y")
    with col2:
        gen = st.button("生成", key="gen_y", use_container_width=True, type="primary")

    if gen:
        st.session_state["yearly_report"] = report.generate_yearly_report(selected)

    rpt = st.session_state.get("yearly_report")
    if not rpt:
        return

    st.markdown(f"### {rpt['period']} 年度报告")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("实际支出", f"¥{rpt['total_actual_expense']:,.0f}")
    with c2:
        st.metric("公司支出", f"¥{rpt['total_company_expense']:,.0f}")
    with c3:
        st.metric("公司收款", f"¥{rpt['total_company_income']:,.0f}")

    # 月度明细表
    monthly_data = []
    for mr in rpt["monthly_reports"]:
        monthly_data.append({
            "月份": mr["period"],
            "实际支出": f"¥{mr['actual_expense_total']:,.0f}",
            "公司支出": f"¥{mr['company_expense']:,.0f}",
            "公司收款": f"¥{mr['company_income']:,.0f}",
        })
    st.dataframe(monthly_data, use_container_width=True, hide_index=True)

    # 年度分类
    if rpt["year_category_stats"]:
        st.markdown("**年度分类**")
        for cat, amt in sorted(rpt["year_category_stats"].items(), key=lambda x: -x[1])[:10]:
            st.markdown(f"- {cat}: **¥{amt:,.2f}**")


def _render_company_income():
    months = db.get_all_months()
    if not months:
        st.info("暂无数据")
        return

    col1, col2 = st.columns([2, 1])
    with col1:
        selected = st.selectbox("月份", ["全部"] + months, key="rpt_ci")
    with col2:
        gen = st.button("生成", key="gen_ci", use_container_width=True, type="primary")

    if gen:
        month = None if selected == "全部" else selected
        st.session_state["company_income_report"] = report.generate_company_income_report(month)

    rpt = st.session_state.get("company_income_report")
    if not rpt:
        return

    st.markdown(f"### 公司收款总结 - {rpt['period']}")
    st.metric("合计", f"¥{rpt['total']:,.2f}")

    if rpt["client_stats"]:
        st.markdown("**按客户汇总**")
        for client, amt in sorted(rpt["client_stats"].items(), key=lambda x: -x[1]):
            st.markdown(f"- {client}: **¥{amt:,.2f}**")

    if rpt["incomes"]:
        st.markdown("**收款明细**")
        detail = []
        for inc in rpt["incomes"][:20]:
            detail.append({
                "时间": inc["tx_time"][:10] if inc["tx_time"] else "-",
                "金额": f"¥{inc['amount']:.2f}",
                "来源": inc["source"],
                "付款方": (inc.get("merchant") or "")[:12],
                "客户": (inc.get("project_client") or "")[:12],
            })
        st.dataframe(detail, use_container_width=True, hide_index=True)

    if st.button("📥 下载 Excel", key="dl_ci"):
        filepath = report.export_to_excel(rpt)
        with open(filepath, "rb") as f:
            st.download_button("📥 点击下载", f.read(), os.path.basename(filepath),
                               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
