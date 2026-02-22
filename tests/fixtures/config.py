"""
测试配置加载器

从 .test_env 文件加载测试配置，或回退到 .test_env.template 默认值。
提供配置验证和环境变量管理。
"""

import os
from pathlib import Path
from typing import Dict, Optional


class TestConfig:
    """测试配置管理器

    注意：这不是一个 pytest 测试类，尽管名字以 Test 开头。
    它是一个用于管理测试配置的工具类。
    """

    __test__ = False  # 告诉 pytest 不要收集这个类

    def __init__(self):
        self.config: Dict[str, str] = {}
        self._load_config()

    def _load_config(self):
        """从 .test_env 或 .test_env.template 加载配置"""
        # fixtures 目录的父目录是 tests 目录
        test_dir = Path(__file__).parent.parent
        test_env_path = test_dir / ".test_env"
        template_path = test_dir / ".test_env.template"

        # 首先尝试从 .test_env 加载
        if test_env_path.exists():
            self._parse_env_file(test_env_path)
        # 回退到模板
        elif template_path.exists():
            self._parse_env_file(template_path)
        else:
            # 如果没有文件存在，使用硬编码的默认值
            self._set_defaults()

    def _parse_env_file(self, file_path: Path):
        """解析环境文件并提取键值对"""
        with open(file_path, "r") as f:
            for line in f:
                line = line.strip()
                # 跳过注释和空行
                if not line or line.startswith("#"):
                    continue

                # 解析 key=value 对
                if "=" in line:
                    key, value = line.split("=", 1)
                    self.config[key.strip()] = value.strip()

    def _set_defaults(self):
        """设置默认配置值"""
        self.config = {
            "DATABASE_URL": "sqlite:///./test.db",
            "JWT_SECRET_KEY": "test_secret_key_for_testing_only",
            "BCRYPT_ROUNDS": "4",  # 使用较少的 rounds 加速测试
            "HYPOTHESIS_PROFILE": "dev",
            "TEST_PARALLEL": "true",
        }

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """获取配置值"""
        return self.config.get(key, default)

    def apply_to_environment(self):
        """将配置应用到环境变量"""
        for key, value in self.config.items():
            # 仅在环境中尚未设置时设置
            os.environ.setdefault(key, value)

    def validate(self) -> bool:
        """验证必需的配置值是否存在"""
        required_keys = [
            "DATABASE_URL",
            "JWT_SECRET_KEY",
        ]

        missing_keys = [key for key in required_keys if key not in self.config]

        if missing_keys:
            raise ValueError(f"缺少必需的配置键：{missing_keys}")

        return True


# 全局配置实例
test_config = TestConfig()
test_config.validate()
test_config.apply_to_environment()
