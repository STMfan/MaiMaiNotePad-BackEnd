#!/bin/bash

# ============================================================================
# Docker Redis 测试脚本
# 用途：验证 Docker Compose Redis 配置是否正常工作
# 使用：./scripts/shell/test_docker_redis.sh
# ============================================================================

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 打印函数
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# 检查 Docker 是否安装
check_docker() {
    print_info "检查 Docker 是否安装..."
    if ! command -v docker &> /dev/null; then
        print_error "Docker 未安装，请先安装 Docker"
        exit 1
    fi
    print_info "Docker 版本: $(docker --version)"
}

# 检查 Docker Compose 是否安装
check_docker_compose() {
    print_info "检查 Docker Compose 是否安装..."
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose 未安装，请先安装 Docker Compose"
        exit 1
    fi
    print_info "Docker Compose 版本: $(docker-compose --version)"
}

# 检查配置文件
check_config() {
    print_info "检查配置文件..."
    
    if [ ! -f "docker-compose.yml" ]; then
        print_error "docker-compose.yml 文件不存在"
        exit 1
    fi
    
    if [ ! -f "configs/redis.conf" ]; then
        print_error "configs/redis.conf 文件不存在"
        exit 1
    fi
    
    print_info "配置文件检查通过"
}

# 验证 Docker Compose 配置
validate_compose() {
    print_info "验证 Docker Compose 配置..."
    if docker-compose config --quiet; then
        print_info "Docker Compose 配置验证通过"
    else
        print_error "Docker Compose 配置验证失败"
        exit 1
    fi
}

# 启动 Redis 服务
start_redis() {
    print_info "启动 Redis 服务..."
    docker-compose up -d redis
    
    # 等待服务启动
    print_info "等待 Redis 服务启动（最多 30 秒）..."
    for i in {1..30}; do
        if docker-compose ps redis | grep -q "Up"; then
            print_info "Redis 服务已启动"
            return 0
        fi
        sleep 1
    done
    
    print_error "Redis 服务启动超时"
    docker-compose logs redis
    exit 1
}

# 测试 Redis 连接
test_redis_connection() {
    print_info "测试 Redis 连接..."
    
    # 等待健康检查通过
    print_info "等待健康检查通过（最多 30 秒）..."
    for i in {1..30}; do
        if docker exec maimnp-redis redis-cli --no-auth-warning ping &> /dev/null; then
            print_info "Redis 连接测试通过"
            return 0
        fi
        sleep 1
    done
    
    print_error "Redis 连接测试失败"
    docker-compose logs redis
    exit 1
}

# 测试基本操作
test_redis_operations() {
    print_info "测试 Redis 基本操作..."
    
    # 设置键值
    docker exec maimnp-redis redis-cli --no-auth-warning SET test_key "test_value" > /dev/null
    print_info "SET 操作成功"
    
    # 获取键值
    value=$(docker exec maimnp-redis redis-cli --no-auth-warning GET test_key)
    if [ "$value" = "test_value" ]; then
        print_info "GET 操作成功"
    else
        print_error "GET 操作失败，期望 'test_value'，实际 '$value'"
        exit 1
    fi
    
    # 删除键
    docker exec maimnp-redis redis-cli --no-auth-warning DEL test_key > /dev/null
    print_info "DEL 操作成功"
    
    print_info "Redis 基本操作测试通过"
}

# 查看 Redis 信息
show_redis_info() {
    print_info "Redis 服务信息："
    echo ""
    docker exec maimnp-redis redis-cli --no-auth-warning INFO server | grep -E "redis_version|os|arch_bits|process_id"
    echo ""
    docker exec maimnp-redis redis-cli --no-auth-warning INFO memory | grep -E "used_memory_human|maxmemory_human|maxmemory_policy"
    echo ""
}

# 清理函数
cleanup() {
    print_warning "是否停止 Redis 服务？(y/N)"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        print_info "停止 Redis 服务..."
        docker-compose stop redis
        print_info "Redis 服务已停止"
    else
        print_info "保持 Redis 服务运行"
    fi
}

# 主函数
main() {
    echo "========================================"
    echo "  Docker Redis 配置测试"
    echo "========================================"
    echo ""
    
    check_docker
    check_docker_compose
    check_config
    validate_compose
    start_redis
    test_redis_connection
    test_redis_operations
    show_redis_info
    
    echo ""
    echo "========================================"
    print_info "所有测试通过！✅"
    echo "========================================"
    echo ""
    
    cleanup
}

# 执行主函数
main
