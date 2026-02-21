#!/bin/bash
# 清理项目中的临时文件和缓存
# 
# 功能：
# - 清理 Python 缓存文件
# - 清理测试相关文件
# - 清理构建产物
# - 清理编辑器临时文件
# - 清理系统临时文件
# - 清理日志文件
# - 清理覆盖率报告

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 计数器
total_cleaned=0

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 清理函数
clean_items() {
    local description=$1
    shift
    local items=("$@")
    local count=0
    
    print_info "$description"
    
    for item in "${items[@]}"; do
        if [ -e "$item" ] || [ -L "$item" ]; then
            rm -rf "$item" 2>/dev/null && ((count++)) || true
        fi
    done
    
    # 使用 find 命令清理
    if [[ "$description" == *"查找"* ]] || [[ "$description" == *"递归"* ]]; then
        for pattern in "${items[@]}"; do
            if [[ "$pattern" == *"-name"* ]]; then
                eval "find . $pattern -delete 2>/dev/null" && ((count++)) || true
            fi
        done
    fi
    
    if [ $count -gt 0 ]; then
        print_success "  清理了 $count 项"
        ((total_cleaned+=count))
    fi
}

echo ""
echo "🧹 开始清理项目..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ============================================================================
# Python 缓存清理
# ============================================================================
print_info "📦 清理 Python 缓存..."

# __pycache__ 目录
pycache_count=$(find . -type d -name "__pycache__" 2>/dev/null | wc -l | tr -d ' ')
if [ "$pycache_count" -gt 0 ]; then
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    print_success "  清理了 $pycache_count 个 __pycache__ 目录"
    ((total_cleaned+=pycache_count))
fi

# .pyc 文件
pyc_count=$(find . -type f -name "*.pyc" 2>/dev/null | wc -l | tr -d ' ')
if [ "$pyc_count" -gt 0 ]; then
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    print_success "  清理了 $pyc_count 个 .pyc 文件"
    ((total_cleaned+=pyc_count))
fi

# .pyo 文件
pyo_count=$(find . -type f -name "*.pyo" 2>/dev/null | wc -l | tr -d ' ')
if [ "$pyo_count" -gt 0 ]; then
    find . -type f -name "*.pyo" -delete 2>/dev/null || true
    print_success "  清理了 $pyo_count 个 .pyo 文件"
    ((total_cleaned+=pyo_count))
fi

# .pyd 文件（Windows Python 扩展）
pyd_count=$(find . -type f -name "*.pyd" 2>/dev/null | wc -l | tr -d ' ')
if [ "$pyd_count" -gt 0 ]; then
    find . -type f -name "*.pyd" -delete 2>/dev/null || true
    print_success "  清理了 $pyd_count 个 .pyd 文件"
    ((total_cleaned+=pyd_count))
fi

echo ""

# ============================================================================
# 测试相关清理
# ============================================================================
print_info "🧪 清理测试相关文件..."

# pytest 缓存
[ -d ".pytest_cache" ] && rm -rf .pytest_cache && print_success "  清理了 .pytest_cache" && ((total_cleaned++))

# hypothesis 缓存
[ -d ".hypothesis" ] && rm -rf .hypothesis && print_success "  清理了 .hypothesis" && ((total_cleaned++))

# 覆盖率文件
coverage_items=(
    ".coverage"
    ".coverage.*"
    "htmlcov"
    "coverage.xml"
    ".coverage.json"
)
for item in "${coverage_items[@]}"; do
    if [ "$item" == ".coverage.*" ]; then
        count=$(find . -maxdepth 1 -name ".coverage.*" 2>/dev/null | wc -l | tr -d ' ')
        if [ "$count" -gt 0 ]; then
            find . -maxdepth 1 -name ".coverage.*" -delete 2>/dev/null
            print_success "  清理了 $count 个覆盖率文件"
            ((total_cleaned+=count))
        fi
    elif [ -e "$item" ]; then
        rm -rf "$item" && print_success "  清理了 $item" && ((total_cleaned++))
    fi
done

# tox 缓存
[ -d ".tox" ] && rm -rf .tox && print_success "  清理了 .tox" && ((total_cleaned++))

# mypy 缓存
[ -d ".mypy_cache" ] && rm -rf .mypy_cache && print_success "  清理了 .mypy_cache" && ((total_cleaned++))

# ruff 缓存
[ -d ".ruff_cache" ] && rm -rf .ruff_cache && print_success "  清理了 .ruff_cache" && ((total_cleaned++))

# 测试数据库
test_db_count=$(find tests -name "test_*.db*" 2>/dev/null | wc -l | tr -d ' ')
if [ "$test_db_count" -gt 0 ]; then
    find tests -name "test_*.db*" -delete 2>/dev/null
    print_success "  清理了 $test_db_count 个测试数据库文件"
    ((total_cleaned+=test_db_count))
fi

# 测试日志
test_log_items=(
    "tests/tests.log"
    "tests/test_results_*.log"
)
for pattern in "${test_log_items[@]}"; do
    if [[ "$pattern" == *"*"* ]]; then
        count=$(find tests -name "$(basename $pattern)" 2>/dev/null | wc -l | tr -d ' ')
        if [ "$count" -gt 0 ]; then
            find tests -name "$(basename $pattern)" -delete 2>/dev/null
            print_success "  清理了 $count 个测试日志文件"
            ((total_cleaned+=count))
        fi
    elif [ -f "$pattern" ]; then
        rm -f "$pattern" && print_success "  清理了 $pattern" && ((total_cleaned++))
    fi
done

# 临时测试文件
temp_test_count=$(find tests -name "temp_*.py" 2>/dev/null | wc -l | tr -d ' ')
if [ "$temp_test_count" -gt 0 ]; then
    find tests -name "temp_*.py" -delete 2>/dev/null
    print_success "  清理了 $temp_test_count 个临时测试文件"
    ((total_cleaned+=temp_test_count))
fi

# 测试上传目录
[ -d "test_uploads" ] && rm -rf test_uploads && print_success "  清理了 test_uploads" && ((total_cleaned++))

echo ""

# ============================================================================
# 构建产物清理
# ============================================================================
print_info "📦 清理构建产物..."

build_items=(
    "build"
    "dist"
    "*.egg-info"
    ".eggs"
    "*.egg"
)

for item in "${build_items[@]}"; do
    if [[ "$item" == *"*"* ]]; then
        count=$(find . -maxdepth 2 -name "$item" 2>/dev/null | wc -l | tr -d ' ')
        if [ "$count" -gt 0 ]; then
            find . -maxdepth 2 -name "$item" -exec rm -rf {} + 2>/dev/null
            print_success "  清理了 $count 个 $item"
            ((total_cleaned+=count))
        fi
    elif [ -e "$item" ]; then
        rm -rf "$item" && print_success "  清理了 $item" && ((total_cleaned++))
    fi
done

echo ""

# ============================================================================
# 编辑器临时文件清理
# ============================================================================
print_info "📝 清理编辑器临时文件..."

# Vim/Vi 临时文件
vim_count=$(find . -name "*~" -o -name "*.swp" -o -name "*.swo" -o -name "*.swn" 2>/dev/null | wc -l | tr -d ' ')
if [ "$vim_count" -gt 0 ]; then
    find . \( -name "*~" -o -name "*.swp" -o -name "*.swo" -o -name "*.swn" \) -delete 2>/dev/null
    print_success "  清理了 $vim_count 个 Vim 临时文件"
    ((total_cleaned+=vim_count))
fi

# Emacs 临时文件
emacs_count=$(find . -name "#*#" -o -name ".#*" 2>/dev/null | wc -l | tr -d ' ')
if [ "$emacs_count" -gt 0 ]; then
    find . \( -name "#*#" -o -name ".#*" \) -delete 2>/dev/null
    print_success "  清理了 $emacs_count 个 Emacs 临时文件"
    ((total_cleaned+=emacs_count))
fi

# VS Code 临时文件
[ -d ".vscode/.ropeproject" ] && rm -rf .vscode/.ropeproject && print_success "  清理了 .vscode/.ropeproject" && ((total_cleaned++))

# PyCharm 临时文件
[ -d ".idea" ] && print_warning "  发现 .idea 目录（PyCharm 配置），建议添加到 .gitignore"

echo ""

# ============================================================================
# 系统临时文件清理
# ============================================================================
print_info "🖥️  清理系统临时文件..."

# macOS 系统文件
ds_store_count=$(find . -name ".DS_Store" 2>/dev/null | wc -l | tr -d ' ')
if [ "$ds_store_count" -gt 0 ]; then
    find . -name ".DS_Store" -delete 2>/dev/null
    print_success "  清理了 $ds_store_count 个 .DS_Store 文件"
    ((total_cleaned+=ds_store_count))
fi

# macOS 资源分支文件
underscore_count=$(find . -name "._*" 2>/dev/null | wc -l | tr -d ' ')
if [ "$underscore_count" -gt 0 ]; then
    find . -name "._*" -delete 2>/dev/null
    print_success "  清理了 $underscore_count 个 ._ 文件"
    ((total_cleaned+=underscore_count))
fi

# Thumbs.db (Windows)
thumbs_count=$(find . -name "Thumbs.db" 2>/dev/null | wc -l | tr -d ' ')
if [ "$thumbs_count" -gt 0 ]; then
    find . -name "Thumbs.db" -delete 2>/dev/null
    print_success "  清理了 $thumbs_count 个 Thumbs.db 文件"
    ((total_cleaned+=thumbs_count))
fi

# desktop.ini (Windows)
desktop_ini_count=$(find . -name "desktop.ini" 2>/dev/null | wc -l | tr -d ' ')
if [ "$desktop_ini_count" -gt 0 ]; then
    find . -name "desktop.ini" -delete 2>/dev/null
    print_success "  清理了 $desktop_ini_count 个 desktop.ini 文件"
    ((total_cleaned+=desktop_ini_count))
fi

echo ""

# ============================================================================
# 日志文件清理（可选）
# ============================================================================
print_info "📋 检查日志文件..."

if [ -d "logs" ]; then
    log_count=$(find logs -type f -name "*.log" 2>/dev/null | wc -l | tr -d ' ')
    if [ "$log_count" -gt 0 ]; then
        print_warning "  发现 $log_count 个日志文件"
        read -p "$(echo -e ${YELLOW}是否清理日志文件？[y/N]: ${NC})" -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            find logs -type f -name "*.log" -delete 2>/dev/null
            print_success "  清理了 $log_count 个日志文件"
            ((total_cleaned+=log_count))
        else
            print_info "  跳过日志文件清理"
        fi
    fi
fi

echo ""

# ============================================================================
# 其他临时文件清理
# ============================================================================
print_info "🗑️  清理其他临时文件..."

# pip 缓存（可选）
if [ -d "$HOME/.cache/pip" ]; then
    print_warning "  发现 pip 缓存目录"
    read -p "$(echo -e ${YELLOW}是否清理 pip 缓存？[y/N]: ${NC})" -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$HOME/.cache/pip"
        print_success "  清理了 pip 缓存"
        ((total_cleaned++))
    fi
fi

# SQLite 临时文件
sqlite_temp_count=$(find . -name "*.db-journal" -o -name "*.db-wal" -o -name "*.db-shm" 2>/dev/null | wc -l | tr -d ' ')
if [ "$sqlite_temp_count" -gt 0 ]; then
    find . \( -name "*.db-journal" -o -name "*.db-wal" -o -name "*.db-shm" \) -delete 2>/dev/null
    print_success "  清理了 $sqlite_temp_count 个 SQLite 临时文件"
    ((total_cleaned+=sqlite_temp_count))
fi

# 备份文件
backup_count=$(find . -name "*.bak" -o -name "*.backup" -o -name "*.old" 2>/dev/null | wc -l | tr -d ' ')
if [ "$backup_count" -gt 0 ]; then
    print_warning "  发现 $backup_count 个备份文件"
    read -p "$(echo -e ${YELLOW}是否清理备份文件？[y/N]: ${NC})" -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        find . \( -name "*.bak" -o -name "*.backup" -o -name "*.old" \) -delete 2>/dev/null
        print_success "  清理了 $backup_count 个备份文件"
        ((total_cleaned+=backup_count))
    fi
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
print_success "✨ 清理完成！共清理了 $total_cleaned 项"
echo ""
