"""alert_history.py — SQLite 告警历史记录（仅 warn/crit 事件）

数据库：~/.aigard/alert_history.db（用户目录，App bundle 外）
表结构：alerts(id, ts, level, reason)

使用方式：
    from alert_history import record_alert, get_recent_alerts
    record_alert("warn", "内存 82% / Swap 55%")
    history = get_recent_alerts(20)
"""

import sqlite3
import time
from pathlib import Path

DB_PATH = Path.home() / ".aigard" / "alert_history.db"


def _get_conn() -> sqlite3.Connection:
    """获取连接并确保表存在"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            ts      REAL    NOT NULL,
            level   TEXT    NOT NULL,
            reason  TEXT    NOT NULL
        )
    """)
    conn.commit()
    return conn


def record_alert(level: str, reason: str) -> None:
    """记录一条告警事件（非阻塞，忽略写入错误避免影响监控主循环）"""
    if level not in ("warn", "crit"):
        return
    try:
        conn = _get_conn()
        conn.execute(
            "INSERT INTO alerts (ts, level, reason) VALUES (?, ?, ?)",
            (time.time(), level, reason),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


def get_recent_alerts(limit: int = 20) -> list:
    """读取最近 N 条告警，按时间倒序"""
    try:
        conn = _get_conn()
        rows = conn.execute(
            "SELECT ts, level, reason FROM alerts ORDER BY ts DESC LIMIT ?",
            (limit,),
        ).fetchall()
        conn.close()
        return [{"ts": r[0], "level": r[1], "reason": r[2]} for r in rows]
    except Exception:
        return []
