"""
AI ConfigurationReadModule
# [CN] 从 Claude Code 的 settings.json 读取 API 配置
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any


class AIConfig:
    # [CN] """AI 配置管理器,读取 Claude Code 的配置"""

    CLAUDE_SETTINGS_PATH = Path.home() / ".claude" / "settings.json"

    def __init__(self):
        self.api_key: Optional[str] = None
        self.base_url: Optional[str] = None
        self.model: str = "claude-sonnet-4-20250514"  # DefaultModel
        self._load_from_claude_settings()

    def _load_from_claude_settings(self) -> bool:
        """
        从 Claude Code 的 settings.json 读取配置

        Returns:
            是否成功加载配置
        """
        if not self.CLAUDE_SETTINGS_PATH.exists():
            return False

        try:
            with open(self.CLAUDE_SETTINGS_PATH, 'r', encoding='utf-8') as f:
                settings = json.load(f)

            # ReadEnvironmentVariableConfiguration
            env = settings.get("env", {})
            self.api_key = env.get("ANTHROPIC_AUTH_TOKEN")
            self.base_url = env.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com")

            # ReadModelConfiguration
            model_setting = settings.get("model", "")
            if model_setting:
                # [CN] # 处理 "opus[1m]" 这样的格式
                if "opus" in model_setting.lower():
                    self.model = "claude-opus-4-20250514"
                elif "sonnet" in model_setting.lower():
                    self.model = "claude-sonnet-4-20250514"

            return self.api_key is not None

        except Exception as e:
            print(f"Read Claude Code ConfigurationFailure: {e}")
            return False

    def is_configured(self) -> bool:
        # [CN] """检查是否已配置 API"""
        return self.api_key is not None

    def get_headers(self) -> Dict[str, str]:
        """获取 API 请求头"""
        if not self.api_key:
            raise ValueError("API key 未配置")

        return {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }

    def get_api_endpoint(self) -> str:
        # [CN] """获取 API 端点"""
        base = self.base_url or "https://api.anthropic.com"
        return f"{base}/v1/messages"

    def to_dict(self) -> Dict[str, Any]:
        # [CN] """转换为字典(用于 API 响应)"""
        return {
            "configured": self.is_configured(),
            "base_url": self.base_url,
            "model": self.model,
            "has_api_key": self.api_key is not None
        }


# [CN] # 全局配置实例
_config_instance: Optional[AIConfig] = None


def get_ai_config() -> AIConfig:
    # [CN] """获取全局 AI 配置实例"""
    global _config_instance
    if _config_instance is None:
        _config_instance = AIConfig()
    return _config_instance


def reload_ai_config():
    # [CN] """重新加载 AI 配置"""
    global _config_instance
    _config_instance = AIConfig()
    return _config_instance
