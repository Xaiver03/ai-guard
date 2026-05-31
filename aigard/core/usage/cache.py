"""
SQLite 缓存 - 持久化聚合后的使用数据,减少内存占用
"""
import json
import os
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any


class UsageCache:
    """SQLite 缓存,存储聚合后的使用统计"""

    def __init__(self, db_dir: Optional[str] = None):
        if db_dir is None:
            db_dir = os.path.expanduser("~/.aigard")
        os.makedirs(db_dir, exist_ok=True)
        self.db_path = Path(db_dir) / "usage_cache.db"
        self._init_db()

    def _init_db(self):
        """初始化数据库表"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS daily_usage (
                    date TEXT PRIMARY KEY,
                    input_tokens INTEGER DEFAULT 0,
                    output_tokens INTEGER DEFAULT 0,
                    cache_creation_tokens INTEGER DEFAULT 0,
                    cache_read_tokens INTEGER DEFAULT 0,
                    total_tokens INTEGER DEFAULT 0,
                    total_cost REAL DEFAULT 0,
                    models_used TEXT DEFAULT '[]',
                    model_breakdowns TEXT DEFAULT '[]',
                    request_count INTEGER DEFAULT 0,
                    updated_at TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS hourly_usage (
                    hour TEXT PRIMARY KEY,
                    input_tokens INTEGER DEFAULT 0,
                    output_tokens INTEGER DEFAULT 0,
                    cache_creation_tokens INTEGER DEFAULT 0,
                    cache_read_tokens INTEGER DEFAULT 0,
                    total_tokens INTEGER DEFAULT 0,
                    total_cost REAL DEFAULT 0,
                    models_used TEXT DEFAULT '[]',
                    model_breakdowns TEXT DEFAULT '[]',
                    request_count INTEGER DEFAULT 0,
                    updated_at TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            conn.commit()

    def get_last_update_time(self) -> Optional[str]:
        """获取上次更新时间"""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT value FROM cache_meta WHERE key = 'last_update'"
            ).fetchone()
            return row[0] if row else None

    def set_last_update_time(self, timestamp: str):
        """设置上次更新时间"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO cache_meta (key, value) VALUES (?, ?)",
                ('last_update', timestamp)
            )
            conn.commit()

    def save_daily(self, data: List[Dict[str, Any]]):
        """保存日报数据"""
        with sqlite3.connect(self.db_path) as conn:
            for item in data:
                conn.execute("""
                    INSERT OR REPLACE INTO daily_usage
                    (date, input_tokens, output_tokens, cache_creation_tokens,
                     cache_read_tokens, total_tokens, total_cost,
                     models_used, model_breakdowns, request_count, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    item['date'],
                    item.get('input_tokens', 0),
                    item.get('output_tokens', 0),
                    item.get('cache_creation_tokens', 0),
                    item.get('cache_read_tokens', 0),
                    item.get('total_tokens', 0),
                    item.get('total_cost', 0),
                    json.dumps(item.get('models_used', [])),
                    json.dumps(item.get('model_breakdowns', [])),
                    item.get('request_count', 0),
                    datetime.now().isoformat()
                ))
            conn.commit()

    def save_hourly(self, data: List[Dict[str, Any]]):
        """保存小时报数据"""
        with sqlite3.connect(self.db_path) as conn:
            for item in data:
                conn.execute("""
                    INSERT OR REPLACE INTO hourly_usage
                    (hour, input_tokens, output_tokens, cache_creation_tokens,
                     cache_read_tokens, total_tokens, total_cost,
                     models_used, model_breakdowns, request_count, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    item['hour'],
                    item.get('input_tokens', 0),
                    item.get('output_tokens', 0),
                    item.get('cache_creation_tokens', 0),
                    item.get('cache_read_tokens', 0),
                    item.get('total_tokens', 0),
                    item.get('total_cost', 0),
                    json.dumps(item.get('models_used', [])),
                    json.dumps(item.get('model_breakdowns', [])),
                    item.get('request_count', 0),
                    datetime.now().isoformat()
                ))
            conn.commit()

    def get_daily(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict]:
        """获取日报数据"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            if start_date and end_date:
                rows = conn.execute(
                    "SELECT * FROM daily_usage WHERE date >= ? AND date <= ? ORDER BY date",
                    (start_date, end_date)
                ).fetchall()
            elif start_date:
                rows = conn.execute(
                    "SELECT * FROM daily_usage WHERE date >= ? ORDER BY date",
                    (start_date,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM daily_usage ORDER BY date"
                ).fetchall()

            return [self._row_to_daily_dict(row) for row in rows]

    def get_hourly(self, start_hour: Optional[str] = None, end_hour: Optional[str] = None) -> List[Dict]:
        """获取小时报数据"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            if start_hour and end_hour:
                rows = conn.execute(
                    "SELECT * FROM hourly_usage WHERE hour >= ? AND hour <= ? ORDER BY hour",
                    (start_hour, end_hour)
                ).fetchall()
            elif start_hour:
                rows = conn.execute(
                    "SELECT * FROM hourly_usage WHERE hour >= ? ORDER BY hour",
                    (start_hour,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM hourly_usage ORDER BY hour"
                ).fetchall()

            return [self._row_to_hourly_dict(row) for row in rows]

    def get_summary(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict:
        """获取汇总数据"""
        with sqlite3.connect(self.db_path) as conn:
            if start_date and end_date:
                row = conn.execute("""
                    SELECT
                        COALESCE(SUM(input_tokens), 0),
                        COALESCE(SUM(output_tokens), 0),
                        COALESCE(SUM(cache_creation_tokens), 0),
                        COALESCE(SUM(cache_read_tokens), 0),
                        COALESCE(SUM(total_tokens), 0),
                        COALESCE(SUM(total_cost), 0),
                        COUNT(*) as active_days,
                        COALESCE(SUM(request_count), 0)
                    FROM daily_usage WHERE date >= ? AND date <= ?
                """, (start_date, end_date)).fetchone()
            elif start_date:
                row = conn.execute("""
                    SELECT
                        COALESCE(SUM(input_tokens), 0),
                        COALESCE(SUM(output_tokens), 0),
                        COALESCE(SUM(cache_creation_tokens), 0),
                        COALESCE(SUM(cache_read_tokens), 0),
                        COALESCE(SUM(total_tokens), 0),
                        COALESCE(SUM(total_cost), 0),
                        COUNT(*) as active_days,
                        COALESCE(SUM(request_count), 0)
                    FROM daily_usage WHERE date >= ?
                """, (start_date,)).fetchone()
            else:
                row = conn.execute("""
                    SELECT
                        COALESCE(SUM(input_tokens), 0),
                        COALESCE(SUM(output_tokens), 0),
                        COALESCE(SUM(cache_creation_tokens), 0),
                        COALESCE(SUM(cache_read_tokens), 0),
                        COALESCE(SUM(total_tokens), 0),
                        COALESCE(SUM(total_cost), 0),
                        COUNT(*) as active_days,
                        COALESCE(SUM(request_count), 0)
                    FROM daily_usage
                """).fetchone()

            # 获取模型数
            models_count = self._count_unique_models(conn, start_date, end_date)

            # Get coverage Data
            coverage = self.get_coverage()

            return {
                'input_tokens': row[0],
                'output_tokens': row[1],
                'cache_creation_tokens': row[2],
                'cache_read_tokens': row[3],
                'total_tokens': row[4],
                'total_cost': round(row[5], 4),
                'active_days': row[6],
                'models_count': models_count,
                'total_requests': row[7],  # 使用查询结果中的 request_count
                'request_count': row[7],   # 同时提供 request_count 字段
                'coverage': coverage,
            }

    def _count_unique_models(self, conn, start_date=None, end_date=None) -> int:
        """统计唯一模型数"""
        if start_date and end_date:
            rows = conn.execute(
                "SELECT models_used FROM daily_usage WHERE date >= ? AND date <= ?",
                (start_date, end_date)
            ).fetchall()
        elif start_date:
            rows = conn.execute(
                "SELECT models_used FROM daily_usage WHERE date >= ?",
                (start_date,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT models_used FROM daily_usage").fetchall()

        all_models = set()
        for row in rows:
            models = json.loads(row[0])
            all_models.update(models)
        return len(all_models)

    def _row_to_daily_dict(self, row) -> Dict:
        """将数据库行转为字典"""
        return {
            'date': row['date'],
            'input_tokens': row['input_tokens'],
            'output_tokens': row['output_tokens'],
            'cache_creation_tokens': row['cache_creation_tokens'],
            'cache_read_tokens': row['cache_read_tokens'],
            'total_tokens': row['total_tokens'],
            'total_cost': round(row['total_cost'], 4),
            'models_used': json.loads(row['models_used']),
            'model_breakdowns': json.loads(row['model_breakdowns']),
            'request_count': row['request_count'] if 'request_count' in row.keys() else 0,
        }

    def _row_to_hourly_dict(self, row) -> Dict:
        """将数据库行转为字典"""
        result = {
            'hour': row['hour'],
            'input_tokens': row['input_tokens'],
            'output_tokens': row['output_tokens'],
            'cache_creation_tokens': row['cache_creation_tokens'],
            'cache_read_tokens': row['cache_read_tokens'],
            'total_tokens': row['total_tokens'],
            'total_cost': round(row['total_cost'], 4),
            'models_used': json.loads(row['models_used']),
            'request_count': row['request_count'] if 'request_count' in row.keys() else 0,
        }
        try:
            result['model_breakdowns'] = json.loads(row['model_breakdowns'])
        except (KeyError, IndexError):
            result['model_breakdowns'] = []
        return result

    def save_coverage(self, coverage: Dict[str, Any]):
        """Save coverage Data"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO cache_meta (key, value) VALUES (?, ?)",
                ('coverage', json.dumps(coverage))
            )
            conn.commit()

    def get_coverage(self) -> Dict[str, Any]:
        """Get coverage Data"""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT value FROM cache_meta WHERE key = 'coverage'"
            ).fetchone()
            if row:
                return json.loads(row[0])
            return {
                'coverage_percent': 100.0,
                'total_tokens': 0,
                'priced_tokens': 0,
                'unknown_models': [],
            }

    def has_data(self) -> bool:
        """检查是否有缓存数据"""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("SELECT COUNT(*) FROM daily_usage").fetchone()
            return row[0] > 0

    def clear(self):
        """清空缓存"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM daily_usage")
            conn.execute("DELETE FROM hourly_usage")
            conn.execute("DELETE FROM cache_meta")
            conn.commit()
