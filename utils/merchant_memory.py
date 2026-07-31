"""商户记忆模块 - 记住每个商户的分类规则"""
import os
import json

MEMO_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "merchant_memory.json")


def load_memory() -> dict:
    """加载商户记忆，返回 {商户名: {ownership, usage_category, usage_note}}"""
    if not os.path.exists(MEMO_PATH):
        return {}
    try:
        with open(MEMO_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def save_memory(memory: dict):
    """保存商户记忆"""
    with open(MEMO_PATH, "w", encoding="utf-8") as f:
        json.dump(memory, f, ensure_ascii=False, indent=2)


def remember(merchant: str, ownership: str, usage_category: str = None, usage_note: str = None):
    """记住一个商户的分类规则"""
    if not merchant:
        return
    memory = load_memory()
    memory[merchant] = {
        "ownership": ownership,
        "usage_category": usage_category or "",
        "usage_note": usage_note or "",
    }
    save_memory(memory)


def get_rule(merchant: str) -> dict | None:
    """查询商户记忆规则"""
    if not merchant:
        return None
    memory = load_memory()
    rule = memory.get(merchant)
    return rule if rule else None


def auto_classify(merchant: str) -> dict | None:
    """
    根据商户记忆自动分类。
    返回 {"ownership": ..., "usage_category": ..., "usage_note": ...} 或 None
    """
    rule = get_rule(merchant)
    if not rule:
        return None
    # 只返回有明确分类的规则
    if not rule.get("ownership"):
        return None
    return rule
