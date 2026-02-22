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
    pytest
    pause
}

run_unit_tests() {
    print_header "运行单元测试"
    pytest -m unit
    pause
}

run_integration_tests() {
    print_header "运行集成测试"
    pytest -m integration
    pause
}

run_fast_tests() {
    print_header "运行快速测试（排除慢速测试）"
    pytest -m "not slow"
    pause
}

run_coverage_tests() {
    print_header "生成测试覆盖率报告"
    pytest --cov=app --cov-report=html --cov-report=term
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
    echo "  start-dev       启动开发服务器（交互式配置）"
    echo "  start-prod      启动生产服务器（交互式配置）"
    echo "  test            运行所有测试"
    echo "  test-unit       运行单元测试"
    echo "  test-int        运行集成测试"
    echo "  test-cov        生成测试覆盖率报告"
    echo "  cleanup         清理项目缓存和临时文件"
    echo "  db-upgrade      升级数据库到最新版本"
    echo "  db-current      查看当前数据库版本"
    echo "  docs-errors     生成错误码文档"
    echo "  help            显示此帮助信息"
    echo ""
    
    echo -e "${BOLD}示例:${NC}"
    echo "  ./manage.sh                # 交互式菜单"
    echo "  ./manage.sh start-dev      # 启动开发服务器（会提示输入主机和端口）"
    echo "  ./manage.sh start-prod     # 启动生产服务器（会提示输入配置）"
    echo "  ./manage.sh test           # 运行所有测试"
    echo "  ./manage.sh cleanup        # 清理项目"
    echo ""
    
    echo -e "${BOLD}说明:${NC}"
    echo "  • 主机地址默认为 0.0.0.0（监听所有网络接口）"
    echo "  • 端口默认为 9278"
    echo "  • 生产模式默认使用 4 个工作进程"
    echo ""
}

show_menu() {
    clear
    print_header "MaiMaiNotePad 后端管理工具"
    
    echo -e "${BOLD}${MAGENTA}服务管理${NC}"
    echo "  1. 启动服务（开发模式）"
    echo "  2. 启动服务（生产模式）"
    echo ""
    
    echo -e "${BOLD}${MAGENTA}测试相关${NC}"
    echo "  3. 运行所有测试"
    echo "  4. 运行单元测试"
    echo "  5. 运行集成测试"
    echo "  6. 运行快速测试（排除慢速）"
    echo "  7. 生成测试覆盖率报告"
    echo ""
    
    echo -e "${BOLD}${MAGENTA}项目维护${NC}"
    echo "  8. 清理项目（缓存、临时文件）"
    echo "  9. 数据库管理"
    echo " 10. 生成文档"
    echo ""
    
    echo -e "${BOLD}${MAGENTA}高级操作${NC}"
    echo -e " 11. 清档重置（${RED}⚠️  危险操作${NC}）"
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
        start-dev)
            start_dev_server
            ;;
        start-prod)
            start_prod_server
            ;;
        test)
            run_all_tests
            ;;
        test-unit)
            run_unit_tests
            ;;
        test-int)
            run_integration_tests
            ;;
        test-fast)
            run_fast_tests
            ;;
        test-cov)
            run_coverage_tests
            ;;
        cleanup)
            cleanup_project
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
    read -p "$(echo -e ${CYAN}请选择操作 [0-11/h]: ${NC})" choice
    
    case $choice in
        0)
            echo ""
            print_info "再见！"
            exit 0
            ;;
        1)
            start_dev_server
            ;;
        2)
            start_prod_server
            ;;
        3)
            run_all_tests
            ;;
        4)
            run_unit_tests
            ;;
        5)
            run_integration_tests
            ;;
        6)
            run_fast_tests
            ;;
        7)
            run_coverage_tests
            ;;
        8)
            cleanup_project
            ;;
        9)
            database_menu
            ;;
        10)
            generate_docs
            ;;
        11)
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
