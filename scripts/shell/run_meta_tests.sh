#!/bin/bash
# 运行元测试套件
# 这些测试用于验证测试框架本身的正确性

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}============================================================================${NC}"
echo -e "${BLUE}运行元测试套件${NC}"
echo -e "${BLUE}============================================================================${NC}"
echo ""

echo -e "${YELLOW}⚠️  注意：${NC}"
echo "  - 元测试用于测试测试框架本身，不测试业务逻辑"
echo "  - 这些测试会启动子进程运行并行测试，执行时间较长"
echo "  - 不要在并行模式下运行元测试（会导致嵌套并行）"
echo ""

# 检查是否在虚拟环境中
if [ -z "$CONDA_DEFAULT_ENV" ] && [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${YELLOW}⚠️  警告：未检测到虚拟环境${NC}"
    echo "建议在虚拟环境中运行测试"
    echo ""
fi

# 询问用户要运行哪些测试
echo "请选择要运行的元测试："
echo "  1. 所有元测试"
echo "  2. 并行隔离测试"
echo "  3. 缓存隔离测试"
echo "  4. 事务管理测试"
echo "  5. 外键处理测试"
echo "  6. 依赖注入隔离测试"
echo ""
read -p "请输入选项 [1-6]: " choice

case $choice in
    1)
        echo -e "${GREEN}运行所有元测试...${NC}"
        pytest tests/meta/ -v
        ;;
    2)
        echo -e "${GREEN}运行并行隔离测试...${NC}"
        pytest tests/meta/test_parallel_isolation.py::TestParallelIsolation -v
        ;;
    3)
        echo -e "${GREEN}运行缓存隔离测试...${NC}"
        pytest tests/meta/test_parallel_isolation.py::TestCacheIsolation -v
        ;;
    4)
        echo -e "${GREEN}运行事务管理测试...${NC}"
        pytest tests/meta/test_parallel_isolation.py::TestTransactionManagement -v
        ;;
    5)
        echo -e "${GREEN}运行外键处理测试...${NC}"
        pytest tests/meta/test_parallel_isolation.py::TestForeignKeyHandling -v
        ;;
    6)
        echo -e "${GREEN}运行依赖注入隔离测试...${NC}"
        pytest tests/meta/test_parallel_isolation.py::TestDependencyOverrideIsolation -v
        ;;
    *)
        echo -e "${RED}无效的选项${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${BLUE}============================================================================${NC}"
echo -e "${GREEN}✓ 元测试完成${NC}"
echo -e "${BLUE}============================================================================${NC}"
