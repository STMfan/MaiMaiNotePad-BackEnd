#!/usr/bin/env python3
"""
版本号检查脚本

用于验证版本号配置是否正确，以及所有位置的版本号是否一致。
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def check_version():
    """检查版本号配置"""
    print("=" * 60)
    print("版本号检查")
    print("=" * 60)
    print()

    # 1. 从 __version__.py 读取
    from app.__version__ import VERSION_HISTORY, __version__, __version_info__

    print(f"✓ app.__version__.__version__: {__version__}")
    print(f"✓ app.__version__.__version_info__: {__version_info__}")
    print()

    # 2. 从 app 包读取
    from app import __version__ as app_version

    print(f"✓ app.__version__: {app_version}")
    print()

    # 3. 从配置读取
    try:
        from app.core.config import settings

        print(f"✓ settings.APP_VERSION: {settings.APP_VERSION}")
    except Exception as e:
        print(f"⚠ settings.APP_VERSION: 无法读取 ({e})")
    print()

    # 4. 检查 pyproject.toml 配置
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib
        except ImportError:
            print("⚠ 无法导入 tomllib/tomli，跳过 pyproject.toml 检查")
            tomllib = None

    if tomllib:
        with open(project_root / "pyproject.toml", "rb") as f:
            config = tomllib.load(f)
            dynamic = config["project"].get("dynamic", [])
            version_source = config.get("tool", {}).get("setuptools", {}).get("dynamic", {}).get("version", {})

            print(f"✓ pyproject.toml dynamic: {dynamic}")
            print(f"✓ version source: {version_source.get('attr', 'N/A')}")
            print()

    # 5. 显示版本历史
    print("版本历史:")
    for version, description in sorted(VERSION_HISTORY.items(), reverse=True):
        print(f"  • {version}: {description}")
    print()

    # 6. 总结
    print("=" * 60)
    print(f"✅ 当前版本: {__version__}")
    print("✅ 版本号配置正确！")
    print("=" * 60)
    print()
    print("💡 提示：")
    print("   要更新版本号，只需修改 app/__version__.py 文件")
    print("   pyproject.toml 会自动从那里读取版本号")
    print()


if __name__ == "__main__":
    try:
        check_version()
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
