"""配置管理模块 - rules.json 读写"""
import os
import json

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "rules.json")

DEFAULT_EXPENSE_TYPES = [
    "差旅", "原材料", "办公", "软件订阅", "采购",
    "设备", "市场", "招待", "维修", "运输", "包装", "人工", "油费", "其他"
]

DEFAULT_QUICK_BUTTONS = ["差旅", "原材料", "办公", "软件订阅", "采购", "设备"]


def load_config() -> dict:
    """加载配置，不存在则创建默认"""
    if not os.path.exists(CONFIG_PATH):
        save_config({
            "expense_types": DEFAULT_EXPENSE_TYPES,
            "quick_buttons": DEFAULT_QUICK_BUTTONS,
        })
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {
            "expense_types": DEFAULT_EXPENSE_TYPES,
            "quick_buttons": DEFAULT_QUICK_BUTTONS,
        }


def save_config(config: dict):
    """保存配置"""
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def get_expense_types() -> list[str]:
    return load_config().get("expense_types", DEFAULT_EXPENSE_TYPES)


def get_quick_buttons() -> list[str]:
    return load_config().get("quick_buttons", DEFAULT_QUICK_BUTTONS)


def add_expense_type(name: str) -> bool:
    """新增费用类型"""
    config = load_config()
    types = config.get("expense_types", [])
    name = name.strip()
    if not name or name in types:
        return False
    types.append(name)
    config["expense_types"] = types
    save_config(config)
    return True


def delete_expense_type(name: str) -> bool:
    """删除费用类型"""
    config = load_config()
    types = config.get("expense_types", [])
    if name not in types:
        return False
    types.remove(name)
    config["expense_types"] = types
    buttons = config.get("quick_buttons", [])
    if name in buttons:
        buttons.remove(name)
        config["quick_buttons"] = buttons
    save_config(config)
    return True


def set_quick_buttons(buttons: list[str]):
    """设置快捷按钮，最多6个"""
    config = load_config()
    config["quick_buttons"] = buttons[:6]
    save_config(config)
