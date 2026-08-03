"""业务逻辑层 - 重复识别、同商户同步、待处理筛选"""
from datetime import datetime, timedelta
from utils import db


def detect_duplicates(transactions: list[dict] = None) -> int:
    """
    检测跨来源疑似重复交易
    - 同一分钟内金额相同 → 疑似重复
    - 10 分钟内金额相同且商户/备注能对应 → 疑似重复
    - 每月续费（相同金额但不同日期）不会被误判
    返回标记的条数
    """
    if transactions is None:
        transactions = db.get_all_transactions()

    # 只处理有真实交易时间、真实支出/收入、且非跨平台内部转账
    valid = [t for t in transactions if t["tx_time"] and t["amount"] > 0]

    # 按时间排序
    valid.sort(key=lambda x: x["tx_time"])

    marked = 0
    already_marked = set()

    for i, tx in enumerate(valid):
        if tx["id"] in already_marked:
            continue

        tx_time = parse_time(tx["tx_time"])
        if not tx_time:
            continue

        for j in range(i + 1, len(valid)):
            other = valid[j]
            if other["id"] in already_marked:
                continue
            if other["id"] == tx["id"]:
                continue

            other_time = parse_time(other["tx_time"])
            if not other_time:
                continue

            time_diff = abs((other_time - tx_time).total_seconds())

            # 超过 10 分钟，不可能重复
            if time_diff > 600:
                break  # 因为已按时间排序，后续更不可能

            # 金额必须相同
            if abs(tx["amount"] - other["amount"]) > 0.01:
                continue

            # 必须跨来源
            if tx["source"] == other["source"]:
                continue

            # 同一分钟内金额相同 → 疑似重复
            if time_diff <= 60:
                # 标记后一条为疑似重复
                if other["duplicate_status"] != "疑似重复":
                    db.update_transaction(other["id"], {"duplicate_status": "疑似重复"})
                    already_marked.add(other["id"])
                    marked += 1
                continue

            # 10 分钟内，金额相同，商户/备注能对应
            if time_diff <= 600:
                if merchants_match(tx, other):
                    if other["duplicate_status"] != "疑似重复":
                        db.update_transaction(other["id"], {"duplicate_status": "疑似重复"})
                        already_marked.add(other["id"])
                        marked += 1

    return marked


def parse_time(time_str: str) -> datetime | None:
    """解析时间字符串"""
    try:
        return datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        try:
            return datetime.strptime(time_str[:19], "%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            return None


def merchants_match(tx1: dict, tx2: dict) -> bool:
    """判断两个交易的商户/备注是否匹配"""
    m1 = (tx1.get("merchant") or "") + " " + (tx1.get("original_note") or "")
    m2 = (tx2.get("merchant") or "") + " " + (tx2.get("original_note") or "")

    if not m1.strip() or not m2.strip():
        return False

    # 简单的关键词匹配
    m1_lower = m1.lower()
    m2_lower = m2.lower()

    # 提取关键词（长度>=2的中文或英文单词）
    keywords1 = extract_keywords(m1)
    keywords2 = extract_keywords(m2)

    # 有共同关键词即认为匹配
    common = keywords1 & keywords2
    return len(common) > 0


def extract_keywords(text: str) -> set[str]:
    """提取文本中的关键词"""
    import re
    # 移除常见无意义词
    stop_words = {"交易", "支付", "收款", "转账", "消费", "退款", "订单", "商户", "对方", "元"}
    # 中文词组（2-4字）+ 英文单词
    cn_words = set(re.findall(r'[\u4e00-\u9fa5]{2,4}', text))
    en_words = set(re.findall(r'[a-zA-Z]{2,}', text))
    keywords = (cn_words | en_words) - stop_words
    return keywords


def sync_same_merchant(merchant: str, ownership: str, usage_category: str,
                       tx_nature: str = None) -> int:
    """
    同步同商户的待确认交易
    规则：
    - 只同步同商户
    - 只同步待确认
    - 只同步真实支出
    - 不覆盖已确认交易
    返回同步条数
    """
    txs = db.get_transactions_by_merchant(merchant)
    count = 0
    for tx in txs:
        # 只同步待确认
        if tx["ownership"] != "待确认":
            continue
        # 只同步真实支出
        if tx["direction"] != "支出" or tx["tx_nature"] != "消费":
            continue
        # 不覆盖已确认
        if tx["confirmed"]:
            continue
        # 不同步疑似重复
        if tx["duplicate_status"] == "疑似重复":
            continue

        update_fields = {
            "ownership": ownership,
            "usage_category": usage_category,
            "confirmed": 1,
        }
        if tx_nature:
            update_fields["tx_nature"] = tx_nature
        db.update_transaction(tx["id"], update_fields)
        count += 1

    return count


def mark_not_counted(tx_id: int):
    """标记为不计入统计"""
    db.update_transaction(tx_id, {
        "tx_nature": "不计入统计",
        "confirmed": 1,
    })


def classify_expense(tx_id: int, ownership: str, usage_category: str = None,
                     project_client: str = None, usage_note: str = None,
                     confirm: bool = True):
    """分类支出"""
    fields = {"ownership": ownership}
    if usage_category is not None:
        fields["usage_category"] = usage_category
    if project_client is not None:
        fields["project_client"] = project_client
    if usage_note is not None:
        fields["usage_note"] = usage_note
    if confirm:
        fields["confirmed"] = 1
    db.update_transaction(tx_id, fields)


def classify_income(tx_id: int, ownership: str, project_client: str = None,
                    usage_note: str = None, confirm: bool = True):
    """分类收入"""
    fields = {"ownership": ownership}
    if project_client is not None:
        fields["project_client"] = project_client
    if usage_note is not None:
        fields["usage_note"] = usage_note
    if confirm:
        fields["confirmed"] = 1
    db.update_transaction(tx_id, fields)


def batch_classify(tx_ids: list[int], ownership: str, usage_category: str = None,
                   project_client: str = None):
    """批量分类"""
    for tx_id in tx_ids:
        classify_expense(tx_id, ownership, usage_category, project_client, confirm=True)


def get_pending_expenses() -> list[dict]:
    """获取待处理支出"""
    return db.get_pending_expenses()


def get_pending_incomes() -> list[dict]:
    """获取待处理收入"""
    return db.get_pending_incomes()


def get_pending_duplicates() -> list[dict]:
    """获取疑似重复"""
    return db.get_pending_duplicates()


def resolve_duplicate(tx_id: int, action: str):
    """
    处理疑似重复
    - keep: 保留（标记为正常）
    - exclude: 不计入统计
    """
    if action == "keep":
        db.update_transaction(tx_id, {"duplicate_status": "正常"})
    elif action == "exclude":
        db.update_transaction(tx_id, {
            "duplicate_status": "正常",
            "tx_nature": "不计入统计",
            "confirmed": 1,
        })
