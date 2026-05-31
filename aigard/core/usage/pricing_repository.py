"""
定价持久化仓库 - 管理用户自定义定价的数据库读写
"""
import sqlite3
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict
from .pricing import ModelPricing, normalize_model_name


class PricingRepository:
    """管理定价覆盖的 SQLite 持久化"""

    def __init__(self, db_dir: Optional[str] = None):
        if db_dir is None:
            db_dir = os.path.expanduser("~/.aigard")
        os.makedirs(db_dir, exist_ok=True)
        self.db_path = Path(db_dir) / "usage_cache.db"
        self._init_table()

    def _init_table(self):
        """初始化 pricing_overrides 表"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS pricing_overrides (
                    model_name TEXT PRIMARY KEY,
                    input_price REAL NOT NULL,
                    output_price REAL NOT NULL,
                    cache_creation_price REAL NOT NULL,
                    cache_read_price REAL NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.commit()

    def save_override(self, model: str, pricing: ModelPricing):
        """保存单个模型的定价覆盖(upsert)"""
        normalized = normalize_model_name(model)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO pricing_overrides
                (model_name, input_price, output_price, cache_creation_price,
                 cache_read_price, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                normalized,
                pricing.input_price,
                pricing.output_price,
                pricing.cache_creation_price,
                pricing.cache_read_price,
                datetime.now().isoformat()
            ))
            conn.commit()

    def get_override(self, model: str) -> Optional[ModelPricing]:
        """获取单个模型的定价覆盖,不存在返回 None"""
        normalized = normalize_model_name(model)
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT input_price, output_price, cache_creation_price, cache_read_price "
                "FROM pricing_overrides WHERE model_name = ?",
                (normalized,)
            ).fetchone()
            if row:
                return ModelPricing(
                    input_price=row[0],
                    output_price=row[1],
                    cache_creation_price=row[2],
                    cache_read_price=row[3]
                )
            return None

    def get_all_overrides(self) -> Dict[str, ModelPricing]:
        """获取所有定价覆盖"""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT model_name, input_price, output_price, "
                "cache_creation_price, cache_read_price FROM pricing_overrides"
            ).fetchall()
            return {
                row[0]: ModelPricing(
                    input_price=row[1],
                    output_price=row[2],
                    cache_creation_price=row[3],
                    cache_read_price=row[4]
                )
                for row in rows
            }

    def delete_override(self, model: str) -> bool:
        """删除单个模型的定价覆盖,返回是否删除成功"""
        normalized = normalize_model_name(model)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM pricing_overrides WHERE model_name = ?",
                (normalized,)
            )
            conn.commit()
            return cursor.rowcount > 0

    def clear_all_overrides(self):
        """清空所有定价覆盖"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM pricing_overrides")
            conn.commit()

    def get_override_count(self) -> int:
        """获取覆盖数量"""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM pricing_overrides"
            ).fetchone()
            return row[0] if row else 0
