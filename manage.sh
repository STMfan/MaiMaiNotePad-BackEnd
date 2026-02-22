#!/usr/bin/env bash
# ============================================================================
# MaiMaiNotePad 后端管理工具
# ============================================================================
# 一个友好的命令行工具，用于管理后端服务的各种操作
#
# 使用方法：
#   ./manage.sh              # 交互式菜单
#   ./manage.sh start        # 直接启动服务
#   ./manage.sh test         # 运行测试
#   ./manage.sh help         # 查看帮助
# ============================================================================

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# 切换到脚本所在目录（项目根目录）
cd "$(dirname "$0")"

# ============================================================================
# 工具函数
# ============================================================================

# 检查命令是否存在
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# 获取 Python 版本
get_python_version() {
    python --version 2>&1 | awk '{print $2}'
}

# 检查 Python 版本是否满足要求
check_python_version() {
    local version=$(get_python_version)
    local major=$(echo "$version" | cut -d. -f1)
    local minor=$(echo "$version" | cut -d. -f2)
    
    if [ "$major" -ge 3 ] && [ "$minor" -ge 11 ]; then
        return 0
    else
        return 1
    fi
}

# 创建虚拟环境
create_virtual_environment() {
    print_header "创建 Python 虚拟环境"
    
    echo "请选择虚拟环境类型："
    echo "  1. Conda 环境（推荐）"
    echo "  2. venv 环境（Python 内置）"
    echo "  3. uv 环境（快速，需要安装 uv）"
    echo "  0. 返回"
    echo ""
    
    read -p "$(echo -e ${CYAN}请选择 [0-3]: ${NC})" choice
    
    case $choice in
        1)
            create_conda_env
            ;;
        2)
            create_venv_env
            ;;
        3)
            create_uv_env
            ;;
        0)
            return
            ;;
        *)
            print_error "无效的选择"
            pause
            ;;
    esac
}

# 创建 Conda 环境
create_conda_env() {
    print_header "创建 Conda 环境"
    
    # 检查 conda 是否安装
    if ! command_exists conda; then
        print_error "未检测到 Conda"
        echo ""
        print_info "Conda 是一个强大的包管理器和环境管理器"
        print_info "推荐安装 Miniconda 或 Anaconda"
        echo ""
        print_info "下载地址："
        print_info "  Miniconda: https://docs.conda.io/en/latest/miniconda.html"
        print_info "  Anaconda: https://www.anaconda.com/download"
        echo ""
        read -p "$(echo -e ${YELLOW}是否使用其他方式创建环境？[y/N]: ${NC})" use_other
        if [ "$use_other" = "y" ] || [ "$use_other" = "Y" ]; then
            create_virtual_environment
        fi
        return
    fi
    
    # 获取环境名称
    echo ""
    read -p "$(echo -e ${CYAN}环境名称 [mai_notebook]: ${NC})" env_name
    env_name=${env_name:-mai_notebook}
    
    # 检查环境是否已存在
    if conda env list | grep -q "^${env_name} "; then
        print_warning "环境 '$env_name' 已存在"
        read -p "$(echo -e ${YELLOW}是否删除并重新创建？[y/N]: ${NC})" recreate
        if [ "$recreate" = "y" ] || [ "$recreate" = "Y" ]; then
            print_info "删除现有环境..."
            conda env remove -n "$env_name" -y
        else
            print_info "已取消操作"
            pause
            return
        fi
    fi
    
    # 选择 Python 版本
    echo ""
    echo "选择 Python 版本："
    echo "  1. Python 3.13 (最新)"
    echo "  2. Python 3.12"
    echo "  3. Python 3.11 (最低要求)"
    echo ""
    read -p "$(echo -e ${CYAN}请选择 [1-3, 默认 1]: ${NC})" py_choice
    py_choice=${py_choice:-1}
    
    case $py_choice in
        1) py_version="3.13" ;;
        2) py_version="3.12" ;;
        3) py_version="3.11" ;;
        *) py_version="3.13" ;;
    esac
    
    # 创建环境
    echo ""
    print_info "创建 Conda 环境: $env_name (Python $py_version)"
    print_separator
    echo ""
    
    conda create -n "$env_name" python="$py_version" -y
    
    echo ""
    print_success "Conda 环境创建成功！"
    echo ""
    print_info "激活环境："
    print_info "  conda activate $env_name"
    echo ""
    print_info "安装依赖："
    print_info "  pip install -r requirements.txt"
    echo ""
    
    read -p "$(echo -e ${YELLOW}是否现在安装依赖？[y/N]: ${NC})" install_deps
    if [ "$install_deps" = "y" ] || [ "$install_deps" = "Y" ]; then
        print_info "激活环境并安装依赖..."
        eval "$(conda shell.bash hook)"
        conda activate "$env_name"
        pip install -r requirements.txt
        print_success "依赖安装完成！"
    fi
    
    pause
}

# 创建 venv 环境
create_venv_env() {
    print_header "创建 venv 环境"
    
    # 检查 Python 版本
    local py_version=$(get_python_version)
    print_info "当前 Python 版本: $py_version"
    
    if ! check_python_version; then
        print_error "Python 版本过低，需要 Python 3.11+"
        print_info "请升级 Python 或使用 Conda 创建指定版本的环境"
        pause
        return
    fi
    
    # 获取环境目录
    echo ""
    read -p "$(echo -e ${CYAN}环境目录名称 [.venv]: ${NC})" env_dir
    env_dir=${env_dir:-.venv}
    
    # 检查目录是否已存在
    if [ -d "$env_dir" ]; then
        print_warning "目录 '$env_dir' 已存在"
        read -p "$(echo -e ${YELLOW}是否删除并重新创建？[y/N]: ${NC})" recreate
        if [ "$recreate" = "y" ] || [ "$recreate" = "Y" ]; then
            print_info "删除现有目录..."
            rm -rf "$env_dir"
        else
            print_info "已取消操作"
            pause
            return
        fi
    fi
    
    # 创建环境
    echo ""
    print_info "创建 venv 环境: $env_dir (Python $py_version)"
    print_separator
    echo ""
    
    python -m venv "$env_dir"
    
    echo ""
    print_success "venv 环境创建成功！"
    echo ""
    print_info "激活环境："
    if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
        print_info "  $env_dir\\Scripts\\activate"
    else
        print_info "  source $env_dir/bin/activate"
    fi
    echo ""
    print_info "安装依赖："
    print_info "  pip install -r requirements.txt"
    echo ""
    
    read -p "$(echo -e ${YELLOW}是否现在安装依赖？[y/N]: ${NC})" install_deps
    if [ "$install_deps" = "y" ] || [ "$install_deps" = "Y" ]; then
        print_info "激活环境并安装依赖..."
        source "$env_dir/bin/activate"
        pip install -r requirements.txt
        print_success "依赖安装完成！"
    fi
    
    pause
}

# 创建 uv 环境
create_uv_env() {
    print_header "创建 uv 环境"
    
    # 检查 uv 是否安装
    if ! command_exists uv; then
        print_warning "未检测到 uv"
        echo ""
        print_info "uv 是一个极快的 Python 包管理器"
        print_info "官网: https://docs.astral.sh/uv/"
        echo ""
        read -p "$(echo -e ${YELLOW}是否安装 uv？[y/N]: ${NC})" install_uv
        
        if [ "$install_uv" = "y" ] || [ "$install_uv" = "Y" ]; then
            print_info "安装 uv..."
            if command_exists curl; then
                curl -LsSf https://astral.sh/uv/install.sh | sh
            elif command_exists wget; then
                wget -qO- https://astral.sh/uv/install.sh | sh
            else
                print_error "需要 curl 或 wget 来安装 uv"
                print_info "请手动安装: https://docs.astral.sh/uv/getting-started/installation/"
                pause
                return
            fi
            
            # 重新加载 PATH
            export PATH="$HOME/.cargo/bin:$PATH"
            
            if ! command_exists uv; then
                print_error "uv 安装失败"
                print_info "请手动安装: https://docs.astral.sh/uv/getting-started/installation/"
                pause
                return
            fi
            
            print_success "uv 安装成功！"
        else
            print_info "已取消操作"
            pause
            return
        fi
    fi
    
    # 检查 Python 版本
    local py_version=$(get_python_version)
    print_info "当前 Python 版本: $py_version"
    
    # 获取环境目录
    echo ""
    read -p "$(echo -e ${CYAN}环境目录名称 [.venv]: ${NC})" env_dir
    env_dir=${env_dir:-.venv}
    
    # 检查目录是否已存在
    if [ -d "$env_dir" ]; then
        print_warning "目录 '$env_dir' 已存在"
        read -p "$(echo -e ${YELLOW}是否删除并重新创建？[y/N]: ${NC})" recreate
        if [ "$recreate" = "y" ] || [ "$recreate" = "Y" ]; then
            print_info "删除现有目录..."
            rm -rf "$env_dir"
        else
            print_info "已取消操作"
            pause
            return
        fi
    fi
    
    # 选择 Python 版本
    echo ""
    echo "选择 Python 版本："
    echo "  1. Python 3.13 (最新)"
    echo "  2. Python 3.12"
    echo "  3. Python 3.11 (最低要求)"
    echo "  4. 使用系统 Python ($py_version)"
    echo ""
    read -p "$(echo -e ${CYAN}请选择 [1-4, 默认 4]: ${NC})" py_choice
    py_choice=${py_choice:-4}
    
    case $py_choice in
        1) py_version="3.13" ;;
        2) py_version="3.12" ;;
        3) py_version="3.11" ;;
        4) py_version="" ;;
        *) py_version="" ;;
    esac
    
    # 创建环境
    echo ""
    if [ -n "$py_version" ]; then
        print_info "创建 uv 环境: $env_dir (Python $py_version)"
        print_separator
        echo ""
        uv venv "$env_dir" --python "$py_version"
    else
        print_info "创建 uv 环境: $env_dir (使用系统 Python)"
        print_separator
        echo ""
        uv venv "$env_dir"
    fi
    
    echo ""
    print_success "uv 环境创建成功！"
    echo ""
    print_info "激活环境："
    if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
        print_info "  $env_dir\\Scripts\\activate"
    else
        print_info "  source $env_dir/bin/activate"
    fi
    echo ""
    print_info "使用 uv 安装依赖（推荐，更快）："
    print_info "  uv pip install -r requirements.txt"
    echo ""
    print_info "或使用 pip 安装依赖："
    print_info "  pip install -r requirements.txt"
    echo ""
    
    read -p "$(echo -e ${YELLOW}是否现在使用 uv 安装依赖？[y/N]: ${NC})" install_deps
    if [ "$install_deps" = "y" ] || [ "$install_deps" = "Y" ]; then
        print_info "激活环境并安装依赖..."
        source "$env_dir/bin/activate"
        uv pip install -r requirements.txt
        print_success "依赖安装完成！"
    fi
    
    pause
}

# 检查 Python 环境
check_python_environment() {
    local required_env="$1"
    local current_env=""
    
    # 检查是否在 conda 环境中
    if [ -n "$CONDA_DEFAULT_ENV" ]; then
        current_env="$CONDA_DEFAULT_ENV"
        
        if [ -n "$required_env" ] && [ "$current_env" != "$required_env" ]; then
            print_warning "当前 Conda 环境: $current_env"
            print_warning "推荐使用环境: $required_env"
            echo ""
            read -p "$(echo -e ${YELLOW}是否继续？[y/N]: ${NC})" confirm
            if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
                print_info "已取消操作"
                print_info "请使用以下命令切换环境："
                print_info "  conda activate $required_env"
                return 1
            fi
        else
            print_success "Conda 环境: $current_env"
        fi
    else
        print_warning "未检测到 Conda 环境"
        if [ -n "$required_env" ]; then
            print_info "推荐使用 Conda 环境: $required_env"
            echo ""
            read -p "$(echo -e ${YELLOW}是否继续？[y/N]: ${NC})" confirm
            if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
                print_info "已取消操作"
                return 1
            fi
        fi
    fi
    
    # 检查 Python 版本
    local python_version=$(python --version 2>&1 | awk '{print $2}')
    print_info "Python 版本: $python_version"
    
    # 检查关键依赖
    print_info "检查关键依赖..."
    local missing_deps=()
    
    if ! python -c "import pytest" 2>/dev/null; then
        missing_deps+=("pytest")
    fi
    
    if ! python -c "import xdist" 2>/dev/null; then
        missing_deps+=("pytest-xdist")
    fi
    
    if ! python -c "import fastapi" 2>/dev/null; then
        missing_deps+=("fastapi")
    fi
    
    if [ ${#missing_deps[@]} -gt 0 ]; then
        print_error "缺少以下依赖: ${missing_deps[*]}"
        print_info "请运行以下命令安装依赖："
        print_info "  pip install -r requirements.txt"
        return 1
    fi
    
    print_success "所有关键依赖已安装"
    return 0
}

# 加载测试配置
load_test_config() {
    local config_file="tests/.test_env"
    
    if [ ! -f "$config_file" ]; then
        print_warning "测试配置文件不存在: $config_file"
        return 1
    fi
    
    # 读取配置
    TEST_PARALLEL=$(grep "^TEST_PARALLEL=" "$config_file" | cut -d'=' -f2)
    TEST_WORKERS=$(grep "^TEST_WORKERS=" "$config_file" | cut -d'=' -f2)
    TEST_EXTRA_ARGS=$(grep "^TEST_EXTRA_ARGS=" "$config_file" | cut -d'=' -f2)
    RECOMMENDED_CONDA_ENV=$(grep "^RECOMMENDED_CONDA_ENV=" "$config_file" | cut -d'=' -f2)
    
    # 设置默认值
    TEST_PARALLEL=${TEST_PARALLEL:-true}
    TEST_WORKERS=${TEST_WORKERS:-auto}
    TEST_EXTRA_ARGS=${TEST_EXTRA_ARGS:-}
    RECOMMENDED_CONDA_ENV=${RECOMMENDED_CONDA_ENV:-}
}

# 构建 pytest 命令
build_pytest_command() {
    local base_cmd="pytest"
    local args=""
    
    # 加载配置
    load_test_config
    
    # 添加并行参数
    if [ "$TEST_PARALLEL" = "true" ]; then
        args="$args -n $TEST_WORKERS"
        print_info "并行测试: 启用 (工作进程: $TEST_WORKERS)"
    else
        print_info "并行测试: 禁用"
    fi
    
    # 添加额外参数
    if [ -n "$TEST_EXTRA_ARGS" ]; then
        args="$args $TEST_EXTRA_ARGS"
    fi
    
    echo "$base_cmd $args"
}

print_header() {
    echo ""
    echo -e "${BLUE}============================================================================${NC}"
    echo -e "${BOLD}${CYAN}$1${NC}"
    echo -e "${BLUE}============================================================================${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC}  $1"
}

print_info() {
    echo -e "${CYAN}ℹ${NC}  $1"
}

print_separator() {
    echo -e "${BLUE}────────────────────────────────────────────────────────────────────────────${NC}"
}

pause() {
    echo ""
    read -p "$(echo -e ${CYAN}按回车继续...${NC})"
}

# ============================================================================
# 功能函数
# ============================================================================

start_dev_server() {
    print_header "启动开发服务器"
    echo ""
    read -p "$(echo -e ${CYAN}主机地址 [0.0.0.0]: ${NC})" host
    host=${host:-0.0.0.0}
    
    read -p "$(echo -e ${CYAN}端口 [9278]: ${NC})" port
    port=${port:-9278}
    
    echo ""
    print_info "模式: 开发模式（自动重载）"
    print_info "主机: $host"
    print_info "端口: $port"
    
    # 显示访问地址
    if [ "$host" = "0.0.0.0" ]; then
        print_info "访问地址: http://localhost:$port 或 http://127.0.0.1:$port"
    else
        print_info "访问地址: http://$host:$port"
    fi
    print_info "API 文档: http://localhost:$port/docs"
    echo ""
    
    print_info "按 Ctrl+C 停止服务"
    echo ""
    print_separator
    echo ""
    
    python -m uvicorn app.main:app \
        --host "$host" \
        --port "$port" \
        --reload \
        --reload-dir app \
        --log-level info
}

start_prod_server() {
    print_header "启动生产服务器"
    echo ""
    read -p "$(echo -e ${CYAN}主机地址 [0.0.0.0]: ${NC})" host
    host=${host:-0.0.0.0}
    
    read -p "$(echo -e ${CYAN}端口 [9278]: ${NC})" port
    port=${port:-9278}
    
    read -p "$(echo -e ${CYAN}工作进程数 [4]: ${NC})" workers
    workers=${workers:-4}
    
    echo ""
    print_info "模式: 生产模式（多进程）"
    print_info "主机: $host"
    print_info "端口: $port"
    print_info "工作进程: $workers"
    
    # 显示访问地址
    if [ "$host" = "0.0.0.0" ]; then
        print_info "访问地址: http://localhost:$port 或 http://127.0.0.1:$port"
    else
        print_info "访问地址: http://$host:$port"
    fi
    echo ""
    
    print_info "按 Ctrl+C 停止服务"
    echo ""
    print_separator
    echo ""
    
    python -m uvicorn app.main:app \
        --host "$host" \
        --port "$port" \
        --workers "$workers" \
        --log-level info \
        --access-log \
        --no-use-colors
}

run_all_tests() {
    print_header "运行所有测试"
    
    # 加载配置
    load_test_config
    
    # 检查环境
    echo ""
    if ! check_python_environment "$RECOMMENDED_CONDA_ENV"; then
        pause
        return 1
    fi
    
    echo ""
    print_separator
    echo ""
    
    # 构建并执行命令
    local cmd=$(build_pytest_command)
    print_info "执行命令: $cmd"
    echo ""
    
    eval "$cmd"
    pause
}

run_unit_tests() {
    print_header "运行单元测试"
    
    # 加载配置
    load_test_config
    
    # 检查环境
    echo ""
    if ! check_python_environment "$RECOMMENDED_CONDA_ENV"; then
        pause
        return 1
    fi
    
    echo ""
    print_separator
    echo ""
    
    # 构建并执行命令
    local cmd=$(build_pytest_command)
    print_info "执行命令: $cmd -m unit"
    echo ""
    
    eval "$cmd -m unit"
    pause
}

run_integration_tests() {
    print_header "运行集成测试"
    
    # 加载配置
    load_test_config
    
    # 检查环境
    echo ""
    if ! check_python_environment "$RECOMMENDED_CONDA_ENV"; then
        pause
        return 1
    fi
    
    echo ""
    print_separator
    echo ""
    
    # 构建并执行命令
    local cmd=$(build_pytest_command)
    print_info "执行命令: $cmd -m integration"
    echo ""
    
    eval "$cmd -m integration"
    pause
}

run_fast_tests() {
    print_header "运行快速测试（排除慢速测试）"
    
    # 加载配置
    load_test_config
    
    # 检查环境
    echo ""
    if ! check_python_environment "$RECOMMENDED_CONDA_ENV"; then
        pause
        return 1
    fi
    
    echo ""
    print_separator
    echo ""
    
    # 构建并执行命令
    local cmd=$(build_pytest_command)
    print_info "执行命令: $cmd -m 'not slow'"
    echo ""
    
    eval "$cmd -m 'not slow'"
    pause
}

run_coverage_tests() {
    print_header "生成测试覆盖率报告"
    
    # 加载配置
    load_test_config
    
    # 检查环境
    echo ""
    if ! check_python_environment "$RECOMMENDED_CONDA_ENV"; then
        pause
        return 1
    fi
    
    echo ""
    print_separator
    echo ""
    
    # 构建并执行命令（覆盖率测试使用配置中的参数）
    local cmd=$(build_pytest_command)
    print_info "执行命令: $cmd"
    echo ""
    
    eval "$cmd"
    echo ""
    print_success "覆盖率报告已生成"
    print_info "查看 HTML 报告: open htmlcov/index.html"
    pause
}

cleanup_project() {
    print_header "清理项目"
    
    print_info "清理 Python 缓存..."
    find . -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name '*.pyc' -delete 2>/dev/null || true
    find . -type f -name '*.pyo' -delete 2>/dev/null || true
    
    print_info "清理测试缓存..."
    rm -rf .pytest_cache .hypothesis htmlcov .coverage coverage.json 2>/dev/null || true
    
    print_info "清理系统临时文件..."
    find . -type f -name '.DS_Store' -delete 2>/dev/null || true
    find . -type f -name '*~' -delete 2>/dev/null || true
    find . -type f -name '*.swp' -delete 2>/dev/null || true
    
    echo ""
    print_success "项目清理完成"
    pause
}

database_menu() {
    while true; do
        print_header "数据库管理"
        echo "  1. 查看当前版本"
        echo "  2. 升级到最新版本"
        echo "  3. 降级一个版本"
        echo "  4. 查看迁移历史"
        echo "  5. 生成新的迁移"
        echo "  0. 返回主菜单"
        echo ""
        
        read -p "$(echo -e ${CYAN}请选择操作 [0-5]: ${NC})" choice
        
        case $choice in
            0)
                break
                ;;
            1)
                echo ""
                print_info "查看当前版本..."
                ./scripts/shell/alembic.sh current
                pause
                ;;
            2)
                echo ""
                print_info "升级数据库到最新版本..."
                ./scripts/shell/alembic.sh upgrade head
                print_success "数据库升级完成"
                pause
                ;;
            3)
                echo ""
                print_warning "确认降级数据库？"
                read -p "$(echo -e ${YELLOW}输入 y 确认: ${NC})" confirm
                if [ "$confirm" = "y" ]; then
                    ./scripts/shell/alembic.sh downgrade -1
                    print_success "数据库降级完成"
                else
                    print_info "已取消操作"
                fi
                pause
                ;;
            4)
                echo ""
                print_info "查看迁移历史..."
                ./scripts/shell/alembic.sh history
                pause
                ;;
            5)
                echo ""
                read -p "$(echo -e ${CYAN}迁移说明: ${NC})" message
                if [ -n "$message" ]; then
                    ./scripts/shell/alembic.sh revision --autogenerate -m "$message"
                    print_success "迁移文件生成完成"
                else
                    print_error "迁移说明不能为空"
                fi
                pause
                ;;
            *)
                print_error "无效的选择"
                pause
                ;;
        esac
    done
}

code_quality_menu() {
    while true; do
        print_header "代码质量检查"
        echo "  1. 运行所有检查（格式化 + Lint）"
        echo "  2. 代码格式化（Black）"
        echo "  3. 代码风格检查（Flake8）"
        echo "  4. 仅检查格式（不修改）"
        echo "  0. 返回主菜单"
        echo ""
        print_warning "注意：类型检查（Mypy）已暂时禁用，需要修复 SQLAlchemy 类型问题"
        echo ""
        
        read -p "$(echo -e ${CYAN}请选择操作 [0-4]: ${NC})" choice
        
        case $choice in
            0)
                break
                ;;
            1)
                echo ""
                print_info "运行代码格式化..."
                black app tests scripts/python
                echo ""
                print_info "运行代码风格检查..."
                flake8 app tests scripts/python
                echo ""
                print_success "所有检查完成"
                pause
                ;;
            2)
                echo ""
                print_info "格式化代码..."
                black app tests scripts/python
                print_success "代码格式化完成"
                pause
                ;;
            3)
                echo ""
                print_info "检查代码风格..."
                flake8 app tests scripts/python
                print_success "代码风格检查完成"
                pause
                ;;
            4)
                echo ""
                print_info "检查代码格式（不修改）..."
                black --check --diff app tests scripts/python
                pause
                ;;
            *)
                print_error "无效的选择"
                pause
                ;;
        esac
    done
}

generate_docs() {
    print_header "生成文档"
    echo "  1. 生成错误码文档"
    echo "  2. 生成测试模板"
    echo "  0. 返回"
    echo ""
    
    read -p "$(echo -e ${CYAN}请选择 [0-2]: ${NC})" choice
    
    case $choice in
        1)
            echo ""
            print_info "生成错误码文档..."
            python scripts/python/generate_error_codes_doc.py
            print_success "错误码文档生成完成"
            pause
            ;;
        2)
            echo ""
            print_info "首先需要生成覆盖率报告..."
            pytest --cov=app --cov-report=json --cov-report=term-missing
            echo ""
            print_info "生成测试模板..."
            python scripts/python/generate_test_templates.py
            print_success "测试模板生成完成"
            pause
            ;;
        0)
            ;;
        *)
            print_error "无效的选择"
            pause
            ;;
    esac
}

reset_environment() {
    print_header "清档重置"
    print_warning "此操作将："
    echo "  • 重新生成所有安全密钥"
    echo "  • 删除并重新创建数据库"
    echo "  • 清空所有上传文件"
    echo "  • 清空所有日志文件"
    echo ""
    print_error "⚠️  此操作不可撤销！"
    echo ""
    
    read -p "$(echo -e ${YELLOW}确认执行清档操作？请输入 'RESET' 确认: ${NC})" confirm
    
    if [ "$confirm" = "RESET" ]; then
        echo ""
        python scripts/python/reset_security_env.py
    else
        print_info "已取消操作"
    fi
    pause
}

show_help() {
    print_header "MaiMaiNotePad 后端管理工具 - 帮助"
    
    echo -e "${BOLD}用法:${NC}"
    echo "  ./manage.sh [命令] [选项]"
    echo ""
    
    echo -e "${BOLD}命令:${NC}"
    echo "  create-env      创建虚拟环境（Conda/venv/uv）"
    echo "  start-dev       启动开发服务器（交互式配置）"
    echo "  start-prod      启动生产服务器（交互式配置）"
    echo "  test            运行所有测试"
    echo "  test-unit       运行单元测试"
    echo "  test-int        运行集成测试"
    echo "  test-cov        生成测试覆盖率报告"
    echo "  test-env        检查测试环境和配置"
    echo "  cleanup         清理项目缓存和临时文件"
    echo "  lint            运行代码质量检查（格式化 + Lint + 类型检查）"
    echo "  format          格式化代码（Black）"
    echo "  db-upgrade      升级数据库到最新版本"
    echo "  db-current      查看当前数据库版本"
    echo "  docs-errors     生成错误码文档"
    echo "  help            显示此帮助信息"
    echo ""
    
    echo -e "${BOLD}示例:${NC}"
    echo "  ./manage.sh                # 交互式菜单"
    echo "  ./manage.sh create-env     # 创建虚拟环境"
    echo "  ./manage.sh start-dev      # 启动开发服务器（会提示输入主机和端口）"
    echo "  ./manage.sh start-prod     # 启动生产服务器（会提示输入配置）"
    echo "  ./manage.sh test           # 运行所有测试"
    echo "  ./manage.sh test-env       # 检查测试环境"
    echo "  ./manage.sh cleanup        # 清理项目"
    echo ""
    
    echo -e "${BOLD}虚拟环境:${NC}"
    echo "  支持三种虚拟环境类型："
    echo "    • Conda 环境（推荐）- 可指定 Python 版本"
    echo "    • venv 环境 - Python 内置，使用系统 Python"
    echo "    • uv 环境 - 极快的包管理器，可指定 Python 版本"
    echo ""
    
    echo -e "${BOLD}测试配置:${NC}"
    echo "  测试配置文件位于: tests/.test_env"
    echo "  可配置项："
    echo "    TEST_PARALLEL=true/false     # 是否启用并行测试"
    echo "    TEST_WORKERS=auto/数字       # 并行工作进程数"
    echo "    RECOMMENDED_CONDA_ENV=名称   # 推荐的 Conda 环境"
    echo ""
    
    echo -e "${BOLD}说明:${NC}"
    echo "  • 主机地址默认为 0.0.0.0（监听所有网络接口）"
    echo "  • 端口默认为 9278"
    echo "  • 生产模式默认使用 4 个工作进程"
    echo "  • 测试前会自动检查 Python 环境和依赖"
    echo ""
}

show_menu() {
    clear
    print_header "MaiMaiNotePad 后端管理工具"
    
    echo -e "${BOLD}${MAGENTA}环境管理${NC}"
    echo "  1. 创建虚拟环境"
    echo ""
    
    echo -e "${BOLD}${MAGENTA}服务管理${NC}"
    echo "  2. 启动服务（开发模式）"
    echo "  3. 启动服务（生产模式）"
    echo ""
    
    echo -e "${BOLD}${MAGENTA}测试相关${NC}"
    echo "  4. 运行所有测试"
    echo "  5. 运行单元测试"
    echo "  6. 运行集成测试"
    echo "  7. 运行快速测试（排除慢速）"
    echo "  8. 生成测试覆盖率报告"
    echo ""
    
    echo -e "${BOLD}${MAGENTA}项目维护${NC}"
    echo "  9. 清理项目（缓存、临时文件）"
    echo " 10. 数据库管理"
    echo " 11. 代码质量检查"
    echo " 12. 生成文档"
    echo ""
    
    echo -e "${BOLD}${MAGENTA}高级操作${NC}"
    echo -e " 13. 清档重置（${RED}⚠️  危险操作${NC}）"
    echo ""
    
    echo -e "${BOLD}${MAGENTA}其他${NC}"
    echo "  h. 查看帮助"
    echo "  0. 退出"
    echo ""
    print_separator
}

# ============================================================================
# 主程序
# ============================================================================

# 如果有命令行参数，直接执行对应命令
if [ $# -gt 0 ]; then
    case "$1" in
        create-env)
            create_virtual_environment
            ;;
        start-dev)
            start_dev_server
            ;;
        start-prod)
            start_prod_server
            ;;
        test)
            load_test_config
            echo ""
            if check_python_environment "$RECOMMENDED_CONDA_ENV"; then
                echo ""
                cmd=$(build_pytest_command)
                print_info "执行命令: $cmd"
                echo ""
                eval "$cmd"
            fi
            ;;
        test-unit)
            load_test_config
            echo ""
            if check_python_environment "$RECOMMENDED_CONDA_ENV"; then
                echo ""
                cmd=$(build_pytest_command)
                print_info "执行命令: $cmd -m unit"
                echo ""
                eval "$cmd -m unit"
            fi
            ;;
        test-int)
            load_test_config
            echo ""
            if check_python_environment "$RECOMMENDED_CONDA_ENV"; then
                echo ""
                cmd=$(build_pytest_command)
                print_info "执行命令: $cmd -m integration"
                echo ""
                eval "$cmd -m integration"
            fi
            ;;
        test-fast)
            load_test_config
            echo ""
            if check_python_environment "$RECOMMENDED_CONDA_ENV"; then
                echo ""
                cmd=$(build_pytest_command)
                print_info "执行命令: $cmd -m 'not slow'"
                echo ""
                eval "$cmd -m 'not slow'"
            fi
            ;;
        test-cov)
            load_test_config
            echo ""
            if check_python_environment "$RECOMMENDED_CONDA_ENV"; then
                echo ""
                cmd=$(build_pytest_command)
                print_info "执行命令: $cmd"
                echo ""
                eval "$cmd"
                echo ""
                print_success "覆盖率报告已生成"
                print_info "查看 HTML 报告: open htmlcov/index.html"
            fi
            ;;
        test-env)
            print_header "检查测试环境"
            load_test_config
            echo ""
            check_python_environment "$RECOMMENDED_CONDA_ENV"
            echo ""
            print_info "测试配置:"
            print_info "  并行测试: $TEST_PARALLEL"
            print_info "  工作进程: $TEST_WORKERS"
            if [ -n "$TEST_EXTRA_ARGS" ]; then
                print_info "  额外参数: $TEST_EXTRA_ARGS"
            fi
            if [ -n "$RECOMMENDED_CONDA_ENV" ]; then
                print_info "  推荐环境: $RECOMMENDED_CONDA_ENV"
            fi
            ;;
        cleanup)
            cleanup_project
            ;;
        lint)
            print_header "代码质量检查"
            echo ""
            print_info "运行代码格式化..."
            black app tests scripts/python
            echo ""
            print_info "运行代码风格检查..."
            flake8 app tests scripts/python
            echo ""
            print_success "所有检查完成"
            print_warning "注意：类型检查（Mypy）已暂时禁用"
            ;;
        format)
            print_header "代码格式化"
            black app tests scripts/python
            print_success "代码格式化完成"
            ;;
        db-upgrade)
            print_header "升级数据库"
            ./scripts/shell/alembic.sh upgrade head
            print_success "数据库升级完成"
            ;;
        db-current)
            print_header "查看数据库版本"
            ./scripts/shell/alembic.sh current
            ;;
        db-history)
            print_header "查看迁移历史"
            ./scripts/shell/alembic.sh history
            ;;
        docs-errors)
            print_header "生成错误码文档"
            python scripts/python/generate_error_codes_doc.py
            print_success "错误码文档生成完成"
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            print_error "未知命令: $1"
            echo ""
            show_help
            exit 1
            ;;
    esac
    exit 0
fi

# 交互式菜单模式
while true; do
    show_menu
    read -p "$(echo -e ${CYAN}请选择操作 [0-13/h]: ${NC})" choice
    
    case $choice in
        0)
            echo ""
            print_info "再见！"
            exit 0
            ;;
        1)
            create_virtual_environment
            ;;
        2)
            start_dev_server
            ;;
        3)
            start_prod_server
            ;;
        4)
            run_all_tests
            ;;
        5)
            run_unit_tests
            ;;
        6)
            run_integration_tests
            ;;
        7)
            run_fast_tests
            ;;
        8)
            run_coverage_tests
            ;;
        9)
            cleanup_project
            ;;
        10)
            database_menu
            ;;
        11)
            code_quality_menu
            ;;
        12)
            generate_docs
            ;;
        13)
            reset_environment
            ;;
        h|H)
            show_help
            pause
            ;;
        *)
            print_error "无效的选择，请重试"
            pause
            ;;
    esac
done
