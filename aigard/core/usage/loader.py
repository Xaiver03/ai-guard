"""
Claude 数据加载器 - 从 JSONL 文件加载使用数据
"""
import json
import os
from pathlib import Path
from datetime import datetime
from typing import List, Optional
from .models import UsageEntry, SessionSummary


class ClaudeDataLoader:
    """加载 Claude Code 的使用数据"""

    def __init__(self, claude_dir: Optional[str] = None):
        """
        初始化数据加载器

        Args:
            claude_dir: Claude 数据目录，默认为 ~/.claude
        """
        if claude_dir is None:
            claude_dir = os.path.expanduser("~/.claude")
        self.claude_dir = Path(claude_dir)
        self.projects_dir = self.claude_dir / "projects"

    def load_all_usage(self) -> List[UsageEntry]:
        """
        加载所有项目的使用数据

        Returns:
            所有使用记录的列表
        """
        all_entries = []

        if not self.projects_dir.exists():
            return all_entries

        # 遍历所有项目目录
        for project_dir in self.projects_dir.iterdir():
            if not project_dir.is_dir():
                continue

            project_name = project_dir.name

            # 遍历项目中的所有 JSONL 文件
            for jsonl_file in project_dir.glob("*.jsonl"):
                session_id = jsonl_file.stem
                entries = self._load_session_file(jsonl_file, project_name, session_id)
                all_entries.extend(entries)

        # 按时间排序
        all_entries.sort(key=lambda x: x.timestamp)

        return all_entries

    def load_project_usage(self, project_name: str) -> List[UsageEntry]:
        """
        加载指定项目的使用数据

        Args:
            project_name: 项目名称

        Returns:
            该项目的所有使用记录
        """
        project_dir = self.projects_dir / project_name
        if not project_dir.exists():
            return []

        all_entries = []
        for jsonl_file in project_dir.glob("*.jsonl"):
            session_id = jsonl_file.stem
            entries = self._load_session_file(jsonl_file, project_name, session_id)
            all_entries.extend(entries)

        all_entries.sort(key=lambda x: x.timestamp)
        return all_entries

    def _load_session_file(self, file_path: Path, project_name: str, session_id: str) -> List[UsageEntry]:
        """
        加载单个会话文件

        Args:
            file_path: JSONL 文件路径
            project_name: 项目名称
            session_id: 会话 ID

        Returns:
            该会话的所有使用记录
        """
        entries = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        data = json.loads(line)
                        entry = self._parse_usage_entry(data, project_name, session_id)
                        if entry:
                            entries.append(entry)
                    except json.JSONDecodeError as e:
                        # 跳过无效的 JSON 行
                        continue
                    except Exception as e:
                        # 跳过解析失败的行
                        continue
        except Exception as e:
            # 跳过无法读取的文件
            pass

        return entries

    def _parse_usage_entry(self, data: dict, project_name: str, session_id: str) -> Optional[UsageEntry]:
        """
        解析单条使用记录

        Claude Code 的 JSONL 格式：
        - type: "assistant" 的记录包含 message.usage 和 message.model
        - usage 字段包含 input_tokens, output_tokens, cache_creation_input_tokens, cache_read_input_tokens

        Args:
            data: JSON 数据
            project_name: 项目名称
            session_id: 会话 ID

        Returns:
            UsageEntry 对象，如果不包含 usage 数据则返回 None
        """
        # 只处理 assistant 类型（包含 usage 数据）
        if data.get('type') != 'assistant':
            return None

        message = data.get('message', {})
        usage = message.get('usage')
        if not usage:
            return None

        try:
            timestamp = self._parse_timestamp(data.get('timestamp'))
            model = message.get('model', 'unknown')

            # Token 数据
            input_tokens = usage.get('input_tokens', 0)
            output_tokens = usage.get('output_tokens', 0)
            cache_creation_tokens = usage.get('cache_creation_input_tokens', 0)
            cache_read_tokens = usage.get('cache_read_input_tokens', 0)

            # 费用（JSONL 中通常没有预计算的费用）
            cost = data.get('costUSD', 0.0)

            return UsageEntry(
                timestamp=timestamp,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cache_creation_tokens=cache_creation_tokens,
                cache_read_tokens=cache_read_tokens,
                cost=cost,
                project=project_name,
                session_id=session_id
            )
        except Exception:
            return None

    def _parse_timestamp(self, timestamp_str: Optional[str]) -> datetime:
        """
        解析时间戳

        Args:
            timestamp_str: 时间戳字符串

        Returns:
            datetime 对象
        """
        if not timestamp_str:
            return datetime.now()

        # 尝试多种时间格式
        formats = [
            '%Y-%m-%dT%H:%M:%S.%fZ',
            '%Y-%m-%dT%H:%M:%SZ',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%d %H:%M:%S',
        ]

        for fmt in formats:
            try:
                return datetime.strptime(timestamp_str, fmt)
            except ValueError:
                continue

        # 如果都失败了，返回当前时间
        return datetime.now()

    def get_projects(self) -> List[str]:
        """
        获取所有项目列表

        Returns:
            项目名称列表
        """
        if not self.projects_dir.exists():
            return []

        projects = []
        for project_dir in self.projects_dir.iterdir():
            if project_dir.is_dir():
                projects.append(project_dir.name)

        return sorted(projects)

    def load_session_summaries(self, project: Optional[str] = None) -> List[SessionSummary]:
        """
        加载会话汇总数据

        Args:
            project: 可选的项目名称，如果指定则只加载该项目的会话

        Returns:
            会话汇总列表
        """
        # 加载所有使用记录
        if project:
            entries = self.load_project_usage(project)
        else:
            entries = self.load_all_usage()

        if not entries:
            return []

        # 按 (project, session_id) 分组
        sessions_dict = {}
        for entry in entries:
            key = (entry.project, entry.session_id)
            if key not in sessions_dict:
                sessions_dict[key] = []
            sessions_dict[key].append(entry)

        # 计算每个会话的汇总
        summaries = []
        for (proj, sess_id), sess_entries in sessions_dict.items():
            if not sess_entries:
                continue

            # 按时间排序
            sess_entries.sort(key=lambda x: x.timestamp)

            start_time = sess_entries[0].timestamp
            end_time = sess_entries[-1].timestamp
            duration_seconds = int((end_time - start_time).total_seconds())

            message_count = len(sess_entries)
            total_tokens = sum(
                e.input_tokens + e.output_tokens + e.cache_creation_tokens + e.cache_read_tokens
                for e in sess_entries
            )
            input_tokens = sum(e.input_tokens for e in sess_entries)
            output_tokens = sum(e.output_tokens for e in sess_entries)
            cache_creation_tokens = sum(e.cache_creation_tokens for e in sess_entries)
            cache_read_tokens = sum(e.cache_read_tokens for e in sess_entries)
            total_cost = sum(e.cost for e in sess_entries)
            models_used = list(set(e.model for e in sess_entries))

            summaries.append(SessionSummary(
                session_id=sess_id,
                project=proj,
                start_time=start_time,
                end_time=end_time,
                duration_seconds=duration_seconds,
                message_count=message_count,
                total_tokens=total_tokens,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cache_creation_tokens=cache_creation_tokens,
                cache_read_tokens=cache_read_tokens,
                total_cost=total_cost,
                models_used=models_used,
            ))

        # 按开始时间倒序排列（最新的在前）
        summaries.sort(key=lambda x: x.start_time, reverse=True)

        return summaries

