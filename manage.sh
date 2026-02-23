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

# 注意：不使用 set -e，以便在错误时可以继续执行或给用户选择

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

# 错误处理函数
handle_error() {
    local exit_code=$1
    local error_msg="$2"
    local continue_prompt="${3:-是否继续？}"
    
    if [ $exit_code -ne 0 ]; then
        echo ""
        print_error "$error_msg"
        echo ""
        read -p "$(echo -e ${YELLOW}$continue_prompt [y/N]: ${NC})" continue_choice
        if [ "$continue_choice" != "y" ] && [ "$continue_choice" != "Y" ]; then
            print_info "操作已取消"
            return 1
        fi
    fi
    return 0
}

# 执行命令并处理错误
execute_with_error_handling() {
    local cmd="$1"
    local error_msg="$2"
    local continue_prompt="${3:-命令执行失败，是否继续？}"
    
    eval "$cmd"
    local exit_code=$?
    
    if [ $exit_code -ne 0 ]; then
        handle_error $exit_code "$error_msg" "$continue_prompt"
        return $?
    fi
    return 0
}

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
    
    if ! conda create -n "$env_name" python="$py_version" -y; then
        print_error "Conda 环境创建失败"
        pause
        return 1
    fi
    
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
        
        if pip install -r requirements.txt; then
            print_success "依赖安装完成！"
        else
            print_error "依赖安装失败"
            print_info "您可以稍后手动安装："
            print_info "  conda activate $env_name"
            print_info "  pip install -r requirements.txt"
        fi
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
    local enable_parallel="${1:-true}"  # 默认启用并行
    
    # 加载配置
    load_test_config
    
    # 添加并行参数
    if [ "$TEST_PARALLEL" = "true" ] && [ "$enable_parallel" = "true" ]; then
        args="$args -n $TEST_WORKERS"
        # 并行测试时禁用 coverage 以避免数据库冲突
        args="$args --no-cov"
        print_info "并行测试: 启用 (工作进程: $TEST_WORKERS)" >&2
        print_info "Coverage: 已禁用（并行模式下）" >&2
    else
        print_info "并行测试: 禁用" >&2
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
    print_header "运行所有测试（并行模式）"
    
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
    
    if eval "$cmd"; then
        echo ""
        print_success "所有测试通过！"
    else
        echo ""
        print_error "部分测试失败"
        print_info "查看上方输出了解详细信息"
    fi
    pause
}

run_all_tests_with_coverage() {
    print_header "完整测试流程（并行测试 + 覆盖率报告）"
    
    # 加载配置
    load_test_config
    
    # 检查环境
    echo ""
    if ! check_python_environment "$RECOMMENDED_CONDA_ENV"; then
        pause
        return 1
    fi
    
    # 第一步：并行测试（快速验证）
    echo ""
    print_separator
    echo ""
    print_info "步骤 1/3: 运行并行测试（快速验证）"
    echo ""
    
    local parallel_cmd=$(build_pytest_command "true")
    print_info "执行命令: $parallel_cmd"
    echo ""
    
    if ! eval "$parallel_cmd"; then
        print_error "并行测试失败，跳过覆盖率测试"
        pause
        return 1
    fi
    
    # 第二步：覆盖率测试（单线程）
    echo ""
    print_separator
    echo ""
    print_info "步骤 2/3: 生成覆盖率报告（单线程模式）"
    echo ""
    
    local coverage_cmd=$(build_pytest_command "false")
    print_info "执行命令: $coverage_cmd"
    echo ""
    
    eval "$coverage_cmd"
    
    # 第三步：清理临时文件
    echo ""
    print_separator
    echo ""
    print_info "步骤 3/3: 清理临时文件"
    echo ""
    
    # 清理损坏的 coverage 文件
    find . -maxdepth 1 -name ".coverage.*" -type f -delete 2>/dev/null || true
    print_success "已清理临时 coverage 文件"
    
    echo ""
    print_success "完整测试流程已完成"
    print_info "查看 HTML 报告: open htmlcov/index.html"
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
    
    # 构建并执行命令，指定单元测试目录
    local cmd=$(build_pytest_command)
    print_info "执行命令: $cmd tests/unit"
    echo ""
    
    if eval "$cmd tests/unit"; then
        echo ""
        print_success "单元测试通过！"
    else
        echo ""
        print_error "部分单元测试失败"
        print_info "查看上方输出了解详细信息"
    fi
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
    
    # 构建并执行命令，指定集成测试目录
    local cmd=$(build_pytest_command)
    print_info "执行命令: $cmd tests/integration"
    echo ""
    
    if eval "$cmd tests/integration"; then
        echo ""
        print_success "集成测试通过！"
    else
        echo ""
        print_error "部分集成测试失败"
        print_info "查看上方输出了解详细信息"
    fi
    pause
}

run_fast_tests() {
    print_header "运行详细模式测试"
    
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
    
    # 构建并执行命令，添加详细输出
    local cmd=$(build_pytest_command)
    print_info "执行命令: $cmd -vv"
    print_info "详细模式: 显示每个测试的完整信息"
    echo ""
    
    if eval "$cmd -vv"; then
        echo ""
        print_success "测试通过！"
    else
        echo ""
        print_error "部分测试失败"
        print_info "查看上方输出了解详细信息"
    fi
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
    
    # 覆盖率测试必须在单线程模式下运行以避免数据库冲突
    print_info "覆盖率测试: 单线程模式（避免数据冲突）"
    local cmd=$(build_pytest_command "false")  # 禁用并行
    print_info "执行命令: $cmd"
    echo ""
    
    if eval "$cmd"; then
        echo ""
        print_success "覆盖率报告已生成"
        print_info "查看 HTML 报告: open htmlcov/index.html"
    else
        echo ""
        print_error "测试执行失败"
        print_info "覆盖率报告可能不完整"
    fi
    pause
}

cleanup_project() {
    print_header "清理项目"
    
    print_info "清理 Python 缓存..."
    find . -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name '*.pyc' -delete 2>/dev/null || true
    find . -type f -name '*.pyo' -delete 2>/dev/null || true
    rm -rf .mypy_cache 2>/dev/null || true
    
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
        echo "  1. 运行所有检查（格式化 + Lint + 类型检查）"
        echo "  2. 代码格式化（Black）"
        echo "  3. 代码风格检查（Flake8）"
        echo "  4. 类型检查（Mypy）"
        echo "  5. 仅检查格式（不修改）"
        echo "  0. 返回主菜单"
        echo ""
        
        read -p "$(echo -e ${CYAN}请选择操作 [0-5]: ${NC})" choice
        
        case $choice in
            0)
                break
                ;;
            1)
                echo ""
                print_info "运行代码格式化..."
                if black app tests scripts/python; then
                    print_success "代码格式化完成"
                else
                    print_error "代码格式化失败"
                fi
                echo ""
                print_info "运行代码风格检查..."
                if flake8 app tests scripts/python; then
                    print_success "代码风格检查通过"
                else
                    print_warning "发现代码风格问题"
                fi
                echo ""
                print_info "运行类型检查..."
                if mypy app --config-file=pyproject.toml; then
                    print_success "类型检查通过"
                else
                    print_warning "发现类型问题"
                fi
                echo ""
                print_success "所有检查完成"
                pause
                ;;
            2)
                echo ""
                print_info "格式化代码..."
                echo ""
                if black app tests scripts/python; then
                    echo ""
                    print_success "代码格式化完成"
                else
                    echo ""
                    print_error "代码格式化失败"
                fi
                pause
                ;;
            3)
                echo ""
                print_info "检查代码风格..."
                if flake8 app tests scripts/python; then
                    print_success "代码风格检查通过"
                else
                    print_warning "发现代码风格问题，请查看上方输出"
                fi
                pause
                ;;
            4)
                echo ""
                print_info "运行类型检查..."
                if mypy app --config-file=pyproject.toml; then
                    print_success "类型检查通过"
                else
                    print_warning "发现类型问题，请查看上方输出"
                fi
                pause
                ;;
            5)
                echo ""
                print_info "检查代码格式（不修改）..."
                if black --check --diff app tests scripts/python; then
                    print_success "代码格式符合规范"
                else
                    print_warning "代码格式需要调整，请运行格式化"
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

# Docker 管理
docker_management() {
    while true; do
        print_header "Docker 管理"
        
        # 检查 Docker 是否安装
        if ! command_exists docker; then
            print_error "未检测到 Docker"
            print_info "请先安装 Docker: https://docs.docker.com/get-docker/"
            pause
            return
        fi
        
        # 检查 docker-compose 是否安装
        if ! command_exists docker-compose && ! docker compose version >/dev/null 2>&1; then
            print_error "未检测到 docker-compose"
            print_info "请先安装 docker-compose"
            pause
            return
        fi
        
        echo "  1. 启动 Redis 服务"
        echo "  2. 停止 Redis 服务"
        echo "  3. 重启 Redis 服务"
        echo "  4. 查看 Redis 状态"
        echo "  5. 查看 Redis 日志"
        echo "  6. 测试 Redis 连接"
        echo "  0. 返回主菜单"
        echo ""
        
        read -p "$(echo -e ${CYAN}请选择操作 [0-6]: ${NC})" choice
        
        case $choice in
            0)
                break
                ;;
            1)
                echo ""
                print_info "启动 Redis 服务..."
                cd docker
                if docker-compose up -d redis 2>/dev/null || docker compose up -d redis; then
                    print_success "Redis 服务已启动"
                else
                    print_error "Redis 服务启动失败"
                fi
                cd ..
                pause
                ;;
            2)
                echo ""
                print_info "停止 Redis 服务..."
                cd docker
                if docker-compose stop redis 2>/dev/null || docker compose stop redis; then
                    print_success "Redis 服务已停止"
                else
                    print_error "Redis 服务停止失败"
                fi
                cd ..
                pause
                ;;
            3)
                echo ""
                print_info "重启 Redis 服务..."
                cd docker
                if docker-compose restart redis 2>/dev/null || docker compose restart redis; then
                    print_success "Redis 服务已重启"
                else
                    print_error "Redis 服务重启失败"
                fi
                cd ..
                pause
                ;;
            4)
                echo ""
                print_info "查看 Redis 状态..."
                cd docker
                docker-compose ps redis 2>/dev/null || docker compose ps redis
                cd ..
                pause
                ;;
            5)
                echo ""
                print_info "查看 Redis 日志（最近 50 行）..."
                print_info "按 Ctrl+C 退出"
                echo ""
                cd docker
                docker-compose logs --tail=50 -f redis 2>/dev/null || docker compose logs --tail=50 -f redis
                cd ..
                ;;
            6)
                echo ""
                print_info "测试 Redis 连接..."
                if docker exec maimnp-redis redis-cli ping >/dev/null 2>&1; then
                    print_success "Redis 连接正常 (PONG)"
                else
                    print_error "Redis 连接失败"
                    print_info "请确保 Redis 服务已启动"
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

# 初始化超级管理员
init_superadmin() {
    print_header "初始化超级管理员"
    
    echo ""
    print_warning "此操作将创建或重置超级管理员账号"
    echo ""
    
    read -p "$(echo -e ${YELLOW}是否继续？[y/N]: ${NC})" confirm
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        print_info "已取消操作"
        pause
        return
    fi
    
    echo ""
    print_info "正在初始化超级管理员..."
    echo ""
    
    if python scripts/python/init_superadmin.py; then
        echo ""
        print_success "超级管理员初始化完成"
    else
        echo ""
        print_error "超级管理员初始化失败"
    fi
    pause
}

# 配置管理
config_management() {
    while true; do
        print_header "配置管理"
        
        # 获取当前配置环境
        local current_env="${CONFIG_ENV:-dev}"
        echo -e "${BOLD}${CYAN}当前配置环境${NC}"
        case $current_env in
            dev)
                print_info "环境: 开发环境 (dev)"
                print_info "文件: configs/config.dev.toml"
                ;;
            prod)
                print_info "环境: 生产环境 (prod)"
                print_info "文件: configs/config.prod.toml"
                ;;
            degraded)
                print_info "环境: 降级模式 (degraded)"
                print_info "文件: configs/config.degraded.toml"
                ;;
            *)
                print_warning "环境: 未知 ($current_env)"
                ;;
        esac
        echo ""
        
        echo "  1. 切换到开发环境 (dev)"
        echo "  2. 切换到生产环境 (prod)"
        echo "  3. 切换到降级模式 (degraded)"
        echo "  4. 查看当前配置文件内容"
        echo "  5. 查看所有配置文件"
        echo "  6. 验证配置文件"
        echo "  0. 返回主菜单"
        echo ""
        
        read -p "$(echo -e ${CYAN}请选择操作 [0-6]: ${NC})" choice
        
        case $choice in
            0)
                break
                ;;
            1)
                echo ""
                print_info "切换到开发环境..."
                export CONFIG_ENV=dev
                print_success "已切换到开发环境 (dev)"
                print_info "配置文件: configs/config.dev.toml"
                print_info "重启服务后生效"
                pause
                ;;
            2)
                echo ""
                print_warning "切换到生产环境"
                print_warning "请确保已正确配置所有环境变量"
                echo ""
                read -p "$(echo -e ${YELLOW}是否继续？[y/N]: ${NC})" confirm
                if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
                    export CONFIG_ENV=prod
                    print_success "已切换到生产环境 (prod)"
                    print_info "配置文件: configs/config.prod.toml"
                    print_info "重启服务后生效"
                else
                    print_info "已取消操作"
                fi
                pause
                ;;
            3)
                echo ""
                print_info "切换到降级模式..."
                print_warning "降级模式将禁用缓存，所有请求直接访问数据库"
                echo ""
                read -p "$(echo -e ${YELLOW}是否继续？[y/N]: ${NC})" confirm
                if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
                    export CONFIG_ENV=degraded
                    print_success "已切换到降级模式 (degraded)"
                    print_info "配置文件: configs/config.degraded.toml"
                    print_info "重启服务后生效"
                else
                    print_info "已取消操作"
                fi
                pause
                ;;
            4)
                echo ""
                local config_file="configs/config.${current_env}.toml"
                if [ -f "$config_file" ]; then
                    print_info "查看配置文件: $config_file"
                    echo ""
                    print_separator
                    cat "$config_file"
                    print_separator
                else
                    print_error "配置文件不存在: $config_file"
                fi
                pause
                ;;
            5)
                echo ""
                print_info "所有配置文件："
                echo ""
                ls -lh configs/*.toml 2>/dev/null || print_warning "未找到配置文件"
                pause
                ;;
            6)
                echo ""
                print_info "验证配置文件..."
                local has_error=0
                
                for env in dev prod degraded; do
                    local file="configs/config.${env}.toml"
                    if [ -f "$file" ]; then
                        if python -c "import toml; toml.load(open('$file'))" 2>/dev/null; then
                            print_success "$file: 格式正确"
                        else
                            print_error "$file: 格式错误"
                            has_error=1
                        fi
                    else
                        print_warning "$file: 文件不存在"
                    fi
                done
                
                echo ""
                if [ $has_error -eq 0 ]; then
                    print_success "所有配置文件验证通过"
                else
                    print_error "部分配置文件验证失败"
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

# 配置管理
config_management() {
    while true; do
        print_header "配置管理"
        
        # 获取当前配置环境
        local current_env="${CONFIG_ENV:-dev}"
        echo -e "${BOLD}${CYAN}当前配置环境${NC}"
        case $current_env in
            dev)
                print_info "环境: 开发环境 (dev)"
                print_info "文件: configs/config.dev.toml"
                ;;
            prod)
                print_info "环境: 生产环境 (prod)"
                print_info "文件: configs/config.prod.toml"
                ;;
            degraded)
                print_info "环境: 降级模式 (degraded)"
                print_info "文件: configs/config.degraded.toml"
                ;;
            *)
                print_warning "环境: 未知 ($current_env)"
                ;;
        esac
        echo ""
        
        echo "  1. 切换到开发环境 (dev)"
        echo "  2. 切换到生产环境 (prod)"
        echo "  3. 切换到降级模式 (degraded)"
        echo "  4. 查看当前配置文件内容"
        echo "  5. 查看所有配置文件"
        echo "  6. 验证配置文件"
        echo "  0. 返回主菜单"
        echo ""
        
        read -p "$(echo -e ${CYAN}请选择操作 [0-6]: ${NC})" choice
        
        case $choice in
            0)
                break
                ;;
            1)
                echo ""
                print_info "切换到开发环境..."
                export CONFIG_ENV=dev
                print_success "已切换到开发环境 (dev)"
                print_info "配置文件: configs/config.dev.toml"
                print_info "重启服务后生效"
                pause
                ;;
            2)
                echo ""
                print_warning "切换到生产环境"
                print_warning "请确保已正确配置所有环境变量"
                echo ""
                read -p "$(echo -e ${YELLOW}是否继续？[y/N]: ${NC})" confirm
                if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
                    export CONFIG_ENV=prod
                    print_success "已切换到生产环境 (prod)"
                    print_info "配置文件: configs/config.prod.toml"
                    print_info "重启服务后生效"
                else
                    print_info "已取消操作"
                fi
                pause
                ;;
            3)
                echo ""
                print_info "切换到降级模式..."
                print_warning "降级模式将禁用缓存，所有请求直接访问数据库"
                echo ""
                read -p "$(echo -e ${YELLOW}是否继续？[y/N]: ${NC})" confirm
                if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
                    export CONFIG_ENV=degraded
                    print_success "已切换到降级模式 (degraded)"
                    print_info "配置文件: configs/config.degraded.toml"
                    print_info "重启服务后生效"
                else
                    print_info "已取消操作"
                fi
                pause
                ;;
            4)
                echo ""
                local config_file="configs/config.${current_env}.toml"
                if [ -f "$config_file" ]; then
                    print_info "查看配置文件: $config_file"
                    echo ""
                    print_separator
                    cat "$config_file"
                    print_separator
                else
                    print_error "配置文件不存在: $config_file"
                fi
                pause
                ;;
            5)
                echo ""
                print_info "所有配置文件："
                echo ""
                ls -lh configs/*.toml 2>/dev/null || print_warning "未找到配置文件"
                pause
                ;;
            6)
                echo ""
                print_info "验证配置文件..."
                local has_error=0
                
                for env in dev prod degraded; do
                    local file="configs/config.${env}.toml"
                    if [ -f "$file" ]; then
                        if python -c "import toml; toml.load(open('$file'))" 2>/dev/null; then
                            print_success "$file: 格式正确"
                        else
                            print_error "$file: 格式错误"
                            has_error=1
                        fi
                    else
                        print_warning "$file: 文件不存在"
                    fi
                done
                
                echo ""
                if [ $has_error -eq 0 ]; then
                    print_success "所有配置文件验证通过"
                else
                    print_error "部分配置文件验证失败"
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

# 初始化超级管理员
init_superadmin() {
    print_header "初始化超级管理员"
    
    echo ""
    print_warning "此操作将创建或重置超级管理员账号"
    echo ""
    
    read -p "$(echo -e ${YELLOW}是否继续？[y/N]: ${NC})" confirm
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        print_info "已取消操作"
        pause
        return
    fi
    
    echo ""
    print_info "正在初始化超级管理员..."
    echo ""
    
    if python scripts/python/init_superadmin.py; then
        echo ""
        print_success "超级管理员初始化完成"
    else
        echo ""
        print_error "超级管理员初始化失败"
    fi
    pause
}
show_project_status() {
    print_header "项目状态"
    
    # Python 环境
    echo -e "${BOLD}${CYAN}Python 环境${NC}"
    if [ -n "$CONDA_DEFAULT_ENV" ]; then
        print_success "Conda 环境: $CONDA_DEFAULT_ENV"
    else
        print_info "未使用 Conda 环境"
    fi
    print_info "Python 版本: $(python --version 2>&1 | awk '{print $2}')"
    print_info "Python 路径: $(which python)"
    echo ""
    
    # 关键依赖
    echo -e "${BOLD}${CYAN}关键依赖${NC}"
    local deps_ok=true
    
    if python -c "import fastapi" 2>/dev/null; then
        local fastapi_ver=$(python -c "import fastapi; print(fastapi.__version__)" 2>/dev/null)
        print_success "FastAPI: $fastapi_ver"
    else
        print_error "FastAPI: 未安装"
        deps_ok=false
    fi
    
    if python -c "import pytest" 2>/dev/null; then
        local pytest_ver=$(python -c "import pytest; print(pytest.__version__)" 2>/dev/null)
        print_success "Pytest: $pytest_ver"
    else
        print_error "Pytest: 未安装"
        deps_ok=false
    fi
    
    if python -c "import redis" 2>/dev/null; then
        local redis_ver=$(python -c "import redis; print(redis.__version__)" 2>/dev/null)
        print_success "Redis: $redis_ver"
    else
        print_error "Redis: 未安装"
        deps_ok=false
    fi
    
    if python -c "import sqlalchemy" 2>/dev/null; then
        local sqlalchemy_ver=$(python -c "import sqlalchemy; print(sqlalchemy.__version__)" 2>/dev/null)
        print_success "SQLAlchemy: $sqlalchemy_ver"
    else
        print_error "SQLAlchemy: 未安装"
        deps_ok=false
    fi
    echo ""
    
    # 数据库状态
    echo -e "${BOLD}${CYAN}数据库状态${NC}"
    if [ -f "data/mainnp.db" ]; then
        local db_size=$(du -h data/mainnp.db | awk '{print $1}')
        print_success "数据库文件: data/mainnp.db ($db_size)"
    else
        print_warning "数据库文件不存在"
    fi
    echo ""
    
    # Docker 服务
    echo -e "${BOLD}${CYAN}Docker 服务${NC}"
    if command_exists docker; then
        if docker ps --format '{{.Names}}' | grep -q "maimnp-redis"; then
            print_success "Redis 容器: 运行中"
        else
            print_warning "Redis 容器: 未运行"
        fi
    else
        print_info "Docker: 未安装"
    fi
    echo ""
    
    # 配置文件
    echo -e "${BOLD}${CYAN}配置文件${NC}"
    if [ -f ".env" ]; then
        print_success ".env: 存在"
    else
        print_warning ".env: 不存在"
    fi
    
    if [ -f "configs/config.toml" ]; then
        print_success "config.toml: 存在"
    else
        print_warning "config.toml: 不存在"
    fi
    echo ""
    
    # 总结
    if [ "$deps_ok" = true ]; then
        print_success "所有关键依赖已安装"
    else
        print_warning "部分依赖缺失，请运行: pip install -r requirements.txt"
    fi
    
    pause
}

# 查看日志
view_logs() {
    print_header "查看日志"
    
    if [ ! -d "logs" ] || [ -z "$(ls -A logs 2>/dev/null)" ]; then
        print_warning "日志目录为空"
        pause
        return
    fi
    
    echo "  1. 查看应用日志（最近 50 行）"
    echo "  2. 查看应用日志（实时）"
    echo "  3. 查看所有日志文件"
    echo "  4. 清空日志文件"
    echo "  0. 返回"
    echo ""
    
    read -p "$(echo -e ${CYAN}请选择 [0-4]: ${NC})" choice
    
    case $choice in
        1)
            echo ""
            if [ -f "logs/app.log" ]; then
                print_info "应用日志（最近 50 行）："
                echo ""
                tail -n 50 logs/app.log
            else
                print_warning "日志文件不存在: logs/app.log"
            fi
            pause
            ;;
        2)
            echo ""
            if [ -f "logs/app.log" ]; then
                print_info "实时查看应用日志（按 Ctrl+C 退出）..."
                echo ""
                tail -f logs/app.log
            else
                print_warning "日志文件不存在: logs/app.log"
                pause
            fi
            ;;
        3)
            echo ""
            print_info "所有日志文件："
            echo ""
            ls -lh logs/
            pause
            ;;
        4)
            echo ""
            print_warning "确认清空所有日志文件？"
            read -p "$(echo -e ${YELLOW}输入 y 确认: ${NC})" confirm
            if [ "$confirm" = "y" ]; then
                rm -f logs/*.log
                print_success "日志文件已清空"
            else
                print_info "已取消操作"
            fi
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

# 依赖管理
dependency_management() {
    while true; do
        print_header "依赖管理"
        echo "  1. 安装所有依赖"
        echo "  2. 安装开发依赖"
        echo "  3. 更新依赖"
        echo "  4. 检查依赖状态"
        echo "  5. 导出当前依赖"
        echo "  0. 返回主菜单"
        echo ""
        
        read -p "$(echo -e ${CYAN}请选择操作 [0-5]: ${NC})" choice
        
        case $choice in
            0)
                break
                ;;
            1)
                echo ""
                print_info "安装生产依赖..."
                if pip install -r requirements.txt; then
                    print_success "依赖安装完成"
                else
                    print_error "依赖安装失败"
                fi
                pause
                ;;
            2)
                echo ""
                print_info "安装开发依赖..."
                if pip install -r requirements-dev.txt; then
                    print_success "开发依赖安装完成"
                else
                    print_error "开发依赖安装失败"
                fi
                pause
                ;;
            3)
                echo ""
                print_warning "此操作将更新所有依赖到最新版本"
                read -p "$(echo -e ${YELLOW}是否继续？[y/N]: ${NC})" confirm
                if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
                    print_info "更新依赖..."
                    if pip install --upgrade -r requirements.txt; then
                        print_success "依赖更新完成"
                    else
                        print_error "依赖更新失败"
                    fi
                else
                    print_info "已取消操作"
                fi
                pause
                ;;
            4)
                echo ""
                print_info "检查依赖状态..."
                echo ""
                pip list --format=columns
                pause
                ;;
            5)
                echo ""
                print_info "导出当前依赖到 requirements-freeze.txt..."
                if pip freeze > requirements-freeze.txt; then
                    print_success "依赖已导出到 requirements-freeze.txt"
                else
                    print_error "依赖导出失败"
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
    
    echo -e "${BOLD}环境管理:${NC}"
    echo "  create-env      创建虚拟环境（Conda/venv/uv）"
    echo "  status          查看项目状态（环境、依赖、服务）"
    echo "  deps-install    安装生产依赖"
    echo "  config-show     查看当前配置文件"
    echo "  config-switch   切换配置环境（dev/prod/degraded）"
    echo "  config-validate 验证所有配置文件"
    echo ""
    
    echo -e "${BOLD}服务管理:${NC}"
    echo "  start-dev       启动开发服务器（交互式配置）"
    echo "  start-prod      启动生产服务器（交互式配置）"
    echo "  docker-start    启动 Redis 服务"
    echo "  docker-stop     停止 Redis 服务"
    echo "  docker-status   查看 Redis 状态"
    echo ""
    
    echo -e "${BOLD}测试相关:${NC}"
    echo "  test            运行所有测试"
    echo "  test-unit       运行单元测试"
    echo "  test-int        运行集成测试"
    echo "  test-cov        生成测试覆盖率报告"
    echo "  test-env        检查测试环境和配置"
    echo ""
    
    echo -e "${BOLD}项目维护:${NC}"
    echo "  cleanup         清理项目缓存和临时文件"
    echo "  lint            运行代码质量检查（格式化 + Lint + 类型检查）"
    echo "  format          格式化代码（Black）"
    echo "  logs            查看应用日志"
    echo ""
    
    echo -e "${BOLD}数据库管理:${NC}"
    echo "  db-upgrade      升级数据库到最新版本"
    echo "  db-current      查看当前数据库版本"
    echo "  db-history      查看迁移历史"
    echo ""
    
    echo -e "${BOLD}其他:${NC}"
    echo "  init-admin      初始化超级管理员"
    echo "  docs-errors     生成错误码文档"
    echo "  help            显示此帮助信息"
    echo ""
    
    echo -e "${BOLD}示例:${NC}"
    echo "  ./manage.sh                    # 交互式菜单"
    echo "  ./manage.sh create-env         # 创建虚拟环境"
    echo "  ./manage.sh status             # 查看项目状态"
    echo "  ./manage.sh config-show        # 查看当前配置"
    echo "  ./manage.sh config-switch prod # 切换到生产环境"
    echo "  ./manage.sh docker-start       # 启动 Redis 服务"
    echo "  ./manage.sh test               # 运行所有测试"
    echo "  ./manage.sh init-admin         # 初始化超级管理员"
    echo "  ./manage.sh logs               # 查看应用日志"
    echo ""
    
    echo -e "${BOLD}新功能说明:${NC}"
    echo "  • 配置管理: 支持 dev/prod/degraded 三种配置环境切换"
    echo "  • Docker 管理: 方便地启动/停止 Redis 服务"
    echo "  • 项目状态: 一键查看环境、依赖、服务状态"
    echo "  • 日志查看: 快速查看应用日志"
    echo "  • 依赖管理: 安装、更新、检查依赖"
    echo "  • 超级管理员: 快速初始化管理员账号"
    echo ""
    
    echo -e "${BOLD}配置环境说明:${NC}"
    echo "  通过 CONFIG_ENV 环境变量切换配置："
    echo "    • dev (默认)  - 开发环境，使用 configs/config.dev.toml"
    echo "    • prod        - 生产环境，使用 configs/config.prod.toml"
    echo "    • degraded    - 降级模式，使用 configs/config.degraded.toml（禁用缓存）"
    echo ""
    echo "  切换方式："
    echo "    1. 使用 manage.sh: ./manage.sh config-switch prod"
    echo "    2. 设置环境变量: export CONFIG_ENV=prod"
    echo "    3. 启动时指定: CONFIG_ENV=prod python -m uvicorn app.main:app"
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
}

show_menu() {
    clear
    print_header "MaiMaiNotePad 后端管理工具"
    
    echo -e "${BOLD}${MAGENTA}环境管理${NC}"
    echo "  1. 创建虚拟环境"
    echo "  2. 查看项目状态"
    echo "  3. 依赖管理"
    echo "  4. 配置管理"
    echo ""
    
    echo -e "${BOLD}${MAGENTA}服务管理${NC}"
    echo "  5. 启动服务（开发模式）"
    echo "  6. 启动服务（生产模式）"
    echo "  7. Docker 管理（Redis）"
    echo ""
    
    echo -e "${BOLD}${MAGENTA}测试相关${NC}"
    echo "  8. 运行所有测试（并行，快速验证）"
    echo "  9. 运行单元测试（tests/unit）"
    echo " 10. 运行集成测试（tests/integration）"
    echo " 11. 详细模式测试（-vv，调试用）"
    echo " 12. 生成测试覆盖率报告（单线程，完整报告）"
    echo " 13. 完整测试流程（并行验证 + 覆盖率分析）"
    echo ""
    
    echo -e "${BOLD}${MAGENTA}项目维护${NC}"
    echo " 14. 清理项目（缓存、临时文件）"
    echo " 15. 数据库管理"
    echo " 16. 代码质量检查"
    echo " 17. 生成文档"
    echo " 18. 查看日志"
    echo ""
    
    echo -e "${BOLD}${MAGENTA}高级操作${NC}"
    echo " 19. 初始化超级管理员"
    echo -e " 20. 清档重置（${RED}⚠️  危险操作${NC}）"
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
                if eval "$cmd"; then
                    echo ""
                    print_success "所有测试通过！"
                    exit 0
                else
                    echo ""
                    print_error "部分测试失败"
                    exit 1
                fi
            else
                exit 1
            fi
            ;;
        test-unit)
            load_test_config
            echo ""
            if check_python_environment "$RECOMMENDED_CONDA_ENV"; then
                echo ""
                cmd=$(build_pytest_command)
                print_info "执行命令: $cmd tests/unit"
                echo ""
                if eval "$cmd tests/unit"; then
                    echo ""
                    print_success "单元测试通过！"
                    exit 0
                else
                    echo ""
                    print_error "部分单元测试失败"
                    exit 1
                fi
            else
                exit 1
            fi
            ;;
        test-int)
            load_test_config
            echo ""
            if check_python_environment "$RECOMMENDED_CONDA_ENV"; then
                echo ""
                cmd=$(build_pytest_command)
                print_info "执行命令: $cmd tests/integration"
                echo ""
                if eval "$cmd tests/integration"; then
                    echo ""
                    print_success "集成测试通过！"
                    exit 0
                else
                    echo ""
                    print_error "部分集成测试失败"
                    exit 1
                fi
            else
                exit 1
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
                cmd=$(build_pytest_command "false")
                print_info "执行命令: $cmd"
                echo ""
                if eval "$cmd"; then
                    echo ""
                    print_success "覆盖率报告已生成"
                    print_info "查看 HTML 报告: open htmlcov/index.html"
                    exit 0
                else
                    echo ""
                    print_error "测试执行失败"
                    exit 1
                fi
            else
                exit 1
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
            local has_error=0
            
            print_info "运行代码格式化..."
            if black app tests scripts/python; then
                print_success "代码格式化完成"
            else
                print_error "代码格式化失败"
                has_error=1
            fi
            
            echo ""
            print_info "运行代码风格检查..."
            if flake8 app tests scripts/python; then
                print_success "代码风格检查通过"
            else
                print_warning "发现代码风格问题"
                has_error=1
            fi
            
            echo ""
            print_info "运行类型检查..."
            if mypy app --config-file=pyproject.toml; then
                print_success "类型检查通过"
            else
                print_warning "发现类型问题"
                has_error=1
            fi
            
            echo ""
            if [ $has_error -eq 0 ]; then
                print_success "所有检查通过！"
                exit 0
            else
                print_warning "部分检查未通过，请查看上方输出"
                exit 1
            fi
            ;;
        format)
            print_header "代码格式化"
            if black app tests scripts/python; then
                print_success "代码格式化完成"
                exit 0
            else
                print_error "代码格式化失败"
                exit 1
            fi
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
        docker-start)
            print_header "启动 Redis 服务"
            cd docker
            if docker-compose up -d redis 2>/dev/null || docker compose up -d redis; then
                print_success "Redis 服务已启动"
                exit 0
            else
                print_error "Redis 服务启动失败"
                exit 1
            fi
            ;;
        docker-stop)
            print_header "停止 Redis 服务"
            cd docker
            if docker-compose stop redis 2>/dev/null || docker compose stop redis; then
                print_success "Redis 服务已停止"
                exit 0
            else
                print_error "Redis 服务停止失败"
                exit 1
            fi
            ;;
        docker-status)
            print_header "查看 Redis 状态"
            cd docker
            docker-compose ps redis 2>/dev/null || docker compose ps redis
            ;;
        init-admin)
            print_header "初始化超级管理员"
            python scripts/python/init_superadmin.py
            ;;
        status)
            show_project_status
            ;;
        logs)
            print_header "查看应用日志"
            if [ -f "logs/app.log" ]; then
                tail -n 50 logs/app.log
            else
                print_warning "日志文件不存在: logs/app.log"
            fi
            ;;
        deps-install)
            print_header "安装依赖"
            if pip install -r requirements.txt; then
                print_success "依赖安装完成"
                exit 0
            else
                print_error "依赖安装失败"
                exit 1
            fi
            ;;
        config-show)
            print_header "查看当前配置"
            current_env="${CONFIG_ENV:-dev}"
            echo ""
            print_info "当前配置环境: $current_env"
            print_info "配置文件: configs/config.${current_env}.toml"
            echo ""
            if [ -f "configs/config.${current_env}.toml" ]; then
                cat "configs/config.${current_env}.toml"
            else
                print_error "配置文件不存在"
                exit 1
            fi
            ;;
        config-switch)
            if [ -z "$2" ]; then
                print_error "请指定配置环境: dev, prod, degraded"
                echo ""
                echo "用法: ./manage.sh config-switch <env>"
                echo "示例: ./manage.sh config-switch prod"
                exit 1
            fi
            
            target_env="$2"
            case $target_env in
                dev|prod|degraded)
                    print_header "切换配置环境"
                    export CONFIG_ENV="$target_env"
                    print_success "已切换到 $target_env 环境"
                    print_info "配置文件: configs/config.${target_env}.toml"
                    print_info "请设置环境变量: export CONFIG_ENV=$target_env"
                    print_info "或在启动服务时指定: CONFIG_ENV=$target_env python -m uvicorn app.main:app"
                    ;;
                *)
                    print_error "无效的配置环境: $target_env"
                    print_info "可选值: dev, prod, degraded"
                    exit 1
                    ;;
            esac
            ;;
        config-validate)
            print_header "验证配置文件"
            has_error=0
            
            for env in dev prod degraded; do
                file="configs/config.${env}.toml"
                if [ -f "$file" ]; then
                    if python -c "import toml; toml.load(open('$file'))" 2>/dev/null; then
                        print_success "$file: 格式正确"
                    else
                        print_error "$file: 格式错误"
                        has_error=1
                    fi
                else
                    print_warning "$file: 文件不存在"
                fi
            done
            
            echo ""
            if [ $has_error -eq 0 ]; then
                print_success "所有配置文件验证通过"
                exit 0
            else
                print_error "部分配置文件验证失败"
                exit 1
            fi
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
    read -p "$(echo -e ${CYAN}请选择操作 [0-20/h]: ${NC})" choice
    
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
            show_project_status
            ;;
        3)
            dependency_management
            ;;
        4)
            config_management
            ;;
        5)
            start_dev_server
            ;;
        6)
            start_prod_server
            ;;
        7)
            docker_management
            ;;
        8)
            run_all_tests
            ;;
        9)
            run_unit_tests
            ;;
        10)
            run_integration_tests
            ;;
        11)
            run_fast_tests
            ;;
        12)
            run_coverage_tests
            ;;
        13)
            run_all_tests_with_coverage
            ;;
        14)
            cleanup_project
            ;;
        15)
            database_menu
            ;;
        16)
            code_quality_menu
            ;;
        17)
            generate_docs
            ;;
        18)
            view_logs
            ;;
        19)
            init_superadmin
            ;;
        20)
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
