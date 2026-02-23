"""
配置管理器

统一管理应用配置，支持从 TOML 文件和环境变量加载配置。
优先级：环境变量 > config.toml > 默认值

配置环境切换：
    通过 CONFIG_ENV 环境变量选择配置文件：
    - CONFIG_ENV=dev      -> configs/config.dev.toml (默认)
    - CONFIG_ENV=prod     -> configs/config.prod.toml
    - CONFIG_ENV=degraded -> configs/config.degraded.toml
"""

import os
import toml
from pathlib import Path
from typing import Any, Dict, Optional, List
from functools import lru_cache


class ConfigManager:
    """配置管理器类"""

    def __init__(self, config_file: Optional[str] = None):
        """
        初始化配置管理器

        Args:
            config_file: 配置文件路径，如果为 None 则根据 CONFIG_ENV 环境变量自动选择
                        CONFIG_ENV 可选值: dev, prod, degraded
                        默认使用 dev 配置
        """
        if config_file is None:
            # 从环境变量读取配置环境
            config_env = os.environ.get("CONFIG_ENV", "dev").lower()
            
            # 映射环境到配置文件
            env_to_file = {
                "dev": "configs/config.dev.toml",
                "prod": "configs/config.prod.toml",
                "degraded": "configs/config.degraded.toml",
            }
            
            self.config_file = env_to_file.get(config_env, "configs/config.dev.toml")
            self.config_env = config_env
        else:
            self.config_file = config_file
            self.config_env = "custom"
        
        self._config: Dict[str, Any] = {}
        self._load_config()

    def _load_config(self):
        """加载配置文件"""
        # 尝试从项目根目录加载配置文件
        config_path = Path(self.config_file)

        if not config_path.is_absolute():
            # 如果是相对路径，从项目根目录查找
            # 假设此文件在 app/core/ 目录下
            project_root = Path(__file__).parent.parent.parent
            config_path = project_root / self.config_file

        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    self._config = toml.load(f)
            except Exception as e:
                print(f"警告: 无法加载配置文件 {config_path}: {e}")
                self._config = {}
        else:
            print(f"警告: 配置文件 {config_path} 不存在，使用默认配置")
            self._config = {}

    def get(self, key_path: str, default: Any = None, env_var: Optional[str] = None) -> Any:
        """
        获取配置值

        优先级：环境变量 > config.toml > 默认值

        Args:
            key_path: 配置键路径，使用点号分隔，如 "upload.avatar.max_size_mb"
            default: 默认值
            env_var: 对应的环境变量名，如果提供则优先从环境变量读取

        Returns:
            配置值

        Example:
            >>> config = ConfigManager()
            >>> max_size = config.get("upload.avatar.max_size_mb", default=2)
            >>> jwt_key = config.get("jwt.secret_key", env_var="JWT_SECRET_KEY")
        """
        # 1. 优先从环境变量读取
        if env_var and env_var in os.environ:
            value = os.environ[env_var]
            # 尝试转换类型
            return self._convert_type(value, type(default) if default is not None else str)

        # 2. 从 TOML 配置读取
        keys = key_path.split(".")
        current_value: Any = self._config

        for key in keys:
            if isinstance(current_value, dict) and key in current_value:
                current_value = current_value[key]
            else:
                return default

        return current_value

    def _convert_type(self, value: str, target_type: type) -> Any:
        """
        转换环境变量的字符串值为目标类型

        Args:
            value: 字符串值
            target_type: 目标类型

        Returns:
            转换后的值
        """
        if target_type == bool:
            return value.lower() in ("true", "1", "yes", "on")
        elif target_type == int:
            return int(value)
        elif target_type == float:
            return float(value)
        elif target_type == list:
            # 简单的列表解析，假设用逗号分隔
            return [item.strip() for item in value.split(",")]
        else:
            return value

    def get_int(self, key_path: str, default: int = 0, env_var: Optional[str] = None) -> int:
        """获取整数配置值"""
        value = self.get(key_path, default, env_var)
        return int(value) if value is not None else default

    def get_float(self, key_path: str, default: float = 0.0, env_var: Optional[str] = None) -> float:
        """获取浮点数配置值"""
        value = self.get(key_path, default, env_var)
        return float(value) if value is not None else default

    def get_bool(self, key_path: str, default: bool = False, env_var: Optional[str] = None) -> bool:
        """获取布尔配置值"""
        value = self.get(key_path, default, env_var)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes", "on")
        return bool(value) if value is not None else default

    def get_list(self, key_path: str, default: Optional[List] = None, env_var: Optional[str] = None) -> List:
        """获取列表配置值"""
        if default is None:
            default = []
        value = self.get(key_path, default, env_var)
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            return [item.strip() for item in value.split(",")]
        return default

    def get_section(self, section: str) -> Dict[str, Any]:
        """
        获取整个配置节

        Args:
            section: 配置节名称，如 "upload.avatar"

        Returns:
            配置节字典
        """
        keys = section.split(".")
        value = self._config

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return {}

        return value if isinstance(value, dict) else {}

    def reload(self):
        """重新加载配置文件"""
        self._load_config()

    def get_current_env(self) -> str:
        """
        获取当前配置环境
        
        Returns:
            配置环境名称 (dev/prod/degraded/custom)
        """
        return self.config_env

    def get_config_file_path(self) -> str:
        """
        获取当前使用的配置文件路径
        
        Returns:
            配置文件路径
        """
        return self.config_file


# 全局配置管理器实例（单例模式）
@lru_cache(maxsize=1)
def get_config_manager() -> ConfigManager:
    """获取全局配置管理器实例"""
    return ConfigManager()


# 便捷访问
config_manager = get_config_manager()
