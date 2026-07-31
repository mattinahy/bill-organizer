"""报告生成模块 - 月度/年度/公司收款总结 + Excel 导出"""
import os
from datetime import datetime
import pandas as pd
from utils import db

REPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)


def generate_monthly_report(month: str) -> dict:
    """生成月度报告"""
    expenses = db.get_monthly_expenses(month)
    incomes = db.get_monthly_incomes(month)

    # 过滤掉不计入统计和疑似重复
    real_expenses = [e for e in expenses
                     if e["tx_nature"] not in ("不计入统计",) and e["duplicate_status"] != "疑似重复"]
    real_incomes = [i for i in incomes
                    if i["tx_nature"] not in ("不计入统计",) and i["duplicate_status"] != "疑似重复"]

    # 总流出（所有支出）
    total_outflow = sum(e["amount"] for e in expenses)
    # 实际支出（剔除内部转账和信用卡还款）
    actual_expenses = [e for e in real_expenses if e["tx_nature"] in ("消费",)]
    actual_expense_total = sum(e["amount"] for e in actual_expenses)

    # 个人/公司/待确认
    personal = sum(e["amount"] for e in actual_expenses if e["ownership"] == "个人")
    company = sum(e["amount"] for e in actual_expenses if e["ownership"] == "公司")
    pending = sum(e["amount"] for e in actual_expenses if e["ownership"] == "待确认")

    # 分类统计（按用途分类）
    category_stats = {}
    for e in actual_expenses:
        cat = e.get("usage_category") or "未分类"
        category_stats[cat] = category_stats.get(cat, 0) + e["amount"]

    # 公司用途汇总
    company_expenses = [e for e in actual_expenses if e["ownership"] == "公司"]
    company_usage_stats = {}
    for e in company_expenses:
        cat = e.get("usage_category") or "未分类"
        company_usage_stats[cat] = company_usage_stats.get(cat, 0) + e["amount"]

    # 收入统计
    income_total = sum(i["amount"] for i in real_incomes)
    personal_income = sum(i["amount"] for i in real_incomes if i["ownership"] == "个人")
    company_income = sum(i["amount"] for i in real_incomes if i["ownership"] == "公司")
    pending_income = sum(i["amount"] for i in real_incomes if i["ownership"] == "待确认")

    # 公司客户收款汇总
    company_income_list = [i for i in real_incomes if i["ownership"] == "公司"]
    client_stats = {}
    for i in company_income_list:
        client = i.get("project_client") or "未指定"
        client_stats[client] = client_stats.get(client, 0) + i["amount"]

    return {
        "type": "月度报告",
        "period": month,
        "total_outflow": total_outflow,
        "actual_expense_total": actual_expense_total,
        "personal_expense": personal,
        "company_expense": company,
        "pending_expense": pending,
        "category_stats": category_stats,
        "company_usage_stats": company_usage_stats,
        "income_total": income_total,
        "personal_income": personal_income,
        "company_income": company_income,
        "pending_income": pending_income,
        "client_stats": client_stats,
        "expenses": actual_expenses,
        "incomes": real_incomes,
        "company_expenses": company_expenses,
        "company_incomes": company_income_list,
    }


def generate_yearly_report(year: str) -> dict:
    """生成年度报告"""
    months = db.get_all_months()
    year_months = [m for m in months if m.startswith(year)]

    all_reports = []
    for m in sorted(year_months):
        r = generate_monthly_report(m)
        all_reports.append(r)

    # 汇总
    total_actual = sum(r["actual_expense_total"] for r in all_reports)
    total_personal = sum(r["personal_expense"] for r in all_reports)
    total_company = sum(r["company_expense"] for r in all_reports)
    total_pending = sum(r["pending_expense"] for r in all_reports)
    total_income = sum(r["income_total"] for r in all_reports)
    total_company_income = sum(r["company_income"] for r in all_reports)

    # 年度分类汇总
    year_category = {}
    for r in all_reports:
        for cat, amt in r["category_stats"].items():
            year_category[cat] = year_category.get(cat, 0) + amt

    year_company_usage = {}
    for r in all_reports:
        for cat, amt in r["company_usage_stats"].items():
            year_company_usage[cat] = year_company_usage.get(cat, 0) + amt

    year_client_stats = {}
    for r in all_reports:
        for client, amt in r["client_stats"].items():
            year_client_stats[client] = year_client_stats.get(client, 0) + amt

    return {
        "type": "年度报告",
        "period": year,
        "monthly_reports": all_reports,
        "total_actual_expense": total_actual,
        "total_personal_expense": total_personal,
        "total_company_expense": total_company,
        "total_pending_expense": total_pending,
        "total_income": total_income,
        "total_company_income": total_company_income,
        "year_category_stats": year_category,
        "year_company_usage_stats": year_company_usage,
        "year_client_stats": year_client_stats,
    }


def generate_company_income_report(month: str | None = None) -> dict:
    """生成公司收款总结"""
    incomes = db.get_monthly_incomes(month)
    company_incomes = [i for i in incomes
                       if i["ownership"] == "公司"
                       and i["tx_nature"] not in ("不计入统计",)
                       and i["duplicate_status"] != "疑似重复"]

    total = sum(i["amount"] for i in company_incomes)

    client_stats = {}
    for i in company_incomes:
        client = i.get("project_client") or "未指定"
        client_stats[client] = client_stats.get(client, 0) + i["amount"]

    return {
        "type": "公司收款总结",
        "period": month or "全部",
        "total": total,
        "client_stats": client_stats,
        "incomes": company_incomes,
    }


def export_to_excel(report: dict, filename: str | None = None) -> str:
    """将报告导出为 Excel 文件"""
    if filename is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{report['type']}_{report['period']}_{ts}.xlsx"

    filepath = os.path.join(REPORTS_DIR, filename)

    with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
        if report["type"] == "月度报告":
            # 摘要
            summary_df = pd.DataFrame({
                "项目": [
                    "账户总流出", "实际支出（剔除内部转账/还款）",
                    "个人支出", "公司支出", "待确认支出",
                    "收入合计", "个人收款", "公司收款", "待确认收入"
                ],
                "金额": [
                    report["total_outflow"], report["actual_expense_total"],
                    report["personal_expense"], report["company_expense"], report["pending_expense"],
                    report["income_total"], report["personal_income"], report["company_income"], report["pending_income"]
                ],
            })
            summary_df.to_excel(writer, sheet_name="摘要", index=False)

            # 分类统计
            if report["category_stats"]:
                cat_df = pd.DataFrame(
                    sorted(report["category_stats"].items(), key=lambda x: -x[1]),
                    columns=["分类", "金额"]
                )
                cat_df.to_excel(writer, sheet_name="分类统计", index=False)

            # 公司用途汇总
            if report["company_usage_stats"]:
                usage_df = pd.DataFrame(
                    sorted(report["company_usage_stats"].items(), key=lambda x: -x[1]),
                    columns=["公司用途", "金额"]
                )
                usage_df.to_excel(writer, sheet_name="公司用途汇总", index=False)

            # 公司收款汇总
            if report["client_stats"]:
                client_df = pd.DataFrame(
                    sorted(report["client_stats"].items(), key=lambda x: -x[1]),
                    columns=["客户/来源", "金额"]
                )
                client_df.to_excel(writer, sheet_name="公司收款汇总", index=False)

            # 交易明细
            if report["expenses"]:
                detail_df = pd.DataFrame(report["expenses"])[
                    ["tx_time", "amount", "direction", "source", "merchant",
                     "original_note", "ownership", "usage_category", "project_client", "usage_note"]
                ]
                detail_df.columns = ["交易时间", "金额", "方向", "来源", "商户",
                                     "备注", "归属", "用途", "项目/客户", "说明"]
                detail_df.to_excel(writer, sheet_name="支出明细", index=False)

        elif report["type"] == "公司收款总结":
            # 摘要
            summary_df = pd.DataFrame({
                "项目": ["公司收款合计"],
                "金额": [report["total"]],
            })
            summary_df.to_excel(writer, sheet_name="摘要", index=False)

            # 客户汇总
            if report["client_stats"]:
                client_df = pd.DataFrame(
                    sorted(report["client_stats"].items(), key=lambda x: -x[1]),
                    columns=["客户/来源", "金额"]
                )
                client_df.to_excel(writer, sheet_name="客户汇总", index=False)

            # 明细
            if report["incomes"]:
                detail_df = pd.DataFrame(report["incomes"])[
                    ["tx_time", "amount", "source", "merchant",
                     "original_note", "ownership", "project_client", "usage_note"]
                ]
                detail_df.columns = ["交易时间", "金额", "来源", "付款方",
                                     "备注", "归属", "客户/来源", "收款说明"]
                detail_df.to_excel(writer, sheet_name="收款明细", index=False)

    return filepath
