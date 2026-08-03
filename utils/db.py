"""数据库管理模块 - SQLite 数据库初始化与 CRUD 操作"""
import sqlite3
import os
from datetime import datetime
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "database.db")


@contextmanager
def get_conn():
    """获取数据库连接的上下文管理器"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """初始化数据库，创建所有表"""
    with get_conn() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tx_time TEXT NOT NULL,
            amount REAL NOT NULL,
            direction TEXT NOT NULL,
            source TEXT NOT NULL,
            merchant TEXT,
            original_note TEXT,
            tx_nature TEXT DEFAULT '消费',
            ownership TEXT DEFAULT '待确认',
            usage_category TEXT,
            project_client TEXT,
            usage_note TEXT,
            duplicate_status TEXT DEFAULT '正常',
            confirmed INTEGER DEFAULT 0,
            raw_data TEXT,
            import_batch TEXT,
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            updated_at TEXT DEFAULT (datetime('now', 'localtime'))
        );

        CREATE INDEX IF NOT EXISTS idx_tx_time ON transactions(tx_time);
        CREATE INDEX IF NOT EXISTS idx_direction ON transactions(direction);
        CREATE INDEX IF NOT EXISTS idx_source ON transactions(source);
        CREATE INDEX IF NOT EXISTS idx_ownership ON transactions(ownership);
        CREATE INDEX IF NOT EXISTS idx_duplicate ON transactions(duplicate_status);
        CREATE INDEX IF NOT EXISTS idx_merchant ON transactions(merchant);
        """)


def insert_transaction(tx: dict) -> int:
    """插入单笔交易，返回 ID"""
    with get_conn() as conn:
        cur = conn.execute("""
            INSERT INTO transactions
                (tx_time, amount, direction, source, merchant, original_note,
                 tx_nature, ownership, usage_category, project_client, usage_note,
                 duplicate_status, confirmed, raw_data, import_batch)
            VALUES
                (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            tx.get("tx_time"), tx.get("amount"), tx.get("direction"),
            tx.get("source"), tx.get("merchant"), tx.get("original_note"),
            tx.get("tx_nature", "消费"), tx.get("ownership", "待确认"),
            tx.get("usage_category"), tx.get("project_client"), tx.get("usage_note"),
            tx.get("duplicate_status", "正常"), tx.get("confirmed", 0),
            tx.get("raw_data"), tx.get("import_batch"),
        ))
        return cur.lastrowid


def batch_insert(transactions: list[dict]) -> int:
    """批量插入交易，自动跳过重复记录，返回实际插入条数
    重复判断：相同 (tx_time, amount, source, merchant) 视为重复
    """
    count = 0
    with get_conn() as conn:
        for tx in transactions:
            # 检查是否已存在相同记录
            existing = conn.execute("""
                SELECT id FROM transactions
                WHERE tx_time = ? AND abs(amount - ?) < 0.001
                  AND source = ? AND COALESCE(merchant,'') = COALESCE(?, '')
                LIMIT 1
            """, (tx.get("tx_time"), tx.get("amount"), tx.get("source"),
                  tx.get("merchant") or "")).fetchone()

            if existing:
                continue  # 跳过重复

            conn.execute("""
                INSERT INTO transactions
                    (tx_time, amount, direction, source, merchant, original_note,
                     tx_nature, ownership, usage_category, project_client, usage_note,
                     duplicate_status, confirmed, raw_data, import_batch)
                VALUES
                    (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                tx.get("tx_time"), tx.get("amount"), tx.get("direction"),
                tx.get("source"), tx.get("merchant"), tx.get("original_note"),
                tx.get("tx_nature", "消费"), tx.get("ownership", "待确认"),
                tx.get("usage_category"), tx.get("project_client"), tx.get("usage_note"),
                tx.get("duplicate_status", "正常"), tx.get("confirmed", 0),
                tx.get("raw_data"), tx.get("import_batch"),
            ))
            count += 1
    return count


def query_all(sql: str, params: tuple = ()) -> list[dict]:
    """查询返回字典列表"""
    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]


def query_one(sql: str, params: tuple = ()) -> dict | None:
    """查询单条"""
    with get_conn() as conn:
        row = conn.execute(sql, params).fetchone()
        return dict(row) if row else None


def execute(sql: str, params: tuple = ()) -> int:
    """执行写操作，返回 affected rows"""
    with get_conn() as conn:
        cur = conn.execute(sql, params)
        return cur.rowcount


def update_transaction(tx_id: int, fields: dict):
    """更新指定交易的字段"""
    if not fields:
        return
    sets = []
    vals = []
    for k, v in fields.items():
        if k == "id":
            continue
        sets.append(f"{k} = ?")
        vals.append(v)
    sets.append("updated_at = datetime('now', 'localtime')")
    vals.append(tx_id)
    with get_conn() as conn:
        conn.execute(f"UPDATE transactions SET {', '.join(sets)} WHERE id = ?", vals)


def get_all_transactions() -> list[dict]:
    """获取所有交易"""
    return query_all("SELECT * FROM transactions ORDER BY tx_time DESC")


def get_transactions_by_filter(direction: str | None = None,
                               ownership: str | None = None,
                               month: str | None = None,
                               tx_nature: str | None = None,
                               search: str | None = None) -> list[dict]:
    """按条件筛选交易"""
    sql = "SELECT * FROM transactions WHERE 1=1"
    params = []
    if direction:
        sql += " AND direction = ?"
        params.append(direction)
    if ownership:
        sql += " AND ownership = ?"
        params.append(ownership)
    if month:
        sql += " AND substr(tx_time, 1, 7) = ?"
        params.append(month)
    if tx_nature:
        sql += " AND tx_nature = ?"
        params.append(tx_nature)
    if search:
        sql += " AND (merchant LIKE ? OR original_note LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])
    sql += " ORDER BY tx_time DESC"
    return query_all(sql, tuple(params))


def get_pending_expenses() -> list[dict]:
    """获取待处理支出"""
    return query_all("""
        SELECT * FROM transactions
        WHERE direction = '支出'
          AND tx_nature = '消费'
          AND duplicate_status != '疑似重复'
          AND (
              ownership = '待确认'
              OR (ownership = '公司' AND (usage_category IS NULL OR usage_category = '' OR usage_category = '其他'))
          )
        ORDER BY tx_time DESC
    """)


def get_pending_incomes() -> list[dict]:
    """获取待处理收入"""
    return query_all("""
        SELECT * FROM transactions
        WHERE direction = '收入'
          AND duplicate_status != '疑似重复'
          AND ownership = '待确认'
        ORDER BY tx_time DESC
    """)


def get_pending_duplicates() -> list[dict]:
    """获取疑似重复交易"""
    return query_all("""
        SELECT * FROM transactions
        WHERE duplicate_status = '疑似重复'
        ORDER BY tx_time DESC
    """)


def get_monthly_expenses(month: str | None = None) -> list[dict]:
    """获取月度支出"""
    sql = """
        SELECT * FROM transactions
        WHERE direction = '支出' AND tx_nature = '消费'
    """
    params = ()
    if month:
        sql += " AND substr(tx_time, 1, 7) = ?"
        params = (month,)
    sql += " ORDER BY tx_time DESC"
    return query_all(sql, params)


def get_monthly_incomes(month: str | None = None) -> list[dict]:
    """获取月度收入"""
    sql = """
        SELECT * FROM transactions
        WHERE direction = '收入' AND tx_nature = '消费'
    """
    params = ()
    if month:
        sql += " AND substr(tx_time, 1, 7) = ?"
        params = (month,)
    sql += " ORDER BY tx_time DESC"
    return query_all(sql, params)


def get_all_months() -> list[str]:
    """获取所有有交易的月份"""
    rows = query_all("""
        SELECT DISTINCT substr(tx_time, 1, 7) as month
        FROM transactions
        WHERE tx_time IS NOT NULL AND tx_time != ''
        ORDER BY month DESC
    """)
    return [r["month"] for r in rows if r["month"]]


def get_summary() -> dict:
    """获取首页概览数据"""
    now = datetime.now()
    current_month = now.strftime("%Y-%m")

    total_expense = query_one("""
        SELECT COALESCE(SUM(amount), 0) as total FROM transactions
        WHERE direction = '支出' AND tx_nature = '消费'
          AND ownership != '不计入统计'
          AND duplicate_status != '疑似重复'
          AND substr(tx_time, 1, 7) = ?
    """, (current_month,)) or {}

    personal_expense = query_one("""
        SELECT COALESCE(SUM(amount), 0) as total FROM transactions
        WHERE direction = '支出' AND tx_nature = '消费'
          AND ownership = '个人'
          AND substr(tx_time, 1, 7) = ?
    """, (current_month,)) or {}

    company_expense = query_one("""
        SELECT COALESCE(SUM(amount), 0) as total FROM transactions
        WHERE direction = '支出' AND tx_nature = '消费'
          AND ownership = '公司'
          AND substr(tx_time, 1, 7) = ?
    """, (current_month,)) or {}

    pending_expense = query_one("""
        SELECT COALESCE(SUM(amount), 0) as total, COUNT(*) as cnt FROM transactions
        WHERE direction = '支出' AND tx_nature = '消费'
          AND ownership = '待确认'
          AND duplicate_status != '疑似重复'
          AND substr(tx_time, 1, 7) = ?
    """, (current_month,)) or {}

    recent_expenses = query_all("""
        SELECT * FROM transactions
        WHERE direction = '支出' AND tx_nature = '消费'
        ORDER BY tx_time DESC LIMIT 10
    """)

    recent_incomes = query_all("""
        SELECT * FROM transactions
        WHERE direction = '收入' AND tx_nature = '消费'
        ORDER BY tx_time DESC LIMIT 10
    """)

    pending_count = query_one("""
        SELECT COUNT(*) as cnt FROM transactions
        WHERE direction = '支出' AND tx_nature = '消费'
          AND duplicate_status != '疑似重复'
          AND (
              ownership = '待确认'
              OR (ownership = '公司' AND (usage_category IS NULL OR usage_category = '' OR usage_category = '其他'))
          )
    """) or {"cnt": 0}

    pending_dup_count = query_one("""
        SELECT COUNT(*) as cnt FROM transactions
        WHERE duplicate_status = '疑似重复'
    """) or {"cnt": 0}

    return {
        "total_expense": total_expense.get("total", 0),
        "personal_expense": personal_expense.get("total", 0),
        "company_expense": company_expense.get("total", 0),
        "pending_amount": pending_expense.get("total", 0),
        "pending_count": pending_expense.get("cnt", 0),
        "recent_expenses": recent_expenses,
        "recent_incomes": recent_incomes,
        "pending_todo": pending_count.get("cnt", 0),
        "pending_dup_count": pending_dup_count.get("cnt", 0),
        "current_month": current_month,
    }


def clear_all_transactions():
    """清空所有交易数据"""
    with get_conn() as conn:
        conn.execute("DELETE FROM transactions")


def get_transaction_by_id(tx_id: int) -> dict | None:
    return query_one("SELECT * FROM transactions WHERE id = ?", (tx_id,))


def get_transactions_by_merchant(merchant: str) -> list[dict]:
    """通过商户获取交易"""
    return query_all(
        "SELECT * FROM transactions WHERE merchant = ? ORDER BY tx_time DESC",
        (merchant,)
    )


def delete_transaction(tx_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM transactions WHERE id = ?", (tx_id,))
