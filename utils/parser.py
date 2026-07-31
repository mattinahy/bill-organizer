"""账单导入解析器 - 支付宝、微信、银行卡、信用卡"""
import os
import io
import csv
import json
import chardet
from datetime import datetime
import pandas as pd


def detect_encoding(file_path: str) -> str:
    """检测文件编码"""
    with open(file_path, "rb") as f:
        raw = f.read(65536)
    result = chardet.detect(raw)
    return result.get("encoding", "utf-8") or "utf-8"


def parse_alipay(file_path: str) -> list[dict]:
    """
    解析支付宝账单 CSV
    - 处理 GBK 编码
    - 跳过前面的说明行（以 # 开头或前 ~24 行的说明）
    - 处理 "不计收支"
    """
    encoding = detect_encoding(file_path)
    if encoding.lower() in ("gb2312", "gbk", "ascii"):
        encoding = "gbk"

    with open(file_path, "r", encoding=encoding, errors="replace") as f:
        lines = f.readlines()

    # 找到表头行（包含"交易号"或"交易时间"的行）
    header_idx = None
    for i, line in enumerate(lines):
        if "交易号" in line or ("交易时间" in line and "交易分类" in line):
            header_idx = i
            break

    if header_idx is None:
        # 尝试找含"交易时间"的行
        for i, line in enumerate(lines):
            if "交易时间" in line:
                header_idx = i
                break

    if header_idx is None:
        raise ValueError("无法识别支付宝账单表头，请确认文件格式")

    # 解析 CSV
    csv_lines = lines[header_idx:]
    reader = csv.reader(csv_lines)
    rows = list(reader)

    # 过滤掉空行和说明行
    rows = [r for r in rows if r and len(r) > 1 and not r[0].startswith("#") and not r[0].startswith("---")]

    if not rows:
        return []

    header = [h.strip() for h in rows[0]]
    data_rows = rows[1:]

    # 也过滤掉尾部汇总行
    data_rows = [r for r in data_rows if r[0] and not r[0].startswith("---") and "本期" not in str(r[0])]

    transactions = []
    for row in data_rows:
        if len(row) < len(header):
            row = row + [""] * (len(header) - len(row))
        record = dict(zip(header, [c.strip() for c in row]))

        # 资金收支：优先用"收/支"列，其次"资金状态"
        direction_raw = record.get("收/支", record.get("资金状态", ""))
        # 金额：尝试多种列名
        amount_str = record.get("金额（元）", record.get("金额(元)", record.get("金额", record.get("订单金额", "0"))))

        # 支付宝有 "不计收支"
        if "不计" in direction_raw:
            direction = "中性"
            tx_nature = "不计入统计"
        elif "收入" in direction_raw:
            direction = "收入"
            tx_nature = "消费"
        elif "支出" in direction_raw:
            direction = "支出"
            tx_nature = "消费"
        else:
            direction = "中性"
            tx_nature = "不计入统计"

        # 金额
        try:
            amount = float(amount_str.replace(",", "").replace("¥", "").strip())
        except (ValueError, AttributeError):
            continue

        if amount <= 0:
            continue

        tx_time = parse_datetime(record.get("交易时间", record.get("付款时间", "")))

        merchant = record.get("交易对方", record.get("对方账号", ""))
        note = record.get("商品说明", record.get("商品名称", ""))

        # 识别内部转账 / 理财
        combined_text = f"{merchant} {note}"
        if any(k in combined_text for k in ["余额宝", "理财通", "零钱通", "小荷包"]):
            tx_nature = "内部转账"
        elif "还款" in combined_text or "信用卡" in combined_text:
            tx_nature = "还款"

        transactions.append({
            "tx_time": tx_time,
            "amount": round(amount, 2),
            "direction": direction,
            "source": "支付宝",
            "merchant": merchant or "",
            "original_note": note or "",
            "tx_nature": tx_nature,
            "ownership": "待确认" if direction == "支出" else "待确认",
            "raw_data": json.dumps(record, ensure_ascii=False),
        })

    return transactions


def parse_wechat(file_path: str) -> list[dict]:
    """
    解析微信支付账单 Excel
    - 跳过前 16-20 行说明
    - 处理中性交易
    """
    # 微信账单 Excel 通常前 16 行是说明
    try:
        df = pd.read_excel(file_path, header=None)
    except Exception:
        raise ValueError("无法读取微信 Excel 文件")

    # 找到表头行
    header_idx = None
    for i in range(min(len(df), 30)):
        row_vals = [str(v) for v in df.iloc[i].tolist()]
        if "交易时间" in row_vals:
            header_idx = i
            break

    if header_idx is None:
        raise ValueError("无法识别微信账单表头")

    # 重新读取，用正确的表头
    df = pd.read_excel(file_path, header=header_idx)
    df.columns = [str(c).strip() for c in df.columns]

    # 过滤空行和汇总行
    df = df.dropna(subset=["交易时间"])
    df = df[df["交易时间"].astype(str).str.contains(r"\d{4}-\d{2}-\d{2}", regex=True, na=False)]

    transactions = []
    for _, row in df.iterrows():
        direction_raw = str(row.get("收/支", row.get("交易类型", "")))
        amount_str = str(row.get("金额(元)", row.get("金额", "0")))

        # 微信中性交易
        if "/" in direction_raw and "收入" not in direction_raw and "支出" not in direction_raw:
            direction = "中性"
            tx_nature = "不计入统计"
        elif "收入" in direction_raw:
            direction = "收入"
            tx_nature = "消费"
        elif "支出" in direction_raw:
            direction = "支出"
            tx_nature = "消费"
        else:
            direction = "中性"
            tx_nature = "不计入统计"

        try:
            amount = float(amount_str.replace(",", "").replace("¥", "").replace("元", "").strip())
        except (ValueError, AttributeError):
            continue

        if amount <= 0:
            continue

        tx_time = parse_datetime(str(row.get("交易时间", "")))
        merchant = str(row.get("交易对方", row.get("对方", "")))
        note = str(row.get("商品", row.get("商品说明", row.get("备注", ""))))

        combined_text = f"{merchant} {note}"
        if any(k in combined_text for k in ["零钱通", "理财通", "小荷包"]):
            tx_nature = "内部转账"
        elif "还款" in combined_text or "信用卡还款" in combined_text:
            tx_nature = "还款"

        transactions.append({
            "tx_time": tx_time,
            "amount": round(amount, 2),
            "direction": direction,
            "source": "微信",
            "merchant": merchant if merchant != "nan" else "",
            "original_note": note if note != "nan" else "",
            "tx_nature": tx_nature,
            "ownership": "待确认",
            "raw_data": json.dumps({k: str(v) for k, v in row.items()}, ensure_ascii=False),
        })

    return transactions


def parse_bank(file_path: str, source_name: str = "银行卡") -> list[dict]:
    """
    解析银行卡 / 信用卡流水 Excel/CSV
    - 自动检测表头
    - 尝试匹配常见的字段名
    """
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".csv":
        encoding = detect_encoding(file_path)
        df = pd.read_csv(file_path, encoding=encoding, dtype=str)
    elif ext in (".xlsx", ".xls"):
        df = pd.read_excel(file_path, dtype=str)
    else:
        raise ValueError(f"不支持的文件格式: {ext}")

    df.columns = [str(c).strip() for c in df.columns]

    # 映射常见表头
    col_map = {
        "time": find_col(df, ["交易时间", "日期", "记账日期", "交易日期", "入账时间", "时间"]),
        "amount": find_col(df, ["金额", "交易金额", "发生额", "金额(元)", "人民币金额"]),
        "direction": find_col(df, ["收/支", "摘要", "交易类型", "借贷方向", "方向", "收支"]),
        "merchant": find_col(df, ["交易对方", "对方户名", "商户名称", "对方", "摘要"]),
        "note": find_col(df, ["备注", "交易摘要", "说明", "附言", "摘要说明"]),
    }

    if not col_map["time"] or not col_map["amount"]:
        raise ValueError("无法识别银行卡流水的交易时间或金额列，请检查表头")

    transactions = []
    for _, row in df.iterrows():
        time_val = str(row.get(col_map["time"], ""))
        if not time_val or time_val == "nan" or not any(c.isdigit() for c in time_val):
            continue

        amount_str = str(row.get(col_map["amount"], "0"))
        try:
            amount = float(amount_str.replace(",", "").replace("¥", "").replace("元", "").strip())
        except (ValueError, AttributeError):
            continue

        # 金额可能是正负数表示方向
        direction_raw = ""
        if col_map["direction"]:
            direction_raw = str(row.get(col_map["direction"], ""))

        if amount < 0:
            direction = "支出"
            amount = abs(amount)
            tx_nature = "消费"
        elif amount > 0 and "支" in direction_raw:
            direction = "支出"
            tx_nature = "消费"
        elif "收" in direction_raw or (amount > 0 and "贷" in direction_raw):
            direction = "收入"
            tx_nature = "消费"
        else:
            # 无法确定方向，默认支出
            if amount > 0:
                direction = "支出"
                tx_nature = "消费"
            else:
                continue

        if amount <= 0:
            continue

        tx_time = parse_datetime(time_val)
        merchant = str(row.get(col_map["merchant"], "")) if col_map["merchant"] else ""
        note = str(row.get(col_map["note"], "")) if col_map["note"] else ""

        if merchant == "nan":
            merchant = ""
        if note == "nan":
            note = ""

        combined_text = f"{merchant} {note}"
        if any(k in combined_text for k in ["还款", "信用卡还", "信用卡还款"]):
            tx_nature = "还款"
        elif any(k in combined_text for k in ["理财", "活期", "定期", "转入", "转出"]):
            tx_nature = "内部转账"

        transactions.append({
            "tx_time": tx_time,
            "amount": round(amount, 2),
            "direction": direction,
            "source": source_name,
            "merchant": merchant,
            "original_note": note,
            "tx_nature": tx_nature,
            "ownership": "待确认",
            "raw_data": json.dumps({k: str(v) for k, v in row.items()}, ensure_ascii=False),
        })

    return transactions


def find_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    """在 DataFrame 中查找匹配的列名"""
    for c in candidates:
        for col in df.columns:
            if c in col:
                return col
    return None


def parse_datetime(time_str: str) -> str:
    """解析各种日期格式，返回统一的 YYYY-MM-DD HH:MM:SS"""
    time_str = str(time_str).strip()
    if not time_str or time_str == "nan":
        return ""

    # 尝试多种格式
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%Y年%m月%d日 %H:%M:%S",
        "%Y年%m月%d日 %H:%M",
        "%Y年%m月%d日",
        "%Y%m%d",
        "%Y.%m.%d %H:%M:%S",
        "%Y.%m.%d",
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(time_str, fmt)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue

    # 尝试用 pandas 解析
    try:
        ts = pd.to_datetime(time_str, errors="coerce")
        if pd.notna(ts):
            return ts.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        pass

    return time_str


def parse_bill(file_path: str, source: str) -> tuple[list[dict], str]:
    """
    根据来源调用对应解析器
    返回 (transactions, message)
    """
    try:
        if source == "alipay":
            txs = parse_alipay(file_path)
        elif source == "wechat":
            txs = parse_wechat(file_path)
        elif source == "bank":
            txs = parse_bank(file_path, "银行卡")
        elif source == "credit":
            txs = parse_bank(file_path, "信用卡")
        else:
            return [], f"不支持的来源: {source}"

        if not txs:
            return [], "解析完成，但未找到有效交易记录"

        return txs, f"成功解析 {len(txs)} 条交易记录"
    except Exception as e:
        return [], f"解析失败: {str(e)}"
