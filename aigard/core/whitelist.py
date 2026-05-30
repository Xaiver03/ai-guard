"""
# [CN] 白名单管理模块

# [CN] 管理永不终止的进程白名单，支持：
# [CN] - 进程名白名单（精确匹配）
# [CN] - 命令行关键字白名单（包含匹配）
# [CN] - PID 白名单（临时，运行时动态添加）
"""

import threading
from typing import Dict, List, Set


class WhitelistManager:
    # [CN] """白名单管理器"""

    def __init__(self, config: dict):
        """
        初始化白名单管理器

        Args:
            config: 白名单配置字典，包含 process_names, command_keywords, pids
        """
        self.lock = threading.Lock()

        # [CN] # 从配置加载白名单
        self._process_names: Set[str] = set(
            name.lower() for name in config.get("process_names", [])
        )
        self._command_keywords: Set[str] = set(
            kw.lower() for kw in config.get("command_keywords", [])
        )
        self._pids: Set[int] = set(config.get("pids", []))

    def is_whitelisted(self, process: Dict) -> bool:
        """
        检查进程是否在白名单中

        Args:
            process: 进程信息字典，包含 pid, name, cmdline

        Returns:
            True 如果进程在白名单中，否则 False
        """
        with self.lock:
            pid = process.get("pid")
            name = process.get("name", "").lower()
            cmdline = process.get("cmdline", "").lower()

            # [CN] # 检查 PID 白名单
            if pid in self._pids:
                return True

            # [CN] # 检查进程名白名单（精确匹配）
            if name in self._process_names:
                return True

            # [CN] # 检查命令行关键字白名单（包含匹配）
            for keyword in self._command_keywords:
                if keyword in cmdline:
                    return True

            return False

    def add_process_name(self, name: str) -> bool:
        """
        添加进程名到白名单

        Args:
            name: 进程名

        Returns:
            True 如果添加成功，False 如果已存在
        """
        with self.lock:
            name_lower = name.lower()
            if name_lower in self._process_names:
                return False
            self._process_names.add(name_lower)
            return True

    def remove_process_name(self, name: str) -> bool:
        """
        从白名单移除进程名

        Args:
            name: 进程名

        Returns:
            True 如果移除成功，False 如果不存在
        """
        with self.lock:
            name_lower = name.lower()
            if name_lower not in self._process_names:
                return False
            self._process_names.discard(name_lower)
            return True

    def add_command_keyword(self, keyword: str) -> bool:
        """
        添加命令行关键字到白名单

        Args:
            keyword: 命令行关键字

        Returns:
            True 如果添加成功，False 如果已存在
        """
        with self.lock:
            keyword_lower = keyword.lower()
            if keyword_lower in self._command_keywords:
                return False
            self._command_keywords.add(keyword_lower)
            return True

    def remove_command_keyword(self, keyword: str) -> bool:
        """
        从白名单移除命令行关键字

        Args:
            keyword: 命令行关键字

        Returns:
            True 如果移除成功，False 如果不存在
        """
        with self.lock:
            keyword_lower = keyword.lower()
            if keyword_lower not in self._command_keywords:
                return False
            self._command_keywords.discard(keyword_lower)
            return True

    def add_pid(self, pid: int) -> bool:
        """
        添加 PID 到白名单（临时，重启后失效）

        Args:
            pid: 进程 PID

        Returns:
            True 如果添加成功，False 如果已存在
        """
        with self.lock:
            if pid in self._pids:
                return False
            self._pids.add(pid)
            return True

    def remove_pid(self, pid: int) -> bool:
        """
        从白名单移除 PID

        Args:
            pid: 进程 PID

        Returns:
            True 如果移除成功，False 如果不存在
        """
        with self.lock:
            if pid not in self._pids:
                return False
            self._pids.discard(pid)
            return True

    def get_all(self) -> Dict[str, List]:
        """
        获取所有白名单条目

        Returns:
            包含 process_names, command_keywords, pids 的字典
        """
        with self.lock:
            return {
                "process_names": sorted(self._process_names),
                "command_keywords": sorted(self._command_keywords),
                "pids": sorted(self._pids),
            }

    def clear_pids(self):
        # [CN] """清空所有 PID 白名单（用于重启时清理）"""
        with self.lock:
            self._pids.clear()
