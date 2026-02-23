#!/bin/bash
# ============================================================================
# 缓存配置验证脚本
# 用途：验证缓存配置文件的正确性和合理性
# 使用方法：
#   ./scripts/shell/validate_cache_config.sh [config_file]
# 示例：
#   ./scripts/shell/validate_cache_config.sh configs/config.dev.toml
#   ./scripts/shell/validate_cache_config.sh configs/config.prod.toml
#   ./scripts/shell/validate_cache_config.sh configs/config.degraded.toml
# ============================================================================

set -e  # 遇到错误立即退出

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# 切换到项目根目录
cd "$PROJECT_ROOT"

# 激活 Conda 环境（如果需要）
if command -v conda &> /dev/null; then
    # 检查是否在 Conda 环境中
    if [ -z "$CONDA_DEFAULT_ENV" ]; then
        echo "⚠️  未检测到 Conda 环境，尝试激活 mai_notebook 环境..."
        eval "$(conda shell.bash hook)"
        conda activate mai_notebook 2>/dev/null || echo "⚠️  无法激活 Conda 环境，继续使用系统 Python"
    fi
fi

# 检查 Python 是否可用
if ! command -v python &> /dev/null; then
    echo "❌ 错误: 未找到 Python 解释器"
    exit 1
fi

# 运行验证脚本
python scripts/python/validate_cache_config.py "$@"
