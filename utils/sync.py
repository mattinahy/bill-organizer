"""GitHub 自动同步模块 - 每次关键操作后自动推送数据库到 GitHub"""
import os
import subprocess
from datetime import datetime

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_last_sync_time = None
MIN_SYNC_INTERVAL = 30  # 最小同步间隔（秒），防止频繁推送


def sync_to_github(force: bool = False) -> tuple[bool, str]:
    """
    将 database.db 自动 git add/commit/push 到 GitHub。
    返回 (成功与否, 消息)
    """
    global _last_sync_time

    now = datetime.now()
    if not force and _last_sync_time:
        elapsed = (now - _last_sync_time).total_seconds()
        if elapsed < MIN_SYNC_INTERVAL:
            return False, f"跳过同步（距上次仅 {elapsed:.0f} 秒）"

    db_path = os.path.join(PROJECT_DIR, "database.db")
    if not os.path.exists(db_path):
        return False, "数据库文件不存在"

    try:
        # git add database.db
        subprocess.run(
            ["git", "add", "database.db"],
            cwd=PROJECT_DIR, capture_output=True, timeout=10
        )

        # git commit（如果没有变化会返回非零，但不影响）
        ts = now.strftime("%Y-%m-%d %H:%M:%S")
        result = subprocess.run(
            ["git", "commit", "-m", f"Auto backup: {ts}"],
            cwd=PROJECT_DIR, capture_output=True, timeout=10
        )

        # git push
        push_result = subprocess.run(
            ["git", "push"],
            cwd=PROJECT_DIR, capture_output=True, timeout=30
        )

        _last_sync_time = now

        if push_result.returncode == 0:
            return True, f"✅ 数据已同步到 GitHub ({ts})"
        else:
            err = push_result.stderr.decode()[:100]
            return False, f"推送失败: {err}"

    except subprocess.TimeoutExpired:
        return False, "同步超时"
    except Exception as e:
        return False, f"同步异常: {str(e)}"


def manual_backup() -> str:
    """手动备份：复制 database.db 到 reports/ 目录"""
    db_path = os.path.join(PROJECT_DIR, "database.db")
    if not os.path.exists(db_path):
        return "数据库文件不存在，无需备份"

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(PROJECT_DIR, "reports", f"backup_{ts}.db")

    with open(db_path, "rb") as src:
        with open(backup_path, "wb") as dst:
            dst.write(src.read())

    return f"✅ 备份已保存: reports/backup_{ts}.db"


def restore_backup(backup_filename: str) -> tuple[bool, str]:
    """从备份文件恢复数据库"""
    backup_path = os.path.join(PROJECT_DIR, "reports", backup_filename)
    if not os.path.exists(backup_path):
        return False, f"备份文件不存在: {backup_filename}"

    db_path = os.path.join(PROJECT_DIR, "database.db")
    # 先备份当前数据库
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.rename(db_path, os.path.join(PROJECT_DIR, "reports", f"before_restore_{ts}.db"))

    # 恢复
    with open(backup_path, "rb") as src:
        with open(db_path, "wb") as dst:
            dst.write(src.read())

    return True, f"✅ 已从 {backup_filename} 恢复数据库"


def get_sync_status() -> dict:
    """获取同步状态"""
    global _last_sync_time
    return {
        "last_sync": _last_sync_time.strftime("%Y-%m-%d %H:%M:%S") if _last_sync_time else "从未同步",
        "db_exists": os.path.exists(os.path.join(PROJECT_DIR, "database.db")),
    }
