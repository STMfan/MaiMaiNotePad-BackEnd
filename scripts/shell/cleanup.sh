#!/bin/bash
# 清理项目中的临时文件和缓存

echo "🧹 开始清理项目..."

# 清理 Python 缓存
echo "清理 Python 缓存..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -delete 2>/dev/null
find . -type f -name "*.pyo" -delete 2>/dev/null

# 清理测试缓存
echo "清理测试缓存..."
rm -rf .pytest_cache 2>/dev/null
rm -rf .hypothesis 2>/dev/null
rm -rf htmlcov 2>/dev/null
rm -rf .coverage 2>/dev/null
rm -rf .tox 2>/dev/null

# 清理测试数据库
echo "清理测试数据库..."
find tests -name "test_*.db*" -delete 2>/dev/null
rm -f tests/test.db* 2>/dev/null

# 清理测试日志
echo "清理测试日志..."
rm -f tests/tests.log 2>/dev/null
rm -f tests/test_results_*.log 2>/dev/null

# 清理临时测试文件
echo "清理临时测试文件..."
find tests -name "temp_*.py" -delete 2>/dev/null

# 清理测试上传目录
echo "清理测试上传目录..."
rm -rf test_uploads 2>/dev/null

# 清理 macOS 系统文件
echo "清理 macOS 系统文件..."
find . -name ".DS_Store" -delete 2>/dev/null

# 清理临时文件
echo "清理临时文件..."
find . -name "*~" -delete 2>/dev/null
find . -name "*.swp" -delete 2>/dev/null
find . -name "*.swo" -delete 2>/dev/null

echo "✨ 清理完成！"
